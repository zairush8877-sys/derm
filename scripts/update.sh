#!/usr/bin/env bash
# Обновление живого сайта Aura на сервере до свежего кода из GitHub.
# Запуск на сервере (в веб-консоли Timeweb):  bash /root/aura/scripts/update.sh
set -euo pipefail

cd /root/aura

echo "== 1/3 Забираем свежий код =="
git pull --ff-only

echo "== 2/3 Пересобираем и перезапускаем =="
docker compose up -d --build

echo "== 3/3 Проверяем =="
for i in $(seq 1 15); do
  if curl -fsS http://localhost/health 2>/dev/null; then
    echo; echo "✅ Сайт обновлён и работает"
    # Туннель поднимаем, если он есть, но остановлен.
    docker start aura-tunnel >/dev/null 2>&1 || true
    exit 0
  fi
  sleep 3
done
echo "❌ Сайт не ответил после обновления — логи:"
docker compose logs --tail 40 app
exit 1
