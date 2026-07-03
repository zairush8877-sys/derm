"""Конфигурация платформы derm.

Настройки берутся из переменных окружения (см. .env.example).
Если ключ Anthropic не задан — автоматически включается демо-режим (mock).
"""

from __future__ import annotations

import os
from functools import lru_cache


class Settings:
    """Глобальные настройки приложения."""

    def __init__(self) -> None:
        self.anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "").strip()
        self.model: str = os.getenv("DERM_MODEL", "claude-opus-4-8").strip()
        self.db_path: str = os.getenv("DERM_DB_PATH", "derm.db").strip()
        self.demo_api_key: str = os.getenv("DERM_DEMO_API_KEY", "demo-key-derm-2026").strip()

        # Биллинг: платный AI-скан по фото (кожа/еда).
        self.scan_price_rub: int = int(os.getenv("DERM_SCAN_PRICE_RUB", "199"))
        self.free_trial_scans: int = int(os.getenv("DERM_FREE_TRIAL_SCANS", "1"))
        # Провайдер оплаты: demo (по умолчанию) | yookassa (подключается ключами).
        self.payment_provider: str = os.getenv("DERM_PAYMENT_PROVIDER", "demo").strip()

        # Демо-режим: явно через DERM_MOCK_MODE=1 ИЛИ если нет ключа Anthropic.
        forced = os.getenv("DERM_MOCK_MODE", "").strip().lower() in {"1", "true", "yes"}
        self.mock_mode: bool = forced or not self.anthropic_api_key

    @property
    def mode_label(self) -> str:
        return "Демо-режим (mock)" if self.mock_mode else "Реальный AI (Claude vision)"


@lru_cache
def get_settings() -> Settings:
    return Settings()
