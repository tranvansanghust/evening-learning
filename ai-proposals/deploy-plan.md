# Deploy Evening Learning lên VPS

## Mục tiêu
Deploy project `evening-learning` lên VPS theo cách khớp với codebase hiện tại, ưu tiên dùng **một stack Docker Compose duy nhất** gồm các service `mysql`, `api`, `bot`, `nginx` để có một production baseline chạy được sớm, dễ update, ít drift với repo.

## Bối cảnh thực tế đã đọc từ code/docs
- Repo **đã có sẵn hạ tầng deploy bằng Docker Compose**:
  - `docker-compose.yml`
  - `docker-compose.override.yml` (dev only)
  - `backend/Dockerfile`
  - `deploy/Dockerfile.nginx`
  - `deploy/nginx.docker.conf`
  - `deploy/update.sh`
  - `Makefile`
- `backend/entrypoint.sh` tự chạy `alembic upgrade head` trước khi start API/bot container.
- `docker-compose.yml` hiện dựng 4 service:
  - `mysql`
  - `api`
  - `bot` (đang chạy `python -m app.bot_polling`)
  - `nginx`
- `backend/app/main.py` **không có webhook endpoint**.
- `TELEGRAM_WEBHOOK_SETUP.md` và plan deploy cũ đang giả định có `/webhook` hoặc `/webhook/telegram`, nhưng **code thực tế hiện giờ chưa expose route này**.
- `docs/tech/codebase-health.md` xác nhận bot hiện tại chạy như **một service/process riêng bên trong stack Docker Compose** dùng polling, không đi qua FastAPI.

## Kết luận thiết kế
**Deploy production khả thi ngay bây giờ bằng polling mode**, không cần webhook trước.

Lý do:
1. Phù hợp 100% với code hiện có.
2. Tận dụng luôn Docker assets đã tồn tại trong repo.
3. Tránh phải implement thêm webhook route chỉ để deploy.
4. Có thể nâng cấp sang webhook sau như một task riêng nếu cần scale/clean architecture hơn.

## Các file cần thay đổi / tạo mới
- `ai-proposals/deploy-plan.md` — **sửa** — cập nhật plan deploy để khớp codebase thật.
- `backend/.env` — **tạo trên server, không commit** — cấu hình production secrets.
- `docker-compose.prod.yml` — **có thể tạo mới** — nếu muốn tách production khỏi `docker-compose.override.yml` và tránh dev override hoàn toàn.
- `deploy/nginx.ssl.conf` — **có thể tạo mới** — nếu muốn terminate HTTPS trực tiếp trong containerized nginx.
- `deploy/update.sh` — **có thể sửa** — nếu cần đổi branch, thêm health-check, rollback step.
- `/etc/nginx/sites-available/...` — **không cần** nếu giữ Nginx trong Docker.
- `/etc/systemd/system/evening-api.service` — **không cần** cho phương án Docker-first.
- `/etc/systemd/system/evening-bot.service` — **không cần** cho phương án Docker-first.

## Kế hoạch thực hiện (từng bước)

### Phase 0 — Chốt strategy deploy
1. **Chọn polling-first production** thay vì webhook-first.
2. Không implement webhook trong task này.
3. Nếu sau này cần webhook, tách thành proposal riêng.

### Phase 1 — Audit deploy assets hiện có
1. Đọc lại các file deploy thật:
   - `docker-compose.yml`
   - `docker-compose.override.yml`
   - `backend/Dockerfile`
   - `backend/entrypoint.sh`
   - `deploy/Dockerfile.nginx`
   - `deploy/nginx.docker.conf`
   - `deploy/update.sh`
   - `Makefile`
2. Xác nhận các assumptions:
   - API chạy ở port 8000 trong network nội bộ Docker.
   - Bot polling là service riêng **trong cùng stack Docker Compose**, không phải một cách deploy tách rời khỏi compose.
   - MySQL dùng volume `mysql_data`.
   - Frontend được build vào image nginx.
