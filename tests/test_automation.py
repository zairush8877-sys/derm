"""Тесты движка автоматизаций и событийных уведомлений."""

import os
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.automation import service as automation
from app.billing import service as credits
from app.db import store
from app.main import app
from app.notifications import service as notifications
from app.protocol.quiz import QuizAnswers
from app.shop import orders
from app.shop import service as shop
from app.subscription import service as subscription

client = TestClient(app)
ADMIN = {"X-Admin-Token": os.getenv("DERM_ADMIN_TOKEN", "admin-derm-2026")}


def _img(seed: int = 1) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + bytes([seed % 256]) * (20 + seed)


def _titles(user_id: str) -> list[str]:
    return [n["title"] for n in notifications.list_for(user_id)]


# --- Джобы ---

def test_refresh_due_protocols_notifies():
    subscription.subscribe("auto-sub", QuizAnswers(age=30))
    # Прошло 40 дней — срок обновления позади.
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    with store.connect() as conn:
        conn.execute(
            "UPDATE protocol_subscriptions SET next_update = ? WHERE user_id = 'auto-sub'", (past,)
        )
    assert automation.refresh_due_protocols() == 1
    assert any("Протокол обновлён" in t for t in _titles("auto-sub"))
    # Повторный запуск ничего не обновляет (next_update теперь в будущем).
    assert automation.refresh_due_protocols() == 0


def test_abandoned_cart_reminder_once():
    shop.clear_cart("auto-cart")
    shop.add_to_cart("auto-cart", "vt-001", 2)
    old = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
    with store.connect() as conn:
        conn.execute("UPDATE cart SET updated_at = ? WHERE user_id = 'auto-cart'", (old,))
    assert automation.remind_abandoned_carts() == 1
    assert any("В корзине" in t for t in _titles("auto-cart"))
    # Кулдаун: второй запуск не спамит.
    assert automation.remind_abandoned_carts() == 0


def test_fresh_cart_not_reminded():
    shop.clear_cart("auto-fresh")
    shop.add_to_cart("auto-fresh", "vt-001", 1)  # updated_at = сейчас
    automation.remind_abandoned_carts()
    assert not any("В корзине" in t for t in _titles("auto-fresh"))


def test_cleanup_expired_otp():
    client.post("/api/auth/otp/request", data={"phone": "+79008880001"})
    past = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    with store.connect() as conn:
        conn.execute("UPDATE otp_codes SET expires = ?", (past,))
    assert automation.cleanup_expired_otp() >= 1


def test_run_all_logs_runs():
    results = automation.run_all()
    assert set(results) == {"refresh_due_protocols", "remind_abandoned_carts", "cleanup_expired_otp"}
    jobs = [r["job"] for r in automation.list_runs()]
    assert "refresh_due_protocols" in jobs


def test_run_log_is_trimmed():
    # Пишем больше лимита — журнал не должен превышать RUN_LOG_KEEP.
    for i in range(automation.RUN_LOG_KEEP + 40):
        automation.log_run("noise", str(i))
    with store.connect() as conn:
        n = conn.execute("SELECT COUNT(*) AS c FROM automation_runs").fetchone()["c"]
    assert n <= automation.RUN_LOG_KEEP


# --- Админ-эндпоинты ---

def test_admin_run_jobs_endpoint():
    assert client.post("/api/admin/run-jobs").status_code == 401
    res = client.post("/api/admin/run-jobs", headers=ADMIN)
    assert res.status_code == 200
    assert "cleanup_expired_otp" in res.json()
    runs = client.get("/api/admin/automation", headers=ADMIN)
    assert runs.status_code == 200 and runs.json()["runs"]


def _set_status(order_id: str, status: str):
    return client.post("/api/admin/order-status",
                       data={"order_id": order_id, "status": status}, headers=ADMIN)


def test_order_status_flow_step_by_step():
    shop.clear_cart("auto-ord")
    shop.add_to_cart("auto-ord", "sp-001", 1)
    oid = orders.checkout("auto-ord", address="Москва")["order_id"]

    # Пошаговый переход оплачен -> собирается -> отправлен.
    assert _set_status(oid, "собирается").status_code == 200
    assert _set_status(oid, "отправлен").status_code == 200
    assert orders.list_orders("auto-ord")[0]["status"] == "отправлен"
    assert any("отправлен" in t for t in _titles("auto-ord"))


