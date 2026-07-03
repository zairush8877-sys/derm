"""Тесты B2B-тарифов и квот."""

from fastapi.testclient import TestClient

from app.api.plans import estimate_cost_usd, get_plan
from app.config import get_settings
from app.main import app

client = TestClient(app)


def _img(seed: int = 1) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + bytes([seed % 256]) * (20 + seed)


def test_estimate_cost_payg():
    # payg: только за сканы.
    assert estimate_cost_usd("payg", 10) == round(10 * get_plan("payg").price_per_scan_usd, 2)


def test_estimate_cost_with_overage():
    # starter: подписка + overage сверх включённой квоты.
    plan = get_plan("starter")
    over = 100
    cost = estimate_cost_usd("starter", plan.included_scans + over)
    assert cost == round(plan.monthly_price_usd + over * plan.price_per_scan_usd, 2)


def test_plans_endpoint():
    res = client.get("/v1/plans")
    assert res.status_code == 200
    ids = {p["id"] for p in res.json()["plans"]}
    assert {"payg", "starter", "growth", "enterprise"} <= ids


def test_usage_endpoint_reports_plan():
    key = get_settings().demo_api_key
    client.post("/v1/analyze", files={"image": ("f.png", _img(2), "image/png")},
                headers={"X-API-Key": key})
    usage = client.get("/v1/usage", headers={"X-API-Key": key}).json()
    assert usage["scans_this_month"] >= 1
    assert usage["plan"]["id"] in {"starter", "payg", "growth", "enterprise"}
    assert usage["api_version"] == "1.0"


def test_analyze_has_dermatologist_flag():
    key = get_settings().demo_api_key
    res = client.post("/v1/analyze", files={"image": ("f.png", _img(3), "image/png")},
                      headers={"X-API-Key": key})
    assert res.json()["dermatologist_validated"] is True
