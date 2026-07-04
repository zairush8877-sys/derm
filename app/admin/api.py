"""Административная панель: сводка по заказам, подписке, B2B и уведомлениям.

Защита простым админ-токеном (заголовок X-Admin-Token). В проде — полноценная
авторизация сотрудников и роли (личный кабинет сотрудников, CRM/ERP).
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Form, Header, HTTPException
from fastapi.responses import JSONResponse

from app.automation import service as automation
from app.db import store
from app.shop import orders

router = APIRouter(prefix="/api/admin", tags=["Админ-панель"])

ADMIN_TOKEN = os.getenv("DERM_ADMIN_TOKEN", "admin-derm-2026")


def _guard(token: str) -> None:
    import hmac

    if not hmac.compare_digest(token.encode(), ADMIN_TOKEN.encode()):
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
            "status_flow": orders.STATUS_FLOW,
        }
    )


@router.post("/run-jobs")
def run_jobs(x_admin_token: str = Header(default="", alias="X-Admin-Token")) -> JSONResponse:
    """Запустить все автоматизации сейчас (для внешнего cron или кнопки в админке)."""
    _guard(x_admin_token)
    return JSONResponse(automation.run_all())


@router.get("/automation")
def automation_runs(x_admin_token: str = Header(default="", alias="X-Admin-Token")) -> JSONResponse:
    _guard(x_admin_token)
    return JSONResponse({"runs": automation.list_runs()})


@router.post("/ai-test")
def ai_test(x_admin_token: str = Header(default="", alias="X-Admin-Token")) -> JSONResponse:
    """Самопроверка ключа Anthropic: пробные вызовы чат- и vision-модели."""
    _guard(x_admin_token)
    from app.aitest import run_selftest

    return JSONResponse(run_selftest())


@router.post("/order-status")
def order_status(
    order_id: str = Form(...),
    status: str = Form(...),
    x_admin_token: str = Header(default="", alias="X-Admin-Token"),
) -> JSONResponse:
    """Сменить статус заказа (покупатель получит уведомление)."""
    _guard(x_admin_token)
    try:
        result = orders.update_status(order_id, status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return JSONResponse(result)
