"""Детерминированный демо-анализ (mock).

Использует хэш изображения, чтобы для одного фото результат был стабильным,
а для разных фото — разным. Это позволяет работать без ключа Anthropic и
демонстрировать полный сценарий (анализ → PDF → трекер) без затрат на API.
"""

from __future__ import annotations

import hashlib

from app.schemas import (
    CONCERN_LABELS,
    Severity,
    SkinAnalysis,
    SkinConcern,
    SkinType,
)

_SKIN_TYPES = list(SkinType)


def _severity_for(score: int) -> Severity:
    if score <= 33:
        return Severity.LOW
    if score <= 66:
        return Severity.MODERATE
    return Severity.HIGH


def mock_analysis(image_bytes: bytes) -> SkinAnalysis:
    """Сформировать стабильный демо-анализ по содержимому изображения."""
    digest = hashlib.sha256(image_bytes).digest()

    skin_type = _SKIN_TYPES[digest[0] % len(_SKIN_TYPES)]

    concerns: list[SkinConcern] = []
    for i, (key, name) in enumerate(CONCERN_LABELS.items()):
        # Раскладываем байты хэша по проблемам, получая значения 0-100.
        score = digest[(i + 1) % len(digest)] * 100 // 255
        confidence = round(0.6 + (digest[(i + 7) % len(digest)] % 40) / 100, 2)
        concerns.append(
            SkinConcern(
                key=key,
                name=name,
                score=score,
                severity=_severity_for(score),
                confidence=min(confidence, 0.99),
            )
        )

    top = sorted(concerns, key=lambda c: c.score, reverse=True)[:2]
    top_names = " и ".join(c.name.lower() for c in top)
    summary = (
        f"Тип кожи: {skin_type.value}. Основное внимание стоит уделить таким "
        f"зонам, как {top_names}. В целом состояние кожи рабочее — регулярный "
        f"уход даст заметный результат."
    )

    return SkinAnalysis(
        skin_type=skin_type,
        concerns=concerns,
        summary=summary,
        model="mock (демо-режим)",
    )
