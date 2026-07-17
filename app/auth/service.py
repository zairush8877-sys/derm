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

OTP_TTL_SECONDS = 300        # код живёт 5 минут
OTP_MAX_ATTEMPTS = 5         # попыток ввода кода, дальше — только новый код
OTP_RESEND_COOLDOWN = 60     # секунд между повторными отправками
OTP_MAX_PER_HOUR = 5         # SMS на один номер в час (SMS стоят денег)


def _check_sms_throttle(row, now: datetime) -> tuple[int, str]:
    """Антиспам реальных SMS. Возвращает (новый sent_count, window_start)."""
    if row is None:
        return 1, now.isoformat()
    if row["last_sent"]:
        elapsed = (now - datetime.fromisoformat(row["last_sent"])).total_seconds()
        if elapsed < OTP_RESEND_COOLDOWN:
            wait = int(OTP_RESEND_COOLDOWN - elapsed) + 1
            raise AuthError(f"Код уже отправлен — повторная отправка через {wait} сек.")
    window_start = row["window_start"]
    sent_count = row["sent_count"] or 0
    in_window = (
        window_start
        and (now - datetime.fromisoformat(window_start)).total_seconds() < 3600
    )
    if in_window:
        if sent_count >= OTP_MAX_PER_HOUR:
            raise AuthError("Слишком много запросов кода — попробуйте через час.")
        return sent_count + 1, window_start
    return 1, now.isoformat()


def request_otp(phone: str, channel: str = "call") -> dict:
    """Код входа: звонок (последние 4 цифры номера) или SMS.

    channel="call" — робот звонит, кодом служат последние 4 цифры входящего
    номера (в разы дешевле SMS); channel="sms" — классическое сообщение.
    Без настроенного провайдера — демо-режим: код возвращается в ответе
    и показывается в интерфейсе, деньги не тратятся.
    """
    import secrets
    from datetime import timedelta

    from app.auth import sms

    phone = _normalize_phone(phone)
    now = datetime.now(timezone.utc)
    real = sms.provider_configured()
    use_call = real and channel != "sms" and sms.call_code_supported()

    with store.connect() as conn:
        sent_count, window_start = 0, None
        if real:  # троттлинг только для реальных отправок — в демо коды бесплатны
            row = conn.execute(
                "SELECT last_sent, sent_count, window_start FROM otp_codes WHERE phone = ?",
                (phone,),
            ).fetchone()
            sent_count, window_start = _check_sms_throttle(row, now)

    # Код: при звонке его выдаёт провайдер (последние 4 цифры номера),
    # для SMS и демо генерируем сами.
    if use_call:
        try:
            code = sms.send_call_code(phone)
        except sms.SmsError as exc:
            import logging

            logging.getLogger("derm.auth").warning("Сбой звонка с кодом: %s", exc)
            raise AuthError(
                "Не получилось позвонить — попробуйте ещё раз или запросите SMS."
            )
    else:
        code = f"{secrets.randbelow(10000):04d}"

    with store.connect() as conn:
        expires = (now + timedelta(seconds=OTP_TTL_SECONDS)).isoformat()
        conn.execute(
            "INSERT INTO otp_codes (phone, code, expires, attempts, last_sent, sent_count, window_start) "
            "VALUES (?, ?, ?, 0, ?, ?, ?) "
            "ON CONFLICT(phone) DO UPDATE SET code=excluded.code, expires=excluded.expires, "
            "attempts=0, last_sent=excluded.last_sent, sent_count=excluded.sent_count, "
            "window_start=excluded.window_start",
            (phone, code, expires, now.isoformat() if real else None,
             sent_count, window_start),
        )

    if use_call:
        return {"sent": True, "phone": phone, "channel": "call"}

    if real:
        try:
            sms.send_sms(phone, f"Aura: код входа {code}. Никому не сообщайте его.")
        except sms.SmsError as exc:
            import logging

            logging.getLogger("derm.auth").warning("Сбой отправки SMS: %s", exc)
            raise AuthError("Не удалось отправить SMS — попробуйте ещё раз через минуту.")
        return {"sent": True, "phone": phone, "channel": "sms"}

    return {"sent": True, "phone": phone, "channel": "demo", "demo_code": code}


