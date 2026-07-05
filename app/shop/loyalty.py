"""Программа лояльности Aura: баллы и уровни.

Начисление: 5% от суммы заказа в баллах (1 балл = 1 ₽ к списанию в будущем).
Уровни по сумме покупок за всё время (влияют на кешбэк).
"""

from __future__ import annotations

from app.db import store

EARN_RATE = 0.05  # 5% кешбэк баллами

TIERS = [
    ("Base", 0, 0.05),
    ("Silver", 30000, 0.07),
    ("Gold", 100000, 0.10),
    ("Platinum", 300000, 0.12),
]


def _row(user_id: str) -> dict:
    with store.connect() as conn:
        conn.execute("INSERT OR IGNORE INTO loyalty (user_id) VALUES (?)", (user_id,))
        r = conn.execute(
            "SELECT points, lifetime_spent_rub FROM loyalty WHERE user_id = ?", (user_id,)
        ).fetchone()
    return {"points": int(r["points"]), "lifetime_spent_rub": int(r["lifetime_spent_rub"])}


def tier_for(lifetime_spent: int) -> tuple[str, float]:
    name, _, rate = TIERS[0]
    for t_name, threshold, t_rate in TIERS:
        if lifetime_spent >= threshold:
            name, rate = t_name, t_rate
    return name, rate


def status(user_id: str) -> dict:
    data = _row(user_id)
    name, rate = tier_for(data["lifetime_spent_rub"])
    return {
        "user_id": user_id,
        "points": data["points"],
        "lifetime_spent_rub": data["lifetime_spent_rub"],
        "tier": name,
        "cashback_rate": rate,
    }


def accrue(user_id: str, order_total_rub: int) -> int:
    """Начислить баллы за заказ по ставке уровня. Возвращает начисленные баллы."""
    data = _row(user_id)
    _, rate = tier_for(data["lifetime_spent_rub"] + order_total_rub)
    earned = int(round(order_total_rub * rate))
    with store.connect() as conn:
        conn.execute(
            "UPDATE loyalty SET points = points + ?, lifetime_spent_rub = lifetime_spent_rub + ? "
            "WHERE user_id = ?",
            (earned, order_total_rub, user_id),
        )
    return earned
