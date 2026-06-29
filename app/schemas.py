"""Типизированные схемы данных (Pydantic) — общий контракт для всех модулей."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

DISCLAIMER = (
    "Это косметический анализ кожи для подбора ухода, а не медицинский диагноз. "
    "Он не заменяет очную консультацию врача-дерматолога."
)


class Severity(str, Enum):
    LOW = "низкая"
    MODERATE = "умеренная"
    HIGH = "высокая"


class SkinType(str, Enum):
    DRY = "сухая"
    OILY = "жирная"
    COMBINATION = "комбинированная"
    NORMAL = "нормальная"
    SENSITIVE = "чувствительная"


# Канонический список оцениваемых проблем кожи (ключ -> русское название).
CONCERN_LABELS: dict[str, str] = {
    "acne": "Акне и высыпания",
    "redness": "Покраснения",
    "pigmentation": "Пигментация",
    "wrinkles": "Морщины и старение",
    "hydration": "Увлажнённость",
    "pores": "Расширенные поры",
    "oiliness": "Жирность кожи",
    "dark_circles": "Тёмные круги",
    "texture": "Текстура и рельеф",
}


class SkinConcern(BaseModel):
    key: str = Field(..., description="Технический ключ проблемы")
    name: str = Field(..., description="Название проблемы на русском")
    score: int = Field(..., ge=0, le=100, description="Выраженность 0–100")
    severity: Severity
    confidence: float = Field(..., ge=0.0, le=1.0, description="Уверенность модели 0–1")


class SkinAnalysis(BaseModel):
    skin_type: SkinType
    concerns: list[SkinConcern]
    summary: str = Field(..., description="Краткое резюме на русском")
    model: str = Field(..., description="Модель/режим, сформировавший анализ")
    disclaimer: str = DISCLAIMER
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProtocolStep(BaseModel):
    step: str = Field(..., description="Что делать")
    category: str = Field(..., description="Категория средства")
    why: str = Field(..., description="Зачем это нужно")


class Protocol(BaseModel):
    am_steps: list[ProtocolStep]
    pm_steps: list[ProtocolStep]
    weekly: list[str] = Field(default_factory=list, description="Еженедельные процедуры")
    lifestyle: list[str] = Field(default_factory=list, description="Рекомендации по образу жизни")
    next_review: datetime = Field(..., description="Дата следующего обновления протокола")
    disclaimer: str = DISCLAIMER


class ScanRecord(BaseModel):
    id: int
    user_id: str
    analysis: SkinAnalysis
    created_at: datetime


class ConcernTrend(BaseModel):
    key: str
    name: str
    current: int
    previous: Optional[int] = None
    delta: Optional[int] = None
    direction: str = Field(..., description="улучшение / ухудшение / без изменений / новая")


class TrackerSummary(BaseModel):
    user_id: str
    scans_count: int
    trends: list[ConcernTrend]
    overall: str = Field(..., description="Общий вывод по динамике кожи")
