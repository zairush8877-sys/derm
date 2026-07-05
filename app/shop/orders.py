"""Оформление заказов, доставка и история заказов."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.config import get_settings
from app.db import store
from app.shop import loyalty, service

# Способы доставки. Тарифы демо; точка под API СДЭК/Почты — рассчитывать
# fee/eta по адресу через их API вместо фиксированных значений.
DELIVERY_METHODS: dict[str, dict] = {
    "courier": {"title": "Курьер до двери", "fee_rub": 390, "free_from_rub": 5000, "eta_days": 2},
    "pvz": {"title": "Пункт выдачи (ПВЗ)", "fee_rub": 250, "free_from_rub": 3500, "eta_days": 3},
    "post": {"title": "Почта России", "fee_rub": 350, "free_from_rub": 5000, "eta_days": 6},
}
DEFAULT_METHOD = "courier"

# Обратная совместимость со старым квотированием.
FREE_DELIVERY_FROM_RUB = DELIVERY_METHODS[DEFAULT_METHOD]["free_from_rub"]
DELIVERY_FEE_RUB = DELIVERY_METHODS[DEFAULT_METHOD]["fee_rub"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def delivery_quote(subtotal_rub: int, method: str = DEFAULT_METHOD) -> dict:
    m = DELIVERY_METHODS.get(method, DELIVERY_METHODS[DEFAULT_METHOD])
    fee = 0 if subtotal_rub >= m["free_from_rub"] else m["fee_rub"]
    return {
        "method": method if method in DELIVERY_METHODS else DEFAULT_METHOD,
        "title": m["title"], "fee_rub": fee,
        "free_from_rub": m["free_from_rub"], "eta_days": m["eta_days"],
    }


def delivery_options(subtotal_rub: int) -> list[dict]:
    return [delivery_quote(subtotal_rub, key) for key in DELIVERY_METHODS]


def checkout(user_id: str, address: str, name: str = "", phone: str = "",
             method: str = DEFAULT_METHOD) -> dict:
    """Оформить заказ из корзины: создать заказ, начислить баллы, очистить корзину."""
    cart = service.get_cart(user_id)
    if not cart["items"]:
        raise ValueError("Корзина пуста")

    subtotal = cart["total_rub"]
    delivery = delivery_quote(subtotal, method)
    total = subtotal + delivery["fee_rub"]

    order_id = uuid.uuid4().hex[:12]
    delivery_info = {
        "name": name, "phone": phone, "address": address,
        "method": delivery["method"], "method_title": delivery["title"],
        "fee_rub": delivery["fee_rub"], "eta_days": delivery["eta_days"],
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


# Жизненный цикл заказа. Смена статуса — из админки, с уведомлением покупателю.
STATUS_FLOW = ["оплачен", "собирается", "отправлен", "доставлен"]

_STATUS_MESSAGES = {
    "собирается": ("Заказ собирается 📦", "Мы начали собирать ваш заказ {oid}."),
    "отправлен": ("Заказ отправлен 🚚", "Заказ {oid} передан в доставку. Ожидайте!"),
    "доставлен": ("Заказ доставлен ✅", "Заказ {oid} доставлен. Спасибо, что выбираете Aura!"),
}


def update_status(order_id: str, status: str) -> dict:
    """Сменить статус заказа и уведомить покупателя.

    Допускается только переход на следующий по порядку статус (или повтор
    текущего). Уведомление и запись отправляются лишь при реальной смене —
    повторный клик/двойной запрос не спамит покупателя.
    """
    if status not in STATUS_FLOW:
        raise ValueError(f"Недопустимый статус: {status}. Доступны: {', '.join(STATUS_FLOW)}")
    with store.connect() as conn:
        row = conn.execute(
            "SELECT id, user_id, status FROM orders WHERE id = ?", (order_id,)
        ).fetchone()
        if row is None:
            raise LookupError("Заказ не найден")

        current = row["status"]
        if status == current:
            return {"order_id": order_id, "user_id": row["user_id"], "status": current, "changed": False}

        cur_idx, new_idx = STATUS_FLOW.index(current), STATUS_FLOW.index(status)
        if new_idx != cur_idx + 1:
            raise ValueError(
                f"Недопустимый переход {current} → {status}. "
                f"Следующий статус: {STATUS_FLOW[cur_idx + 1] if cur_idx + 1 < len(STATUS_FLOW) else '—'}."
            )
        conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))

    if status in _STATUS_MESSAGES:
        from app.notifications import service as notifications

        title, body = _STATUS_MESSAGES[status]
        notifications.push(row["user_id"], title, body.format(oid=order_id))
    return {"order_id": order_id, "user_id": row["user_id"], "status": status, "changed": True}


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
