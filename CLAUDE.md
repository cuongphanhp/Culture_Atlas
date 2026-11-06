# CultureAtlas AI — quy tắc làm việc

## Đọc trước: tổng quan dự án

- [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) mô tả tính năng, kiến trúc, luồng xử lý và chức năng của **từng file**. Đọc file này trước khi tìm hiểu mã nguồn.
- Khi thêm, xoá hoặc đổi chức năng một file: sửa docstring / chú thích đầu file đó, rồi chạy `python3 scripts/project_overview.py`. Bản đồ file sẽ được sinh lại.
- Khi đổi tính năng, kiến trúc hoặc quy ước: sửa tay mục 1–6 của file tổng quan, và thêm một dòng vào mục "Thay đổi gần đây".
- `scripts/test.sh` và CI sẽ fail nếu file tổng quan đã cũ.

## Code sạch

- Mỗi file mở đầu bằng docstring (Python) hoặc chú thích `/** … */` (TypeScript) nói rõ file làm gì.
- Mỗi class và hàm public có docstring / JSDoc mô tả chức năng: tham số, giá trị trả về, lỗi ném ra nếu không hiển nhiên.
- Mọi tham số và giá trị trả về có type hint. Với phụ thuộc ngoài (LLM, embedder, Qdrant…), dùng `Protocol` thay vì để trống kiểu.
- Python được kiểm bằng `ruff check` (luật `D1`, `ANN` trong `pyproject.toml`). Lệnh này chạy trong `scripts/test.sh` và CI.
- Comment giải thích *vì sao*, không lặp lại *làm gì*.

## Kiểm thử là bắt buộc

- Mọi thay đổi tính năng (backend, frontend, schema DB, OpenAPI) phải **cập nhật test trong cùng thay đổi** và **chạy `scripts/test.sh`** trước khi báo là xong. Chi tiết: [src/backend/tests/README.md](src/backend/tests/README.md).
- Test bám theo mã tiêu chí `ACxx.y` trong `docs/06-acceptance-criteria.md`:
  - Backend: dùng `@ac(...)` và `@route(...)`.
  - Frontend: đặt tên test `[ACxx.y] …`.
  - `tests/test_traceability.py` sẽ fail nếu một AC hoặc endpoint chưa có test.
- Khi code một endpoint, các test PENDING của endpoint đó sẽ tự chạy và phải pass. Không được sửa test cho dễ pass. Nếu hành vi đúng khác với test, hãy sửa tài liệu AC trước rồi mới sửa test.
- Khi làm xong một tính năng UI, bỏ `.skip` ở các test `PENDING` tương ứng.
- Bộ test không bao giờ gọi OpenAI hay mạng ngoài. Mọi thứ bên ngoài phải đi qua `tests/fakes.py`.

## Môi trường

- Backend: `cd src/backend && .venv/bin/pip install -e ".[dev]"`.
- DB test: `docker compose -f compose.test.yaml up -d --wait` (cổng 55432, dữ liệu trong RAM).
- Frontend: `cd src/frontend && npm ci --legacy-peer-deps && npm test`.
- AI local (Python **3.12**): xem [src/ai-local/README.md](src/ai-local/README.md). Chạy test nhanh bằng `pytest -q`, test với model thật bằng `pytest -m models`.
- Git hook: `git config core.hooksPath .githooks`.

## AI

- **LLM (core AI) chỉ dùng OpenAI `gpt-6-luna` (chính) và `gpt-4o` (dự phòng)**. Danh sách cho phép nằm ở `ALLOWED_LLM_MODELS` trong `app/core/config.py`. Không thêm nhà cung cấp hoặc model LLM khác nếu chưa được đồng ý.
- Luna là model suy luận: không gửi `temperature`, dùng `reasoning_effort=none` để có TTFT thấp. `OpenAIAdapter` tự xử lý việc này.
- **Mọi AI khác chạy local, mã nguồn mở, miễn phí** trong `src/ai-local`: STT Gipformer, TTS VieNeu, embedding và rerank AITeamVN. Không dùng API trả phí cho các phần này.
- Khi chọn model mới, chỉ dùng model có giấy phép cho phép dùng thương mại (MIT, Apache, BSD). **Không dùng model CC BY-NC.**
- Lý do và số đo: [docs/11-vietnamese-chat-stack.md](docs/11-vietnamese-chat-stack.md).

## Docker

- Theo [docker-production-skill.md](docker-production-skill.md), mức 2 trở lên:
  - Multi-stage build, user không phải root, root filesystem chỉ đọc.
  - `cap_drop: ALL`, `no-new-privileges`, giới hạn tài nguyên.
  - Base image ghim theo digest (lấy từ `public.ecr.aws`); thư viện cài theo `requirements.lock`.
- Image `ai-local` lúc chạy **không được có torch**. Torch chỉ nằm trong target `setup`.
- AI local luôn ở mạng `internal` và không mở cổng ra host.
- Ngoại lệ đã ghi nhận: image MinIO (`object-storage`) còn lỗ hổng CRITICAL, xem [docs/security-exceptions.md](docs/security-exceptions.md). Không mở MinIO ra ngoài `127.0.0.1`; nginx chỉ cho `GET`/`HEAD` vào `/media/`.

## Lưu trữ dữ liệu

- **File phi cấu trúc** (ảnh, video, âm thanh, tài liệu, payload thô) nằm ở **object storage S3 (MinIO)**. **PostgreSQL chỉ lưu metadata** (bucket, object_key, content-type, kích thước, sha256, tác giả, giấy phép) **cùng URL** (`/media/<key>`). Không lưu nội dung file vào DB, không đóng gói ảnh vào bản build frontend.
- **Embedding nằm ở Qdrant** (point id = `entry_chunks.id`). PostgreSQL giữ văn bản và metadata của đoạn, không có cột vector.
- Chỉ media đã xác minh giấy phép mới được lưu file (BR09). Bucket media chỉ cho đọc từng object; bucket raw riêng tư.
- Truy cập Qdrant bằng REST (httpx), không dùng `qdrant-client`, để image nhỏ gọn.
- Đổi Dockerfile hoặc thư viện thì chạy `docker build --check`, build lại, rồi chạy `scripts/scan-images.sh`. Không chấp nhận lỗ hổng CRITICAL.

## Nguyên tắc sản phẩm

- "Có nguồn hoặc không khẳng định": claim không có nguồn thì không được xuất bản. Nội dung do AI sinh luôn ở trạng thái `draft`.
- Luồng xử lý request của người dùng không gọi API ngoài, ngoại trừ OpenAI (Luna / GPT-4o). Âm thanh của người dùng không được gửi ra ngoài và không được lưu.
