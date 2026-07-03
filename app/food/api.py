"""HTTP-эндпоинты AI-трекера еды (платный фото-анализ)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse

from app.auth.deps import token_user_id
from app.billing import service as credits
from app.food import service
from app.food.engine import analyze_food

router = APIRouter(prefix="/api/food", tags=["Питание"])


@router.post("/analyze")
async def analyze(
    image: UploadFile = File(...),
    user_id: str = Form("demo-user"),
    auth_id: str | None = Depends(token_user_id),
) -> JSONResponse:
    """Платный фото-анализ еды: списывает 1 кредит, затем анализирует и логирует."""
    user_id = auth_id or user_id
    try:
        credits.charge(user_id, 1)
    except credits.InsufficientCredits as exc:
        return JSONResponse(status_code=402, content={"error": str(exc), "need_payment": True})

    data = await image.read()
    analysis = analyze_food(data)
    service.log_meal(user_id, analysis)
    return JSONResponse(
        {"analysis": analysis.model_dump(mode="json"), "balance": credits.balance(user_id)}
    )


@router.get("/day")
def day(
    user_id: str = "demo-user",
    day: str | None = None,
    auth_id: str | None = Depends(token_user_id),
) -> JSONResponse:
    return JSONResponse(service.day_nutrition(auth_id or user_id, day).model_dump(mode="json"))
