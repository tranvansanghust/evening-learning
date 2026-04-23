# Kế hoạch Deploy — Evening Learning

## Mục tiêu

Deploy hệ thống lên VPS: FastAPI backend + Telegram bot (webhook) + MySQL + React frontend (static), accessible qua HTTPS với domain riêng.

---

## Kiến trúc trên server

```
Internet
    │
    ▼
[Nginx] ← SSL termination (Let's Encrypt), port 80/443
    ├── / → serve frontend static files (React build)
    └── /api, /webhook, /health → proxy → uvicorn :8000
    
[systemd]
    ├── evening-api.service   → uvicorn FastAPI (port 8000)
    └── evening-bot.service   → Telegram bot (webhook mode, không polling)
    
[MySQL 8.0] → local, port 3306 (không expose ra ngoài)
```

---

## Phase 1: Thuê server

### Lựa chọn đề xuất: DigitalOcean Droplet hoặc Vultr

| Tier | RAM | vCPU | Storage | Giá/tháng | Ghi chú |
|------|-----|------|---------|-----------|---------|
| Tối thiểu | 1 GB | 1 | 25 GB SSD | ~$6 | Đủ cho dev/test |
| **Đề xuất** | **2 GB** | **1** | **50 GB SSD** | **~$12** | Production ổn định |
| Thoải mái | 4 GB | 2 | 80 GB SSD | ~$24 | Nếu có nhiều users |

**Đề xuất: Vultr hoặc DigitalOcean, 2GB RAM, Ubuntu 22.04 LTS**

Lý do: Python + MySQL + Nginx chiếm ~600MB RAM khi idle; 2GB đủ headroom.

**Cần thêm: Domain name** (~$10-15/năm, Namecheap hoặc GoDaddy)

---

## Phase 2: Chuẩn bị server (một lần)

### 2.1 Cấu hình ban đầu
```bash
# SSH vào server với root
ssh root@<server-ip>

# Tạo user deploy (không dùng root)
adduser deploy
usermod -aG sudo deploy

# Copy SSH key
mkdir -p /home/deploy/.ssh
cp ~/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh

# Cấu hình firewall
ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw enable
```

### 2.2 Cài đặt packages
```bash
# Python 3.11
sudo apt update && sudo apt install -y python3.11 python3.11-venv python3-pip

# MySQL 8.0
sudo apt install -y mysql-server
sudo mysql_secure_installation

# Nginx
sudo apt install -y nginx

# Certbot (Let's Encrypt)
sudo apt install -y certbot python3-certbot-nginx

# Git
sudo apt install -y git
```

### 2.3 Setup MySQL
```bash
sudo mysql -u root -p < docs/setup.sql
# hoặc chạy thủ công:
# CREATE DATABASE evening_learning CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
# CREATE USER 'evening_user'@'localhost' IDENTIFIED BY '<mật khẩu>';
# GRANT ALL ON evening_learning.* TO 'evening_user'@'localhost';
```

---

## Phase 3: Deploy ứng dụng

### 3.1 Clone repo và setup backend
```bash
sudo mkdir -p /opt/evening-learning
sudo chown deploy:deploy /opt/evening-learning
cd /opt/evening-learning

git clone <repo-url> .

cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Tạo .env từ .env.example
cp .env.example .env
nano .env  # điền đầy đủ: DB credentials, Telegram token, LLM API key, webhook URL
```

### 3.2 Chạy migrations
```bash
cd /opt/evening-learning/backend
source venv/bin/activate
alembic upgrade head
```

### 3.3 Build frontend
```bash
cd /opt/evening-learning/frontend
npm install
VITE_API_BASE_URL=https://<domain>/api npm run build
# Output: frontend/dist/
```

---

## Phase 4: Process management (systemd)

