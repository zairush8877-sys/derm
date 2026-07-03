"""B2B API v1 — лицензируемые эндпоинты для beauty-брендов.

Монетизация #1: pay-per-scan или SaaS-подписка с месячной квотой сканов.
Каждый вызов анализа логируется и учитывается в квоте/биллинге бренда.

POST /v1/analyze   — фото -> структурированный анализ кожи (JSON)
POST /v1/protocol  — фото (+ квиз) -> персональный протокол ухода
GET  /v1/usage     — план, использование за месяц и оценка стоимости
GET  /v1/plans     — доступные тарифы
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.analysis.engine import analyze_image
from app.api.auth import require_client
from app.api.plans import PLANS, estimate_cost_usd, get_plan
from app.db import store
from app.protocol.engine import build_protocol
from app.protocol.quiz import QuizAnswers
from app.schemas import Protocol, SkinAnalysis

router = APIRouter(prefix="/v1", tags=["B2B API"])

API_VERSION = "1.0"


def _month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _enforce_quota(client: dict) -> None:
    """Проверить месячную квоту плана. payg — без жёсткого лимита."""
    plan = get_plan(client["plan"])
    if plan.included_scans <= 0:
        return  # pay-as-you-go: лимита нет, просто тарификация за скан
    used = store.usage_count_month(client["api_key"], _month())
    # Мягкий потолок: включённая квота + 100% overage перед блокировкой.
    hard_cap = plan.included_scans * 2
    if used >= hard_cap:
        raise HTTPException(
            status_code=429,
            detail=f"Превышен лимит плана {plan.name} ({hard_cap} сканов/мес). Обновите тариф.",
        )


@router.get("/plans", summary="Доступные тарифы")
async def plans() -> dict:
    return {
        "plans": [
            {
                "id": p.id, "name": p.name, "monthly_price_usd": p.monthly_price_usd,
                "included_scans": p.included_scans, "price_per_scan_usd": p.price_per_scan_usd,
            }
            for p in PLANS.values()
        ]
    }


@router.post("/analyze", response_model=SkinAnalysis, summary="Анализ кожи по фото")
async def analyze(
    image: UploadFile = File(..., description="Фотография лица"),
    client: dict = Depends(require_client),
) -> SkinAnalysis:
    _enforce_quota(client)
    data = await image.read()
    analysis = analyze_image(data)
    store.log_api_usage(client["api_key"], "/v1/analyze")
    return analysis


@router.post("/protocol", response_model=Protocol, summary="Персональный протокол ухода")
async def protocol(
    image: UploadFile = File(..., description="Фотография лица"),
    age: int | None = Form(default=None),
    sensitivity: bool = Form(default=False),
    pregnant: bool = Form(default=False),
    sun_exposure: str = Form(default="средняя"),
    budget: str = Form(default="средний"),
    hormonal_phase: str = Form(default=""),
    client: dict = Depends(require_client),
) -> Protocol:
    _enforce_quota(client)
    data = await image.read()
    analysis = analyze_image(data)
    quiz = QuizAnswers(
        age=age, sensitivity=sensitivity, pregnant=pregnant,
        sun_exposure=sun_exposure, budget=budget, hormonal_phase=hormonal_phase or None,
    )
    store.log_api_usage(client["api_key"], "/v1/protocol")
    return build_protocol(analysis, quiz)


@router.get("/usage", summary="Использование и биллинг за месяц")
async def usage(client: dict = Depends(require_client)) -> dict:
    plan = get_plan(client["plan"])
    scans_month = store.usage_count_month(client["api_key"], _month())
    return {
        "brand": client["brand_name"],
        "plan": {"id": plan.id, "name": plan.name, "included_scans": plan.included_scans},
        "month": _month(),
        "scans_this_month": scans_month,
        "included_remaining": max(0, plan.included_scans - scans_month),
        "estimated_cost_usd": estimate_cost_usd(plan.id, scans_month),
        "scans_total": store.usage_count(client["api_key"]),
        "api_version": API_VERSION,
    }
