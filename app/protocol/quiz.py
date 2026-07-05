"""Квиз для персонализации протокола ухода."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class QuizAnswers(BaseModel):
    age: Optional[int] = Field(None, ge=10, le=100, description="Возраст")
    sensitivity: bool = Field(False, description="Чувствительная/реактивная кожа")
    pregnant: bool = Field(False, description="Беременность/ГВ (исключаем ретиноиды и кислоты)")
    sun_exposure: str = Field("средняя", description="низкая | средняя | высокая")
    budget: str = Field("средний", description="низкий | средний | высокий")
    goals: list[str] = Field(default_factory=list, description="Цели: anti-age, увлажнение, ровный тон, акне")
    # Гормональная фаза для «живого» протокола (#2): менструальная | фолликулярная
    # | овуляторная | лютеиновая | менопауза. None — не учитывать.
    hormonal_phase: Optional[str] = Field(None, description="Фаза цикла/гормональный статус")
    # Явное указание сезона (иначе берётся из даты анализа).
    season: Optional[str] = Field(None, description="зима | весна | лето | осень")


# Вопросы для отрисовки на фронтенде (демо-квиз).
QUIZ_QUESTIONS = [
    {
        "key": "age",
        "title": "Сколько вам лет?",
        "type": "number",
    },
    {
        "key": "sensitivity",
        "title": "Кожа склонна к раздражению и реактивности?",
        "type": "bool",
    },
    {
        "key": "pregnant",
        "title": "Беременность или грудное вскармливание?",
        "type": "bool",
    },
    {
        "key": "sun_exposure",
        "title": "Сколько времени проводите на солнце?",
        "type": "choice",
        "options": ["низкая", "средняя", "высокая"],
    },
    {
        "key": "budget",
        "title": "Бюджет на уход?",
        "type": "choice",
        "options": ["низкий", "средний", "высокий"],
    },
    {
        "key": "goals",
        "title": "Главные цели ухода?",
        "type": "multi",
        "options": ["anti-age", "увлажнение", "ровный тон", "акне"],
    },
    {
        "key": "hormonal_phase",
        "title": "Гормональная фаза (для «живого» протокола)?",
        "type": "choice",
        "options": ["менструальная", "фолликулярная", "овуляторная", "лютеиновая", "менопауза"],
    },
]


def season_of(month: int) -> str:
    """Определить сезон по номеру месяца (для сезонной адаптации протокола)."""
    if month in (12, 1, 2):
        return "зима"
    if month in (3, 4, 5):
        return "весна"
    if month in (6, 7, 8):
        return "лето"
    return "осень"
