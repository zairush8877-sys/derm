"""Корзина магазина (хранится в SQLite)."""

from __future__ import annotations

from app.db import store
from app.shop import catalog


def add_to_cart(user_id: str, product_id: str, qty: int = 1) -> None:
    if catalog.get_product(product_id) is None:
        raise ValueError("Товар не найден")
    if qty <= 0:
        raise ValueError("Количество должно быть положительным")
    with store.connect() as conn:
        conn.execute(
            "INSERT INTO cart (user_id, product_id, qty) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, product_id) DO UPDATE SET qty = qty + excluded.qty",
            (user_id, product_id, qty),
        )


def remove_from_cart(user_id: str, product_id: str) -> None:
    with store.connect() as conn:
        conn.execute(
            "DELETE FROM cart WHERE user_id = ? AND product_id = ?", (user_id, product_id)
        )


def get_cart(user_id: str) -> dict:
    """Вернуть корзину: список позиций и итоговую сумму в ₽."""
    with store.connect() as conn:
        rows = conn.execute(
            "SELECT product_id, qty FROM cart WHERE user_id = ?", (user_id,)
        ).fetchall()

    items = []
    total = 0
    for row in rows:
        product = catalog.get_product(row["product_id"])
        if product is None:
            continue
        qty = int(row["qty"])
        line = product.price_rub * qty
        total += line
        items.append({"product": product.model_dump(mode="json"), "qty": qty, "line_rub": line})

    return {"items": items, "total_rub": total, "count": sum(i["qty"] for i in items)}


def clear_cart(user_id: str) -> None:
    with store.connect() as conn:
        conn.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