3. Ghi lại các mismatch giữa docs và code:
   - docs cũ nói webhook route tồn tại, nhưng code chưa có.
   - docs cũ nói systemd/nginx host-level là đường chính, nhưng repo hiện nghiêng về Docker deploy.

### Phase 2 — Chuẩn bị VPS
1. Tạo VPS Ubuntu 22.04 hoặc 24.04, tối thiểu 2GB RAM.
2. Cấu hình user deploy không dùng root.
3. Bật firewall:
   - 22/tcp
   - 80/tcp
   - 443/tcp
4. Cài packages tối thiểu:
   - git
   - docker engine
   - docker compose plugin
   - certbot (nếu dùng SSL ngoài container)
5. Clone repo vào `/opt/evening-learning`.

### Phase 3 — Chuẩn bị cấu hình production
1. Tạo `backend/.env` thật trên server từ `backend/.env.example`.
2. Điền đầy đủ:
   - `DB_HOST=mysql`
   - `DB_PORT=3306`
   - `DB_USER`
   - `DB_PASSWORD`
   - `DB_NAME`
   - `MYSQL_ROOT_PASSWORD`
   - `TELEGRAM_BOT_TOKEN`
   - `LLM_BASE_URL`
   - `LLM_API_KEY`
   - `LLM_FAST_MODEL`
   - `LLM_SMART_MODEL`
   - `FRONTEND_URL=https://<domain>`
   - `VITE_API_BASE_URL=https://<domain>`
3. Set permission an toàn:
   - `chmod 600 backend/.env`
4. Xác nhận `docker-compose.yml` không vô tình nạp `docker-compose.override.yml` trong production workflow.
   - Nếu cần, tạo `docker-compose.prod.yml` và dùng explicit file list.

### Phase 4 — Build và bring up production stack
1. Chạy:
   ```bash
   docker compose --env-file backend/.env build
   docker compose --env-file backend/.env up -d
   ```
2. Xác nhận container chạy:
   ```bash
   docker compose ps
   ```
3. Xem logs:
   ```bash
   docker compose logs -f mysql api bot nginx
   ```
4. Kiểm tra migration đã chạy qua `entrypoint.sh`.
5. Test nội bộ:
   ```bash
   curl http://localhost/health
   ```

### Phase 5 — Expose domain + HTTPS
Có 2 phương án. Chỉ chọn **1**.

#### Phương án A — nhanh và ít sửa repo: Nginx/Caddy ngoài Docker làm reverse proxy
1. Để Docker nginx chỉ serve nội bộ hoặc bỏ hẳn nginx container.
2. Dùng host-level reverse proxy nhận 80/443.
3. Proxy vào container `api`/frontend tương ứng.
4. Dùng Certbot hoặc Caddy auto TLS.

#### Phương án B — giữ sát repo hiện tại: Nginx trong Docker + SSL ngoài hoặc chỉnh thêm SSL vào container
1. Dùng `nginx` service như compose hiện tại.
2. Nếu terminate SSL ngoài Docker, proxy 443 → `localhost:80`.
3. Nếu terminate SSL trong Docker, tạo thêm config/cert mount riêng.

**Khuyến nghị:** bắt đầu với **Phương án A** nếu VPS là single-host truyền thống; dễ quản lý SSL hơn.

### Phase 6 — Verify production behavior
1. Health check:
   ```bash
   curl https://<domain>/health
   ```
2. Verify frontend load được từ domain.
3. Verify API route chính:
   - `/health`
   - `/docs`
   - một route `/api/...` không phá app
4. Verify Telegram bot polling:
   - gửi `/start` cho bot
   - xem logs `docker compose logs -f bot`
5. Verify DB persist sau restart:
   ```bash
   docker compose restart
   docker compose ps
   ```
6. Verify migration vẫn an toàn khi restart `api`.

### Phase 7 — Vận hành và update
1. Dùng `deploy/update.sh` làm base, nhưng sửa cho khớp branch thực tế nếu cần.
2. Nên thêm các bước sau vào script update:
   - `git fetch --all`
   - checkout branch/commit rõ ràng
   - `docker compose build`
   - `docker compose up -d`
   - smoke test `/health`
