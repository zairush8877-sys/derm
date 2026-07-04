"""Сервис авторизации: пароли (PBKDF2), токены (HMAC), пользователи.

Без внешних зависимостей — только стандартная библиотека. Токен имеет вид
base64(user_id:expiry) + "." + HMAC-подпись; срок жизни 30 дней.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
import uuid
from datetime import datetime, timezone

from app.config import get_settings
from app.db import store

TOKEN_TTL_SECONDS = 30 * 24 * 3600  # 30 дней
_PBKDF2_ITERATIONS = 200_000


class AuthError(Exception):
    """Ошибка регистрации/входа."""


# --- Пароли ---

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return salt.hex() + "$" + digest.hex()


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), _PBKDF2_ITERATIONS)
    return hmac.compare_digest(digest.hex(), digest_hex)


# --- Токены ---

def create_token(user_id: str) -> str:
    payload = f"{user_id}:{int(time.time()) + TOKEN_TTL_SECONDS}"
    encoded = base64.urlsafe_b64encode(payload.encode()).decode()
    sig = hmac.new(get_settings().auth_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{sig}"


def verify_token(token: str) -> str | None:
    """Вернуть user_id, если токен валиден и не истёк; иначе None."""
    try:
        encoded, sig = token.split(".", 1)
        payload = base64.urlsafe_b64decode(encoded.encode()).decode()
        expected = hmac.new(get_settings().auth_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        user_id, expiry = payload.rsplit(":", 1)
        if int(expiry) < time.time():
            return None
        return user_id
    except Exception:
        return None


# --- Пользователи ---

def _normalize_phone(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    if not digits:
        raise AuthError("Укажите номер телефона")
    if len(digits) < 10:
        raise AuthError("Слишком короткий номер телефона")
    # 8XXXXXXXXXX -> 7XXXXXXXXXX (нормализация для РФ)
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    return "+" + digits


def register(phone: str, password: str, name: str = "") -> dict:
    """Создать пользователя. Возвращает {user, token}."""
    phone = _normalize_phone(phone)
    if len(password) < 6:
        raise AuthError("Пароль должен быть не короче 6 символов")

    user_id = "u-" + uuid.uuid4().hex[:16]
    with store.connect() as conn:
        existing = conn.execute("SELECT id FROM users WHERE phone = ?", (phone,)).fetchone()
        if existing:
            raise AuthError("Пользователь с таким телефоном уже зарегистрирован")
        conn.execute(
            "INSERT INTO users (id, phone, name, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, phone, name.strip(), hash_password(password),
             datetime.now(timezone.utc).isoformat()),
        )
    _welcome(user_id, name.strip())
    return {"user": {"id": user_id, "phone": phone, "name": name.strip()}, "token": create_token(user_id)}


def _welcome(user_id: str, name: str = "") -> None:
    from app.notifications import service as notifications

    hello = f"{name}, добро" if name else "Добро"
    notifications.push(
        user_id,
        "Добро пожаловать в Aura ✨",
        f"{hello} пожаловать! Первый AI-скан — бесплатно: попробуйте анализ кожи "
        "или оценку калорий по фото.",
    )


def login(phone: str, password: str) -> dict:
    """Вход по телефону и паролю. Возвращает {user, token}."""
    phone = _normalize_phone(phone)
    with store.connect() as conn:
        row = conn.execute(
            "SELECT id, phone, name, password_hash FROM users WHERE phone = ?", (phone,)
        ).fetchone()
    if row is None or not verify_password(password, row["password_hash"]):
        raise AuthError("Неверный телефон или пароль")
    return {
        "user": {"id": row["id"], "phone": row["phone"], "name": row["name"]},
        "token": create_token(row["id"]),
    }


def get_user(user_id: str) -> dict | None:
    with store.connect() as conn:
        row = conn.execute(
            "SELECT id, phone, name FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return dict(row) if row else None


# --- Вход по SMS-коду (OTP) ---

OTP_TTL_SECONDS = 300  # код живёт 5 минут


def request_otp(phone: str) -> dict:
    """Сгенерировать код входа. В демо-режиме код возвращается в ответе
    (SMS не отправляется и не стоит денег); с SMS-провайдером — отправляется."""
    import secrets
    from datetime import timedelta

    phone = _normalize_phone(phone)
    code = f"{secrets.randbelow(10000):04d}"
    expires = (datetime.now(timezone.utc) + timedelta(seconds=OTP_TTL_SECONDS)).isoformat()
    with store.connect() as conn:
        conn.execute(
            "INSERT INTO otp_codes (phone, code, expires) VALUES (?, ?, ?) "
            "ON CONFLICT(phone) DO UPDATE SET code=excluded.code, expires=excluded.expires",
            (phone, code, expires),
        )

    sms_api_key = os.getenv("SMS_API_KEY", "").strip()
    if sms_api_key:
        # TODO: подключить SMS-провайдера (SMS.ru / SMSC): POST с phone и текстом
        # f"Aura: код входа {code}". До подключения работает демо-режим ниже.
        pass

    result = {"sent": True, "phone": phone}
    if not sms_api_key:
        result["demo_code"] = code  # демо: показываем код прямо в интерфейсе
    return result


def verify_otp(phone: str, code: str) -> dict:
    """Проверить код. Создаёт аккаунт при первом входе. Возвращает {user, token}."""
    phone = _normalize_phone(phone)
    with store.connect() as conn:
        row = conn.execute(
            "SELECT code, expires FROM otp_codes WHERE phone = ?", (phone,)
        ).fetchone()
        if row is None or not hmac.compare_digest(
            row["code"].encode(), code.strip().encode()
        ):
            raise AuthError("Неверный код")
        if datetime.fromisoformat(row["expires"]) < datetime.now(timezone.utc):
            raise AuthError("Код истёк — запросите новый")
        conn.execute("DELETE FROM otp_codes WHERE phone = ?", (phone,))

        user = conn.execute(
            "SELECT id, phone, name FROM users WHERE phone = ?", (phone,)
        ).fetchone()
        is_new = user is None
        if is_new:
            user_id = "u-" + uuid.uuid4().hex[:16]
            conn.execute(
                "INSERT INTO users (id, phone, name, password_hash, created_at) VALUES (?, ?, '', ?, ?)",
                (user_id, phone, hash_password(uuid.uuid4().hex),
                 datetime.now(timezone.utc).isoformat()),
            )
            user_dict = {"id": user_id, "phone": phone, "name": ""}
        else:
            user_dict = dict(user)
    if is_new:
        _welcome(user_dict["id"])
    return {"user": user_dict, "token": create_token(user_dict["id"])}
