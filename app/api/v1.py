"""B2B API v1 — лицензируемые эндпоинты для beauty-брендов.

POST /v1/analyze   — фото -> структурированный анализ кожи (JSON)
POST /v1/protocol  — фото (+ квиз) -> персональный протокол ухода
GET  /v1/usage     — счётчик использования (для биллинга по сканам)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.analysis.engine import analyze_image
from app.api.auth import require_api_key
from app.db import store
from app.protocol.engine import build_protocol
from app.protocol.quiz import QuizAnswers
from app.schemas import Protocol, SkinAnalysis

router = APIRouter(prefix="/v1", tags=["B2B API"])


@router.post("/analyze", response_model=SkinAnalysis, summary="Анализ кожи по фото")
async def analyze(
    image: UploadFile = File(..., description="Фотография лица"),
    api_key: str = Depends(require_api_key),
) -> SkinAnalysis:
    data = await image.read()
    analysis = analyze_image(data)
    store.log_api_usage(api_key, "/v1/analyze")
    return analysis


@router.post("/protocol", response_model=Protocol, summary="Персональный протокол ухода")
async def protocol(
    image: UploadFile = File(..., description="Фотография лица"),
    age: int | None = Form(default=None),
    sensitivity: bool = Form(default=False),
    pregnant: bool = Form(default=False),
    sun_exposure: str = Form(default="средняя"),
    budget: str = Form(default="средний"),
    api_key: str = Depends(require_api_key),
) -> Protocol:
    data = await image.read()
    analysis = analyze_image(data)
    quiz = QuizAnswers(
        age=age,
        sensitivity=sensitivity,
        pregnant=pregnant,
        sun_exposure=sun_exposure,
        budget=budget,
    )
    store.log_api_usage(api_key, "/v1/protocol")
    return build_protocol(analysis, quiz)


@router.get("/usage", summary="Использование API (биллинг по сканам)")
async def usage(api_key: str = Depends(require_api_key)) -> dict:
    return {"api_key": api_key, "scans": store.usage_count(api_key)}
