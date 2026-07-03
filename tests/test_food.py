"""Тесты AI-трекера еды: анализ и дневник."""

from app.food.engine import analyze_food
from app.food.schemas import FoodAnalysis
from app.food.service import day_nutrition, log_meal


def _img(seed: int = 1) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + bytes([seed % 256]) * (30 + seed)


def test_food_analysis_shape():
    a = analyze_food(_img(1))
    assert isinstance(a, FoodAnalysis)
    assert a.items
    # Итоги равны сумме позиций.
    assert a.total_calories == sum(i.calories for i in a.items)
    assert round(a.total_protein, 1) == round(sum(i.protein for i in a.items), 1)


def test_food_deterministic():
    a = analyze_food(_img(7))
    b = analyze_food(_img(7))
    assert [i.name for i in a.items] == [i.name for i in b.items]
    assert a.total_calories == b.total_calories


def test_empty_food_raises():
    try:
        analyze_food(b"")
    except ValueError:
        return
    raise AssertionError("Ожидалась ValueError на пустом изображении")


def test_day_nutrition_totals():
    a1 = analyze_food(_img(2))
    a2 = analyze_food(_img(3))
    log_meal("eater", a1, day="2026-07-03")
    log_meal("eater", a2, day="2026-07-03")
    day = day_nutrition("eater", "2026-07-03")
    assert day.entries == 2
    assert day.total_calories == a1.total_calories + a2.total_calories
