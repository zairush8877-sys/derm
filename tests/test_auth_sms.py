"""Тесты SMS-провайдера для OTP: отправка, троттлинг, лимит попыток."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.auth import service, sms
from app.config import get_settings
from app.db import store
from app.main import app

client = TestClient(app)
PHONE = "+79115550001"


@pytest.fixture
def real_provider(monkeypatch):
    """Включить «настоящий» SMS.ru и перехватывать отправки в список."""
    monkeypatch.setenv("SMS_API_KEY", "test-api-id")
    monkeypatch.setenv("DERM_CAPTCHA", "0")  # тестируем троттлинг, не капчу
    get_settings.cache_clear()
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(sms, "send_sms", lambda phone, text: sent.append((phone, text)))
    # Канал по умолчанию — звонок; в этих тестах проверяем SMS-путь и троттлинг,
    # поэтому звонок тоже перехватываем (код 1234, как «последние 4 цифры»).
    monkeypatch.setattr(sms, "send_call_code", lambda phone: "1234")
    yield sent
    get_settings.cache_clear()


def _row(phone: str):
    with store.connect() as conn:
        return conn.execute("SELECT * FROM otp_codes WHERE phone = ?", (phone,)).fetchone()


# --- Реальная отправка ---

def test_real_provider_sends_sms_and_hides_code(real_provider):
    res = client.post("/api/auth/otp/request", data={"phone": PHONE, "channel": "sms"})
    assert res.status_code == 200
    body = res.json()
    assert body["sent"] is True and "demo_code" not in body
    assert len(real_provider) == 1
    to, text = real_provider[0]
    assert to == PHONE and "Aura" in text and _row(PHONE)["code"] in text


def test_sms_failure_returns_clear_error(monkeypatch):
    monkeypatch.setenv("SMS_API_KEY", "test-api-id")
    monkeypatch.setenv("DERM_CAPTCHA", "0")
    get_settings.cache_clear()

    def boom(phone, text):
        raise sms.SmsError("нет денег на балансе")

    monkeypatch.setattr(sms, "send_sms", boom)
    res = client.post(
        "/api/auth/otp/request", data={"phone": "+79115550002", "channel": "sms"}
    )
    assert res.status_code == 400
    assert "SMS" in res.json()["detail"]


def test_demo_mode_still_returns_code():
    res = client.post("/api/auth/otp/request", data={"phone": "+79115550003"})
    assert res.status_code == 200
    assert res.json()["demo_code"]


# --- Троттлинг (только при реальном провайдере) ---

def test_resend_cooldown_60s(real_provider):
    data = {"phone": PHONE, "channel": "sms"}
    assert client.post("/api/auth/otp/request", data=data).status_code == 200
    res = client.post("/api/auth/otp/request", data=data)
    assert res.status_code == 400 and "сек" in res.json()["detail"]
    assert len(real_provider) == 1  # вторая SMS не ушла


def test_resend_allowed_after_cooldown(real_provider):
    data = {"phone": PHONE, "channel": "sms"}
    client.post("/api/auth/otp/request", data=data)
    past = (datetime.now(timezone.utc) - timedelta(seconds=90)).isoformat()
    with store.connect() as conn:
        conn.execute("UPDATE otp_codes SET last_sent = ? WHERE phone = ?", (past, PHONE))
    assert client.post("/api/auth/otp/request", data=data).status_code == 200
    assert len(real_provider) == 2


def test_hourly_limit(real_provider):
    client.post("/api/auth/otp/request", data={"phone": PHONE})
    past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    with store.connect() as conn:
        conn.execute(
            "UPDATE otp_codes SET last_sent = ?, sent_count = ? WHERE phone = ?",
            (past, service.OTP_MAX_PER_HOUR, PHONE),
        )
    res = client.post("/api/auth/otp/request", data={"phone": PHONE})
    assert res.status_code == 400 and "час" in res.json()["detail"]


def test_hourly_window_resets(real_provider):
    client.post("/api/auth/otp/request", data={"phone": PHONE})
    long_ago = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    with store.connect() as conn:
        conn.execute(
            "UPDATE otp_codes SET last_sent = ?, sent_count = ?, window_start = ? WHERE phone = ?",
            (long_ago, service.OTP_MAX_PER_HOUR, long_ago, PHONE),
        )
    assert client.post("/api/auth/otp/request", data={"phone": PHONE}).status_code == 200
    assert _row(PHONE)["sent_count"] == 1  # окно началось заново


def test_demo_mode_has_no_cooldown():
    p = "+79115550004"
    assert client.post("/api/auth/otp/request", data={"phone": p}).status_code == 200
    assert client.post("/api/auth/otp/request", data={"phone": p}).status_code == 200


# --- Перебор кода ---

def test_wrong_code_attempts_limited():
    p = "+79115550005"
    code = client.post("/api/auth/otp/request", data={"phone": p}).json()["demo_code"]
    wrong = "0000" if code != "0000" else "1111"
    for _ in range(service.OTP_MAX_ATTEMPTS):
        res = client.post("/api/auth/otp/verify", data={"phone": p, "code": wrong})
        assert res.status_code == 401 and res.json()["detail"] == "Неверный код"
    # Лимит исчерпан: даже ПРАВИЛЬНЫЙ код больше не принимается.
    res = client.post("/api/auth/otp/verify", data={"phone": p, "code": code})
    assert res.status_code == 401 and "попыток" in res.json()["detail"]
    assert _row(p) is None  # код удалён — нужен новый запрос


def test_correct_code_works_within_attempts():
    p = "+79115550006"
    code = client.post("/api/auth/otp/request", data={"phone": p}).json()["demo_code"]
    wrong = "0000" if code != "0000" else "1111"
    client.post("/api/auth/otp/verify", data={"phone": p, "code": wrong})
    res = client.post("/api/auth/otp/verify", data={"phone": p, "code": code})
    assert res.status_code == 200 and res.json()["token"]


def test_new_code_resets_attempts():
    p = "+79115550007"
    code = client.post("/api/auth/otp/request", data={"phone": p}).json()["demo_code"]
    wrong = "0000" if code != "0000" else "1111"
    for _ in range(3):
        client.post("/api/auth/otp/verify", data={"phone": p, "code": wrong})
    assert _row(p)["attempts"] == 3
    client.post("/api/auth/otp/request", data={"phone": p})
    assert _row(p)["attempts"] == 0


# --- Модуль sms: разбор ответов провайдеров ---

def test_smsru_rejection_raises(monkeypatch):
    monkeypatch.setenv("SMS_API_KEY", "test-api-id")
    get_settings.cache_clear()
    monkeypatch.setattr(
        sms, "_http_get_json",
        lambda url, params: {"status": "ERROR", "status_text": "неверный api_id"},
    )
    with pytest.raises(sms.SmsError, match="SMS.ru"):
        sms.send_sms("+79115550008", "тест")
    get_settings.cache_clear()


def test_smsru_ok(monkeypatch):
    monkeypatch.setenv("SMS_API_KEY", "test-api-id")
    get_settings.cache_clear()
    calls = {}

    def fake(url, params):
        calls["url"], calls["params"] = url, params
        return {"status": "OK", "sms": {"79115550009": {"status": "OK"}}}

    monkeypatch.setattr(sms, "_http_get_json", fake)
    sms.send_sms("+79115550009", "код 1234")
    assert "sms.ru" in calls["url"] and calls["params"]["to"] == "79115550009"
    get_settings.cache_clear()


def test_smsc_error_raises(monkeypatch):
    monkeypatch.setenv("SMS_PROVIDER", "smsc")
    monkeypatch.setenv("SMS_LOGIN", "login")
    monkeypatch.setenv("SMS_PASSWORD", "pass")
    get_settings.cache_clear()
    monkeypatch.setattr(
        sms, "_http_get_json",
        lambda url, params: {"error": "invalid password", "error_code": 2},
    )
    with pytest.raises(sms.SmsError, match="SMSC.ru"):
        sms.send_sms("+79115550010", "тест")
    get_settings.cache_clear()


def test_provider_configured_flags(monkeypatch):
    assert sms.provider_configured() is False  # демо по умолчанию (conftest чистит env)
    monkeypatch.setenv("SMS_API_KEY", "x")
    get_settings.cache_clear()
    assert sms.provider_configured() is True
    get_settings.cache_clear()
