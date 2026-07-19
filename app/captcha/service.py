"""Генерация и проверка капчи.

Картинка: 5 символов без неоднозначных (нет 0/O, 1/I/L…), шум и линии.
Токен: nonce.timestamp.hmac — сервер ничего не хранит до момента проверки;
одноразовость обеспечивает таблица captcha_used (nonce помечается
использованным при успешной проверке).
Включение: DERM_CAPTCHA=1|0, по умолчанию auto — включена, когда платформа
не в демо-режиме (на проде), и выключена в тестах/локально.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import io
import os
import random
import secrets
import time

from app.config import get_settings
from app.db import store

ALPHABET = "23456789ABCEFHKMNPRTUVWXY"
CODE_LEN = 5
TTL_SECONDS = 600  # 10 минут на ввод


class CaptchaError(ValueError):
    """Капча не пройдена."""


def required() -> bool:
    """Нужна ли капча (env-переключатель, auto = не в демо-режиме)."""
    flag = os.getenv("DERM_CAPTCHA", "auto").strip().lower()
    if flag in {"1", "true", "yes"}:
        return True
    if flag in {"0", "false", "no"}:
        return False
    # auto: включаем на проде (реальный AI) ИЛИ когда настроен реальный
    # SMS-провайдер — иначе бот мог бы жечь платные звонки/SMS, обходя капчу
    # (мок-режим AI к стоимости входов отношения не имеет).
    if not get_settings().mock_mode:
        return True
    from app.auth import sms

    return sms.provider_configured()


def _sign(nonce: str, ts: int, code: str) -> str:
    secret = get_settings().auth_secret.encode()
    msg = f"{nonce}|{ts}|{code.upper()}".encode()
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()


def make_token(code: str, nonce: str | None = None, ts: int | None = None) -> str:
    nonce = nonce or secrets.token_hex(8)
    ts = ts or int(time.time())
    return f"{nonce}.{ts}.{_sign(nonce, ts, code)}"


def new_challenge() -> dict:
    """Новая капча: {token, image (data-URL PNG)}."""
    code = "".join(random.choice(ALPHABET) for _ in range(CODE_LEN))
    token = make_token(code)
    return {"token": token, "image": _render(code)}


def verify(token: str, answer: str) -> None:
    """Проверить ответ. Бросает CaptchaError; успешный nonce сжигается."""
    try:
        nonce, ts_raw, sig = token.split(".")
        ts = int(ts_raw)
    except (ValueError, AttributeError):
        raise CaptchaError("Капча не пройдена — обновите картинку")
    if time.time() - ts > TTL_SECONDS:
        raise CaptchaError("Капча устарела — обновите картинку и попробуйте снова")
    expected = _sign(nonce, ts, (answer or "").strip())
    if not hmac.compare_digest(expected, sig):
        raise CaptchaError("Код с картинки введён неверно")
    with store.connect() as conn:
        row = conn.execute(
            "SELECT nonce FROM captcha_used WHERE nonce = ?", (nonce,)
        ).fetchone()
        if row is not None:
            raise CaptchaError("Эта капча уже использована — обновите картинку")
        conn.execute(
            "INSERT INTO captcha_used (nonce, created_at) VALUES (?, ?)",
            (nonce, int(time.time())),
        )
        # Уборка: старые nonce больше не нужны (токен всё равно просрочен).
        conn.execute(
            "DELETE FROM captcha_used WHERE created_at < ?",
            (int(time.time()) - 2 * TTL_SECONDS,),
        )


def _render(code: str) -> str:
    """Нарисовать код: PNG как data-URL. Стиль — спокойный, в палитре сайта."""
    from PIL import Image, ImageDraw, ImageFont

    w, h = 220, 72
    img = Image.new("RGB", (w, h), "#f4f4f4")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34
        )
    except OSError:  # pragma: no cover — шрифт есть и в Docker, и в CI
        font = ImageFont.load_default()

    # лёгкий шум-точки
    for _ in range(180):
        draw.point(
            (random.randrange(w), random.randrange(h)),
            fill=random.choice(["#d9d9d9", "#cccccc", "#e3e3e3"]),
        )
    # пара плавных линий
    for _ in range(3):
        x1, x2 = random.randrange(w // 3), random.randrange(2 * w // 3, w)
        y1, y2 = random.randrange(h), random.randrange(h)
        draw.line((x1, y1, x2, y2), fill="#c9c9c9", width=2)

    # символы: каждый со своим поворотом и вертикальным сдвигом
    x = 18
    for ch in code:
        glyph = Image.new("RGBA", (44, 56), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glyph)
        color = random.choice(["#171717", "#333333", "#c0705b"])
        gd.text((4, 4), ch, font=font, fill=color)
        glyph = glyph.rotate(random.uniform(-22, 22), expand=True, resample=Image.BICUBIC)
        img.paste(glyph, (x, random.randint(0, 12)), glyph)
        x += 38

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
