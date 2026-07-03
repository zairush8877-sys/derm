"""Лента уведомлений приложения (in-app push).

Полноценный web-push (Service Worker + VAPID) — точка расширения на будущее;
сейчас уведомления хранятся и отдаются приложению для показа в ленте/бейдже.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.db import store


def push(user_id: str, title: str, body: str) -> None:
    with store.connect() as conn:
        conn.execute(
            "INSERT INTO notifications (user_id, title, body, read, created_at) VALUES (?, ?, ?, 0, ?)",
            (user_id, title, body, datetime.now(timezone.utc).isoformat()),
        )


def list_for(user_id: str, limit: int = 50) -> list[dict]:
    with store.connect() as conn:
        rows = conn.execute(
            "SELECT id, title, body, read, created_at FROM notifications "
            "WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def unread_count(user_id: str) -> int:
    with store.connect() as conn:
        r = conn.execute(
            "SELECT COUNT(*) AS n FROM notifications WHERE user_id = ? AND read = 0", (user_id,)
        ).fetchone()
    return int(r["n"]) if r else 0


def mark_all_read(user_id: str) -> None:
    with store.connect() as conn:
        conn.execute("UPDATE notifications SET read = 1 WHERE user_id = ?", (user_id,))
