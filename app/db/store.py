"""Хранилище SQLite: сканы кожи и логи использования B2B API."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional

from app.config import get_settings
from app.schemas import ScanRecord, SkinAnalysis

_SCHEMA = """
CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    analysis_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_scans_user ON scans(user_id, created_at);

CREATE TABLE IF NOT EXISTS api_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_key TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Биллинг: баланс кредитов (1 кредит = 1 платный AI-скан) и платежи.
CREATE TABLE IF NOT EXISTS credits (
    user_id TEXT PRIMARY KEY,
    balance INTEGER NOT NULL DEFAULT 0,
    trial_granted INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS payments (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    amount_rub INTEGER NOT NULL,
    credits INTEGER NOT NULL,
    status TEXT NOT NULL,
    provider TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Магазин: корзина пользователя (товары берём из каталога в коде).
CREATE TABLE IF NOT EXISTS cart (
    user_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    qty INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (user_id, product_id)
);

-- Дневник питания: результаты фото-анализа еды.
CREATE TABLE IF NOT EXISTS food_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    day TEXT NOT NULL,
    analysis_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_food_user_day ON food_log(user_id, day);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(get_settings().db_path)
    conn.row_factory = sqlite3.Row
    return conn


# Публичный алиас для использования из модулей (billing/shop/food).
def connect() -> sqlite3.Connection:
    return _connect()


def init_db() -> None:
    """Создать таблицы, если их ещё нет."""
    with _connect() as conn:
        conn.executescript(_SCHEMA)


def save_scan(user_id: str, analysis: SkinAnalysis) -> ScanRecord:
    """Сохранить скан пользователя и вернуть запись с id."""
    created_at = analysis.created_at
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO scans (user_id, analysis_json, created_at) VALUES (?, ?, ?)",
            (user_id, analysis.model_dump_json(), created_at.isoformat()),
        )
        scan_id = int(cur.lastrowid)
    return ScanRecord(id=scan_id, user_id=user_id, analysis=analysis, created_at=created_at)


def list_scans(user_id: str, limit: int = 50) -> list[ScanRecord]:
    """Сканы пользователя, от старых к новым."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, user_id, analysis_json, created_at FROM scans "
            "WHERE user_id = ? ORDER BY created_at ASC, id ASC LIMIT ?",
            (user_id, limit),
        ).fetchall()

    records: list[ScanRecord] = []
    for row in rows:
        analysis = SkinAnalysis.model_validate_json(row["analysis_json"])
        records.append(
            ScanRecord(
                id=row["id"],
                user_id=row["user_id"],
                analysis=analysis,
                created_at=datetime.fromisoformat(row["created_at"]),
            )
        )
    return records


def latest_scan(user_id: str) -> Optional[ScanRecord]:
    scans = list_scans(user_id)
    return scans[-1] if scans else None


def log_api_usage(api_key: str, endpoint: str) -> None:
    """Зафиксировать вызов B2B API (для биллинга по сканам)."""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO api_usage (api_key, endpoint, created_at) VALUES (?, ?, ?)",
            (api_key, endpoint, datetime.now(timezone.utc).isoformat()),
        )


def usage_count(api_key: str) -> int:
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM api_usage WHERE api_key = ?", (api_key,)
        ).fetchone()
    return int(row["n"]) if row else 0
