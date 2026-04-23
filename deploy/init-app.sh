#!/bin/bash
# init-app.sh — Chạy một lần sau khi clone repo (với user deploy)
# Usage: bash deploy/init-app.sh <domain>

set -euo pipefail

DOMAIN="${1:?Usage: $0 <domain>}"
APP_DIR="/opt/evening-learning"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"

echo "=== [1/6] Setup Python venv ==="
cd "$BACKEND_DIR"
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "=== [2/6] Tạo .env ==="
if [ ! -f "$BACKEND_DIR/.env" ]; then
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    echo ""
    echo "⚠️  Điền thông tin vào $BACKEND_DIR/.env trước khi tiếp tục:"
    echo "    nano $BACKEND_DIR/.env"
    echo ""
    echo "Sau đó chạy lại: bash deploy/init-app.sh $DOMAIN"
    exit 1
fi
chmod 600 "$BACKEND_DIR/.env"

echo "=== [3/6] Chạy database migrations ==="
cd "$BACKEND_DIR"
source venv/bin/activate
alembic upgrade head

echo "=== [4/6] Build frontend ==="
cd "$FRONTEND_DIR"
npm install
VITE_API_BASE_URL="https://$DOMAIN" npm run build

echo "=== [5/6] Cài systemd services ==="
sudo cp "$APP_DIR/deploy/evening-api.service" /etc/systemd/system/
sudo cp "$APP_DIR/deploy/evening-bot.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable evening-api evening-bot
sudo systemctl start evening-api evening-bot

echo "=== [6/6] SSL với Let's Encrypt ==="
sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos \
    --email "$(grep -oP '(?<=# email=).*' /opt/evening-learning/backend/.env || echo 'admin@example.com')" \
    --redirect || echo "⚠️  Certbot failed — chạy thủ công: sudo certbot --nginx -d $DOMAIN"

echo ""
echo "=== XONG init app ==="
echo ""
echo "Kiểm tra:"
echo "  curl https://$DOMAIN/health"
echo "  sudo journalctl -u evening-api -f"
