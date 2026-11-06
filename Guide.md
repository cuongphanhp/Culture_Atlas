# Hướng dẫn chạy CultureAtlas AI

Tài liệu này hướng dẫn chạy toàn bộ app trên máy dev (Linux/macOS) theo một trong hai cách:

- **Cách A — Conda + Docker** (khuyên dùng khi phát triển): mỗi phần chạy riêng, dễ debug.
- **Cách B — Docker Compose**: một lệnh chạy tất cả.

## 1. App gồm những gì

| Thành phần | Thư mục | Cổng | Vai trò |
|---|---|---|---|
| PostgreSQL 16 | `src/database` | 5432 | Dữ liệu có cấu trúc, **metadata + URL của file media**, văn bản của chỉ mục, tìm kiếm từ khoá |
| Object storage MinIO (S3) | `src/object-storage` | 9000 (S3), 9001 (console) | **File phi cấu trúc**: ảnh, video, âm thanh, tài liệu, payload thô của worker |
| Qdrant (vector DB) | `compose.yaml` | 6333 | **Embedding** của chỉ mục AI Guide |
| Backend API (FastAPI) | `src/backend/app` | 8000 | Content API, AI API, Admin API. Swagger ở `/api/docs` |
| Worker thu thập dữ liệu | `src/backend/worker` | — | Lấy dữ liệu từ 10 nguồn mở và nạp vào PostgreSQL |
| AI local (FastAPI, CPU) | `src/ai-local` | 8100 | Nhận dạng giọng nói, đọc văn bản, embedding, rerank |
| Frontend (Angular) | `src/frontend` | 4200 | Giao diện web |
| Hạ tầng cho test | `compose.test.yaml` | 55432 · 59000 · 56333 | PostgreSQL, MinIO và Qdrant riêng của bộ test (dữ liệu trong RAM) |

**Nguyên tắc lưu trữ:**
- File nằm ở MinIO; DB chỉ giữ metadata (bucket, khoá, loại, kích thước, sha256, tác giả, giấy phép) cùng URL `/media/<khoá>`.
- Embedding nằm ở Qdrant.
- Trình duyệt tải ảnh qua `/media/*` (nginx hoặc proxy dev chuyển tới MinIO, chỉ cho đọc).

Vì sao chọn và các ngoại lệ bảo mật: [docs/security-exceptions.md](docs/security-exceptions.md).

Core AI là **OpenAI `gpt-6-luna`**, dự phòng bằng **`gpt-4o`**. Mọi AI còn lại chạy local bằng model mã nguồn mở. Lý do chọn: [docs/11-vietnamese-chat-stack.md](docs/11-vietnamese-chat-stack.md).

> **Trạng thái hiện tại (11/2026):**
> - Frontend là prototype dùng dữ liệu mẫu, **chưa gọi API**.
> - Backend mới có `/api/health` và 3 API giọng nói (`/api/ai/transcribe`, `/api/ai/speech`, `/api/ai/voices`).
> - Content API, chat, so sánh, quiz và admin đang được làm. Danh sách tính năng còn chờ: chạy `scripts/test.sh` và xem phần **PENDING**.
> - Worker và AI local đã chạy được đầy đủ.

## 2. Chuẩn bị

| Công cụ | Phiên bản | Dùng cho | Kiểm tra |
|---|---|---|---|
| Docker + Docker Compose v2 (BuildKit) | mới | PostgreSQL (bắt buộc), hoặc chạy toàn bộ | `docker compose version` |
| Conda (Anaconda/Miniconda) | mới | Môi trường Python | `conda --version` |
| Node.js | **22** | Frontend | `node -v` |
| Google Chrome | bất kỳ | Chỉ cần cho nguồn `official_sites` của worker (Selenium) | `google-chrome --version` |

**Phần cứng:**
- RAM ≥ 16 GB. Riêng AI local cần khoảng 6 GB khi đã nạp đủ model.
- Ổ đĩa trống khoảng 8 GB (model AI ~5 GB, thư viện torch CPU ~1 GB).
- Không cần GPU.

