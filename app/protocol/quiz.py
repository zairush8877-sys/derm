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
]
