"""Учёт кредитов: баланс, пробный скан, списание за платный AI-анализ.

Правило продукта: **фото-анализ (кожа/еда) платный**, всё остальное бесплатно
(квиз, протокол, история трекера, магазин). 1 кредит = 1 фото-скан.
Новому пользователю единоразово начисляется пробный скан (FREE_TRIAL).
"""

from __future__ import annotations

from app.config import get_settings
from app.db import store


class InsufficientCredits(Exception):
    """Недостаточно кредитов для платного скана."""


def _ensure_account(conn, user_id: str) -> None:
    """Создать счёт пользователя и начислить пробные сканы (один раз)."""
    row = conn.execute("SELECT trial_granted FROM credits WHERE user_id = ?", (user_id,)).fetchone()
    if row is None:
        trial = get_settings().free_trial_scans
        conn.execute(
            "INSERT INTO credits (user_id, balance, trial_granted) VALUES (?, ?, 1)",
            (user_id, trial),
        )


def balance(user_id: str) -> int:
    """Текущий баланс кредитов (с учётом стартового пробного начисления)."""
    with store.connect() as conn:
        _ensure_account(conn, user_id)
        row = conn.execute("SELECT balance FROM credits WHERE user_id = ?", (user_id,)).fetchone()
        return int(row["balance"]) if row else 0


def grant(user_id: str, amount: int) -> int:
    """Начислить кредиты (после успешной оплаты). Возвращает новый баланс."""
    if amount <= 0:
        raise ValueError("Количество кредитов должно быть положительным")
    with store.connect() as conn:
        _ensure_account(conn, user_id)
        conn.execute(
            "UPDATE credits SET balance = balance + ? WHERE user_id = ?", (amount, user_id)
        )
        row = conn.execute("SELECT balance FROM credits WHERE user_id = ?", (user_id,)).fetchone()
        return int(row["balance"])


def charge(user_id: str, amount: int = 1) -> int:
    """Списать кредиты за платный скан. Бросает InsufficientCredits при нехватке."""
    with store.connect() as conn:
        _ensure_account(conn, user_id)
        row = conn.execute("SELECT balance FROM credits WHERE user_id = ?", (user_id,)).fetchone()
        current = int(row["balance"]) if row else 0
        if current < amount:
            raise InsufficientCredits(
                f"Недостаточно кредитов: нужно {amount}, на балансе {current}. "
                f"Купите скан за {get_settings().scan_price_rub} ₽."
            )
        conn.execute(
            "UPDATE credits SET balance = balance - ? WHERE user_id = ?", (amount, user_id)
        )
        return current - amount
