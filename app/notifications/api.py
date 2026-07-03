"""HTTP-эндпоинты уведомлений."""

from __future__ import annotations

from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse

from app.notifications import service

router = APIRouter(prefix="/api/notifications", tags=["Уведомления"])


@router.get("")
def list_notifications(user_id: str = "demo-user") -> JSONResponse:
    return JSONResponse(
        {"unread": service.unread_count(user_id), "items": service.list_for(user_id)}
    )


@router.post("/read")
def mark_read(user_id: str = Form("demo-user")) -> JSONResponse:
    service.mark_all_read(user_id)
    return JSONResponse({"unread": 0})
