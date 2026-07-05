"""Фоновый планировщик автоматизаций.

Запускается при старте приложения (если DERM_AUTOMATION != 0) и раз в
DERM_AUTOMATION_INTERVAL секунд (по умолчанию час) выполняет все задачи.
На VPS работает из коробки; при желании можно выключить и дергать
POST /api/admin/run-jobs внешним cron.
"""

from __future__ import annotations

import logging
import threading
import time

from app.config import get_settings

logger = logging.getLogger("derm.automation")

_started = False


def start_background_scheduler() -> bool:
    """Запустить фоновый поток (однократно). Возвращает True, если запущен."""
    global _started
    settings = get_settings()
    if not settings.automation_enabled or _started:
        return False
    _started = True
    thread = threading.Thread(
        target=_loop,
        args=(settings.automation_interval,),
        daemon=True,
        name="aura-automation",
    )
    thread.start()
    logger.info("Планировщик автоматизаций запущен (интервал %s c)", settings.automation_interval)
    return True


def _loop(interval: int) -> None:  # pragma: no cover - фоновый поток
    from app.automation import service

    while True:
        time.sleep(max(60, interval))
        try:
            results = service.run_all()
            logger.info("Автоматизации выполнены: %s", results)
        except Exception as exc:
            logger.warning("Сбой цикла автоматизаций: %s", exc)
