"""Оформление заказов, доставка и история заказов."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.config import get_settings
from app.db import store
from app.shop import loyalty, service

FREE_DELIVERY_FROM_RUB = 5000
DELIVERY_FEE_RUB = 390


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def delivery_quote(subtotal_rub: int) -> dict:
    fee = 0 if subtotal_rub >= FREE_DELIVERY_FROM_RUB else DELIVERY_FEE_RUB
    return {"fee_rub": fee, "free_from_rub": FREE_DELIVERY_FROM_RUB}


def checkout(user_id: str, address: str, name: str = "", phone: str = "") -> dict:
    """Оформить заказ из корзины: создать заказ, начислить баллы, очистить корзину."""
    cart = service.get_cart(user_id)
    if not cart["items"]:
        raise ValueError("Корзина пуста")

    subtotal = cart["total_rub"]
    delivery = delivery_quote(subtotal)
    total = subtotal + delivery["fee_rub"]

    order_id = uuid.uuid4().hex[:12]
    delivery_info = {
        "name": name, "phone": phone, "address": address,
        "fee_rub": delivery["fee_rub"], "eta_days": 2,
    }
    points = loyalty.accrue(user_id, total)

    with store.connect() as conn:
        conn.execute(
            "INSERT INTO orders (id, user_id, items_json, total_rub, points_earned, status, "
            "delivery_json, created_at) VALUES (?, ?, ?, ?, ?, 'оплачен', ?, ?)",
            (order_id, user_id, service._dump(cart["items"]), total, points,
             service._dump(delivery_info), _now()),
        )
    service.clear_cart(user_id)

    from app.notifications import service as notifications
    notifications.push(user_id, "Заказ оформлен",
                       f"Заказ {order_id} на {total} ₽ принят. Начислено {points} баллов.")

    return {
        "order_id": order_id, "subtotal_rub": subtotal, "delivery_fee_rub": delivery["fee_rub"],
        "total_rub": total, "points_earned": points, "status": "оплачен",
        "payment_provider": get_settings().payment_provider, "delivery": delivery_info,
    }


def list_orders(user_id: str) -> list[dict]:
    with store.connect() as conn:
        rows = conn.execute(
            "SELECT id, items_json, total_rub, points_earned, status, delivery_json, created_at "
            "FROM orders WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return [
        {
            "order_id": r["id"], "total_rub": int(r["total_rub"]),
            "points_earned": int(r["points_earned"]), "status": r["status"],
            "items": service._load(r["items_json"]), "delivery": service._load(r["delivery_json"]),
            "created_at": r["created_at"],
        }
        for r in rows
    ]