### 4.1 Service file cho FastAPI
Tạo `/etc/systemd/system/evening-api.service`:
```ini
[Unit]
Description=Evening Learning API
After=network.target mysql.service

[Service]
User=deploy
WorkingDirectory=/opt/evening-learning/backend
Environment="PATH=/opt/evening-learning/backend/venv/bin"
ExecStart=/opt/evening-learning/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### 4.2 Service file cho Telegram Bot
Tạo `/etc/systemd/system/evening-bot.service`:
```ini
[Unit]
Description=Evening Learning Telegram Bot
After=evening-api.service

[Service]
User=deploy
WorkingDirectory=/opt/evening-learning/backend
Environment="PATH=/opt/evening-learning/backend/venv/bin"
ExecStart=/opt/evening-learning/backend/venv/bin/python -m app.bot_polling
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

> **Lưu ý**: Trong production nên dùng webhook thay polling. Cần set `TELEGRAM_WEBHOOK_URL=https://<domain>/webhook` trong .env và đăng ký webhook với Telegram API.

```bash
sudo systemctl daemon-reload
sudo systemctl enable evening-api evening-bot
sudo systemctl start evening-api evening-bot
```

---

## Phase 5: Nginx + SSL

### 5.1 Nginx config
Tạo `/etc/nginx/sites-available/evening-learning`:
```nginx
server {
    listen 80;
    server_name <domain>;

    # Frontend static files
    root /opt/evening-learning/frontend/dist;
    index index.html;

    # API reverse proxy
    location ~ ^/(api|webhook|health) {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # React SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/evening-learning /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5.2 SSL với Let's Encrypt
```bash
# Trỏ DNS domain về server IP trước
sudo certbot --nginx -d <domain>
# Certbot tự động sửa nginx config và setup auto-renewal
```

---

## Phase 6: Đăng ký Telegram Webhook

Sau khi có HTTPS:
```bash
curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<domain>/webhook"
```

Cập nhật `.env`: `TELEGRAM_WEBHOOK_URL=https://<domain>/webhook`

Lúc này có thể tắt `evening-bot.service` nếu dùng webhook thuần (FastAPI nhận webhook trực tiếp).

---

## Phase 7: Kiểm tra

```bash
# Health check
curl https://<domain>/health

# Nginx logs
sudo tail -f /var/log/nginx/access.log

# App logs
sudo journalctl -u evening-api -f
sudo journalctl -u evening-bot -f

# MySQL
sudo systemctl status mysql
```

---

## Quy trình update code (sau lần đầu)

```bash
cd /opt/evening-learning
git pull origin master

# Nếu có thay đổi backend
cd backend
source venv/bin/activate
pip install -r requirements.txt  # nếu deps thay đổi
alembic upgrade head              # nếu có migration mới
sudo systemctl restart evening-api evening-bot

# Nếu có thay đổi frontend
cd ../frontend
npm install
VITE_API_BASE_URL=https://<domain>/api npm run build
# Nginx tự phục vụ file mới từ dist/
```

---

## Các file cần tạo/sửa khi implement

- `/etc/systemd/system/evening-api.service` — tạo mới trên server
- `/etc/systemd/system/evening-bot.service` — tạo mới trên server
- `/etc/nginx/sites-available/evening-learning` — tạo mới trên server
- `backend/.env` — điền credentials thật trên server
- (Optional) `deploy.sh` — script tự động hóa update code

---

## Chi phí ước tính/tháng

| Hạng mục | Chi phí |
|----------|---------|
| VPS 2GB (Vultr/DO) | ~$12 |
| Domain (.com/năm) | ~$1.2/tháng |
| LLM API (OpenAI) | tùy usage |
| **Tổng fixed** | **~$13-14/tháng** |

---

## Rủi ro & lưu ý

- **Secret management**: `.env` chứa tokens, không commit lên git. Dùng `chmod 600 .env`.
- **Bot webhook vs polling**: Webhook cần HTTPS (đã có). Polling đơn giản hơn nhưng không scale.
- **MySQL backup**: Cần setup cronjob `mysqldump` hàng ngày.
- **CORS**: Cập nhật `config.py` allowed origins khi đã có domain thật.
- **APScheduler**: Đang chạy trong process của bot — nếu bot restart thì scheduler reset.
