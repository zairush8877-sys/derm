"""HTTP-эндпоинт wellness-ассистента."""

from __future__ import annotations

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from app.assistant import engine

router = APIRouter(prefix="/api/assistant", tags=["Wellness-ассистент"])


@router.post("/chat")
def chat(payload: dict = Body(...)) -> JSONResponse:
    message = payload.get("message", "")
    history = payload.get("history", [])
    try:
        result = engine.ask(message, history)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    return JSONResponse(result)
