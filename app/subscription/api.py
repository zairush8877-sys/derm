"""HTTP-эндпоинты DTC-подписки на «живой» протокол ухода (#2)."""

from __future__ import annotations

from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse

from app.protocol.quiz import QuizAnswers
from app.subscription import service

router = APIRouter(prefix="/api/subscription", tags=["Подписка (протокол)"])


@router.post("/subscribe")
def subscribe(
    user_id: str = Form("demo-user"),
    age: int | None = Form(default=None),
    sensitivity: bool = Form(default=False),
    pregnant: bool = Form(default=False),
    sun_exposure: str = Form(default="средняя"),
    budget: str = Form(default="средний"),
    hormonal_phase: str = Form(default=""),
    skin_type: str = Form(default="нормальная"),
) -> JSONResponse:
    quiz = QuizAnswers(
        age=age, sensitivity=sensitivity, pregnant=pregnant,
        sun_exposure=sun_exposure, budget=budget,
        hormonal_phase=hormonal_phase or None,
    )
    protocol = service.subscribe(user_id, quiz)
    return JSONResponse({"active": True, "protocol": protocol.model_dump(mode="json")})


@router.get("/current")
def current(user_id: str = "demo-user", force: bool = False) -> JSONResponse:
    data = service.current_protocol(user_id, force=force)
    if data is None:
        return JSONResponse(status_code=404, content={"active": False, "error": "Нет активной подписки"})
    return JSONResponse(data)


@router.post("/cancel")
def cancel(user_id: str = Form("demo-user")) -> JSONResponse:
    service.cancel(user_id)
    return JSONResponse({"active": False})
