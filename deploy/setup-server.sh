#!/bin/bash
# setup-server.sh — Chạy một lần trên server mới (Ubuntu 22.04)
# Usage: bash setup-server.sh <domain>
# Ví dụ: bash setup-server.sh learn.example.com

set -euo pipefail

DOMAIN="${1:?Usage: $0 <domain>}"
APP_DIR="/opt/evening-learning"
DEPLOY_USER="deploy"

echo "=== [1/7] Cập nhật hệ thống ==="
apt-get update && apt-get upgrade -y

echo "=== [2/7] Tạo user deploy ==="
if ! id "$DEPLOY_USER" &>/dev/null; then
    adduser --disabled-password --gecos "" "$DEPLOY_USER"
    usermod -aG sudo "$DEPLOY_USER"
    mkdir -p /home/$DEPLOY_USER/.ssh
    cp ~/.ssh/authorized_keys /home/$DEPLOY_USER/.ssh/ 2>/dev/null || true
    chown -R $DEPLOY_USER:$DEPLOY_USER /home/$DEPLOY_USER/.ssh
    chmod 700 /home/$DEPLOY_USER/.ssh
    chmod 600 /home/$DEPLOY_USER/.ssh/authorized_keys 2>/dev/null || true
fi

echo "=== [3/7] Cài packages ==="
apt-get install -y \
    python3.11 python3.11-venv python3-pip \
    mysql-server \
    nginx \
    certbot python3-certbot-nginx \
    git curl ufw

echo "=== [4/7] Cấu hình firewall ==="
ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw --force enable

echo "=== [5/7] Cài Node.js (cho build frontend) ==="
if ! command -v node &>/dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
fi

echo "=== [6/7] Setup thư mục app ==="
mkdir -p "$APP_DIR"
chown "$DEPLOY_USER:$DEPLOY_USER" "$APP_DIR"

echo "=== [7/7] Cài Nginx config ==="
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
sed "s/DOMAIN_NAME/$DOMAIN/g" "$SCRIPT_DIR/nginx.conf" \
    > /etc/nginx/sites-available/evening-learning
ln -sf /etc/nginx/sites-available/evening-learning \
       /etc/nginx/sites-enabled/evening-learning
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo ""
echo "=== XONG setup server ==="
echo ""
echo "Bước tiếp theo:"
echo "  1. su - $DEPLOY_USER"
echo "  2. cd $APP_DIR && git clone <repo-url> ."
echo "  3. Chạy: bash deploy/init-app.sh $DOMAIN"
