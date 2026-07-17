"""FastAPI-приложение derm: B2B API + веб-демо + трекер.

Маршруты:
  /                 — демо-страница (загрузка фото -> анализ -> PDF)
  /tracker          — дашборд AI-трекера (динамика кожи)
  /v1/*             — B2B API (см. app/api/v1.py)
  /api/analyze      — внутренний эндпоинт для демо-фронтенда
  /api/report       — PDF-отчёт
  /api/scans        — история сканов пользователя
  /api/trends       — сводка динамики (трекер)
"""

from __future__ import annotations

import io
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.admin.api import router as admin_router
from app.analysis.engine import analyze_image
from app.api.auth import seed_demo_client
from app.api.v1 import router as api_v1
from app.assistant.api import router as assistant_router
from app.auth.api import router as auth_router
from app.auth.deps import token_user_id
from app.automation.scheduler import start_background_scheduler
from app.billing import service as credits
from app.billing.api import router as billing_router
from app.captcha.api import router as captcha_router
from app.config import get_settings
from app.db import store
from app.food.api import router as food_router
from app.lab.api import router as lab_router
from app.notifications.api import router as notifications_router
from app.protocol.engine import build_protocol
from app.protocol.quiz import QUIZ_QUESTIONS, QuizAnswers
from app.report.pdf import render_report
from app.shop import catalog
from app.shop.api import router as shop_router
from app.subscription.api import router as subscription_router
from app.tracker import service as tracker

_STATIC = Path(__file__).parent / "static"

app = FastAPI(
    title="Aura — wellness ecosystem",
    description=(
        "Premium wellness-экосистема: магазин (косметика, БАДы, спортпит, biohacking, "
        "healthy food), AI-анализ кожи, трекер еды, wellness-ассистент, лояльность, "
        "подписки и B2B API анализа кожи для брендов."
    ),
    version=__version__,
)


@app.on_event("startup")
def _startup() -> None:
    import logging
    import os

    store.init_db()
    seed_demo_client()
    start_background_scheduler()
    if not os.getenv("DERM_ADMIN_TOKEN"):
        logging.getLogger("derm").warning(
            "DERM_ADMIN_TOKEN не задан — используется небезопасный дефолт. "
            "Задайте свой токен в .env перед публикацией."
        )
    if get_settings().auth_secret == "dev-secret-change-me":
        logging.getLogger("derm").warning(
            "DERM_SECRET не задан — токены входа подписаны дефолтным секретом. "
            "Задайте DERM_SECRET в .env перед публикацией."
        )


# CORS: виджет анализа встраивается на сайты брендов и обращается к API
# с их домена. В проде ограничьте origins списком доменов клиентов.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(api_v1)
app.include_router(billing_router)
app.include_router(captcha_router)
app.include_router(shop_router)
app.include_router(food_router)
app.include_router(lab_router)
app.include_router(subscription_router)
app.include_router(assistant_router)
app.include_router(notifications_router)
app.include_router(admin_router)


@app.get("/health", tags=["служебное"])
def health() -> dict:
    s = get_settings()
    return {
        "status": "ok", "version": __version__, "mode": s.mode_label,
        "vision_model": s.model, "chat_model": s.chat_model,
    }


@app.get("/quiz", tags=["демо"])
def quiz_questions() -> list[dict]:
    return QUIZ_QUESTIONS


@app.post("/api/analyze", tags=["демо"])
async def api_analyze(
    image: UploadFile = File(...),
    user_id: str = Form(default="demo-user"),
    age: int | None = Form(default=None),
    sensitivity: bool = Form(default=False),
    pregnant: bool = Form(default=False),
    sun_exposure: str = Form(default="средняя"),
    budget: str = Form(default="средний"),
    auth_id: str | None = Depends(token_user_id),
) -> JSONResponse:
    """Платный фото-анализ кожи: списывает 1 кредит, затем анализ + протокол + трекер.

    Платным является ТОЛЬКО фото-анализ. Протокол по квизу, история и магазин —
    бесплатны (см. /api/protocol-quiz).
    """
    user_id = auth_id or user_id
    try:
        balance = credits.charge(user_id, 1)
    except credits.InsufficientCredits as exc:
        return JSONResponse(status_code=402, content={"error": str(exc), "need_payment": True})

    data = await image.read()
    analysis = analyze_image(data)
    quiz = QuizAnswers(
        age=age, sensitivity=sensitivity, pregnant=pregnant,
        sun_exposure=sun_exposure, budget=budget,
    )
    protocol = build_protocol(analysis, quiz)
    record = tracker.record_scan(user_id, analysis)
    # Рекомендации товаров из магазина под выявленные проблемы кожи.
    top_keys = [c.key for c in sorted(analysis.concerns, key=lambda x: x.score, reverse=True)[:4]]
    recommended = catalog.recommend_for_concerns(top_keys)
    # balance получен атомарно из charge() — без повторного чтения (TOCTOU).
    if balance == 0:
        credits.notify_zero_balance(user_id)
    return JSONResponse(
        {
            "scan_id": record.id,
            "analysis": analysis.model_dump(mode="json"),
            "protocol": protocol.model_dump(mode="json"),
            "recommended": [p.model_dump(mode="json") for p in recommended],
            "balance": balance,
        }
    )


