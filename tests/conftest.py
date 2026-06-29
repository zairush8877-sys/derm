"""Общие фикстуры тестов: изолированная БД и демо-режим."""

import sys
from pathlib import Path

import pytest

# Гарантируем демо-режим (без сети) и временную БД для всех тестов.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _isolated_env(tmp_path, monkeypatch):
    monkeypatch.setenv("DERM_MOCK_MODE", "1")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("DERM_DB_PATH", str(tmp_path / "test.db"))
    # Сбрасываем кэш настроек, чтобы подхватить временное окружение.
    from app.config import get_settings
    get_settings.cache_clear()
    from app.db import store
    store.init_db()
    yield
    get_settings.cache_clear()


def _png_bytes(seed: int = 1) -> bytes:
    """Минимальный валидный PNG (1x1) с варьируемым содержимым по seed."""
    # Сигнатура PNG + немного «соли», чтобы хэш отличался.
    return b"\x89PNG\r\n\x1a\n" + bytes([seed % 256]) * (16 + seed)


@pytest.fixture
def png_bytes():
    return _png_bytes
