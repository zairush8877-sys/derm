"""Капча, вход по звонку и профиль пользователя."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.captcha import service as captcha
from app.main import app

client = TestClient(app)


def test_captcha_disabled_in_demo():
    # В тестах DERM_MOCK_MODE=1 → капча выключена, регистрация без неё работает.
    res = client.get("/api/captcha/new")
    assert res.status_code == 200
    assert res.json()["required"] is False


def test_captcha_challenge_and_verify(monkeypatch):
    monkeypatch.setenv("DERM_CAPTCHA", "1")
    res = client.get("/api/captcha/new")
    data = res.json()
    assert data["required"] is True
    assert data["image"].startswith("data:image/png;base64,")
    # Проверка с известным кодом (токен подписываем сами).
    token = captcha.make_token("AB2CD")
    captcha.verify(token, "ab2cd")  # регистронезависимо
    # Повторное использование запрещено.
    try:
        captcha.verify(token, "AB2CD")
        raise AssertionError("повторная проверка должна падать")
    except captcha.CaptchaError:
        pass
    # Неверный ответ.
    try:
        captcha.verify(captcha.make_token("AB2CD"), "XXXXX")
        raise AssertionError("неверный ответ должен падать")
    except captcha.CaptchaError:
        pass


def test_otp_requires_captcha_when_enabled(monkeypatch):
    monkeypatch.setenv("DERM_CAPTCHA", "1")
    res = client.post("/api/auth/otp/request", data={"phone": "+79001234567"})
    assert res.status_code == 400
    token = captcha.make_token("HK7MN")
    res = client.post("/api/auth/otp/request", data={
        "phone": "+79001234567", "captcha_token": token, "captcha_answer": "hk7mn",
    })
    assert res.status_code == 200
    assert res.json()["channel"] == "demo"


def test_otp_call_channel(monkeypatch):
    # Реальный режим со звонком: провайдер отдаёт код = последние 4 цифры номера.
    from app.auth import sms

    monkeypatch.setattr(sms, "provider_configured", lambda: True)
    monkeypatch.setattr(sms, "call_code_supported", lambda: True)
    monkeypatch.setattr(sms, "send_call_code", lambda phone: "4821")
    res = client.post("/api/auth/otp/request", data={"phone": "+79005550001"})
    assert res.status_code == 200
    assert res.json()["channel"] == "call"
    assert "demo_code" not in res.json()
    # Вход по коду из «звонка».
    res = client.post("/api/auth/otp/verify", data={"phone": "+79005550001", "code": "4821"})
    assert res.status_code == 200
    assert res.json()["token"]


def test_otp_sms_fallback(monkeypatch):
    from app.auth import sms

    sent: dict = {}
    monkeypatch.setattr(sms, "provider_configured", lambda: True)
    monkeypatch.setattr(sms, "call_code_supported", lambda: True)
    monkeypatch.setattr(sms, "send_sms", lambda phone, text: sent.update(text=text))
    res = client.post("/api/auth/otp/request", data={"phone": "+79005550002", "channel": "sms"})
    assert res.status_code == 200
    assert res.json()["channel"] == "sms"
    assert "код входа" in sent["text"]


def test_profile_flow_and_bonus():
    r = client.post("/api/auth/register", data={"phone": "+79007770001", "password": "secret1"})
    headers = {"Authorization": "Bearer " + r.json()["token"]}

    res = client.get("/api/auth/profile", headers=headers)
    p = res.json()
    assert p["complete"] is False
    assert "фамилия" in p["missing_required"]

    res = client.post("/api/auth/profile", headers=headers, data={
        "last_name": "Иванова", "first_name": "Анна", "gender": "женщина",
        "birth_date": "1995-04-12", "city": "Москва",
    })
    assert res.status_code == 200
    p = res.json()
    assert p["complete"] is True and p["bonus_granted_now"] is True

    # Баллы начислены один раз.
    loy = client.get("/api/shop/loyalty", headers=headers).json()
    assert loy["points"] >= 50
    res = client.post("/api/auth/profile", headers=headers, data={
        "last_name": "Иванова", "first_name": "Анна", "gender": "женщина",
        "birth_date": "1995-04-12",
    })
    assert res.json()["bonus_granted_now"] is False
    loy2 = client.get("/api/shop/loyalty", headers=headers).json()
    assert loy2["points"] == loy["points"]


def test_profile_validation():
    r = client.post("/api/auth/register", data={"phone": "+79007770002", "password": "secret1"})
    headers = {"Authorization": "Bearer " + r.json()["token"]}
    res = client.post("/api/auth/profile", headers=headers, data={"birth_date": "12.04.1995"})
    assert res.status_code == 422
    res = client.post("/api/auth/profile", headers=headers, data={"gender": "другое"})
    assert res.status_code == 422
