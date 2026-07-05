"""FastAPI-зависимость: пользователь из заголовка Authorization (Bearer).

Если токен передан и валиден — эндпоинты используют id аккаунта и игнорируют
user_id из формы/запроса. Без токена работает демо-режим (user_id из параметра),
чтобы страницы оставались доступными без регистрации.
"""

from __future__ import annotations

from fastapi import Header

from app.auth import service


async def token_user_id(authorization: str = Header(default="")) -> str | None:
    if authorization.startswith("Bearer "):
        return service.verify_token(authorization[7:].strip())
    return None