def verify_otp(phone: str, code: str) -> dict:
    """Проверить код. Создаёт аккаунт при первом входе. Возвращает {user, token}."""
    phone = _normalize_phone(phone)
    with store.connect() as conn:
        row = conn.execute(
            "SELECT code, expires, attempts FROM otp_codes WHERE phone = ?", (phone,)
        ).fetchone()
        if row is None:
            raise AuthError("Неверный код")
        if row["attempts"] >= OTP_MAX_ATTEMPTS:
            conn.execute("DELETE FROM otp_codes WHERE phone = ?", (phone,))
            conn.commit()  # иначе raise откатит удаление кода
            raise AuthError("Слишком много попыток — запросите новый код")
        if not hmac.compare_digest(row["code"].encode(), code.strip().encode()):
            conn.execute(
                "UPDATE otp_codes SET attempts = attempts + 1 WHERE phone = ?", (phone,)
            )
            conn.commit()  # иначе raise откатит счётчик попыток
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


# ===== Профиль пользователя =====

PROFILE_BONUS_POINTS = 50
_PROFILE_REQUIRED = {
    "last_name": "фамилия",
    "first_name": "имя",
    "gender": "пол",
    "birth_date": "дата рождения",
}


def get_profile(user_id: str) -> dict | None:
    """Профиль + список незаполненных обязательных полей."""
    with store.connect() as conn:
        row = conn.execute(
            "SELECT id, phone, name, last_name, first_name, middle_name, "
            "gender, birth_date, city, profile_bonus FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    if row is None:
        return None
    data = dict(row)
    missing = [label for f, label in _PROFILE_REQUIRED.items() if not data.get(f)]
    data["missing_required"] = missing
    data["complete"] = not missing
    data["bonus_points"] = PROFILE_BONUS_POINTS
    return data


def update_profile(
    user_id: str,
    last_name: str = "",
    first_name: str = "",
    middle_name: str = "",
    gender: str = "",
    birth_date: str = "",
    city: str = "",
) -> dict:
    """Сохранить профиль; за первое полное заполнение — баллы лояльности."""
    gender = gender.strip().lower()
    if gender and gender not in {"женщина", "мужчина"}:
        raise AuthError("Пол: выберите «женщина» или «мужчина»")
    birth_date = birth_date.strip()
    if birth_date:
        try:
            born = datetime.strptime(birth_date, "%Y-%m-%d")
        except ValueError:
            raise AuthError("Дата рождения — в формате ГГГГ-ММ-ДД")
        age = (datetime.now() - born).days // 365
        if not 10 <= age <= 110:
            raise AuthError("Проверьте дату рождения")

    fields = {
        "last_name": last_name.strip()[:80],
        "first_name": first_name.strip()[:80],
        "middle_name": middle_name.strip()[:80],
        "gender": gender,
        "birth_date": birth_date,
        "city": city.strip()[:80],
    }
    bonus_granted = False
    with store.connect() as conn:
        row = conn.execute(
            "SELECT id, profile_bonus FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if row is None:
            raise AuthError("Пользователь не найден")
        conn.execute(
            "UPDATE users SET last_name=?, first_name=?, middle_name=?, "
            "gender=?, birth_date=?, city=?, "
            "name = CASE WHEN ? != '' THEN ? ELSE name END "
            "WHERE id = ?",
            (*fields.values(), fields["first_name"], fields["first_name"], user_id),
        )
        complete = all(fields[f] for f in _PROFILE_REQUIRED)
        if complete and not row["profile_bonus"]:
            conn.execute("INSERT OR IGNORE INTO loyalty (user_id) VALUES (?)", (user_id,))
            conn.execute(
                "UPDATE loyalty SET points = points + ? WHERE user_id = ?",
                (PROFILE_BONUS_POINTS, user_id),
            )
            conn.execute("UPDATE users SET profile_bonus = 1 WHERE id = ?", (user_id,))
            bonus_granted = True

    if bonus_granted:
        from app.notifications import service as notifications

        notifications.push(
            user_id,
            "Спасибо за заполнение профиля!",
            f"Начислили {PROFILE_BONUS_POINTS} баллов — 1 балл = 1 ₽ при оплате в магазине.",
        )
    profile = get_profile(user_id)
    profile["bonus_granted_now"] = bonus_granted
    return profile