## 3. Lấy mã nguồn và tạo file `.env`

```bash
git clone <repo-url> Culture && cd Culture
cp .env.example .env
```

Mở `.env` và sửa các dòng sau:

```dotenv
OPENAI_API_KEY=sk-...                 # bắt buộc cho chat AI
LLM_MODEL=gpt-6-luna                  # chỉ nhận gpt-6-luna hoặc gpt-4o
LLM_FALLBACK_MODEL=gpt-4o
DATABASE_URL=postgresql+asyncpg://atlas:atlas@localhost:5432/culture_atlas   # khi chạy theo Cách A
JWT_SECRET=<chuỗi ngẫu nhiên dài>     # tạo bằng: openssl rand -hex 32
```

Lưu ý:
- `.env` đã nằm trong `.gitignore`. **Không commit file này.**
- Mỗi biến chỉ nên có **một dòng**. Nếu có hai dòng `OPENAI_API_KEY`, dòng sau sẽ ghi đè dòng trước.
- Các khoá `SMITHSONIAN_API_KEY`, `EUROPEANA_WSKEY`, `REST_COUNTRIES_TOKEN` là tuỳ chọn. Không có thì worker dùng khoá demo (bị giới hạn lượt) hoặc bỏ qua nguồn đó.

## 4. Cách A — Chạy bằng Conda (khuyên dùng khi phát triển)

> **Chạy nhanh trong VS Code** (sau khi đã làm xong các bước cài đặt 4.2, 4.4 và có dữ liệu ở 4.3):
> - Bấm `Ctrl+Shift+P` → **Tasks: Run Task** → **CultureAtlas: chạy toàn bộ**.
> - VS Code mở 4 terminal xếp cạnh nhau: *1 · Database*, *2 · Backend API*, *3 · AI local*, *4 · Frontend*. Mỗi terminal chạy `scripts/dev.sh db|api|ai|web`.
> - Cổng 8000/4200 bị bận thì script tự chuyển sang cổng kế tiếp và in địa chỉ thật ra terminal.
> - Muốn dừng: bấm `Ctrl+C` trong từng terminal, hoặc **Tasks: Terminate Task**.
> - **Truy cập từ máy khác** (khi SSH, Tailscale hoặc LAN): Backend và Frontend lắng nghe ở `0.0.0.0`, nên mở được bằng IP của máy chạy, ví dụ `http://100.x.x.x:4200`. Các địa chỉ dùng được đều được in ra terminal. AI local chỉ mở cho `127.0.0.1`. Chỉ muốn mở trong máy này: đặt `DEV_HOST=127.0.0.1`.
> - Script tự tìm conda và Node 22 (qua nvm), kể cả khi shell của VS Code Task không có chúng trong PATH.
>
> Không dùng VS Code thì làm thủ công như dưới đây.

Cần **4 terminal**, chạy lần lượt:
- Terminal 1: database + worker.
- Terminal 2: API.
- Terminal 3: AI local.
- Terminal 4: frontend.

Mọi lệnh đều chạy từ **thư mục gốc repo**.

### 4.1 Database, object storage, vector DB

```bash
docker compose up -d --wait db object-storage qdrant
```

- Lần đầu chạy, PostgreSQL tự tạo schema từ `src/database/culture_atlas.sql` và thêm 10 quốc gia mẫu.
- MinIO và Qdrant cần `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `QDRANT_API_KEY` trong `.env` (mục 3). Cả ba chỉ mở cho `127.0.0.1`.
- Bảng điều khiển MinIO: <http://localhost:9001> (đăng nhập bằng `S3_ACCESS_KEY` / `S3_SECRET_KEY`).
- Kiểm tra: `docker compose exec db psql -U atlas -d culture_atlas -c "select count(*) from countries"` phải trả về `10`.

### 4.2 Môi trường Python cho backend + worker

```bash
conda create -y -n culture-api python=3.12
conda activate culture-api
pip install -e "src/backend[dev]"
```

### 4.3 Thu thập và nạp dữ liệu (worker)

```bash
conda activate culture-api
set -a && . ./.env && set +a                       # nạp S3_*, QDRANT_* cho worker (chạy từ gốc repo)
cd src/backend
export WORKER_DATABASE_URL=postgresql://atlas:atlas@localhost:5432/culture_atlas

