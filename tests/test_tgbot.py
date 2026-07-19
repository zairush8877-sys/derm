"""Telegram-бот каталога: доступ, добавление, список, удаление."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.shop import catalog
from app.tgbot import api as tgapi
from app.tgbot import service

client = TestClient(app)


@pytest.fixture
def bot(monkeypatch):
    """Настроенный бот: токен/чат владельца + перехват ответов."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-bot-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111222333")
    get_settings.cache_clear()
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(tgapi, "send_reply", lambda chat, text: sent.append((str(chat), text)))
    yield sent
    get_settings.cache_clear()


def _msg(text: str, chat_id: int = 111222333) -> dict:
    return {"message": {"chat": {"id": chat_id}, "text": text}}


def _hook(payload: dict):
    return client.post(f"/api/telegram/webhook/{service.webhook_secret()}", json=payload)


def test_webhook_requires_token_and_secret(bot):
    res = client.post("/api/telegram/webhook/wrong-secret", json=_msg("привет"))
    assert res.status_code == 403


def test_webhook_404_without_token():
    res = client.post("/api/telegram/webhook/anything", json=_msg("привет"))
    assert res.status_code == 404


def test_foreign_chat_rejected(bot):
    res = _hook(_msg("Бренд; Товар; 100", chat_id=999))
    assert res.status_code == 200
    assert "только у владельца" in bot[-1][1]
    assert not any("Добавлено" in t for _, t in bot)


def test_add_list_remove_flow(bot):
    res = _hook(_msg("Aura; Морской коллаген премиум; 2 490; витамины и БАДы; Порошок с пептидами"))
    assert res.status_code == 200
    reply = bot[-1][1]
    assert "Добавлено в магазин: 1" in reply and "2490" in reply

    # товар виден в каталоге магазина
    items = catalog.search("коллаген премиум")
    assert any(p.brand == "Aura" and p.price_rub == 2490 for p in items)
    pid = next(p.id for p in items if p.price_rub == 2490)
    assert pid.startswith("tg-")
    assert catalog.get_product(pid) is not None

    # /список
    _hook(_msg("/список"))
    assert "коллаген" in bot[-1][1].lower()

    # /удалить
    _hook(_msg(f"/удалить {pid}"))
    assert "Удалил" in bot[-1][1]
    assert catalog.get_product(pid) is None


def test_multiline_and_bad_lines(bot):
    _hook(_msg("Aura; Матча латте; 890; функциональные напитки\nмусорная строка\nX; Y; ноль"))
    reply = bot[-1][1]
    assert "Добавлено в магазин: 1" in reply


def test_help_and_start(bot):
    _hook(_msg("/start"))
    assert "бот каталога" in bot[-1][1]


def test_shop_api_shows_custom_product(bot):
    _hook(_msg("Aura; Тестовый шейкер из бота; 1 190; гаджеты"))
    res = client.get("/api/shop/products", params={"q": "шейкер из бота"})
    data = res.json()
    items = data.get("items") or data.get("products") or []
    assert any("шейкер" in (i.get("name") or "").lower() for i in items)


def test_fail_closed_without_owner_id(monkeypatch):
    # Токен есть, ID владельца НЕ задан → никто не должен управлять каталогом.
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-bot-token")
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    get_settings.cache_clear()
    before = len(service.list_custom())
    res = client.post(
        f"/api/telegram/webhook/{service.webhook_secret()}",
        json={"update_id": 1, "message": {"chat": {"id": 555}, "text": "X; Y; 100"}},
    )
    assert res.status_code == 200
    assert len(service.list_custom()) == before  # ничего не добавлено
    get_settings.cache_clear()


def test_update_deduplicated(bot):
    payload = {"update_id": 777, "message": {"chat": {"id": 111222333},
               "text": "Aura; Дедуп-товар; 500; гаджеты"}}
    _hook(payload)
    _hook(payload)  # повтор того же update_id
    found = [p for p in catalog.search("дедуп-товар")]
    assert len(found) == 1  # не задвоился


def test_edited_message_not_added(bot):
    # Правка сообщения не должна добавлять новый товар.
    before = len(service.list_custom())
    client.post(
        f"/api/telegram/webhook/{service.webhook_secret()}",
        json={"update_id": 888, "edited_message": {"chat": {"id": 111222333},
              "text": "Aura; Из правки; 900; гаджеты"}},
    )
    assert len(service.list_custom()) == before
