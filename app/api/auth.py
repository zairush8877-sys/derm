"""Аутентификация B2B-клиентов по API-ключу (X-API-Key)."""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from app.config import get_settings


def valid_api_keys() -> set[str]:
    """Набор валидных ключей. В демо — один ключ из настроек."""
    return {get_settings().demo_api_key}


async def require_api_key(x_api_key: str = Header(default="", alias="X-API-Key")) -> str:
    """FastAPI-зависимость: проверяет ключ и возвращает его."""
    if x_api_key not in valid_api_keys():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный или отсутствующий X-API-Key",
        )
    return x_api_key
