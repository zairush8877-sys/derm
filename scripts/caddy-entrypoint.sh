#!/bin/sh
# Точка входа Caddy: если сертификат от lego уже есть — работаем по
# Caddyfile.files (готовые файлы); если нет — по обычному Caddyfile
# (ACME через DNS-плагин, сайт в любом случае жив на :80).
# Фоном ждём появления файлов и переключаемся без даунтайма (caddy reload),
# плюс раз в сутки перечитываем конфиг, чтобы подхватывать продления.
set -u
CRT=/certs/certificates/aura-wellness.ru.crt
KEY=/certs/certificates/aura-wellness.ru.key
FILESCFG=/etc/caddy/Caddyfile.files
BASECFG=/etc/caddy/Caddyfile

if [ -f "$CRT" ] && [ -f "$KEY" ]; then CFG="$FILESCFG"; else CFG="$BASECFG"; fi

(
  while [ ! -f "$CRT" ] || [ ! -f "$KEY" ]; do sleep 15; done
  sleep 3
  caddy reload --config "$FILESCFG" --adapter caddyfile 2>/dev/null || true
  while :; do
    sleep 86400
    caddy reload --config "$FILESCFG" --adapter caddyfile 2>/dev/null || true
  done
) &

exec caddy run --config "$CFG" --adapter caddyfile
