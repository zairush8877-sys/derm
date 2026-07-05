#!/usr/bin/env bash
# Первичная настройка VPS и (пере)запуск Aura.
# Запускается деплой-workflow'ом (.github/workflows/deploy-vps.yml) на сервере.
# Код к этому моменту уже распакован в /root/aura.
set -euo pipefail

APP_DIR=/root/aura
cd "$APP_DIR"

echo "== 1/4 Docker =="
if ! command -v curl >/dev/null 2>&1; then
  apt-get update -qq && apt-get install -y -qq curl
fi
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi

echo "== 2/4 Настройка .env =="
[ -f .env ] || cp .env.example .env

# Дописать/обновить ключ в .env (пустые значения не трогают существующие).
upsert() {
  local key="$1" val="$2"
  [ -z "$val" ] && return 0
  if grep -q "^${key}=" .env; then
    sed -i "s|^${key}=.*|${key}=${val}|" .env
  else
    echo "${key}=${val}" >> .env
  fi
}

upsert ANTHROPIC_API_KEY "${ANTHROPIC_API_KEY:-}"
upsert DERM_ADMIN_TOKEN "${DERM_ADMIN_TOKEN:-}"
upsert DOMAIN "${DOMAIN:-}"

# Секрет подписи токенов: заменить дефолтный на случайный (один раз).
if ! grep -q "^DERM_SECRET=." .env || grep -q "^DERM_SECRET=dev-secret-change-me" .env; then
  upsert DERM_SECRET "$(openssl rand -hex 32)"
fi

echo "== 3/4 Запуск контейнеров =="
docker compose up -d --build

echo "== 4/4 Проверка здоровья =="
for i in $(seq 1 15); do
  if curl -fsS http://localhost/health 2>/dev/null; then
    echo
    echo "✅ Aura работает"
    exit 0
  fi
  sleep 4
done
echo "❌ Сервис не ответил на /health — смотрим логи:"
docker compose logs --tail 50
exit 1
