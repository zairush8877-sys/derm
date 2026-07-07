#!/usr/bin/env bash
# Автообновление Aura: каждые 5 минут сервер сам забирает свежий код
# из GitHub (ветка main) и пересобирает сайт, если появились изменения.
# Установка (один раз, на сервере): bash /root/aura/scripts/setup-autodeploy.sh
set -euo pipefail

cat > /usr/local/bin/aura-autodeploy <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
cd /root/aura
git fetch -q origin main
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)
[ "$LOCAL" = "$REMOTE" ] && exit 0
echo "[$(date '+%F %T')] Обновление: ${LOCAL:0:7} -> ${REMOTE:0:7}"
git merge --ff-only origin/main
docker compose up -d --build
sleep 8
curl -fsS http://localhost/health && echo " — сайт жив после обновления"
EOF
chmod +x /usr/local/bin/aura-autodeploy

# cron: проверка каждые 5 минут, журнал в /var/log/aura-deploy.log
( crontab -l 2>/dev/null | grep -v aura-autodeploy || true
  echo "*/5 * * * * /usr/local/bin/aura-autodeploy >> /var/log/aura-deploy.log 2>&1 # aura-autodeploy"
) | crontab -

echo "✅ Автообновление включено: сервер проверяет GitHub каждые 5 минут"
echo "   Журнал обновлений: tail -20 /var/log/aura-deploy.log"
