"""Аутентификация B2B-клиентов (брендов) по API-ключу (X-API-Key)."""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from app.api.plans import DEFAULT_PLAN
from app.config import get_settings
from app.db import store


def seed_demo_client() -> None:
    """Создать демо-клиента (бренд) с ключом из настроек, если его нет."""
    key = get_settings().demo_api_key
    if store.get_client(key) is None:
        store.upsert_client(key, brand_name="Demo Brand", plan="starter")


def resolve_client(api_key: str) -> dict | None:
    """Вернуть клиента по ключу. Демо-ключ создаётся на лету."""
    client = store.get_client(api_key)
    if client is None and api_key == get_settings().demo_api_key:
        store.upsert_client(api_key, brand_name="Demo Brand", plan="starter")
        client = store.get_client(api_key)
    return client


async def require_client(x_api_key: str = Header(default="", alias="X-API-Key")) -> dict:
    """FastAPI-зависимость: проверяет ключ и возвращает клиента (бренд) с планом."""
    client = resolve_client(x_api_key)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный или отсутствующий X-API-Key",
        )
    client.setdefault("plan", DEFAULT_PLAN)
    return client
