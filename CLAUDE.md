# CultureAtlas AI — quy tắc làm việc

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

## Nguyên tắc sản phẩm

- "Có nguồn hoặc không khẳng định": claim không có nguồn thì không được xuất bản. Nội dung do AI sinh luôn ở trạng thái `draft`.
- Luồng xử lý request của người dùng không gọi API ngoài, ngoại trừ OpenAI (Luna / GPT-4o). Âm thanh của người dùng không được gửi ra ngoài và không được lưu.
