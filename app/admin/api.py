"""Административная панель: сводка по заказам, подписке, B2B и уведомлениям.

Защита простым админ-токеном (заголовок X-Admin-Token). В проде — полноценная
авторизация сотрудников и роли (личный кабинет сотрудников, CRM/ERP).
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse

from app.db import store

router = APIRouter(prefix="/api/admin", tags=["Админ-панель"])

ADMIN_TOKEN = os.getenv("DERM_ADMIN_TOKEN", "admin-derm-2026")


def _guard(token: str) -> None:
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Неверный админ-токен")


@router.get("/overview")
def overview(x_admin_token: str = Header(default="", alias="X-Admin-Token")) -> JSONResponse:
    _guard(x_admin_token)
    with store.connect() as conn:
        def scalar(sql: str) -> int:
            row = conn.execute(sql).fetchone()
            return int(row[0]) if row else 0

        orders_count = scalar("SELECT COUNT(*) FROM orders")
        revenue = scalar("SELECT COALESCE(SUM(total_rub),0) FROM orders")
        subs_active = scalar("SELECT COUNT(*) FROM protocol_subscriptions WHERE active = 1")
        clients = scalar("SELECT COUNT(*) FROM clients")
        scans = scalar("SELECT COUNT(*) FROM scans")
        food = scalar("SELECT COUNT(*) FROM food_log")
        b2b_calls = scalar("SELECT COUNT(*) FROM api_usage")

        recent = conn.execute(
            "SELECT id, user_id, total_rub, status, created_at FROM orders "
            "ORDER BY created_at DESC LIMIT 10"
        ).fetchall()

    return JSONResponse(
        {
            "orders": {"count": orders_count, "revenue_rub": revenue},
            "subscriptions_active": subs_active,
            "b2b": {"clients": clients, "api_calls": b2b_calls},
            "ai": {"skin_scans": scans, "food_scans": food},
            "recent_orders": [dict(r) for r in recent],
        }
    )
