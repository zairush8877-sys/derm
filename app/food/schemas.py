"""Схемы AI-трекера еды."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

FOOD_DISCLAIMER = (
    "Оценка калорий и БЖУ по фото — приблизительная, для ориентира, "
    "а не медицинская рекомендация по питанию."
)


class Micro(BaseModel):
    """Витамин/минерал с оценкой доли дневной нормы."""
    name: str = Field(..., description="Название (например, Витамин C)")
    amount: str = Field("", description="Кол-во с единицей (например, 45 мг)")
    daily_pct: int = Field(0, ge=0, le=999, description="≈ % дневной нормы")


class FoodItem(BaseModel):
    name: str = Field(..., description="Название блюда/продукта")
    grams: int = Field(..., ge=0, description="Оценка веса порции, г")
    calories: int = Field(..., ge=0, description="Калории, ккал")
    protein: float = Field(..., ge=0, description="Белки, г")
    fat: float = Field(..., ge=0, description="Жиры, г")
    carbs: float = Field(..., ge=0, description="Углеводы, г")


class FoodAnalysis(BaseModel):
    items: list[FoodItem]
    total_calories: int = Field(..., ge=0)
    total_protein: float = Field(..., ge=0)
    total_fat: float = Field(..., ge=0)
    total_carbs: float = Field(..., ge=0)
    summary: str
    micros: list[Micro] = Field(default_factory=list, description="Витамины и минералы")
    model: str
    disclaimer: str = FOOD_DISCLAIMER
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_items(cls, items: list[FoodItem], summary: str, model: str,
                   micros: list[Micro] | None = None) -> "FoodAnalysis":
        return cls(
            items=items,
            total_calories=sum(i.calories for i in items),
            total_protein=round(sum(i.protein for i in items), 1),
            total_fat=round(sum(i.fat for i in items), 1),
            total_carbs=round(sum(i.carbs for i in items), 1),
            summary=summary,
            micros=micros or [],
            model=model,
        )


class DayNutrition(BaseModel):
    user_id: str
    day: str
    entries: int
    total_calories: int
    total_protein: float
    total_fat: float
    total_carbs: float
    meals: list[FoodAnalysis]
