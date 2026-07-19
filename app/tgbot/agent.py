"""Клод-агент в Telegram: свободный диалог + инструменты управления Aura.

Владелец пишет обычным языком («добавь морской коллаген за 2490»,
«сколько заказов за неделю?», «покажи заявки в лабораторию») — модель сама
выбирает нужный инструмент и отвечает по-человечески. Диалог помнится
(последние сообщения хранятся в БД). В демо-режиме без ключа Anthropic —
упрощённый построчный разбор товаров.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.config import get_settings
from app.db import store
from app.shop.catalog import Category
from app.tgbot import service

logger = logging.getLogger("derm.tgbot.agent")

_HISTORY_LIMIT = 12  # реплик диалога в контексте

SYSTEM = (
    "Ты — Aura, ассистентка владелицы wellness-платформы aura-wellness.ru "
    "(магазин, AI-анализ кожи, трекер питания, лаборатория). Ты общаешься с "
    "владелицей в Telegram: дружелюбно, по-русски, коротко и по делу. "
    "У тебя есть инструменты управления каталогом и просмотра статистики — "
    "используй их сам, когда просят что-то сделать или узнать. "
    "Цены в рублях. Категории каталога: "
    + ", ".join(c.value for c in Category) + ". "
    "Если владелица прислала фото прайса — распознай товары и добавь их. "
    "После добавления товаров перечисли, что добавлено, с id (для удаления). "
    "Не выдумывай данные: всё, что можно узнать инструментом, узнавай им."
)

TOOLS = [
    {
        "name": "add_products",
        "description": "Добавить товары в каталог магазина (появляются на сайте сразу).",
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "brand": {"type": "string"},
                            "price_rub": {"type": "integer"},
                            "old_price_rub": {"type": ["integer", "null"]},
                            "category": {"type": "string"},
                            "description": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["name", "price_rub"],
                    },
                }
            },
            "required": ["items"],
        },
    },
    {
        "name": "remove_product",
        "description": "Удалить добавленный владелицей товар по id (вида tg-XXXXXXXX).",
        "input_schema": {
            "type": "object",
            "properties": {"product_id": {"type": "string"}},
            "required": ["product_id"],
        },
    },
    {
        "name": "list_custom_products",
        "description": "Список товаров, добавленных владелицей через бота.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "search_catalog",
        "description": "Поиск по всему каталогу магазина (название/бренд/описание).",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "business_stats",
        "description": "Сводка по бизнесу: пользователи, заказы, заявки в лабораторию, сканы.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def _run_tool(name: str, args: dict) -> str:
    """Выполнить инструмент; результат — строка для модели."""
    if name == "add_products":
        added = service.add_products(args.get("items") or [])
        return json.dumps({"added": added}, ensure_ascii=False)
    if name == "remove_product":
        ok = service.remove_product(str(args.get("product_id", "")))
        return json.dumps({"removed": ok})
    if name == "list_custom_products":
        return json.dumps({"items": service.list_custom()}, ensure_ascii=False)
    if name == "search_catalog":
        from app.shop import catalog

        found = catalog.search(str(args.get("query", "")))[:10]
        return json.dumps({"items": [
            {"id": p.id, "name": p.name, "brand": p.brand,
             "price_rub": p.price_rub, "category": p.category.value}
            for p in found]}, ensure_ascii=False)
    if name == "business_stats":
        with store.connect() as conn:
            def count(sql: str) -> int:
                try:
                    return int(conn.execute(sql).fetchone()[0])
                except Exception:
                    return 0
            stats = {
                "пользователей": count("SELECT COUNT(*) FROM users"),
                "заказов": count("SELECT COUNT(*) FROM orders"),
                "заявок_в_лабораторию": count("SELECT COUNT(*) FROM lab_bookings"),
                "новых_заявок": count("SELECT COUNT(*) FROM lab_bookings WHERE status='new'"),
                "сканов_кожи": count("SELECT COUNT(*) FROM scans"),
                "записей_еды": count("SELECT COUNT(*) FROM food_log"),
                "товаров_от_владельца": count("SELECT COUNT(*) FROM products"),
            }
        return json.dumps(stats, ensure_ascii=False)
    return json.dumps({"error": f"неизвестный инструмент {name}"})


def _history_load(chat_id: str) -> list[dict]:
    with store.connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM tg_history WHERE chat_id = ? "
            "ORDER BY id DESC LIMIT ?", (chat_id, _HISTORY_LIMIT),
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def _history_save(chat_id: str, role: str, content: str) -> None:
    with store.connect() as conn:
        conn.execute(
            "INSERT INTO tg_history (chat_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (chat_id, role, content[:4000], datetime.now(timezone.utc).isoformat()),
        )
        conn.execute(
            "DELETE FROM tg_history WHERE chat_id = ? AND id NOT IN "
            "(SELECT id FROM tg_history WHERE chat_id = ? ORDER BY id DESC LIMIT 40)",
            (chat_id, chat_id),
        )


def _mock_answer(text: str) -> str:
    """Демо-режим: построчное добавление товаров без модели."""
    items = service.parse_products(text)
    added = service.add_products(items)
    if added:
        lines = [f"Добавила {len(added)} товар(ов):"]
        lines += [f"• {a['name']} — {a['price_rub']} ₽ · {a['id']}" for a in added]
        return "\n".join(lines)
    return ("Демо-режим (без ключа AI). Понимаю строки вида:\n"
            "Бренд; Название; Цена; Категория; Описание")


def chat(chat_id: str, text: str = "", image_b64: str = "",
         media_type: str = "image/jpeg") -> str:
    """Обработать сообщение владелицы, вернуть ответ для Telegram."""
    settings = get_settings()
    if settings.mock_mode:
        return _mock_answer(text)

    from anthropic import Anthropic

    user_content: list[dict] = []
    if image_b64:
        user_content.append({"type": "image", "source": {
            "type": "base64", "media_type": media_type, "data": image_b64}})
    user_content.append({"type": "text", "text": text or "Фото прайса — добавь товары."})

    messages = _history_load(chat_id) + [{"role": "user", "content": user_content}]
    client = Anthropic(api_key=settings.anthropic_api_key)
    try:
        final_text = ""
        for _ in range(6):  # максимум 5 витков инструментов
            resp = client.messages.create(
                model=settings.chat_model, max_tokens=2000,
                system=SYSTEM, tools=TOOLS, messages=messages,
            )
            tool_uses = [b for b in resp.content if getattr(b, "type", "") == "tool_use"]
            final_text = "".join(
                b.text for b in resp.content if getattr(b, "type", "") == "text")
            if not tool_uses:
                break
            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for tu in tool_uses:
                results.append({
                    "type": "tool_result", "tool_use_id": tu.id,
                    "content": _run_tool(tu.name, tu.input or {}),
                })
            messages.append({"role": "user", "content": results})
        reply = final_text.strip() or "Сделано."
    except Exception as exc:
        logger.warning("Сбой Клод-агента: %s", exc)
        return _mock_answer(text) if text else "Не получилось обработать — попробуйте ещё раз."

    _history_save(chat_id, "user", text or "[фото прайса]")
    _history_save(chat_id, "assistant", reply)
    return reply
