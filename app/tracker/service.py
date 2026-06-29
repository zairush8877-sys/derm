"""AI-трекер: сохранение сканов и расчёт динамики кожи во времени."""

from __future__ import annotations

from app.db import store
from app.schemas import (
    ConcernTrend,
    ScanRecord,
    SkinAnalysis,
    TrackerSummary,
)


def record_scan(user_id: str, analysis: SkinAnalysis) -> ScanRecord:
    """Сохранить новый скан пользователя."""
    return store.save_scan(user_id, analysis)


def _direction(delta: int | None) -> str:
    if delta is None:
        return "новая"
    # Для проблем кожи МЕНЬШЕ score = ЛУЧШЕ (проблема выражена слабее).
    if delta < -2:
        return "улучшение"
    if delta > 2:
        return "ухудшение"
    return "без изменений"


def compute_trends(user_id: str) -> TrackerSummary:
    """Сравнить последний скан с предыдущим и собрать сводку динамики."""
    scans = store.list_scans(user_id)
    if not scans:
        return TrackerSummary(user_id=user_id, scans_count=0, trends=[], overall="Сканов пока нет.")

    current = scans[-1].analysis
    previous = scans[-2].analysis if len(scans) >= 2 else None
    prev_map = {c.key: c.score for c in previous.concerns} if previous else {}

    trends: list[ConcernTrend] = []
    improved = worsened = 0
    for concern in current.concerns:
        prev_score = prev_map.get(concern.key)
        delta = (concern.score - prev_score) if prev_score is not None else None
        direction = _direction(delta)
        if direction == "улучшение":
            improved += 1
        elif direction == "ухудшение":
            worsened += 1
        trends.append(
            ConcernTrend(
                key=concern.key,
                name=concern.name,
                current=concern.score,
                previous=prev_score,
                delta=delta,
                direction=direction,
            )
        )

    if previous is None:
        overall = "Это первый скан — он станет точкой отсчёта для отслеживания прогресса."
    elif improved > worsened:
        overall = f"Положительная динамика: улучшений — {improved}, ухудшений — {worsened}. Продолжайте уход."
    elif worsened > improved:
        overall = f"Есть над чем поработать: ухудшений — {worsened}, улучшений — {improved}. Стоит скорректировать протокол."
    else:
        overall = "Кожа стабильна. Поддерживайте текущий уход и регулярность."

    return TrackerSummary(
        user_id=user_id,
        scans_count=len(scans),
        trends=trends,
        overall=overall,
    )
