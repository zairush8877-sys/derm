"""Python SDK для derm B2B API.

Установка зависимости: pip install requests

Пример:
    from derm_sdk import DermClient

    client = DermClient(api_key="demo-key-derm-2026", base_url="http://localhost:8000")
    result = client.analyze("face.jpg")
    print(result["skin_type"], result["concerns"])

    usage = client.usage()
    print(usage["scans_this_month"], usage["estimated_cost_usd"])
"""

from __future__ import annotations

from typing import Any, BinaryIO


class DermError(Exception):
    """Ошибка вызова derm API."""


class DermClient:
    """Тонкий клиент над B2B API derm (dermatologist-validated анализ кожи)."""

    def __init__(self, api_key: str, base_url: str = "https://api.derm.example") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    # --- внутреннее ---
    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key}

    def _post(self, path: str, image: str | BinaryIO, data: dict | None = None) -> dict[str, Any]:
        import requests  # локальный импорт, чтобы не тянуть зависимость без нужды

        fh = open(image, "rb") if isinstance(image, str) else image
        try:
            resp = requests.post(
                f"{self.base_url}{path}",
                headers=self._headers(),
                files={"image": fh},
                data=data or {},
                timeout=60,
            )
        finally:
            if isinstance(image, str):
                fh.close()
        if resp.status_code == 401:
            raise DermError("Неверный API-ключ")
        if resp.status_code == 429:
            raise DermError("Превышен лимит тарифа")
        if not resp.ok:
            raise DermError(f"Ошибка API {resp.status_code}: {resp.text}")
        return resp.json()

    # --- публичное API ---
    def analyze(self, image: str | BinaryIO) -> dict[str, Any]:
        """Анализ кожи по фото. Возвращает структурированный результат."""
        return self._post("/v1/analyze", image)

    def protocol(self, image: str | BinaryIO, **quiz: Any) -> dict[str, Any]:
        """Персональный протокол ухода по фото (+ параметры квиза)."""
        return self._post("/v1/protocol", image, data=quiz)

    def usage(self) -> dict[str, Any]:
        """Использование и биллинг за текущий месяц."""
        import requests

        resp = requests.get(f"{self.base_url}/v1/usage", headers=self._headers(), timeout=30)
        if not resp.ok:
            raise DermError(f"Ошибка API {resp.status_code}: {resp.text}")
        return resp.json()

    def plans(self) -> dict[str, Any]:
        """Список доступных тарифов."""
        import requests

        resp = requests.get(f"{self.base_url}/v1/plans", timeout=30)
        return resp.json()
