"""Тесты HTTP-эндпоинтов (B2B API + демо), демо-режим."""

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

client = TestClient(app)


def _img(seed: int = 1) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + bytes([seed % 256]) * (20 + seed)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_b2b_requires_api_key():
    res = client.post("/v1/analyze", files={"image": ("face.png", _img(), "image/png")})
    assert res.status_code == 401


def test_b2b_analyze_happy_path():
    key = get_settings().demo_api_key
    res = client.post(
        "/v1/analyze",
        files={"image": ("face.png", _img(2), "image/png")},
        headers={"X-API-Key": key},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["skin_type"]
    assert len(body["concerns"]) == 9
    assert "не медицинский диагноз" in body["disclaimer"].lower() or "диагноз" in body["disclaimer"].lower()


def test_b2b_protocol_and_usage():
    key = get_settings().demo_api_key
    res = client.post(
        "/v1/protocol",
        files={"image": ("face.png", _img(3), "image/png")},
        headers={"X-API-Key": key},
        data={"age": "30"},
    )
    assert res.status_code == 200
    assert res.json()["am_steps"]

    usage = client.get("/v1/usage", headers={"X-API-Key": key})
    assert usage.status_code == 200
    assert usage.json()["scans_this_month"] >= 1


def test_demo_analyze_and_pdf():
    from app.billing import service as credits

    credits.grant("demo-user", 1)
    res = client.post(
        "/api/analyze",
        files={"image": ("face.png", _img(4), "image/png")},
        data={"user_id": "demo-user"},
    )
    assert res.status_code == 200
    body = res.json()
    assert "analysis" in body and "protocol" in body
    assert "recommended" in body  # рекомендации товаров из магазина

    # PDF-отчёт бесплатный (без гейтинга).
    pdf = client.post("/api/report", files={"image": ("face.png", _img(4), "image/png")})
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content[:4] == b"%PDF"


def test_analyze_requires_credit_when_empty():
    # Новый пользователь получает free_trial_scans пробных сканов; дальше — 402.
    from app.config import get_settings

    for _ in range(get_settings().free_trial_scans + 1):
        res = client.post(
            "/api/analyze",
            files={"image": ("face.png", _img(6), "image/png")},
            data={"user_id": "paywall-user"},
        )
    assert res.status_code == 402
    assert res.json()["need_payment"] is True


def test_tracker_endpoints():
    from app.billing import service as credits

    credits.grant("trk", 1)
    client.post(
        "/api/analyze",
        files={"image": ("face.png", _img(5), "image/png")},
        data={"user_id": "trk"},
    )
    scans = client.get("/api/scans", params={"user_id": "trk"})
    assert scans.status_code == 200
    assert len(scans.json()) >= 1

    trends = client.get("/api/trends", params={"user_id": "trk"})
    assert trends.status_code == 200
    assert trends.json()["scans_count"] >= 1