python -m worker.cli sources                       # liệt kê 10 nguồn
python -m worker.cli run-all                       # thu thập (~5 phút, có giãn cách để không làm phiền máy chủ nguồn)
python -m worker.cli aggregate                     # gộp dữ liệu → data/aggregated + data/report.md
python -m worker.cli load --dsn "$WORKER_DATABASE_URL"   # nạp vào PostgreSQL; file media đã xác minh giấy phép → MinIO
python -m worker.cli seed-media ../media-seed      # ảnh của giao diện (src/media-seed) → MinIO + metadata vào DB
cd ../..
```

- `.env` cần `S3_ENDPOINT=localhost:<S3_PORT>` và `QDRANT_URL=http://localhost:6333` để worker chạy trên máy chủ tìm thấy MinIO và Qdrant.
- Nếu thiếu `seed-media`, giao diện sẽ không có ảnh, vì ảnh không còn đóng gói vào bản build frontend.

- **Sau khi đã chạy AI local (bước 4.4)**, lập chỉ mục cho AI Guide. Nếu thiếu bước này, AI chỉ trả lời được câu hỏi dữ kiện:

  ```bash
  cd src/backend && python -m worker.cli index --dsn "$WORKER_DATABASE_URL" --ai-local-url http://localhost:8100
  ```

  Lệnh này chia đoạn tài liệu tham khảo, di sản UNESCO và claim đã duyệt rồi tạo embedding (~3–4 phút cho ~1.200 đoạn). Văn bản lưu vào PostgreSQL, **vector lưu vào Qdrant**. Chạy lại sau mỗi lần nạp dữ liệu mới.
- Muốn thử nhanh với ít dữ liệu: `python -m worker.cli run unesco_whc wikipedia --countries JP,VN --limit 5`.
- Muốn đồng bộ định kỳ: `python -m worker.scheduler`.
- Chi tiết về nguồn và quy tắc thu thập: [docs/09-data-ingestion.md](docs/09-data-ingestion.md).

### 4.4 AI local (giọng nói, embedding, rerank)

Phần này dùng một môi trường **riêng**, vì có torch và onnxruntime nặng.

```bash
conda create -y -n culture-ai python=3.12
conda activate culture-ai
pip install --extra-index-url https://download.pytorch.org/whl/cpu -e "src/ai-local[export,dev]"

cd src/ai-local
python -m ai_local.download                        # tải ~5 GB model + xuất reranker sang ONNX int8, một lần (~4–6 phút, cần ~11 GB RAM lúc xuất)
uvicorn ai_local.main:app --port 8100              # Terminal 3: để chạy
```

- Model được nạp ở lần gọi đầu tiên, mất vài giây. Đặt `AI_LOCAL_PRELOAD=1` để nạp sẵn ngay khi khởi động.
- Kiểm tra: `curl localhost:8100/health`.
- Model, giọng đọc và cấu hình: [src/ai-local/README.md](src/ai-local/README.md).

### 4.5 Backend API

```bash
conda activate culture-api
cd src/backend
uvicorn app.main:app --reload --port 8000          # Terminal 2: để chạy
```

- Mở Swagger tại <http://localhost:8000/api/docs>.
- Backend tự đọc `.env` ở gốc repo. Biến môi trường đặt trực tiếp sẽ được ưu tiên hơn `.env`.

### 4.6 Frontend

```bash
cd src/frontend
npm ci --legacy-peer-deps                          # --legacy-peer-deps là bắt buộc (xem mục 8)
npx ng serve --port 4200                           # Terminal 4: để chạy
```

Mở <http://localhost:4200>.

### 4.7 Kiểm tra toàn bộ đã chạy

