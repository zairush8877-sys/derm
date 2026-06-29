"""Тесты движка персональных протоколов."""

from app.analysis.engine import analyze_image
from app.protocol.engine import build_protocol
from app.protocol.quiz import QuizAnswers


def test_protocol_has_am_and_pm(png_bytes):
    analysis = analyze_image(png_bytes(3))
    protocol = build_protocol(analysis)
    assert protocol.am_steps and protocol.pm_steps
    # SPF обязателен в утреннем уходе.
    cats = " ".join(s.category for s in protocol.am_steps).lower()
    assert "солн" in cats


def test_next_review_is_30_days(png_bytes):
    analysis = analyze_image(png_bytes(4))
    protocol = build_protocol(analysis)
    assert (protocol.next_review - analysis.created_at).days == 30


def test_pregnancy_excludes_retinoids(png_bytes):
    analysis = analyze_image(png_bytes(7))
    # Принудительно делаем морщины главной проблемой.
    for c in analysis.concerns:
        if c.key == "wrinkles":
            c.score = 95
    protocol = build_protocol(analysis, QuizAnswers(pregnant=True))
    pm = " ".join(s.step for s in protocol.pm_steps).lower()
    assert "ретино" not in pm
