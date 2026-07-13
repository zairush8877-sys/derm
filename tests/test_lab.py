"""Лаборатория: панели, запись, отмена."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_panels_list():
    res = client.get("/api/lab/panels")
    assert res.status_code == 200
    data = res.json()
    assert len(data["panels"]) >= 6
    assert data["disclaimer"]
    base = next(p for p in data["panels"] if p["id"] == "lab-base")
    assert base["price_rub"] > 0 and base["biomarkers"]


def test_book_and_list_and_cancel():
    res = client.post("/api/lab/book", data={
        "panel_id": "lab-skin-hair", "city": "Москва",
        "phone": "+7 900 111-22-33", "preferred_date": "2026-08-01",
        "user_id": "lab-user",
    })
    assert res.status_code == 200
    booking = res.json()["booking"]
    assert booking["status"] == "new"
    assert booking["panel_name"] == "Кожа и волосы"

    res = client.get("/api/lab/bookings", params={"user_id": "lab-user"})
    assert any(b["id"] == booking["id"] for b in res.json()["bookings"])

    res = client.post("/api/lab/cancel", data={
        "booking_id": booking["id"], "user_id": "lab-user",
    })
    assert res.status_code == 200
    assert res.json()["booking"]["status"] == "canceled"

    # повторная отмена — ошибка
    res = client.post("/api/lab/cancel", data={
        "booking_id": booking["id"], "user_id": "lab-user",
    })
    assert res.status_code == 422


def test_book_validation():
    res = client.post("/api/lab/book", data={
        "panel_id": "no-such-panel", "city": "Москва", "phone": "+79001112233",
    })
    assert res.status_code == 422
    res = client.post("/api/lab/book", data={
        "panel_id": "lab-base", "city": "", "phone": "+79001112233",
    })
    assert res.status_code == 422
    res = client.post("/api/lab/book", data={
        "panel_id": "lab-base", "city": "Казань", "phone": "abc",
    })
    assert res.status_code == 422


def test_booking_notification_created():
    client.post("/api/lab/book", data={
        "panel_id": "lab-base", "city": "Сочи", "phone": "+79001112255",
        "user_id": "lab-notif-user",
    })
    res = client.get("/api/notifications", params={"user_id": "lab-notif-user"})
    assert res.status_code == 200
    titles = [n.get("title", "") for n in res.json().get("items", [])]
    assert any("Заявка на анализы" in t for t in titles)


def test_lab_page_served():
    res = client.get("/lab")
    assert res.status_code == 200
    assert "Лаборатория" in res.text