```bash
curl localhost:8000/api/health                     # {"status":"ok"}
curl localhost:8100/health                         # {"status":"ok","loaded":{...}}
curl localhost:8000/api/ai/voices                  # 25 giọng Bắc/Nam (backend → AI local)

# Đọc thử một câu thành giọng nói, rồi nhận dạng lại
curl -s -X POST localhost:8000/api/ai/speech -H 'Content-Type: application/json' \
     -d '{"text":"Xin chào, mình là hướng dẫn viên văn hoá.","voice":"Thái Sơn"}' -o hello.wav
curl -s -X POST localhost:8000/api/ai/transcribe -F "file=@hello.wav"
```

## 5. Cách B — Chạy tất cả bằng Docker Compose

Các image được build theo [docker-production-skill.md](docker-production-skill.md) (mức 2: production container). Đo ngày 05/11/2026:

| Image | Kích thước | Nội dung |
|---|---|---|
| `culture-atlas/web` | ~97 MB | Angular bản production + nginx-unprivileged; nginx chuyển `/api` tới backend |
| `culture-atlas/backend` | ~450 MB | API và worker dùng chung image |
| `culture-atlas/ai-local` | ~810 MB | Chỉ ONNX Runtime + PyAV, **không có torch**. Trước khi tối ưu là 3.54 GB |
| `culture-atlas/ai-local-setup` | ~2.7 GB | `ai-local` + torch CPU. **Chỉ dùng một lần** để tải model và xuất reranker sang ONNX int8 |

```bash
# 1. Build image
docker compose build

# 2. Nạp model AI vào volume ai-models (~3.5 GB), chọn MỘT cách:
docker compose --profile setup run --rm ai-local-setup   # a) tải từ Hugging Face (~5 phút, lúc xuất reranker cần ~11 GB RAM)
scripts/seed-ai-models.sh                                 # b) chép từ ~/.cache/huggingface đã có (không cần Internet)

# 3. Chạy toàn bộ (các container tự khởi động lại khi server reboot)
docker compose up -d --wait

# 4. Nạp dữ liệu lần đầu (sau đó service worker tự đồng bộ theo lịch)
docker compose run --rm worker python -m worker.cli run-all
docker compose run --rm worker python -m worker.cli load                 # media đã xác minh giấy phép → MinIO
docker compose run --rm -v ./src/media-seed:/seed:ro worker python -m worker.cli seed-media /seed   # ảnh giao diện → MinIO
docker compose run --rm worker python -m worker.cli index                # văn bản → PostgreSQL, vector → Qdrant
```

**DB đã tạo trước ngày 06/11/2026** cần chạy các migration **theo thứ tự**, rồi chạy lại `load`, `seed-media`, `index`:
- 002: chỉ mục tài liệu tham khảo và di sản;
- 003: media lưu ở object storage;
- 004: embedding chuyển sang Qdrant.

```bash
for m in 002_entry_chunks_reference 003_media_object_storage 004_embeddings_to_qdrant; do
  docker compose exec -T db psql -U atlas -d culture_atlas -v ON_ERROR_STOP=1 < src/database/migrations/$m.sql
done
```

- Cách 2b dùng khi máy chủ không vào được Hugging Face, hoặc khi đã chạy Cách A (`python -m ai_local.download`) trên cùng máy.
- Nếu mạng chặn **Docker Hub**: các Dockerfile đã lấy base image từ **Amazon ECR Public** (`public.ecr.aws`, bản sao chính thức của Docker Official Images), nên vẫn build được.

**Truy cập:**
- Web: <http://IP-máy-chủ:4200>.
- Swagger: <http://IP-máy-chủ:8000/api/docs>, hoặc qua web tại `/api/docs`.

**Bảo mật đã bật:**

