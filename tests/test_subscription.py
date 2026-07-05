"""Тесты «живого» протокола и DTC-подписки."""

from datetime import datetime, timezone

from app.protocol.engine import build_protocol
from app.protocol.quiz import QuizAnswers, season_of
from app.schemas import CONCERN_LABELS, Severity, SkinAnalysis, SkinConcern, SkinType
from app.subscription import service


def _analysis(month: int) -> SkinAnalysis:
    concerns = [
        SkinConcern(key=k, name=v, score=40, severity=Severity.MODERATE, confidence=0.5)
        for k, v in CONCERN_LABELS.items()
    ]
    return SkinAnalysis(
        skin_type=SkinType.NORMAL, concerns=concerns, summary="", model="test",
        created_at=datetime(2026, month, 15, tzinfo=timezone.utc),
    )


def test_season_of():
    assert season_of(1) == "зима"
    assert season_of(7) == "лето"
    assert season_of(4) == "весна"
    assert season_of(10) == "осень"


def test_protocol_season_adapts():
    winter = build_protocol(_analysis(1))
    summer = build_protocol(_analysis(7))
    assert winter.season == "зима"
    assert summer.season == "лето"
    # Зимой добавляется плотный крем в вечерний уход.
    assert any("плотн" in s.step.lower() or "бальзам" in s.step.lower() for s in winter.pm_steps)


def test_protocol_age_adapts():
    young = build_protocol(_analysis(6), QuizAnswers(age=20))
    mature = build_protocol(_analysis(6), QuizAnswers(age=50))
    young_steps = " ".join(s.step.lower() for s in young.pm_steps)
    mature_steps = " ".join(s.step.lower() for s in mature.pm_steps)
    assert "пептид" in mature_steps  # зрелой коже добавляем пептиды
    assert "пептид" not in young_steps  # молодой — нет


def test_protocol_hormonal_phase():
    p = build_protocol(_analysis(6), QuizAnswers(hormonal_phase="лютеиновая"))
    pm = " ".join(s.step.lower() for s in p.pm_steps)
    assert "bha" in pm or "салицил" in pm


def test_subscription_lifecycle():
    proto = service.subscribe("sub-user", QuizAnswers(age=30))
    assert proto.am_steps and proto.season
    current = service.current_protocol("sub-user")
    assert current is not None and current["active"] is True
    # Принудительное обновление помечает refreshed_now.
    forced = service.current_protocol("sub-user", force=True)
    assert forced["refreshed_now"] is True
    service.cancel("sub-user")
    assert service.current_protocol("sub-user") is None
