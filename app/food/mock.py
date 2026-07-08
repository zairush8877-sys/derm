"""Детерминированный демо-анализ еды (без ключа Anthropic)."""

from __future__ import annotations

import hashlib

from app.food.schemas import FoodAnalysis, FoodItem, Micro

# Небольшая база «блюд» для демо-распознавания.
_DISHES = [
    ("Куриная грудка", 0.31, 0.036, 0.0),   # на грамм: белок, жир, углеводы
    ("Рис отварной", 0.027, 0.003, 0.28),
    ("Овощной салат", 0.015, 0.05, 0.06),
    ("Гречка", 0.045, 0.011, 0.20),
    ("Лосось запечённый", 0.20, 0.13, 0.0),
    ("Паста с соусом", 0.05, 0.03, 0.25),
    ("Яичница", 0.13, 0.11, 0.011),
    ("Творог 5%", 0.17, 0.05, 0.03),
    ("Банан", 0.011, 0.003, 0.23),
    ("Хлеб цельнозерновой", 0.09, 0.03, 0.43),
]


def _kcal(protein: float, fat: float, carbs: float) -> int:
    return int(round(protein * 4 + fat * 9 + carbs * 4))


def mock_food_analysis(image_bytes: bytes) -> FoodAnalysis:
    digest = hashlib.sha256(image_bytes).digest()
    n_items = 1 + digest[0] % 3  # 1..3 позиции

    items: list[FoodItem] = []
    for i in range(n_items):
        dish, p_g, f_g, c_g = _DISHES[digest[(i * 3 + 1) % len(digest)] % len(_DISHES)]
        grams = 80 + (digest[(i * 3 + 2) % len(digest)] % 220)  # 80..300 г
        protein = round(p_g * grams, 1)
        fat = round(f_g * grams, 1)
        carbs = round(c_g * grams, 1)
        items.append(
            FoodItem(
                name=dish,
                grams=grams,
                calories=_kcal(protein, fat, carbs),
                protein=protein,
                fat=fat,
                carbs=carbs,
            )
        )

    total = sum(i.calories for i in items)
    summary = f"Всего примерно {total} ккал, {len(items)} поз. Оценка ориентировочная."
    _MICROS = ["Витамин C", "Железо", "Кальций", "Магний", "Калий", "Витамин A", "Цинк", "B12"]
    micros = [
        Micro(name=_MICROS[digest[(i + 5) % len(digest)] % len(_MICROS)],
              amount="", daily_pct=5 + digest[(i + 9) % len(digest)] % 60)
        for i in range(3)
    ]
    # Без дублей названий.
    seen, uniq = set(), []
    for m in micros:
        if m.name not in seen:
            uniq.append(m)
            seen.add(m.name)
    return FoodAnalysis.from_items(items, summary, model="mock (демо-режим)", micros=uniq)
