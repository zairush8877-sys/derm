"""Вебхук Telegram-бота владельца.

Безопасность: путь содержит секрет, выводимый из токена бота; команды
принимаются только из чата владельца (TELEGRAM_CHAT_ID). Ответы уходят
через Bot API (sendMessage). Без настроенного токена вебхук отвечает 404.
"""

from __future__ import annotations

import base64
import json
import logging
import urllib.request

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.tgbot import service

router = APIRouter(prefix="/api/telegram", tags=["Telegram-бот"])
logger = logging.getLogger("derm.tgbot")

HELP_TEXT = (
    "Я бот каталога Aura. Умею:\n\n"
    "• Добавить товары — пришлите текст:\n"
    "Бренд; Название; Цена; Категория; Описание\n"
    "(по строке на товар — или просто опишите свободно, я разберу)\n\n"
    "• Фото прайса — распознаю и добавлю позиции\n\n"
    "• /список — последние добавленные\n"
    "• /удалить tg-XXXXXXXX — убрать позицию\n\n"
    "Товары появляются на сайте и в приложении сразу."
)


def _tg_api(method: str, payload: dict) -> dict:
    token = get_settings().telegram_bot_token
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310
        return json.loads(resp.read().decode())


def send_reply(chat_id: int | str, text: str) -> None:
    try:
        _tg_api("sendMessage", {"chat_id": chat_id, "text": text})
    except Exception as exc:  # ответ не критичен — товары уже записаны
        logger.warning("Не удалось ответить в Telegram: %s", exc)


def download_photo(file_id: str) -> tuple[str, str]:
    """Скачать фото из Telegram → (base64, media_type)."""
    token = get_settings().telegram_bot_token
    info = _tg_api("getFile", {"file_id": file_id})
    path = info["result"]["file_path"]
    with urllib.request.urlopen(  # noqa: S310
        f"https://api.telegram.org/file/bot{token}/{path}", timeout=30
    ) as resp:
        data = resp.read()
    media = "image/png" if path.lower().endswith(".png") else "image/jpeg"
    return base64.b64encode(data).decode(), media


def _format_added(added: list[dict]) -> str:
    if not added:
        return ("Не смог разобрать ни одного товара 😔\n"
                "Формат: Бренд; Название; Цена; Категория; Описание")
    lines = [f"Добавлено в магазин: {len(added)}\n"]
    for a in added:
        lines.append(f"• {a['name']} — {a['price_rub']} ₽ ({a['category']}) · {a['id']}")
    lines.append("\nУдалить: /удалить <id>")
    return "\n".join(lines)


@router.post("/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request) -> JSONResponse:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=404, detail="Бот не настроен")
    if secret != service.webhook_secret():
        raise HTTPException(status_code=403, detail="Неверный секрет")

    update = await request.json()
    msg = update.get("message") or update.get("edited_message") or {}
    chat_id = str(msg.get("chat", {}).get("id", ""))
    if not chat_id:
        return JSONResponse({"ok": True})

    # Только владелец: чужим отвечаем отказом и ничего не делаем.
    if settings.telegram_chat_id and chat_id != str(settings.telegram_chat_id):
        send_reply(chat_id, "Это служебный бот Aura — доступ только у владельца.")
        return JSONResponse({"ok": True})

    text = (msg.get("text") or msg.get("caption") or "").strip()
    low = text.lower()

    if low.startswith("/start") or low.startswith("/help"):
        send_reply(chat_id, HELP_TEXT)
        return JSONResponse({"ok": True})

    if low.startswith("/список") or low.startswith("/list"):
        items = service.list_custom()
        if not items:
            send_reply(chat_id, "Добавленных ботом товаров пока нет.")
        else:
            send_reply(chat_id, "Последние добавленные:\n" + "\n".join(
                f"• {i['name']} — {i['price_rub']} ₽ · {i['id']}" for i in items))
        return JSONResponse({"ok": True})

    if low.startswith("/удалить") or low.startswith("/del"):
        parts = text.split()
        pid = parts[1] if len(parts) > 1 else ""
        if pid and service.remove_product(pid):
            send_reply(chat_id, f"Удалил {pid} — из каталога исчез.")
        else:
            send_reply(chat_id, "Не нашёл такой id. Список: /список")
        return JSONResponse({"ok": True})

    photos = msg.get("photo") or []
    if photos:
        try:
            image_b64, media = download_photo(photos[-1]["file_id"])
        except Exception as exc:
            logger.warning("Не удалось скачать фото: %s", exc)
            send_reply(chat_id, "Не получилось скачать фото — попробуйте ещё раз.")
            return JSONResponse({"ok": True})
        send_reply(chat_id, "Распознаю прайс… ⏳")
        items = service.parse_products(text=text, image_b64=image_b64, media_type=media)
        added = service.add_products(items)
        send_reply(chat_id, _format_added(added))
        return JSONResponse({"ok": True})

    if text:
        items = service.parse_products(text=text)
        added = service.add_products(items)
        send_reply(chat_id, _format_added(added))
        return JSONResponse({"ok": True})

    send_reply(chat_id, HELP_TEXT)
    return JSONResponse({"ok": True})
