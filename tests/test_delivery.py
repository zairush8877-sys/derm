"""Тесты доставки: комментарий, трек-номер, уведомления владельцу, каркас СДЭК."""

import os

from fastapi.testclient import TestClient

from app.main import app
from app.notifications import owner
from app.notifications import service as notifications
from app.shop import cdek, orders
from app.shop import service as shop

client = TestClient(app)
ADMIN = {"X-Admin-Token": os.getenv("DERM_ADMIN_TOKEN", "admin-derm-2026")}


def _make_order(user="dlv-user", comment=""):
    shop.clear_cart(user)
    shop.add_to_cart(user, "sp-001", 1)
    return orders.checkout(user, address="Москва, Тверская 1", name="Заира",
                           phone="+79990000000", comment=comment)


# --- Комментарий к заказу ---

def test_comment_saved_in_order():
    r = _make_order(comment="Домофон 42, звонить после 18:00")
    saved = orders.list_orders("dlv-user")[0]
    assert saved["delivery"]["comment"] == "Домофон 42, звонить после 18:00"
    assert r["delivery"]["comment"]


def test_comment_truncated_to_500():
    _make_order(user="dlv-long", comment="х" * 600)
    saved = orders.list_orders("dlv-long")[0]
    assert len(saved["delivery"]["comment"]) == 500


def test_checkout_api_accepts_comment():
    shop.clear_cart("dlv-api")
    shop.add_to_cart("dlv-api", "vt-001", 1)
    res = client.post("/api/shop/checkout", data={
        "user_id": "dlv-api", "address": "СПб", "comment": "оставить у двери",
    })
    assert res.status_code == 200
    assert orders.list_orders("dlv-api")[0]["delivery"]["comment"] == "оставить у двери"


# --- Трек-номер ---

def test_set_track_notifies_buyer():
    oid = _make_order(user="dlv-track")["order_id"]
    r = orders.set_track_number(oid, "CDEK123456789")
    assert r["changed"] is True
    titles = [n["title"] for n in notifications.list_for("dlv-track")]
    assert any("Трек-номер" in t for t in titles)
    # Повтор того же трека — без нового уведомления.
    r2 = orders.set_track_number(oid, "CDEK123456789")
    assert r2["changed"] is False
    assert sum("Трек-номер" in t for t in titles) == 1


def test_track_saved_in_order():
    oid = _make_order(user="dlv-track2")["order_id"]
    orders.set_track_number(oid, "AB-42")
    assert orders.list_orders("dlv-track2")[0]["delivery"]["track"] == "AB-42"


def test_admin_track_endpoint():
    oid = _make_order(user="dlv-track3")["order_id"]
    assert client.post("/api/admin/order-track",
                       data={"order_id": oid, "track": "X1"}).status_code == 401
    res = client.post("/api/admin/order-track",
                      data={"order_id": oid, "track": "X1"}, headers=ADMIN)
    assert res.status_code == 200 and res.json()["track"] == "X1"
    assert client.post("/api/admin/order-track",
                       data={"order_id": "nope", "track": "X1"},
                       headers=ADMIN).status_code == 404
    assert client.post("/api/admin/order-track",
                       data={"order_id": oid, "track": "  "},
                       headers=ADMIN).status_code == 400


# --- Уведомления владельцу ---

def test_owner_notify_skipped_without_config():
    assert owner.configured() is False
    assert owner.notify_owner("тест") is False  # тихо, без ошибок


def test_owner_notified_on_checkout(monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    get_settings.cache_clear()
    sent = []
    monkeypatch.setattr(owner, "notify_owner", lambda text: sent.append(text) or True)
    _make_order(user="dlv-owner", comment="привет")
    assert len(sent) == 1
    assert "Новый заказ" in sent[0] and "привет" in sent[0]
    get_settings.cache_clear()


def test_owner_failure_does_not_break_checkout(monkeypatch):
    def boom(text):
        raise RuntimeError("сеть упала")
    # notify_owner сам ловит исключения — проверяем через реальную функцию с битым urlopen
    import urllib.request

    from app.config import get_settings
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    get_settings.cache_clear()
    monkeypatch.setattr(urllib.request, "urlopen", boom)
    r = _make_order(user="dlv-fail")  # заказ должен пройти
    assert r["order_id"]
    get_settings.cache_clear()


# --- Каркас СДЭК ---

def test_cdek_not_configured_by_default():
    assert cdek.configured() is False


def test_quote_falls_back_without_cdek():
    q = orders.delivery_quote(1000, "pvz", to_city_code=270)
    assert q["fee_rub"] == 250  # фиксированный тариф, СДЭК не настроен


def test_quote_uses_cdek_when_configured(monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("CDEK_ACCOUNT", "acc")
    monkeypatch.setenv("CDEK_PASSWORD", "pwd")
    get_settings.cache_clear()
    monkeypatch.setattr(cdek, "quote",
                        lambda city, weight_grams=1000, tariff=136: {"fee_rub": 312, "eta_days": 4})
    q = orders.delivery_quote(1000, "pvz", to_city_code=270)
    assert q["fee_rub"] == 312 and q["eta_days"] == 4
    # Бесплатная доставка от порога сохраняется и с реальным тарифом.
    q2 = orders.delivery_quote(99999, "pvz", to_city_code=270)
    assert q2["fee_rub"] == 0
    get_settings.cache_clear()


def test_quote_survives_cdek_error(monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("CDEK_ACCOUNT", "acc")
    monkeypatch.setenv("CDEK_PASSWORD", "pwd")
    get_settings.cache_clear()

    def broken(city, weight_grams=1000, tariff=136):
        raise cdek.CdekError("недоступен")

    monkeypatch.setattr(cdek, "quote", broken)
    q = orders.delivery_quote(1000, "courier", to_city_code=270)
    assert q["fee_rub"] == 390  # откат на фиксированный тариф
    get_settings.cache_clear()


def test_track_url():
    assert cdek.track_url("AB 1").startswith("https://www.cdek.ru/ru/tracking?order_id=AB")
