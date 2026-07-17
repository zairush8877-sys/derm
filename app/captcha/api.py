"""HTTP-эндпоинт капчи: выдача новой картинки."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.captcha import service

router = APIRouter(prefix="/api/captcha", tags=["Капча"])


@router.get("/new")
def new_captcha() -> JSONResponse:
    if not service.required():
        return JSONResponse({"required": False})
    data = service.new_challenge()
    return JSONResponse({"required": True, **data})
