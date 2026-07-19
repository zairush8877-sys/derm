"""Логика бота: разбор товаров из текста/фото (Claude) и запись в каталог.

Реальный режим — модель разбирает свободный текст или фото прайса в JSON.
Демо-режим (и фоллбэк при сбое) — построчный разбор «Бренд; Название; Цена;
Категория; Описание» (категория и описание необязательны).
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone

from app.config import get_settings
from app.db import store
from app.shop.catalog import Category

_CATEGORIES = [c.value for c in Category]

_PARSE_PROMPT = (
    "Ты помощник магазина wellness-товаров. Разбери сообщение владельца "
    "(или фото прайса) в список товаров. Верни ТОЛЬКО JSON-массив объектов "
    "с полями: name (строка), brand (строка, по умолчанию 'Aura'), "
    "price_rub (целое, рубли), old_price_rub (целое или null), "
    f"category (строго одно из: {', '.join(_CATEGORIES)}), "
    "description (1-2 предложения, дружелюбно), tags (массив строк). "
    "Если категория не ясна — подбери ближайшую по смыслу."
)


def webhook_secret() -> str:
    """Секрет пути вебхука — выводится из токена бота (не хранится отдельно)."""
    token = get_settings().telegram_bot_token
    return hashlib.sha256(("aura-tg:" + token).encode()).hexdigest()[:24]


def _parse_lines(text: str) -> list[dict]:
    """Демо-разбор: «Бренд; Название; Цена[; Категория[; Описание]]» построчно."""
    items = []
    for line in text.strip().splitlines():
        parts = [p.strip() for p in re.split(r"[;|]", line) if p.strip()]
        if len(parts) < 3:
            continue
        m = re.search(r"\d[\d\s]*", parts[2])
        if not m:
            continue
        price = int(m.group().replace(" ", ""))
        category = parts[3] if len(parts) > 3 and parts[3] in _CATEGORIES else Category.VITAMINS.value
        items.append({
            "brand": parts[0], "name": parts[1], "price_rub": price,
            "old_price_rub": None, "category": category,
            "description": parts[4] if len(parts) > 4 else "",
            "tags": [],
        })
    return items


def _parse_ai(text: str = "", image_b64: str = "", media_type: str = "image/jpeg") -> list[dict]:
    from anthropic import Anthropic

    settings = get_settings()
    content: list[dict] = []
    if image_b64:
        content.append({"type": "image", "source": {
            "type": "base64", "media_type": media_type, "data": image_b64}})
    content.append({"type": "text", "text": text or "Фото прайса — распознай товары."})
    client = Anthropic(api_key=settings.anthropic_api_key)
    resp = client.messages.create(
        model=settings.model if image_b64 else settings.chat_model,
        max_tokens=4000, system=_PARSE_PROMPT,
        messages=[{"role": "user", "content": content}],
    )
    raw = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    return json.loads(m.group()) if m else []


def parse_products(text: str = "", image_b64: str = "", media_type: str = "image/jpeg") -> list[dict]:
    """Разобрать товары: AI в реальном режиме, построчно — в демо/при сбое."""
    if get_settings().mock_mode or (not text and not image_b64):
        return _parse_lines(text)
    try:
        return _parse_ai(text, image_b64, media_type)
    except Exception:
        return _parse_lines(text)


def add_products(items: list[dict]) -> list[dict]:
    """Записать товары в каталог. Возвращает добавленные (с id)."""
    added = []
    now = datetime.now(timezone.utc).isoformat()
    with store.connect() as conn:
        for it in items:
            name = str(it.get("name", "")).strip()
            try:
                price = int(it.get("price_rub") or 0)
            except (TypeError, ValueError):
                continue
            if not name or price <= 0:
                continue
            category = it.get("category") if it.get("category") in _CATEGORIES else Category.VITAMINS.value
            pid = "tg-" + uuid.uuid4().hex[:8]
            conn.execute(
                "INSERT INTO products (id, name, brand, category, price_rub, old_price_rub, "
                "description, tags_json, in_stock, is_service, hit, image, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 0, 0, NULL, ?)",
                (pid, name[:120], str(it.get("brand") or "Aura")[:60], category, price,
                 it.get("old_price_rub"), str(it.get("description") or "")[:500],
                 json.dumps(it.get("tags") or [], ensure_ascii=False), now),
            )
            added.append({"id": pid, "name": name, "price_rub": price, "category": category})
    return added


def already_seen(update_id: int) -> bool:
    """Идемпотентность вебхука: True, если этот апдейт уже обработан."""
    from datetime import datetime, timezone

    with store.connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM tg_seen WHERE update_id = ?", (update_id,)
        ).fetchone()
        if row is not None:
            return True
        conn.execute(
            "INSERT INTO tg_seen (update_id, created_at) VALUES (?, ?)",
            (update_id, datetime.now(timezone.utc).isoformat()),
        )
        # Уборка старых записей (храним последние ~1000).
        conn.execute(
            "DELETE FROM tg_seen WHERE update_id NOT IN "
            "(SELECT update_id FROM tg_seen ORDER BY update_id DESC LIMIT 1000)"
        )
    return False


def remove_product(product_id: str) -> bool:
    """Удалить «живой» товар (только добавленные ботом/админкой, id tg-*)."""
    with store.connect() as conn:
        cur = conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        return cur.rowcount > 0


def list_custom(limit: int = 30) -> list[dict]:
    with store.connect() as conn:
        rows = conn.execute(
            "SELECT id, name, brand, price_rub, category FROM products "
            "ORDER BY created_at DESC LIMIT ?", (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
