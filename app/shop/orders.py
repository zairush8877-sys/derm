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


def delivery_quote(subtotal_rub: int, method: str = DEFAULT_METHOD,
                   to_city_code: int | None = None) -> dict:
    m = DELIVERY_METHODS.get(method, DELIVERY_METHODS[DEFAULT_METHOD])
    fee = 0 if subtotal_rub >= m["free_from_rub"] else m["fee_rub"]
    eta = m["eta_days"]

    # Реальный тариф СДЭК, если заданы ключи договора и известен город.
    if method in ("courier", "pvz") and to_city_code:
        from app.shop import cdek
        if cdek.configured():
            try:
                tariff = cdek.TARIFF_COURIER if method == "courier" else cdek.TARIFF_PVZ
                q = cdek.quote(to_city_code, tariff=tariff)
                fee = 0 if subtotal_rub >= m["free_from_rub"] else q["fee_rub"]
                eta = q["eta_days"]
            except cdek.CdekError:
                pass  # СДЭК недоступен — работаем по фиксированному тарифу

    return {
        "method": method if method in DELIVERY_METHODS else DEFAULT_METHOD,
        "title": m["title"], "fee_rub": fee,
        "free_from_rub": m["free_from_rub"], "eta_days": eta,
    }


def delivery_options(subtotal_rub: int) -> list[dict]:
    return [delivery_quote(subtotal_rub, key) for key in DELIVERY_METHODS]


def checkout(user_id: str, address: str, name: str = "", phone: str = "",
             method: str = DEFAULT_METHOD, comment: str = "") -> dict:
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
        "comment": comment.strip()[:500],
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

    # Владельцу — мгновенное уведомление в Telegram (если настроено).
    from app.notifications import owner
    items_line = ", ".join(f"{i['product']['name']} ×{i['qty']}" for i in cart["items"])
    owner.notify_owner(
        f"🛍 Новый заказ {order_id} на {total} ₽\n"
        f"Состав: {items_line}\n"
        f"Доставка: {delivery_info['method_title']}, {address}\n"
        f"Покупатель: {name or '—'}, {phone or '—'}"
        + (f"\nКомментарий: {delivery_info['comment']}" if delivery_info["comment"] else "")
    )

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


def set_track_number(order_id: str, track: str) -> dict:
    """Присвоить заказу трек-номер СДЭК и уведомить покупателя со ссылкой."""
    track = track.strip()
    if not track:
        raise ValueError("Пустой трек-номер")
    with store.connect() as conn:
        row = conn.execute(
            "SELECT id, user_id, delivery_json FROM orders WHERE id = ?", (order_id,)
        ).fetchone()
        if row is None:
            raise LookupError("Заказ не найден")
        info = service._load(row["delivery_json"])
        already = info.get("track") == track
        info["track"] = track
        conn.execute("UPDATE orders SET delivery_json = ? WHERE id = ?",
                     (service._dump(info), order_id))

    if not already:
        from app.notifications import service as notifications
        from app.shop import cdek
        notifications.push(
            row["user_id"], "Трек-номер посылки 📦",
            f"Заказ {order_id} можно отслеживать: {track}. "
            f"Статус посылки: {cdek.track_url(track)}",
        )
    return {"order_id": order_id, "track": track, "changed": not already}


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