3. Thiết lập backup:
   - MySQL dump định kỳ hoặc snapshot volume
4. Thiết lập monitoring/log rotation tối thiểu.

## Trình tự implement đề xuất (bite-sized)

### Task 1: Chuẩn hóa tài liệu deploy theo trạng thái code thật
**Mục tiêu:** sửa tài liệu/plan để không còn nói webhook-first như thể route đã tồn tại.

**Files:**
- Modify: `ai-proposals/deploy-plan.md`
- Read: `docs/tech/codebase-health.md`
- Read: `docker-compose.yml`
- Read: `TELEGRAM_WEBHOOK_SETUP.md`

**Expected outcome:** Plan phản ánh polling-first deploy.

### Task 2: Tách rõ production compose path
**Mục tiêu:** tránh production vô tình dùng `docker-compose.override.yml` của dev.

**Files:**
- Create or Modify: `docker-compose.prod.yml`
- Optional Modify: `Makefile`
- Optional Modify: `deploy/update.sh`

**Expected outcome:** Có lệnh rõ ràng cho production, không bị hot-reload bind mount.

### Task 3: Viết runbook cấu hình `.env` production
**Mục tiêu:** chốt chính xác các biến bắt buộc để bring up được stack.

**Files:**
- Modify: `backend/.env.example`
- Optional Create: `docs/tech/deployment-runbook.md`

**Expected outcome:** Không phải đoán env vars khi deploy thật.

### Task 4: Chọn và cố định chiến lược TLS/proxy
**Mục tiêu:** thống nhất 1 cách terminate HTTPS.

**Files:**
- Optional Create: `deploy/nginx.ssl.conf`
- Optional Create: `docs/tech/deployment-runbook.md`

**Expected outcome:** biết chính xác SSL nằm ở đâu, ai giữ cert, cách renew.

### Task 5: Deploy thử lên VPS và verify end-to-end
**Mục tiêu:** stack thật chạy được với domain, DB, bot polling.

**Files:**
- No repo code changes required necessarily
- Server-side only configuration

**Verification:**
- `docker compose ps`
- `curl https://<domain>/health`
- nhắn `/start` cho bot và xem bot phản hồi

## Lệnh deploy production đề xuất (phiên bản ngắn)
```bash
cd /opt/evening-learning
cp backend/.env.example backend/.env
nano backend/.env
chmod 600 backend/.env

docker compose --env-file backend/.env build
docker compose --env-file backend/.env up -d
docker compose --env-file backend/.env ps
curl http://localhost/health
```

## Rủi ro / mismatch cần lưu ý
1. **Webhook docs không khớp code thật**
   - Hiện chưa có route `/webhook` hoặc `/webhook/telegram` trong FastAPI app.
   - Không nên set Telegram webhook cho tới khi code webhook thật sự tồn tại.

2. **`docker-compose.override.yml` là dev-only**
   - Nếu production dùng `docker compose up` mặc định ngay trong repo, cần chắc chắn file override không bị áp dụng ngoài ý muốn.

3. **Polling trong production**
   - Hoàn toàn chạy được cho quy mô nhỏ/đầu tiên.
   - Nhưng bot sẽ là process stateful riêng; cần log/monitor/restart policy ổn.

4. **Migrations chạy trên entrypoint**
   - Thuận tiện, nhưng cần cẩn thận khi scale nhiều replica `api` cùng lúc về sau.

5. **Secret management**
   - `.env` chứa DB password, bot token, LLM key.
   - Không commit, không log, không copy vào docs công khai.

## Đề xuất cuối cùng
**Nên deploy bản đầu tiên bằng một stack Docker Compose duy nhất, trong đó `bot` là service polling riêng cùng với `mysql`, `api`, `nginx`**, không ép webhook ở vòng này. Sau khi production baseline ổn và app chạy thật, nếu muốn tối ưu Telegram delivery thì tạo proposal riêng cho:
- webhook endpoint trong FastAPI
- webhook registration flow
- bỏ polling service nếu phù hợp