@app.post("/api/protocol-quiz", tags=["демо"])
async def api_protocol_quiz(
    age: int | None = Form(default=None),
    sensitivity: bool = Form(default=False),
    pregnant: bool = Form(default=False),
    sun_exposure: str = Form(default="средняя"),
    budget: str = Form(default="средний"),
    skin_type: str = Form(default="нормальная"),
) -> JSONResponse:
    """БЕСПЛАТНЫЙ протокол по квизу без фото (базовый уход по типу кожи)."""
    from app.schemas import CONCERN_LABELS, Severity, SkinAnalysis, SkinConcern, SkinType

    try:
        st = SkinType(skin_type)
    except ValueError:
        st = SkinType.NORMAL
    # Нейтральный «профиль» без фото: умеренные баллы, чтобы собрать базовый уход.
    concerns = [
        SkinConcern(key=k, name=v, score=40, severity=Severity.MODERATE, confidence=0.5)
        for k, v in CONCERN_LABELS.items()
    ]
    analysis = SkinAnalysis(skin_type=st, concerns=concerns,
                            summary="Базовый профиль по квизу (без фото).", model="quiz")
    quiz = QuizAnswers(age=age, sensitivity=sensitivity, pregnant=pregnant,
                       sun_exposure=sun_exposure, budget=budget)
    protocol = build_protocol(analysis, quiz)
    return JSONResponse({"protocol": protocol.model_dump(mode="json")})


@app.post("/api/report", tags=["демо"])
async def api_report(
    image: UploadFile = File(...),
    age: int | None = Form(default=None),
    sensitivity: bool = Form(default=False),
    pregnant: bool = Form(default=False),
    sun_exposure: str = Form(default="средняя"),
    budget: str = Form(default="средний"),
) -> StreamingResponse:
    """Сформировать PDF-отчёт по фото."""
    data = await image.read()
    analysis = analyze_image(data)
    quiz = QuizAnswers(
        age=age, sensitivity=sensitivity, pregnant=pregnant,
        sun_exposure=sun_exposure, budget=budget,
    )
    protocol = build_protocol(analysis, quiz)
    pdf_bytes = render_report(analysis, protocol)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="derm-report.pdf"'},
    )


@app.get("/api/scans", tags=["трекер"])
def api_scans(user_id: str = "demo-user", auth_id: str | None = Depends(token_user_id)) -> JSONResponse:
    scans = store.list_scans(auth_id or user_id)
    return JSONResponse([s.model_dump(mode="json") for s in scans])


@app.get("/api/trends", tags=["трекер"])
def api_trends(user_id: str = "demo-user", auth_id: str | None = Depends(token_user_id)) -> JSONResponse:
    return JSONResponse(tracker.compute_trends(auth_id or user_id).model_dump(mode="json"))


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(_STATIC / "index.html")


@app.get("/skin", include_in_schema=False)
def skin_page() -> FileResponse:
    return FileResponse(_STATIC / "skin.html")


@app.get("/auth", include_in_schema=False)
def auth_page() -> FileResponse:
    return FileResponse(_STATIC / "auth.html")


@app.get("/account", include_in_schema=False)
def account_page() -> FileResponse:
    return FileResponse(_STATIC / "account.html")


@app.get("/legal", include_in_schema=False)
def legal_page() -> FileResponse:
    return FileResponse(_STATIC / "legal.html")


@app.get("/robots.txt", include_in_schema=False)
def robots() -> FileResponse:
    return FileResponse(_STATIC / "robots.txt", media_type="text/plain")


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap() -> FileResponse:
    return FileResponse(_STATIC / "sitemap.xml", media_type="application/xml")


@app.get("/tracker", include_in_schema=False)
def tracker_page() -> FileResponse:
    return FileResponse(_STATIC / "tracker.html")


@app.get("/shop", include_in_schema=False)
def shop_page() -> FileResponse:
    return FileResponse(_STATIC / "shop.html")


@app.get("/food", include_in_schema=False)
def food_page() -> FileResponse:
    return FileResponse(_STATIC / "food.html")


@app.get("/lab", include_in_schema=False)
def lab_page() -> FileResponse:
    return FileResponse(_STATIC / "lab.html")


@app.get("/assistant", include_in_schema=False)
def assistant_page() -> FileResponse:
    return FileResponse(_STATIC / "assistant.html")


@app.get("/subscription", include_in_schema=False)
def subscription_page() -> FileResponse:
    return FileResponse(_STATIC / "subscription.html")


@app.get("/admin", include_in_schema=False)
def admin_page() -> FileResponse:
    return FileResponse(_STATIC / "admin.html")


# Статика (css/js) монтируется последней, чтобы не перехватывать маршруты выше.
app.mount("/static", StaticFiles(directory=_STATIC), name="static")
