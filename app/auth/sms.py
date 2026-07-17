"""Отправка SMS через провайдеров РФ: SMS.ru (по умолчанию) и SMSC.ru.

Без внешних зависимостей — urllib из стандартной библиотеки.
Провайдер выбирается переменной SMS_PROVIDER (smsru | smsc); если ключи
не заданы — платформа работает в демо-режиме (код показывается в интерфейсе).
"""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request

from app.config import get_settings

logger = logging.getLogger("derm.sms")

_TIMEOUT = 10  # секунд на HTTP-запрос к провайдеру


class SmsError(Exception):
    """Не удалось отправить SMS."""


def provider_configured() -> bool:
    """Настроен ли реальный SMS-провайдер (иначе — демо-режим)."""
    s = get_settings()
    if s.sms_provider == "smsc":
        return bool(s.sms_login and s.sms_password)
    return bool(s.sms_api_key)


def _http_get_json(url: str, params: dict) -> dict:
    """GET-запрос к провайдеру, ответ — JSON. Выделено для подмены в тестах."""
    full = url + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(full, timeout=_TIMEOUT) as resp:  # noqa: S310 — https провайдера
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise SmsError(f"Провайдер SMS недоступен: {exc}") from exc


def _send_smsru(phone: str, text: str) -> None:
    """SMS.ru: https://sms.ru/api/send (api_id из личного кабинета)."""
    s = get_settings()
    params = {"api_id": s.sms_api_key, "to": phone.lstrip("+"), "msg": text, "json": 1}
    if s.sms_sender:
        params["from"] = s.sms_sender
    data = _http_get_json("https://sms.ru/sms/send", params)
    if data.get("status") != "OK":
        raise SmsError(f"SMS.ru отклонил запрос: {data.get('status_text', data)}")
    sms_info = next(iter(data.get("sms", {}).values()), {})
    if sms_info.get("status") != "OK":
        raise SmsError(f"SMS.ru не принял номер: {sms_info.get('status_text', sms_info)}")


def _send_smsc(phone: str, text: str) -> None:
    """SMSC.ru: https://smsc.ru/api/http/ (логин и пароль/API-пароль)."""
    s = get_settings()
    params = {
        "login": s.sms_login, "psw": s.sms_password,
        "phones": phone, "mes": text, "fmt": 3, "charset": "utf-8",
    }
    if s.sms_sender:
        params["sender"] = s.sms_sender
    data = _http_get_json("https://smsc.ru/sys/send.php", params)
    if "error" in data:
        raise SmsError(f"SMSC.ru отклонил запрос: {data.get('error')} (код {data.get('error_code')})")


def call_code_supported() -> bool:
    """Доступен ли вход по звонку (реализован для SMS.ru)."""
    s = get_settings()
    return s.sms_provider != "smsc" and bool(s.sms_api_key)


def send_call_code(phone: str) -> str:
    """SMS.ru «авторизация по звонку»: робот звонит с уникального номера,
    кодом служат последние 4 цифры этого номера. Возвращает код,
    который нужно сверить с вводом пользователя."""
    s = get_settings()
    params = {"api_id": s.sms_api_key, "phone": phone.lstrip("+"), "json": 1}
    data = _http_get_json("https://sms.ru/code/call", params)
    if data.get("status") != "OK" or not data.get("code"):
        raise SmsError(f"SMS.ru не смог позвонить: {data.get('status_text', data)}")
    return str(data["code"])


def send_sms(phone: str, text: str) -> None:
    """Отправить SMS через настроенного провайдера. Бросает SmsError при сбое."""
    provider = get_settings().sms_provider
    logger.info("Отправка SMS через %s на %s…%s", provider, phone[:5], phone[-2:])
    if provider == "smsc":
        _send_smsc(phone, text)
    else:
        _send_smsru(phone, text)
