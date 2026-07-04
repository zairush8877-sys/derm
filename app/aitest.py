"""Самопроверка подключения реального AI (ключа Anthropic).

Делает два дешёвых пробных вызова: текстовый (чат-модель) и vision
(модель анализа, картинка 2x2 px). Стоимость проверки — доли цента.
Запуск: python -m app.cli aitest  или  POST /api/admin/ai-test.
"""

from __future__ import annotations

import base64
import struct
import zlib

from app.config import get_settings


def _tiny_png() -> bytes:
    """Красный PNG 2x2 — минимальная валидная картинка для vision-пробы."""
    w = h = 2
    raw = b"".join(b"\x00" + b"\xc8\x3c\x3c" * w for _ in range(h))

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))


def run_selftest() -> dict:
    """Проверить ключ и обе модели. Возвращает подробный отчёт."""
    settings = get_settings()
    report: dict = {
        "key_present": bool(settings.anthropic_api_key),
        "mock_mode": settings.mock_mode,
        "vision_model": settings.model,
        "chat_model": settings.chat_model,
        "chat": None,
        "vision": None,
        "ok": False,
    }
    if not settings.anthropic_api_key:
        report["hint"] = (
            "Ключ не задан. Добавьте ANTHROPIC_API_KEY=sk-ant-... в .env и "
            "перезапустите приложение (docker compose up -d)."
        )
        return report

    from anthropic import Anthropic

    client = Anthropic(api_key=settings.anthropic_api_key)

    # 1) Текстовый пинг (чат-модель, ~30 токенов).
    try:
        r = client.messages.create(
            model=settings.chat_model,
            max_tokens=30,
            messages=[{"role": "user", "content": "Ответь ровно одним словом: работает"}],
        )
        text = "".join(b.text for b in r.content if b.type == "text").strip()
        report["chat"] = f"ok: «{text[:60]}»"
    except Exception as exc:
        report["chat"] = f"error: {type(exc).__name__}: {str(exc)[:300]}"

    # 2) Vision-пинг (модель анализа, крошечная картинка).
    try:
        b64 = base64.standard_b64encode(_tiny_png()).decode()
        r = client.messages.create(
            model=settings.model,
            max_tokens=30,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image",
                     "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                    {"type": "text", "text": "Какой цвет на картинке? Одно слово."},
                ],
            }],
        )
        text = "".join(b.text for b in r.content if b.type == "text").strip()
        report["vision"] = f"ok: «{text[:60]}»"
    except Exception as exc:
        report["vision"] = f"error: {type(exc).__name__}: {str(exc)[:300]}"

    report["ok"] = (str(report["chat"]).startswith("ok") and str(report["vision"]).startswith("ok"))
    if not report["ok"] and not report.get("hint"):
        report["hint"] = (
            "Частые причины: неверный ключ; нет баланса на console.anthropic.com "
            "(нужно пополнить Credits); ключ от другого воркспейса."
        )
    return report
