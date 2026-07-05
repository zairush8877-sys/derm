"""Движок анализа еды: Claude vision + демо-fallback (mock)."""

from __future__ import annotations

import base64
import json
import logging

from app.analysis.engine import _detect_media_type
from app.config import get_settings
from app.food.mock import mock_food_analysis
from app.food.prompts import SYSTEM_PROMPT, USER_PROMPT
from app.food.schemas import FoodAnalysis, FoodItem

logger = logging.getLogger("derm.food")


def _parse(raw: str, model: str) -> FoodAnalysis:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{") :]
    start, end = text.find("{"), text.rfind("}")
    data = json.loads(text[start : end + 1])

    items: list[FoodItem] = []
    for it in data.get("items", []):
        items.append(
            FoodItem(
                name=str(it.get("name", "Блюдо")).strip() or "Блюдо",
                grams=max(0, int(it.get("grams", 0))),
                calories=max(0, int(it.get("calories", 0))),
                protein=max(0.0, float(it.get("protein", 0))),
                fat=max(0.0, float(it.get("fat", 0))),
                carbs=max(0.0, float(it.get("carbs", 0))),
            )
        )
    if not items:
        raise ValueError("Claude не вернул позиции еды")
    summary = str(data.get("summary", "")).strip() or "Оценка калорий выполнена."
    return FoodAnalysis.from_items(items, summary, model=model)


def _analyze_with_claude(image_bytes: bytes) -> FoodAnalysis:
    from anthropic import Anthropic

    settings = get_settings()
    client = Anthropic(api_key=settings.anthropic_api_key)
    media_type = _detect_media_type(image_bytes)
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")

    message = client.messages.create(
        model=settings.model,
        max_tokens=1200,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image",
                     "source": {"type": "base64", "media_type": media_type, "data": b64}},
                    {"type": "text", "text": USER_PROMPT},
                ],
            }
        ],
    )
    raw = "".join(block.text for block in message.content if block.type == "text")
    return _parse(raw, model=settings.model)


def analyze_food(image_bytes: bytes) -> FoodAnalysis:
    """Анализ еды по фото. Демо-режим или ошибка -> детерминированный mock."""
    if not image_bytes:
        raise ValueError("Пустое изображение")

    settings = get_settings()
    if settings.mock_mode:
        return mock_food_analysis(image_bytes)
    try:
        return _analyze_with_claude(image_bytes)
    except Exception as exc:  # pragma: no cover
        logger.warning("Сбой анализа еды, fallback на демо: %s", exc)
        return mock_food_analysis(image_bytes)
