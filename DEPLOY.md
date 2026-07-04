# Деплой Aura на VPS (пошагово, ~30 минут)

Сайт + приложение запускаются **одной командой** через Docker. HTTPS-сертификат
выпускается автоматически (Caddy + Let's Encrypt).

## Что понадобится
1. **VPS в РФ** — Timeweb Cloud / Selectel / REG.RU, тариф от ~500 ₽/мес
   (1 CPU, 1–2 ГБ RAM, Ubuntu 22.04+).
2. **Домен** (~300–800 ₽/год), А-запись домена → IP сервера.
3. **Ключ Anthropic** (console.anthropic.com) — чтобы AI-анализ был настоящим.
   Без ключа всё работает в демо-режиме.

## Шаги

### 1. Подключиться к серверу и поставить Docker
```bash
ssh root@ВАШ_IP
curl -fsSL https://get.docker.com | sh
```

### 2. Скачать проект
```bash
git clone https://github.com/zairush8877-sys/derm.git aura
cd aura
```

### 3. Настроить окружение
```bash
cp .env.example .env
nano .env
```
Обязательно заполнить:
- `DERM_SECRET` — любая длинная случайная строка (токены входа);
- `ANTHROPIC_API_KEY` — ключ Anthropic (или оставить пустым = демо-режим);
- добавить строку `DOMAIN=ваш-домен.ru` (для HTTPS).

### 4. Запустить
```bash
docker compose up -d --build
```
Через 1–2 минуты сайт доступен на `https://ваш-домен.ru` с валидным сертификатом.

### 5. Обновление после изменений кода
```bash
cd aura && git pull && docker compose up -d --build
```

## Проверка
- `https://домен/` — лендинг
- `https://домен/skin` — анализ кожи (с ключом Anthropic — реальный AI)
- `https://домен/docs` — Swagger B2B API
- `docker compose logs -f app` — логи приложения

## Данные и бэкапы
База (SQLite) лежит в docker-томе `aura-data` и переживает перезапуски.

Автобэкап раз в сутки (хранит 14 копий в `./backups`):
```bash
crontab -e
# добавить строку:
0 4 * * * /root/aura/scripts/backup.sh >> /root/aura/backups/backup.log 2>&1
```
Разовый бэкап: `./scripts/backup.sh`

## Автоматизации
Внутри приложения раз в час автоматически выполняются: обновление «живых»
протоколов подписчиков, напоминания о брошенной корзине, чистка кодов входа.
Управление и журнал — в админке (`/admin`). Интервал: `DERM_AUTOMATION_INTERVAL`
(секунды), выключить: `DERM_AUTOMATION=0` (тогда дергайте
`POST /api/admin/run-jobs` внешним cron).

## Что дальше (по мере роста)
- SMS-вход: получить ключ у SMS-провайдера → `SMS_API_KEY` в `.env`
  (сейчас код показывается на экране — демо-режим, 0 ₽).
- Оплата: ЮKassa (подключаем последней, по плану).
- При росте нагрузки: вынести БД в Postgres, добавить второй воркер uvicorn.
