"""Интеграция со СДЭК (API v2): расчёт тарифа доставки.

Включается, когда в .env заданы CDEK_ACCOUNT и CDEK_PASSWORD (выдаются
после заключения договора с ИП/юрлицом в личном кабинете СДЭК).
Без ключей магазин работает на фиксированных тарифах — как раньше.

Документация API: https://api-docs.cdek.ru
"""

from __future__ import annotations

import json
import logging
import time
import urllib.parse
import urllib.request

from app.config import get_settings

logger = logging.getLogger("derm.cdek")

_API = "https://api.cdek.ru/v2"
_TIMEOUT = 10

# Код города отправления (СДЭК city_code). 44 — Москва. Задаётся в .env.
DEFAULT_FROM_CITY = 44

# Тарифы СДЭК: 136 — посылка склад-склад (ПВЗ), 137 — склад-дверь (курьер).
TARIFF_PVZ = 136
TARIFF_COURIER = 137

_token_cache: dict = {"token": None, "expires": 0.0}


class CdekError(Exception):
    """Ошибка обращения к API СДЭК."""


def configured() -> bool:
    s = get_settings()
    return bool(s.cdek_account and s.cdek_password)


def _http_json(url: str, data: bytes | None = None, headers: dict | None = None) -> dict:
    req = urllib.request.Request(url, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise CdekError(f"СДЭК недоступен: {exc}") from exc


def _token() -> str:
    """OAuth-токен СДЭК (кэшируется до истечения)."""
    if _token_cache["token"] and time.time() < _token_cache["expires"] - 60:
        return _token_cache["token"]
    s = get_settings()
    body = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": s.cdek_account,
        "client_secret": s.cdek_password,
    }).encode()
    data = _http_json(f"{_API}/oauth/token", data=body,
                      headers={"Content-Type": "application/x-www-form-urlencoded"})
    if "access_token" not in data:
        raise CdekError(f"СДЭК не выдал токен: {data}")
    _token_cache["token"] = data["access_token"]
    _token_cache["expires"] = time.time() + int(data.get("expires_in", 3600))
    return _token_cache["token"]


def quote(to_city_code: int, weight_grams: int = 1000,
          tariff: int = TARIFF_PVZ) -> dict:
    """Рассчитать стоимость и срок доставки до города (city_code СДЭК)."""
    s = get_settings()
    payload = json.dumps({
        "tariff_code": tariff,
        "from_location": {"code": s.cdek_from_city or DEFAULT_FROM_CITY},
        "to_location": {"code": to_city_code},
        "packages": [{"weight": max(100, weight_grams)}],
    }).encode()
    data = _http_json(f"{_API}/calculator/tariff", data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_token()}",
    })
    if "delivery_sum" not in data:
        raise CdekError(f"СДЭК не рассчитал тариф: {data}")
    return {
        "fee_rub": int(round(float(data["delivery_sum"]))),
        "eta_days": int(data.get("period_max", 3)),
    }


def track_url(track_number: str) -> str:
    """Публичная ссылка отслеживания посылки СДЭК."""
    return f"https://www.cdek.ru/ru/tracking?order_id={urllib.parse.quote(track_number)}"
