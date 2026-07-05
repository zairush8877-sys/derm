"""Тесты входа по SMS-коду и способов доставки."""

from fastapi.testclient import TestClient

from app.main import app
from app.shop import orders, service

client = TestClient(app)


# --- OTP ---

def test_otp_flow_creates_user_and_logs_in():
    r = client.post("/api/auth/otp/request", data={"phone": "+79007770001"})
    assert r.status_code == 200
    body = r.json()
    assert body["sent"] is True
    assert "demo_code" in body  # без SMS-провайдера код показывается (демо)

    v = client.post("/api/auth/otp/verify",
                    data={"phone": "8 900 777-00-01", "code": body["demo_code"]})
    assert v.status_code == 200
    data = v.json()
    assert data["token"] and data["user"]["phone"] == "+79007770001"

    # Повторный вход тем же телефоном возвращает тот же аккаунт.
    r2 = client.post("/api/auth/otp/request", data={"phone": "+79007770001"})
    v2 = client.post("/api/auth/otp/verify",
                     data={"phone": "+79007770001", "code": r2.json()["demo_code"]})
    assert v2.json()["user"]["id"] == data["user"]["id"]


def test_otp_wrong_code_rejected():
    client.post("/api/auth/otp/request", data={"phone": "+79007770002"})
    v = client.post("/api/auth/otp/verify", data={"phone": "+79007770002", "code": "0000"})
    # код случайный 4-значный: 0000 может совпасть с вероятностью 1/10000 — берём заведомо неверный формат
    v = client.post("/api/auth/otp/verify", data={"phone": "+79007770002", "code": "нет"})
    assert v.status_code == 401


def test_otp_code_single_use():
    r = client.post("/api/auth/otp/request", data={"phone": "+79007770003"}).json()
    ok = client.post("/api/auth/otp/verify", data={"phone": "+79007770003", "code": r["demo_code"]})
    assert ok.status_code == 200
    again = client.post("/api/auth/otp/verify", data={"phone": "+79007770003", "code": r["demo_code"]})
    assert again.status_code == 401  # код одноразовый


# --- Доставка ---

def test_delivery_methods_quotes():
    q = orders.delivery_quote(1000, "pvz")
    assert q["fee_rub"] == 250 and q["eta_days"] == 3
    assert orders.delivery_quote(4000, "pvz")["fee_rub"] == 0  # ПВЗ бесплатно от 3500
    assert orders.delivery_quote(4000, "courier")["fee_rub"] == 390
    assert orders.delivery_quote(6000, "courier")["fee_rub"] == 0
    # Неизвестный способ падает на курьера.
    assert orders.delivery_quote(1000, "тапки")["method"] == "courier"
    assert len(orders.delivery_options(1000)) == 3


def test_checkout_with_method():
    service.clear_cart("dlv1")
    service.add_to_cart("dlv1", "vt-002", 1)  # 690 ₽
    result = orders.checkout("dlv1", address="Казань", method="pvz")
    assert result["delivery"]["method"] == "pvz"
    assert result["total_rub"] == 690 + 250


def test_delivery_endpoint_lists_options():
    r = client.get("/api/shop/delivery", params={"user_id": "dlv2"})
    assert r.status_code == 200
    methods = {o["method"] for o in r.json()["options"]}
    assert methods == {"courier", "pvz", "post"}


# --- Страницы и SEO ---

def test_legal_and_seo_pages():
    assert client.get("/legal").status_code == 200
    assert "оферта" in client.get("/legal").text.lower()
    assert client.get("/robots.txt").status_code == 200
    assert client.get("/sitemap.xml").status_code == 200
