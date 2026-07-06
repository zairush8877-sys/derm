#!/usr/bin/env bash
# Запустить/перезапустить Cloudflare-туннель и напечатать HTTPS-ссылку.
# Туннель ставится с автоперезапуском (--restart) — переживает перезагрузку сервера.
# ВАЖНО: у бесплатного quick-туннеля адрес *.trycloudflare.com меняется при
# пересоздании. Для постоянного адреса подключите домен (см. DOMAIN_SETUP.md).
set -euo pipefail

docker rm -f aura-tunnel >/dev/null 2>&1 || true
docker run -d --name aura-tunnel --restart unless-stopped --network host \
  cloudflare/cloudflared:latest tunnel --url http://localhost:80 >/dev/null

echo "Поднимаем туннель…"
for i in $(seq 1 20); do
  url=$(docker logs aura-tunnel 2>&1 | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | head -1 || true)
  if [ -n "$url" ]; then
    echo; echo "🔗 Ваша ссылка: $url"; exit 0
  fi
  sleep 2
done
echo "Не удалось получить ссылку — смотрим логи:"
docker logs aura-tunnel --tail 20
exit 1