| Lớp | Thiết lập |
|---|---|
| Image | Multi-stage build; base ghim theo digest; thư viện khoá phiên bản (`requirements.lock`); không có pip lúc chạy; gói hệ thống đã vá; `.dockerignore` loại `.env` và khoá bí mật |
| Container | User không phải root (10001, nginx 101); root filesystem **chỉ đọc**; `cap_drop: ALL` (riêng DB giữ 5 capability tối thiểu); `no-new-privileges`; giới hạn CPU, RAM và số tiến trình; xoay vòng log |
| Mạng | Chỉ **web** và **API** mở ra ngoài. DB chỉ mở cho `127.0.0.1`. AI local **không mở cổng nào** và nằm trong mạng `internal`, nên không ra được Internet: âm thanh của người dùng không thể rời máy chủ |
| Bí mật | Không nằm trong image. Chỉ được truyền vào lúc chạy qua `env_file: .env` |

**Quét lỗ hổng:** `scripts/scan-images.sh` (Trivy, quét file tar của image, không cần cấp quyền truy cập Docker).
- Kết quả ngày 05/11/2026: **0 CRITICAL**. web: 0 HIGH.
- backend và ai-local còn 46 HIGH, đều trong gói Debian của base image và **chưa có bản vá** từ Debian. Các lỗ hổng này cần theo dõi và vá khi Debian phát hành bản sửa: build lại để chạy `apt-get upgrade`.

**Lưu ý:**
- Trong compose, các địa chỉ nội bộ (`DATABASE_URL`, `WORKER_DATABASE_URL`, `AI_LOCAL_URL`) đã được đặt sẵn và **ghi đè** giá trị trong `.env`.
- Image Python không có Chrome, nên nguồn `official_sites` (dùng Selenium) bị bỏ qua khi chạy trong container.
- Sửa code xong thì build lại phần đã sửa, ví dụ: `docker compose up -d --build api web`.
- Cập nhật thư viện: sửa `pyproject.toml`, tạo lại `requirements.lock` bằng `pip freeze` trong `python:3.12-slim`, rồi build, chạy `scripts/test.sh` và `scripts/scan-images.sh`.

**Đổi cổng khi bị trùng** (ví dụ máy đã có app khác dùng 8000/4200): ghi vào `.env` để lần chạy nào cũng dùng đúng cổng.

```dotenv
API_PORT=8001
WEB_PORT=4201
```

Các biến đổi cổng: `DB_PORT`, `API_PORT`, `WEB_PORT`.

Xem log: `docker compose logs -f api` (thay `api` bằng `ai-local`, `web`, `worker`, `db`).

Dừng app:

```bash
docker compose down            # dữ liệu vẫn được giữ trong volume
docker compose down -v         # xoá luôn dữ liệu DB và model AI
```

## 6. Chạy test

```bash
scripts/test.sh                 # backend + AI local + frontend; tự bật PostgreSQL test ở cổng 55432
scripts/test.sh backend         # chỉ backend
scripts/test.sh ai-local        # chỉ AI local (engine giả, nhanh)
scripts/test.sh frontend        # chỉ frontend (Vitest)
```

- Không cần `conda activate`. Script tự tìm Python theo thứ tự:
  - thư mục `.venv` của từng phần;
  - môi trường conda `culture-api` / `culture-ai` (tạo ở mục 4);
  - `python3`.
- **Test với model thật** (chậm hơn, cần đã tải model): `cd src/ai-local && python -m pytest -q -m models`.
- **Test gọi OpenAI thật** (tốn một ít tiền): `cd src/backend && python -m pytest -q -m live`.
- Bật git hook để tự chạy test trước mỗi commit: `git config core.hooksPath .githooks`.
- Cách bộ test hoạt động (AC, PENDING, test truy vết): [src/backend/tests/README.md](src/backend/tests/README.md).

