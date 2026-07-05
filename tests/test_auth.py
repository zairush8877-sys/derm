"""Тесты аккаунтов: регистрация, вход, токены, привязка данных к пользователю."""

from fastapi.testclient import TestClient

from app.auth import service
from app.main import app

client = TestClient(app)


def _img(seed: int = 1) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + bytes([seed % 256]) * (20 + seed)


def _register(phone: str = "+7 900 123-45-67", password: str = "secret1", name: str = "Заира") -> dict:
    res = client.post("/api/auth/register", data={"phone": phone, "password": password, "name": name})
    assert res.status_code == 200, res.text
    return res.json()


def test_register_and_me():
    data = _register()
    assert data["token"]
    assert data["user"]["phone"] == "+79001234567"  # нормализация номера
    me = client.get("/api/auth/me", headers={"Authorization": "Bearer " + data["token"]})
    assert me.status_code == 200
    assert me.json()["name"] == "Заира"


def test_duplicate_phone_rejected():
    _register(phone="+79005550001")
    res = client.post("/api/auth/register", data={"phone": "8 900 555-00-01", "password": "secret1"})
    assert res.status_code == 409  # 8XXX нормализуется в +7XXX — дубликат


def test_login_and_wrong_password():
    _register(phone="+79005550002", password="pass123")
    ok = client.post("/api/auth/login", data={"phone": "+79005550002", "password": "pass123"})
    assert ok.status_code == 200 and ok.json()["token"]
    bad = client.post("/api/auth/login", data={"phone": "+79005550002", "password": "wrong"})
    assert bad.status_code == 401


def test_short_password_rejected():
    res = client.post("/api/auth/register", data={"phone": "+79005550003", "password": "123"})
    assert res.status_code == 409


def test_token_roundtrip_and_tamper():
    token = service.create_token("u-abc")
    assert service.verify_token(token) == "u-abc"
    assert service.verify_token(token + "x") is None
    assert service.verify_token("garbage") is None


def test_scan_binds_to_account_not_form_user():
    """С токеном скан пишется в аккаунт, а user_id из формы игнорируется."""
    data = _register(phone="+79005550004")
    headers = {"Authorization": "Bearer " + data["token"]}
    uid = data["user"]["id"]

    res = client.post(
        "/api/analyze",
        files={"image": ("face.png", _img(9), "image/png")},
        data={"user_id": "someone-else"},  # должен быть проигнорирован
        headers=headers,
    )
    assert res.status_code == 200  # новый аккаунт имеет пробный скан

    # Скан виден в аккаунте (по токену) и НЕ виден у someone-else.
    mine = client.get("/api/scans", headers=headers).json()
    assert len(mine) == 1
    other = client.get("/api/scans", params={"user_id": "someone-else"}).json()
    assert other == []
    # И напрямую по id аккаунта.
    direct = client.get("/api/scans", params={"user_id": uid}).json()
    assert len(direct) == 1


def test_pages_served():
    for path in ["/", "/skin", "/auth", "/account"]:
        assert client.get(path).status_code == 200
