"""Тесты AI-трекера: хранение сканов и расчёт динамики."""

from app.analysis.engine import analyze_image
from app.tracker import service as tracker


def test_first_scan_is_baseline(png_bytes):
    analysis = analyze_image(png_bytes(10))
    tracker.record_scan("user-a", analysis)
    summary = tracker.compute_trends("user-a")
    assert summary.scans_count == 1
    # У всех проблем направление «новая», previous отсутствует.
    assert all(t.direction == "новая" for t in summary.trends)
    assert all(t.previous is None for t in summary.trends)


def test_trend_detects_improvement(png_bytes):
    a1 = analyze_image(png_bytes(11))
    for c in a1.concerns:
        c.score = 80
    tracker.record_scan("user-b", a1)

    a2 = analyze_image(png_bytes(12))
    for c in a2.concerns:
        c.score = 50  # стало лучше (ниже балл)
    tracker.record_scan("user-b", a2)

    summary = tracker.compute_trends("user-b")
    assert summary.scans_count == 2
    assert all(t.direction == "улучшение" for t in summary.trends)
    assert all(t.delta == -30 for t in summary.trends)


def test_trend_detects_worsening(png_bytes):
    a1 = analyze_image(png_bytes(13))
    for c in a1.concerns:
        c.score = 30
    tracker.record_scan("user-c", a1)

    a2 = analyze_image(png_bytes(14))
    for c in a2.concerns:
        c.score = 70  # стало хуже
    tracker.record_scan("user-c", a2)

    summary = tracker.compute_trends("user-c")
    assert all(t.direction == "ухудшение" for t in summary.trends)


def test_empty_user():
    summary = tracker.compute_trends("nobody")
    assert summary.scans_count == 0
    assert summary.trends == []
