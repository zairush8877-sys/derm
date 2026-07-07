"""Уведомления владельцу магазина (Telegram) о важных событиях.

Включается, когда в .env заданы TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID
(см. CDEK_SETUP.md, раздел «Уведомления о заказах»). Без ключей — тихо
пропускается, ошибки отправки не ломают оформление заказа.
"""

from __future__ import annotations

import json
import logging
import urllib.request

from app.config import get_settings

logger = logging.getLogger("derm.owner")

_TIMEOUT = 8


def configured() -> bool:
    s = get_settings()
    return bool(s.telegram_bot_token and s.telegram_chat_id)


def notify_owner(text: str) -> bool:
    """Отправить сообщение владельцу в Telegram. Возвращает успех."""
    if not configured():
        return False
    s = get_settings()
    url = f"https://api.telegram.org/bot{s.telegram_bot_token}/sendMessage"
    payload = json.dumps({"chat_id": s.telegram_chat_id, "text": text}).encode()
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            ok = json.loads(resp.read().decode()).get("ok", False)
            if not ok:
                logger.warning("Telegram отклонил уведомление владельцу")
            return bool(ok)
    except Exception as exc:  # сбой уведомления не должен ломать заказ
        logger.warning("Не удалось отправить Telegram-уведомление: %s", exc)
        return False
