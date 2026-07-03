# derm SDK — интеграция для брендов

Dermatologist-validated анализ кожи как B2B API. Два способа интеграции: готовый
**встраиваемый виджет** (без кода) и **Python SDK** (серверная интеграция).

> Косметический анализ кожи, не медицинский диагноз.

## 1. Встраиваемый виджет (привязка к сайту бренда)

Одна строка на странице бренда — и клиент анализирует кожу прямо на сайте:

```html
<div id="derm-widget"></div>
<script src="https://<ваш-derm-хост>/static/derm-widget.js"
        data-api-base="https://<ваш-derm-хост>"
        data-api-key="<API-ключ бренда>"
        data-target="#derm-widget"
        data-accent="#b8735a"></script>
```

Виджет вызывает `POST /v1/analyze` с заголовком `X-API-Key`. CORS включён, поэтому
запросы идут напрямую с домена бренда. Живой пример — `sdk/embed-example.html`.

Параметры `data-*`:
- `data-api-base` — адрес вашего derm-хоста
- `data-api-key` — API-ключ бренда
- `data-target` — CSS-селектор контейнера
- `data-accent` — акцентный цвет под брендбук

## 2. Python SDK (серверная интеграция)

```python
from derm_sdk import DermClient

client = DermClient(api_key="demo-key-derm-2026", base_url="http://localhost:8000")

result = client.analyze("face.jpg")
print(result["skin_type"], result["dermatologist_validated"])

protocol = client.protocol("face.jpg", age=32, hormonal_phase="лютеиновая")
usage = client.usage()   # план, сканы за месяц, оценка стоимости
```

Требует `pip install requests`.

## 3. Тарифы (монетизация)

| План | Цена/мес | Включено сканов | Цена за скан (сверх) |
|------|----------|-----------------|----------------------|
| Pay-as-you-go | $0 | 0 | $0.30 |
| Starter | $499 | 2 500 | $0.20 |
| Growth | $1 499 | 10 000 | $0.15 |
| Enterprise | $4 999 | 50 000 | $0.10 |

`GET /v1/plans` — тарифы, `GET /v1/usage` — использование и биллинг за месяц.

## 4. Эндпоинты API

| Метод | Путь | Назначение |
|-------|------|------------|
| POST | `/v1/analyze` | Фото → анализ кожи (JSON) |
| POST | `/v1/protocol` | Фото (+ квиз) → протокол ухода |
| GET | `/v1/usage` | План, сканы за месяц, оценка стоимости |
| GET | `/v1/plans` | Доступные тарифы |

Все требуют заголовок `X-API-Key` (кроме `/v1/plans`). Swagger: `/docs`.
