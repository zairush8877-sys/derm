"""Заявки на анализы: запись, список, отмена.

Пока без онлайн-интеграции с лабораториями: заявка сохраняется со статусом
"new", менеджер связывается по телефону и подтверждает время/адрес.
Статусы: new → confirmed → done | canceled.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from app.db import store
from app.lab.catalog import get_panel
from app.notifications import service as notifications

_PHONE_RE = re.compile(r"^\+?[0-9\s\-()]{10,18}$")


class BookingError(ValueError):
    """Некорректные данные заявки."""


def book(
    user_id: str,
    panel_id: str,
    city: str,
    phone: str,
    preferred_date: str = "",
    comment: str = "",
) -> dict:
    panel = get_panel(panel_id)
    if panel is None:
        raise BookingError("Неизвестная панель анализов")
    city = city.strip()
    if not city:
        raise BookingError("Укажите город — подберём ближайшую лабораторию")
    phone = phone.strip()
    if not _PHONE_RE.match(phone):
        raise BookingError("Укажите телефон для подтверждения записи")

    booking_id = uuid.uuid4().hex[:12]
    with store.connect() as conn:
        conn.execute(
            "INSERT INTO lab_bookings (id, user_id, panel_id, city, phone, "
            "preferred_date, comment, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'new', ?)",
            (booking_id, user_id, panel_id, city, phone,
             preferred_date.strip(), comment.strip(),
             datetime.now(timezone.utc).isoformat()),
        )
    notifications.push(
        user_id,
        "Заявка на анализы принята",
        f"«{panel.name}» ({panel.price_rub} ₽), город {city}. "
        "Менеджер позвонит, чтобы подтвердить лабораторию и время.",
    )
    return get_booking(booking_id)


def get_booking(booking_id: str) -> dict:
    with store.connect() as conn:
        row = conn.execute(
            "SELECT * FROM lab_bookings WHERE id = ?", (booking_id,)
        ).fetchone()
    if row is None:
        raise BookingError("Заявка не найдена")
    return _to_dict(row)


def list_for(user_id: str, limit: int = 50) -> list[dict]:
    with store.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM lab_bookings WHERE user_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [_to_dict(r) for r in rows]


def cancel(user_id: str, booking_id: str) -> dict:
    with store.connect() as conn:
        row = conn.execute(
            "SELECT * FROM lab_bookings WHERE id = ? AND user_id = ?",
            (booking_id, user_id),
        ).fetchone()
        if row is None:
            raise BookingError("Заявка не найдена")
        if row["status"] in ("done", "canceled"):
            raise BookingError("Эту заявку уже нельзя отменить")
        conn.execute(
            "UPDATE lab_bookings SET status = 'canceled' WHERE id = ?", (booking_id,)
        )
    return get_booking(booking_id)


def list_all(limit: int = 200) -> list[dict]:
    """Для админ-панели: все заявки, свежие сверху."""
    with store.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM lab_bookings ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_to_dict(r) for r in rows]


def _to_dict(row) -> dict:
    d = dict(row)
    panel = get_panel(d["panel_id"])
    d["panel_name"] = panel.name if panel else d["panel_id"]
    d["price_rub"] = panel.price_rub if panel else None
    return d
