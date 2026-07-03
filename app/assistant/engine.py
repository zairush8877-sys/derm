"""Wellness-ассистент: Claude-чат + эвристический демо-fallback.

Отвечает на вопросы по уходу за кожей, питанию, добавкам и восстановлению.
Не даёт медицинских диагнозов — только образовательные рекомендации.
"""

from __future__ import annotations

import logging

from app.config import get_settings

logger = logging.getLogger("derm.assistant")

SYSTEM_PROMPT = (
    "Ты — wellness-ассистент премиального сервиса Aura. Отвечай на русском, кратко и по делу, "
    "по темам: уход за кожей, питание и калораж, витамины/БАДы, спортпит, сон и восстановление, "
    "longevity/biohacking. Давай практичные шаги. НЕ ставь медицинских диагнозов и не назначай "
    "лечение — при тревожных симптомах советуй обратиться к врачу."
)

DISCLAIMER = "Образовательные рекомендации, не медицинский диагноз."

# Эвристические ответы для демо-режима (без ключа).
_RULES: list[tuple[tuple[str, ...], str]] = [
    (("сон", "выспа", "бессон"),
     "Для сна: ложитесь в одно время, минимум экранов за час до сна, магний B6 вечером, "
     "прохлада в спальне. Помогают очки с блокировкой синего света."),
    (("похуд", "вес", "калор", "дефицит"),
     "Снижение веса — умеренный дефицит калорий (~15–20%), белок 1.6–2 г/кг, силовые + шаги. "
     "Отслеживайте калораж через трекер еды в приложении."),
    (("кожа", "акне", "прыщ", "уход"),
     "Базовый уход: мягкое очищение, ниацинамид, увлажнение и SPF днём. При акне — BHA точечно. "
     "Сделайте фото-анализ кожи для персонального протокола."),
    (("витамин", "бад", "добавк", "дефицит"),
     "Частые дефициты: витамин D, омега-3, магний, железо/ферритин. Перед курсом лучше сдать "
     "анализы — в разделе диагностики есть панели."),
    (("протеин", "белок", "мышц", "трениров"),
     "Для набора/восстановления: белок 1.6–2.2 г/кг, креатин 3–5 г/день, сон и прогрессия нагрузок."),
    (("стресс", "тревог", "выгор"),
     "При стрессе: дыхательные практики, режим сна, магний, адаптогены (рейши/ашваганда), прогулки."),
]


def _mock_reply(message: str) -> str:
    text = message.lower()
    for keys, answer in _RULES:
        if any(k in text for k in keys):
            return answer
    return (
        "Расскажите подробнее о цели (кожа, питание, сон, энергия, тренировки) — подберу шаги. "
        "Также доступны фото-анализ кожи, трекер еды и персональный протокол ухода."
    )


def ask(message: str, history: list[dict] | None = None) -> dict:
    """Ответ ассистента. Возвращает {reply, model, disclaimer}."""
    message = (message or "").strip()
    if not message:
        raise ValueError("Пустой вопрос")

    settings = get_settings()
    if settings.mock_mode:
        return {"reply": _mock_reply(message), "model": "mock (демо-режим)", "disclaimer": DISCLAIMER}

    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=settings.anthropic_api_key)
        messages = []
        for turn in (history or [])[-6:]:
            role = "assistant" if turn.get("role") == "assistant" else "user"
            messages.append({"role": role, "content": str(turn.get("content", ""))})
        messages.append({"role": "user", "content": message})

        resp = client.messages.create(
            model=settings.model, max_tokens=600, system=SYSTEM_PROMPT, messages=messages
        )
        reply = "".join(b.text for b in resp.content if b.type == "text").strip()
        return {"reply": reply or _mock_reply(message), "model": settings.model, "disclaimer": DISCLAIMER}
    except Exception as exc:  # pragma: no cover
        logger.warning("Сбой ассистента, fallback на демо: %s", exc)
        return {"reply": _mock_reply(message), "model": "mock (fallback)", "disclaimer": DISCLAIMER}
