"""Точка входа для Vercel (serverless Python).

Vercel ищет ASGI-приложение `app` в файле внутри каталога /api.
Переэкспортируем основное FastAPI-приложение.

ВНИМАНИЕ: на Vercel файловая система только для чтения (кроме /tmp), поэтому
SQLite по умолчанию пишется в /tmp/derm.db (см. DERM_DB_PATH в vercel.json).
Для продакшена подключите внешнюю БД.
"""

from app.main import app  # noqa: F401  (re-export для Vercel)