def test_order_status_invalid_and_missing():
    shop.clear_cart("auto-ord2")
    shop.add_to_cart("auto-ord2", "sp-001", 1)
    oid = orders.checkout("auto-ord2", address="Москва")["order_id"]

    assert _set_status(oid, "улетел").status_code == 400          # неизвестный статус
    assert _set_status(oid, "отправлен").status_code == 400        # перепрыгнули шаг
    assert _set_status("nope", "собирается").status_code == 404    # нет заказа


def test_order_status_no_backward_transition():
    shop.clear_cart("auto-ord3")
    shop.add_to_cart("auto-ord3", "sp-001", 1)
    oid = orders.checkout("auto-ord3", address="Москва")["order_id"]
    _set_status(oid, "собирается")
    # Откат назад запрещён.
    assert _set_status(oid, "оплачен").status_code == 400


def test_order_status_idempotent_no_duplicate_notification():
    shop.clear_cart("auto-ord4")
    shop.add_to_cart("auto-ord4", "sp-001", 1)
    oid = orders.checkout("auto-ord4", address="Москва")["order_id"]
    orders.update_status(oid, "собирается")
    r1 = orders.update_status(oid, "отправлен")
    assert r1["changed"] is True
    # Повторная установка того же статуса — без изменения и без нового пуша.
    before = sum("отправлен" in t for t in _titles("auto-ord4"))
    r2 = orders.update_status(oid, "отправлен")
    assert r2["changed"] is False
    after = sum("отправлен" in t for t in _titles("auto-ord4"))
    assert before == after == 1


# --- Событийные уведомления ---

def test_welcome_notification_on_register():
    r = client.post("/api/auth/register",
                    data={"phone": "+79008880002", "password": "secret1", "name": "Ева"})
    uid = r.json()["user"]["id"]
    assert any("Добро пожаловать" in t for t in _titles(uid))


def test_welcome_on_first_otp_login_only():
    req = client.post("/api/auth/otp/request", data={"phone": "+79008880003"}).json()
    uid = client.post("/api/auth/otp/verify",
                      data={"phone": "+79008880003", "code": req["demo_code"]}).json()["user"]["id"]
    assert any("Добро пожаловать" in t for t in _titles(uid))
    # Второй вход — без повторного приветствия.
    req2 = client.post("/api/auth/otp/request", data={"phone": "+79008880003"}).json()
    client.post("/api/auth/otp/verify", data={"phone": "+79008880003", "code": req2["demo_code"]})
    assert sum("Добро пожаловать" in t for t in _titles(uid)) == 1


def test_zero_balance_notification_after_scan():
    r = client.post("/api/auth/register", data={"phone": "+79008880004", "password": "secret1"})
    headers = {"Authorization": "Bearer " + r.json()["token"]}
    res = client.post("/api/analyze", files={"image": ("f.png", _img(3), "image/png")},
                      headers=headers)
    assert res.status_code == 200 and res.json()["balance"] == 0
    uid = r.json()["user"]["id"]
    assert any("Сканы закончились" in t for t in _titles(uid))


def test_zero_balance_notification_food_scan():
    credits.grant("auto-food", 1)
    # Съедаем пробный + купленный, чтобы дойти до нуля.
    balance = credits.balance("auto-food")
    for i in range(balance):
        client.post("/api/food/analyze", files={"image": ("f.png", _img(10 + i), "image/png")},
                    data={"user_id": "auto-food"})
    assert credits.balance("auto-food") == 0
    assert any("Сканы закончились" in t for t in _titles("auto-food"))


# --- Самопроверка AI ---

def test_aitest_without_key_reports_clearly():
    from app.aitest import run_selftest

    r = run_selftest()
    assert r["key_present"] is False and r["ok"] is False
    assert "ANTHROPIC_API_KEY" in r["hint"]
    assert r["vision_model"] and r["chat_model"]


def test_admin_ai_test_endpoint():
    assert client.post("/api/admin/ai-test").status_code == 401
    res = client.post("/api/admin/ai-test", headers=ADMIN)
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is False and body["key_present"] is False
