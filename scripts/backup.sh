#!/usr/bin/env bash
# Консистентный бэкап базы Aura. Использует sqlite3 backup API внутри контейнера
# (снимок целостен даже при активной записи — в отличие от простого cp живого
# файла). Хранит последние 14 копий в ./backups.
# Автоматизация:  0 4 * * * /root/aura/scripts/backup.sh
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p backups
STAMP="$(date +%F-%H%M)"
TMP="/data/_backup_${STAMP}.db"

# 1) Внутри контейнера делаем целостный снимок в /data (тот же том).
docker compose exec -T app python -c "
import sqlite3, os
src = sqlite3.connect(os.getenv('DERM_DB_PATH', '/data/aura.db'))
dst = sqlite3.connect('${TMP}')
with dst:
    src.backup(dst)      # атомарный онлайн-бэкап SQLite
dst.close(); src.close()
"

# 2) Копируем целостный снимок наружу и удаляем временный внутри контейнера.
docker compose cp "app:${TMP}" "backups/aura-${STAMP}.db"
docker compose exec -T app rm -f "${TMP}"

# 3) Оставляем только 14 свежих копий.
ls -t backups/aura-*.db 2>/dev/null | tail -n +15 | xargs -r rm --

echo "OK: backups/aura-${STAMP}.db ($(du -h "backups/aura-${STAMP}.db" | cut -f1))"
