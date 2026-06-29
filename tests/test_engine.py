"""Тесты движка анализа кожи (демо-режим)."""

from app.analysis.engine import analyze_image
from app.schemas import CONCERN_LABELS, SkinAnalysis


def test_analysis_shape(png_bytes):
    result = analyze_image(png_bytes(1))
    assert isinstance(result, SkinAnalysis)
    # Оценены все девять проблем.
    assert len(result.concerns) == len(CONCERN_LABELS)
    keys = {c.key for c in result.concerns}
    assert keys == set(CONCERN_LABELS.keys())


def test_scores_within_bounds(png_bytes):
    result = analyze_image(png_bytes(2))
    for c in result.concerns:
        assert 0 <= c.score <= 100
        assert 0.0 <= c.confidence <= 1.0


def test_deterministic_for_same_image(png_bytes):
    a = analyze_image(png_bytes(5))
    b = analyze_image(png_bytes(5))
    assert [c.score for c in a.concerns] == [c.score for c in b.concerns]
    assert a.skin_type == b.skin_type


def test_different_images_differ(png_bytes):
    a = analyze_image(png_bytes(1))
    b = analyze_image(png_bytes(99))
    assert [c.score for c in a.concerns] != [c.score for c in b.concerns]


def test_empty_image_raises():
    try:
        analyze_image(b"")
    except ValueError:
        return
    raise AssertionError("Ожидалась ValueError на пустом изображении")
