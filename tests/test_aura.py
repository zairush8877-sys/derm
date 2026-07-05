"""Тесты Aura-функций: каталог/поиск, заказы, лояльность, ассистент, уведомления, админ."""

from fastapi.testclient import TestClient

from app.assistant import engine as assistant
from app.config import get_settings
from app.main import app
from app.shop import catalog, loyalty, orders, service
from app.shop.catalog import Category

client = TestClient(app)


# --- Каталог и поиск ---

def test_catalog_covers_brief_categories():
    for cat in Category:
        assert catalog.all_products(cat), f"нет товаров в {cat.value}"


def test_search_finds_by_tag():
    res = catalog.search("матча")
    assert any("матча" in p.name.lower() or "матча" in " ".join(p.tags) for p in res)


def test_search_endpoint():
    r = client.get("/api/shop/search", params={"q": "протеин"})
    assert r.status_code == 200
    assert r.json()["products"]


# --- Заказы, доставка, лояльность ---

def test_delivery_quote_free_over_threshold():
    assert orders.delivery_quote(6000)["fee_rub"] == 0
    assert orders.delivery_quote(1000)["fee_rub"] > 0


def test_checkout_flow_and_loyalty():
    service.clear_cart("buyer1")
    service.add_to_cart("buyer1", "sp-001", 2)  # 1990*2 = 3980
    result = orders.checkout("buyer1", address="Москва, ул. Пример, 1")
    assert result["status"] == "оплачен"
    assert result["total_rub"] >= 3980
    assert result["points_earned"] > 0
    # Заказ появился в истории.
    assert orders.list_orders("buyer1")
    # Баллы начислены.
    assert loyalty.status("buyer1")["points"] == result["points_earned"]


def test_checkout_empty_cart_400():
    service.clear_cart("empty1")
    r = client.post("/api/shop/checkout", data={"user_id": "empty1", "address": "X"})
    assert r.status_code == 400


def test_loyalty_tiers():
    assert loyalty.tier_for(0)[0] == "Base"
    assert loyalty.tier_for(150000)[0] == "Gold"


# --- Wellness-ассистент ---

def test_assistant_mock_reply():
    out = assistant.ask("Как улучшить сон?")
    assert "сон" in out["reply"].lower() or out["reply"]
    assert "диагноз" in out["disclaimer"].lower()


def test_assistant_endpoint():
    r = client.post("/api/assistant/chat", json={"message": "что от акне", "history": []})
    assert r.status_code == 200
    assert r.json()["reply"]


def test_assistant_empty_400():
    r = client.post("/api/assistant/chat", json={"message": "", "history": []})
    assert r.status_code == 400


# --- Уведомления ---

def test_notifications_created_on_order():
    service.clear_cart("notif1")
    service.add_to_cart("notif1", "vt-002", 1)
    orders.checkout("notif1", address="СПб")
    r = client.get("/api/notifications", params={"user_id": "notif1"})
    assert r.json()["unread"] >= 1


# --- Админ-панель ---

def test_admin_requires_token():
    assert client.get("/api/admin/overview").status_code == 401


def test_admin_overview():
    import os
    token = os.getenv("DERM_ADMIN_TOKEN", "admin-derm-2026")
    r = client.get("/api/admin/overview", headers={"X-Admin-Token": token})
    assert r.status_code == 200
    assert "orders" in r.json() and "ai" in r.json()


# --- Страницы отдаются ---

def test_new_pages_served():
    for path in ["/assistant", "/subscription", "/admin", "/shop", "/food"]:
        assert client.get(path).status_code == 200


def test_demo_key_present():
    assert get_settings().demo_api_key
