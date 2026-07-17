"""HTTP-эндпоинты авторизации."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException

from app.auth import service
from app.auth.deps import token_user_id
from app.captcha import service as captcha

router = APIRouter(prefix="/api/auth", tags=["Авторизация"])


def _check_captcha(token: str, answer: str) -> None:
    """Защита от ботов: обязательна на проде для регистрации и запроса SMS."""
    if not captcha.required():
        return
    try:
        captcha.verify(token, answer)
    except captcha.CaptchaError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/register")
def register(
    phone: str = Form(...),
    password: str = Form(...),
    name: str = Form(""),
    captcha_token: str = Form(""),
    captcha_answer: str = Form(""),
) -> dict:
    _check_captcha(captcha_token, captcha_answer)
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


@router.post("/otp/request")
def otp_request(
    phone: str = Form(...),
    channel: str = Form("call"),
    captcha_token: str = Form(""),
    captcha_answer: str = Form(""),
) -> dict:
    _check_captcha(captcha_token, captcha_answer)
    try:
        return service.request_otp(phone, channel)
    except service.AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/otp/verify")
def otp_verify(phone: str = Form(...), code: str = Form(...)) -> dict:
    try:
        return service.verify_otp(phone, code)
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


@router.get("/profile")
def get_profile(auth_id: str | None = Depends(token_user_id)) -> dict:
    if auth_id is None:
        raise HTTPException(status_code=401, detail="Не авторизован")
    profile = service.get_profile(auth_id)
    if profile is None:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return profile


@router.post("/profile")
def update_profile(
    last_name: str = Form(""),
    first_name: str = Form(""),
    middle_name: str = Form(""),
    gender: str = Form(""),
    birth_date: str = Form(""),
    city: str = Form(""),
    auth_id: str | None = Depends(token_user_id),
) -> dict:
    if auth_id is None:
        raise HTTPException(status_code=401, detail="Не авторизован")
    try:
        return service.update_profile(
            auth_id, last_name, first_name, middle_name, gender, birth_date, city
        )
    except service.AuthError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
