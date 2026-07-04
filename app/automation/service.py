"""Периодические задачи Aura.

Запускаются фоновым планировщиком (app/automation/scheduler.py), внешним cron
через POST /api/admin/run-jobs, либо вручную из админ-панели. Каждая задача
идемпотентна: повторный запуск не спамит пользователей и не ломает данные.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from app.db import store
from app.notifications import service as notifications
from app.subscription import service as subscription

logger = logging.getLogger("derm.automation")

ABANDONED_CART_HOURS = 24      # корзина считается «брошенной» через сутки
CART_REMINDER_COOLDOWN_DAYS = 3  # не чаще одного напоминания в N дней


def _now() -> datetime:
    return datetime.now(timezone.utc)


def refresh_due_protocols() -> int:
    """Пересобрать «живые» протоколы, у которых подошёл срок обновления.

    current_protocol() сам пересобирает протокол под текущий сезон, если
    next_update в прошлом; здесь мы лишь находим таких подписчиков и шлём
    уведомление об обновлении.
    """
    with store.connect() as conn:
        rows = conn.execute(
            "SELECT user_id FROM protocol_subscriptions "
            "WHERE active = 1 AND next_update <= ?",
            (_now().isoformat(),),
        ).fetchall()

    refreshed = 0
    for row in rows:
        data = subscription.current_protocol(row["user_id"])
        if data and data.get("refreshed_now"):
            notifications.push(
                row["user_id"],
                "Протокол обновлён 🌿",
                "Ваш персональный протокол ухода пересобран под текущий сезон. "
                "Откройте раздел «Подписка», чтобы посмотреть изменения.",
            )
            refreshed += 1
    return refreshed


def remind_abandoned_carts(hours: int = ABANDONED_CART_HOURS) -> int:
    """Напомнить о товарах, оставленных в корзине больше N часов назад."""
    cutoff = (_now() - timedelta(hours=hours)).isoformat()
    cooldown = (_now() - timedelta(days=CART_REMINDER_COOLDOWN_DAYS)).isoformat()

    with store.connect() as conn:
        rows = conn.execute(
            "SELECT user_id, MAX(updated_at) AS last_touch, SUM(qty) AS items "
            "FROM cart GROUP BY user_id "
            "HAVING last_touch IS NOT NULL AND last_touch <= ?",
            (cutoff,),
        ).fetchall()

        reminded = 0
        for row in rows:
            already = conn.execute(
                "SELECT 1 FROM notifications WHERE user_id = ? "
                "AND title LIKE 'В корзине%' AND created_at >= ? LIMIT 1",
                (row["user_id"], cooldown),
            ).fetchone()
            if already:
                continue
            notifications.push(
                row["user_id"],
                "В корзине остались товары 🛍",
                f"Вы отложили {row['items']} шт. — они ждут вас. "
                "Бесплатная доставка в ПВЗ от 3 500 ₽.",
            )
            reminded += 1
    return reminded


def cleanup_expired_otp() -> int:
    """Удалить истёкшие SMS-коды входа."""
    with store.connect() as conn:
        cur = conn.execute(
            "DELETE FROM otp_codes WHERE expires < ?", (_now().isoformat(),)
        )
        return cur.rowcount


RUN_LOG_KEEP = 500  # сколько последних записей журнала хранить


def log_run(job: str, detail: str) -> None:
    with store.connect() as conn:
        conn.execute(
            "INSERT INTO automation_runs (job, detail, created_at) VALUES (?, ?, ?)",
            (job, detail, _now().isoformat()),
        )
        # Обрезаем журнал, чтобы он не рос бесконечно.
        conn.execute(
            "DELETE FROM automation_runs WHERE id <= "
            "(SELECT MAX(id) FROM automation_runs) - ?",
            (RUN_LOG_KEEP,),
        )


def list_runs(limit: int = 20) -> list[dict]:
    with store.connect() as conn:
        rows = conn.execute(
            "SELECT job, detail, created_at FROM automation_runs "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def run_all() -> dict:
    """Запустить все задачи. Ошибки одной задачи не роняют остальные."""
    jobs = {
        "refresh_due_protocols": refresh_due_protocols,
        "remind_abandoned_carts": remind_abandoned_carts,
        "cleanup_expired_otp": cleanup_expired_otp,
    }
    results: dict[str, str] = {}
    for name, fn in jobs.items():
        try:
            results[name] = str(fn())
        except Exception as exc:  # pragma: no cover - защитный контур
            logger.warning("Автоматизация %s упала: %s", name, exc)
            results[name] = f"error: {exc}"
        log_run(name, results[name])
    return results
