"""HTTP-эндпоинты авторизации."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException

from app.auth import service
from app.auth.deps import token_user_id

router = APIRouter(prefix="/api/auth", tags=["Авторизация"])


@router.post("/register")
def register(
    phone: str = Form(...),
    password: str = Form(...),
    name: str = Form(""),
) -> dict:
    try:
        return service.register(phone, password, name)
    except service.AuthError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/login")
def login(phone: str = Form(...), password: str = Form(...)) -> dict:
    try:
        return service.login(phone, password)
    except service.AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


@router.get("/me")
def me(auth_id: str | None = Depends(token_user_id)) -> dict:
    if auth_id is None:
        raise HTTPException(status_code=401, detail="Не авторизован")
    user = service.get_user(auth_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return user
