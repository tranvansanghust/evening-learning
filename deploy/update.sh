#!/bin/bash
# update.sh — Deploy code mới (chạy trên server)
# Usage: bash deploy/update.sh [--skip-frontend]

set -euo pipefail

SKIP_FRONTEND=false
for arg in "$@"; do
    [[ "$arg" == "--skip-frontend" ]] && SKIP_FRONTEND=true
done

cd /opt/evening-learning

echo "=== [1] Pull code mới ==="
git pull origin master

echo "=== [2] Rebuild và restart services ==="
if [ "$SKIP_FRONTEND" = true ]; then
    docker compose build api bot
    docker compose up -d api bot
else
    docker compose build
    docker compose up -d
fi

echo "=== [3] Dọn image cũ ==="
docker image prune -f

echo ""
echo "=== XONG ==="
docker compose ps
