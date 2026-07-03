"""Провайдеро-независимый слой оплаты.

По умолчанию — DemoProvider (без реальных денег): создаёт «платёж», который
подтверждается вручную/по кнопке и начисляет кредиты. Точка расширения под
ЮKassa (стандарт для РФ) готова — подставьте ключи и реализуйте вызовы API.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from app.billing import service as credits
from app.config import get_settings
from app.db import store

# Пакеты кредитов (id -> (кол-во сканов, цена в ₽)). Цена базового скана из настроек.
CREDIT_PACKS: dict[str, int] = {"1": 1, "5": 5, "20": 20}


@dataclass
class Payment:
    id: str
    user_id: str
    amount_rub: int
    credits: int
    status: str  # pending | succeeded | canceled
    provider: str
    confirmation_url: str


def _pack_price(count: int) -> int:
    """Цена пакета: базовая цена скана × количество (скидка на объём)."""
    base = get_settings().scan_price_rub
    discount = 1.0 if count < 5 else (0.9 if count < 20 else 0.8)
    return int(round(base * count * discount))


def _save(conn, p: Payment) -> None:
    conn.execute(
        "INSERT INTO payments (id, user_id, amount_rub, credits, status, provider, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (p.id, p.user_id, p.amount_rub, p.credits, p.status, p.provider,
         datetime.now(timezone.utc).isoformat()),
    )


def create_payment(user_id: str, pack: str = "1") -> Payment:
    """Создать платёж за пакет кредитов. Возвращает Payment с confirmation_url."""
    count = CREDIT_PACKS.get(pack)
    if not count:
        raise ValueError(f"Неизвестный пакет: {pack}")

    provider = get_settings().payment_provider
    payment_id = uuid.uuid4().hex
    amount = _pack_price(count)

    if provider == "yookassa":
        # TODO: интеграция с ЮKassa — создать платёж через их API и вернуть
        # confirmation_url. Требует YOOKASSA_SHOP_ID / YOOKASSA_SECRET_KEY.
        confirmation_url = _yookassa_create(payment_id, user_id, amount, count)
    else:
        # Демо: подтверждение по нашему же эндпоинту (без реальных денег).
        confirmation_url = f"/api/billing/confirm?payment_id={payment_id}"

    p = Payment(payment_id, user_id, amount, count, "pending", provider, confirmation_url)
    with store.connect() as conn:
        _save(conn, p)
    return p


def confirm_payment(payment_id: str) -> Payment:
    """Подтвердить платёж и начислить кредиты (demo-режим / webhook)."""
    with store.connect() as conn:
        row = conn.execute("SELECT * FROM payments WHERE id = ?", (payment_id,)).fetchone()
        if row is None:
            raise ValueError("Платёж не найден")
        if row["status"] == "succeeded":
            return _row_to_payment(row)
        conn.execute("UPDATE payments SET status = 'succeeded' WHERE id = ?", (payment_id,))

    credits.grant(row["user_id"], int(row["credits"]))
    with store.connect() as conn:
        row = conn.execute("SELECT * FROM payments WHERE id = ?", (payment_id,)).fetchone()
    return _row_to_payment(row)


def _row_to_payment(row) -> Payment:
    return Payment(
        id=row["id"], user_id=row["user_id"], amount_rub=int(row["amount_rub"]),
        credits=int(row["credits"]), status=row["status"], provider=row["provider"],
        confirmation_url=f"/api/billing/confirm?payment_id={row['id']}",
    )


def _yookassa_create(payment_id: str, user_id: str, amount: int, count: int) -> str:  # pragma: no cover
    """Заготовка под ЮKassa. Реализуйте вызов API и верните confirmation_url."""
    raise NotImplementedError(
        "Интеграция с ЮKassa не настроена. Задайте YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY "
        "и реализуйте создание платежа через их API."
    )
