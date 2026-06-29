"""Движок анализа кожи: реальный Claude vision + демо-fallback (mock)."""

from __future__ import annotations

import base64
import json
import logging

from app.analysis.mock import mock_analysis
from app.analysis.prompts import SYSTEM_PROMPT, USER_PROMPT
from app.config import get_settings
from app.schemas import (
    CONCERN_LABELS,
    Severity,
    SkinAnalysis,
    SkinConcern,
    SkinType,
)

logger = logging.getLogger("derm.analysis")


def _detect_media_type(image_bytes: bytes) -> str:
    """Грубое определение типа изображения по сигнатуре."""
    if image_bytes[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def _coerce_severity(value: str, score: int) -> Severity:
    try:
        return Severity(value)
    except ValueError:
        if score <= 33:
            return Severity.LOW
        if score <= 66:
            return Severity.MODERATE
        return Severity.HIGH


def _parse_analysis(raw: str, model: str) -> SkinAnalysis:
    """Распарсить JSON-ответ Claude в SkinAnalysis (с мягкой валидацией)."""
    text = raw.strip()
    # Иногда модель оборачивает JSON в ```json ... ```
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{") :]
    start, end = text.find("{"), text.rfind("}")
    data = json.loads(text[start : end + 1])

    try:
        skin_type = SkinType(data.get("skin_type", "нормальная"))
    except ValueError:
        skin_type = SkinType.NORMAL

    concerns: list[SkinConcern] = []
    for item in data.get("concerns", []):
        key = item.get("key")
        if key not in CONCERN_LABELS:
            continue
        score = max(0, min(100, int(item.get("score", 0))))
        concerns.append(
            SkinConcern(
                key=key,
                name=CONCERN_LABELS[key],
                score=score,
                severity=_coerce_severity(str(item.get("severity", "")), score),
                confidence=max(0.0, min(1.0, float(item.get("confidence", 0.7)))),
            )
        )

    if not concerns:
        raise ValueError("Claude не вернул проблемы кожи в ожидаемом формате")

    return SkinAnalysis(
        skin_type=skin_type,
        concerns=concerns,
        summary=str(data.get("summary", "")).strip() or "Анализ кожи выполнен.",
        model=model,
    )


def _analyze_with_claude(image_bytes: bytes) -> SkinAnalysis:
    from anthropic import Anthropic  # импорт здесь, чтобы mock-режим не требовал SDK

    settings = get_settings()
    client = Anthropic(api_key=settings.anthropic_api_key)
    media_type = _detect_media_type(image_bytes)
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")

    message = client.messages.create(
        model=settings.model,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": b64},
                    },
                    {"type": "text", "text": USER_PROMPT},
                ],
            }
        ],
    )
    raw = "".join(block.text for block in message.content if block.type == "text")
    return _parse_analysis(raw, model=settings.model)


def analyze_image(image_bytes: bytes) -> SkinAnalysis:
    """Главная точка входа: анализ кожи по байтам изображения.

    В демо-режиме (нет ключа) или при любой ошибке реального вызова —
    прозрачно возвращается детерминированный mock, чтобы сценарий не падал.
    """
    if not image_bytes:
        raise ValueError("Пустое изображение")

    settings = get_settings()
    if settings.mock_mode:
        return mock_analysis(image_bytes)

    try:
        return _analyze_with_claude(image_bytes)
    except Exception as exc:  # pragma: no cover - сетевые/SDK ошибки
        logger.warning("Сбой реального анализа, fallback на демо-режим: %s", exc)
        return mock_analysis(image_bytes)
