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

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.analysis.engine import analyze_image
from app.api.v1 import router as api_v1
from app.config import get_settings
from app.db import store
from app.protocol.engine import build_protocol
from app.protocol.quiz import QUIZ_QUESTIONS, QuizAnswers
from app.report.pdf import render_report
from app.tracker import service as tracker

_STATIC = Path(__file__).parent / "static"

app = FastAPI(
    title="derm — AI-анализ кожи",
    description="Дерматологически обоснованный AI-анализ кожи: B2B API, веб-демо и AI-трекер.",
    version=__version__,
)


@app.on_event("startup")
def _startup() -> None:
    store.init_db()


app.include_router(api_v1)


@app.get("/health", tags=["служебное"])
def health() -> dict:
    s = get_settings()
    return {"status": "ok", "version": __version__, "mode": s.mode_label}


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
) -> JSONResponse:
    """Анализ для демо-фронтенда: анализ + протокол + сохранение в трекер."""
    data = await image.read()
    analysis = analyze_image(data)
    quiz = QuizAnswers(
        age=age, sensitivity=sensitivity, pregnant=pregnant,
        sun_exposure=sun_exposure, budget=budget,
    )
    protocol = build_protocol(analysis, quiz)
    record = tracker.record_scan(user_id, analysis)
    return JSONResponse(
        {
            "scan_id": record.id,
            "analysis": analysis.model_dump(mode="json"),
            "protocol": protocol.model_dump(mode="json"),
        }
    )


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
def api_scans(user_id: str = "demo-user") -> JSONResponse:
    scans = store.list_scans(user_id)
    return JSONResponse([s.model_dump(mode="json") for s in scans])


@app.get("/api/trends", tags=["трекер"])
def api_trends(user_id: str = "demo-user") -> JSONResponse:
    return JSONResponse(tracker.compute_trends(user_id).model_dump(mode="json"))


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(_STATIC / "index.html")


@app.get("/tracker", include_in_schema=False)
def tracker_page() -> FileResponse:
    return FileResponse(_STATIC / "tracker.html")


# Статика (css/js) монтируется последней, чтобы не перехватывать маршруты выше.
app.mount("/static", StaticFiles(directory=_STATIC), name="static")
