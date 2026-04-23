#!/bin/bash
# update.sh — Deploy code mới lên server (chạy với user deploy)
# Usage: bash deploy/update.sh [--skip-frontend] [--skip-migrate]

set -euo pipefail

APP_DIR="/opt/evening-learning"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"

SKIP_FRONTEND=false
SKIP_MIGRATE=false

for arg in "$@"; do
    case $arg in
        --skip-frontend) SKIP_FRONTEND=true ;;
        --skip-migrate)  SKIP_MIGRATE=true ;;
    esac
done

echo "=== [1] Pull code mới ==="
cd "$APP_DIR"
git pull origin master

echo "=== [2] Cập nhật backend dependencies ==="
cd "$BACKEND_DIR"
source venv/bin/activate
pip install -r requirements.txt --quiet

if [ "$SKIP_MIGRATE" = false ]; then
    echo "=== [3] Chạy migrations ==="
    alembic upgrade head
fi

if [ "$SKIP_FRONTEND" = false ]; then
    echo "=== [4] Build frontend ==="
    cd "$FRONTEND_DIR"
    npm install --silent
    DOMAIN=$(grep -oP '(?<=FRONTEND_URL=https://).*' "$BACKEND_DIR/.env" || echo "")
    VITE_API_BASE_URL="https://$DOMAIN" npm run build
fi

echo "=== [5] Restart services ==="
sudo systemctl restart evening-api evening-bot

echo ""
echo "=== XONG update ==="
sudo systemctl status evening-api --no-pager -l
