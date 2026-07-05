"""Сервис DTC-подписки: «живой» протокол с авто-обновлением раз в 30 дней.

Протокол пересобирается под текущий сезон/возраст/гормональную фазу, когда
подходит дата обновления (или принудительно). Это ядро подписочной модели #2.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.db import store
from app.protocol.engine import build_protocol
from app.protocol.quiz import QuizAnswers, season_of
from app.schemas import (
    CONCERN_LABELS,
    Protocol,
    Severity,
    SkinAnalysis,
    SkinConcern,
    SkinType,
)

RENEWAL_DAYS = 30


def _profile_from_quiz(quiz: QuizAnswers, now: datetime) -> SkinAnalysis:
    """Базовый профиль кожи по квизу (без фото) для генерации протокола."""
    concerns = [
        SkinConcern(key=k, name=v, score=40, severity=Severity.MODERATE, confidence=0.5)
        for k, v in CONCERN_LABELS.items()
    ]
    return SkinAnalysis(
        skin_type=SkinType.NORMAL,
        concerns=concerns,
        summary="Профиль по квизу для «живого» протокола.",
        model="subscription",
        created_at=now,
    )


def _now() -> datetime:
    return datetime.now(timezone.utc)


def subscribe(user_id: str, quiz: QuizAnswers) -> Protocol:
    """Оформить подписку и сгенерировать первый протокол."""
    now = _now()
    quiz = quiz.model_copy(update={"season": quiz.season or season_of(now.month)})
    protocol = build_protocol(_profile_from_quiz(quiz, now), quiz)
    _save(user_id, quiz, protocol, now)
    return protocol


def _save(user_id: str, quiz: QuizAnswers, protocol: Protocol, now: datetime) -> None:
    next_update = now + timedelta(days=RENEWAL_DAYS)
    with store.connect() as conn:
        conn.execute(
            "INSERT INTO protocol_subscriptions "
            "(user_id, active, quiz_json, protocol_json, updated_at, next_update) "
            "VALUES (?, 1, ?, ?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET active=1, quiz_json=excluded.quiz_json, "
            "protocol_json=excluded.protocol_json, updated_at=excluded.updated_at, "
            "next_update=excluded.next_update",
            (user_id, quiz.model_dump_json(), protocol.model_dump_json(),
             now.isoformat(), next_update.isoformat()),
        )


def get_subscription(user_id: str) -> dict | None:
    with store.connect() as conn:
        row = conn.execute(
            "SELECT * FROM protocol_subscriptions WHERE user_id = ?", (user_id,)
        ).fetchone()
    return dict(row) if row else None


def current_protocol(user_id: str, force: bool = False) -> dict | None:
    """Вернуть текущий протокол, обновив его, если подошёл срок (или force)."""
    sub = get_subscription(user_id)
    if sub is None or not sub["active"]:
        return None

    now = _now()
    due = datetime.fromisoformat(sub["next_update"]) <= now
    refreshed = False
    if due or force:
        quiz = QuizAnswers.model_validate_json(sub["quiz_json"])
        quiz = quiz.model_copy(update={"season": season_of(now.month)})
        protocol = build_protocol(_profile_from_quiz(quiz, now), quiz)
        _save(user_id, quiz, protocol, now)
        sub = get_subscription(user_id)
        refreshed = True

    return {
        "active": bool(sub["active"]),
        "updated_at": sub["updated_at"],
        "next_update": sub["next_update"],
        "refreshed_now": refreshed,
        "protocol": Protocol.model_validate_json(sub["protocol_json"]).model_dump(mode="json"),
    }


def cancel(user_id: str) -> None:
    with store.connect() as conn:
        conn.execute(
            "UPDATE protocol_subscriptions SET active = 0 WHERE user_id = ?", (user_id,)
        )
