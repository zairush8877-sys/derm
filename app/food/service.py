"""Дневник питания: сохранение анализов еды и суточные итоги."""

from __future__ import annotations

from datetime import datetime, timezone

from app.db import store
from app.food.schemas import DayNutrition, FoodAnalysis


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def log_meal(user_id: str, analysis: FoodAnalysis, day: str | None = None) -> None:
    day = day or _today()
    with store.connect() as conn:
        conn.execute(
            "INSERT INTO food_log (user_id, day, analysis_json, created_at) VALUES (?, ?, ?, ?)",
            (user_id, day, analysis.model_dump_json(), analysis.created_at.isoformat()),
        )


def day_nutrition(user_id: str, day: str | None = None) -> DayNutrition:
    day = day or _today()
    with store.connect() as conn:
        rows = conn.execute(
            "SELECT analysis_json FROM food_log WHERE user_id = ? AND day = ? ORDER BY id ASC",
            (user_id, day),
        ).fetchall()

    meals = [FoodAnalysis.model_validate_json(r["analysis_json"]) for r in rows]
    return DayNutrition(
        user_id=user_id,
        day=day,
        entries=len(meals),
        total_calories=sum(m.total_calories for m in meals),
        total_protein=round(sum(m.total_protein for m in meals), 1),
        total_fat=round(sum(m.total_fat for m in meals), 1),
        total_carbs=round(sum(m.total_carbs for m in meals), 1),
        meals=meals,
    )