## 7. Biến môi trường chính

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `OPENAI_API_KEY` | — | Key OpenAI (bắt buộc cho chat) |
| `LLM_MODEL` | `gpt-6-luna` | Model chính. Chỉ nhận `gpt-6-luna` hoặc `gpt-4o` |
| `LLM_FALLBACK_MODEL` | `gpt-4o` | Model dự phòng khi model chính lỗi mạng hoặc quá tải. Để trống để tắt |
| `LLM_REASONING_EFFORT` | `none` | Mức suy luận cho Luna. `none` cho tốc độ nhanh nhất |
| `DATABASE_URL` | `…@localhost:5432/culture_atlas` | DB của API (driver `asyncpg`) |
| `WORKER_DATABASE_URL` | — | DB của worker (driver `psycopg`) |
| `AI_LOCAL_URL` | `http://localhost:8100` | Địa chỉ dịch vụ AI local |
| `JWT_SECRET` | `change-me` | **Phải đổi** khi deploy |
| `GUEST_DAILY_LIMIT` | `10` | Số lượt hỏi AI mỗi ngày của khách |
| `AI_LOCAL_THREADS` | nửa số luồng CPU | Số luồng CPU dùng cho AI local |
| `AI_LOCAL_TTS_PRECISION` | `int8` | Dùng `fp32` nếu CPU không có AVX-VNNI (kiểm tra: `grep -o avx_vnni /proc/cpuinfo`) |

## 8. Lỗi thường gặp

| Hiện tượng | Nguyên nhân / cách xử lý |
|---|---|
| `npm ci` báo `ERESOLVE` | Xung đột phiên bản giữa jsdom và canvas. Chạy `npm ci --legacy-peer-deps` |
| `port is already allocated` hoặc `Address already in use` | Cổng đang bị app khác dùng. Đổi cổng: `--port 8001` / `ng serve --port 4300`, hoặc `API_PORT=8001 WEB_PORT=4300 docker compose up -d` |
| API báo `LLM_MODEL=... không được phép` | Trong `.env` chỉ được đặt `gpt-6-luna` hoặc `gpt-4o` |
| Chat AI trả **503** | Thiếu hoặc sai `OPENAI_API_KEY`, hoặc OpenAI đang lỗi (đã thử cả model dự phòng) |
| `/api/ai/*` giọng nói trả **503** | Dịch vụ AI local chưa chạy, hoặc `AI_LOCAL_URL` sai. Kiểm tra `curl localhost:8100/health` |
| AI local báo `External data path escapes model directory` | Model tải bằng công cụ khác. Chạy lại `python -m ai_local.download`; lệnh này tự sửa symlink trong cache |
| AI local hết RAM | Mỗi model chỉ nạp khi được dùng. Nếu chỉ cần giọng nói, đừng gọi `/v1/rerank`. Có thể giảm `AI_LOCAL_THREADS` |
| Giao diện không có ảnh (ảnh trống / 404 ở `/media/...`) | Chưa nạp ảnh lên MinIO: chạy `seed-media` (mục 4.3 / 5). Kiểm tra `docker compose ps object-storage` |
| MinIO báo `port is already allocated` ở 9000/9001 | App khác đã dùng cổng này. Đặt `S3_PORT=9100`, `S3_CONSOLE_PORT=9101` trong `.env` (và `S3_ENDPOINT=localhost:9100` cho Cách A) |
| AI Guide chỉ tìm theo từ khoá (log: `Qdrant không khả dụng`) | Qdrant chưa chạy, sai `QDRANT_API_KEY`, hoặc chưa chạy `worker.cli index` |
| `psql: the database system is shutting down` ngay sau khi khởi động | DB đang chạy script khởi tạo. Dùng `docker compose up -d --wait db` để chờ đến khi sẵn sàng |
| Đổi schema SQL nhưng DB không cập nhật | Script khởi tạo chỉ chạy khi volume còn trống. Chạy `docker compose down -v` rồi `up` lại (**mất dữ liệu**) |
| Worker: nguồn `smithsonian` báo `429` | Khoá `DEMO_KEY` bị giới hạn. Đăng ký khoá miễn phí tại api.data.gov rồi đặt `SMITHSONIAN_API_KEY` |
| Worker: `official_sites` lỗi Chrome | Cài Google Chrome, hoặc đặt `WORKER_CHROME_BINARY=/đường/dẫn/chrome` |
| `scripts/test.sh` báo PostgreSQL test chưa chạy | Cần Docker. Chạy `docker compose -f compose.test.yaml up -d --wait` |
