# CultureAtlas AI — Tổng quan dự án

> **Đọc file này trước tiên.** Mục 1–6 viết tay: cập nhật khi đổi tính năng, kiến trúc hoặc quy ước.
> Mục 7 (bản đồ file) **tự sinh** từ docstring / chú thích đầu file: `python3 scripts/project_overview.py`.
> `scripts/test.sh` sẽ fail nếu tài liệu đã cũ, hoặc có file chưa có mô tả.

## 1. Sản phẩm

CultureAtlas AI là ứng dụng web giúp người Việt tìm hiểu văn hoá của 10 quốc gia: VN, JP, KR, CN, TH, IN, FR, MX, EG, KE.
Phong tục, phép lịch sự, tặng quà, lễ hội, ẩm thực và di sản UNESCO đều được lấy từ nguồn mở.

Nguyên tắc cốt lõi: **"có nguồn hoặc không khẳng định"**.
- Mọi thông tin văn hoá đều kèm trích dẫn.
- Nội dung do AI sinh luôn ở trạng thái `draft`.
- AI từ chối khi kho dữ liệu chưa đủ nguồn.

| Tính năng | Trang | Trạng thái |
|---|---|---|
| F1 Khám phá: bản đồ thế giới, tìm kiếm, thẻ quốc gia, chủ đề, lễ hội theo tháng | `/` | **Content API chạy thật** (`/api/countries`, `/api/search`, `/api/themes`, `/api/festivals`). Giao diện vẫn dùng dữ liệu mẫu + snapshot nguồn thật (nối API ở P3) |
| F1 Hồ sơ quốc gia: ảnh, mẹo lần đầu, bài viết theo danh mục, di sản UNESCO, báo cáo sai | `/countries/:iso` | Như trên (`/api/countries/{iso}`, `/api/entries/{id}`, `/api/heritage`, `/api/sources/{id}`, `/api/feedback`) |
| **F2 AI Cultural Guide**: hỏi đáp tiếng Việt, stream, trích dẫn, nhiều lượt, 3 mức giải thích, giọng nói, gợi ý câu hỏi theo quốc gia + mối quan tâm | `/guide` | **Chạy thật** (`/api/ai/*`) |
| F3 So sánh văn hoá 2 nước | `/compare` | **API chạy thật** (`POST /api/ai/compare`: bản đã duyệt hoặc nháp AI có nguồn). Giao diện vẫn là prototype (nối API ở P3) |
| F5 Culture Quiz | `/quiz` | Prototype giao diện |
| F7 Quản trị nội dung: duyệt, nguồn, độ phủ | `/admin` | Prototype giao diện. **Đăng nhập JWT + phân quyền chạy thật** (`/api/auth/*`, `/api/admin/users`); các API duyệt còn lại ở P3 |
| F8 Thu thập dữ liệu từ 10 nguồn mở | worker CLI | **Chạy thật** |
| F9 Giọng nói (STT/TTS local) | trong `/guide` | **Chạy thật** |
| F10 Lưu trữ: file ở MinIO, embedding ở Qdrant | — | **Chạy thật** |

Tiêu chí chấp nhận nằm ở [06-acceptance-criteria.md](06-acceptance-criteria.md). Hợp đồng API nằm ở [api/openapi.yaml](api/openapi.yaml). Lộ trình nằm ở [10-roadmap.md](10-roadmap.md).

## 2. Kiến trúc

```
Trình duyệt ──► web (nginx + Angular SPA) :4200
                  ├─ /api/*   ──► api (FastAPI) :8000 ──┬─► PostgreSQL 16   văn bản, metadata, chat_logs, FTS không dấu
                  │                                     ├─► Qdrant          embedding 1024 chiều (point id = entry_chunks.id)
                  │                                     ├─► ai-local        STT · TTS · embedding · rerank (mạng nội bộ, không mở cổng)
                  │                                     └─► OpenAI          gpt-6-luna (chính), gpt-4o (dự phòng) — duy nhất ra ngoài
                  └─ /media/* ──► object-storage (MinIO, chỉ GET/HEAD)   ảnh / file media
worker (CLI, cron) ── nguồn mở (UNESCO, Wikipedia, Wikidata, Smithsonian, Europeana, Commons, SCALE, trang du lịch…)
                  └─► data/ (raw → normalized → aggregated) ─► PostgreSQL + MinIO (file) + Qdrant (vector)
```

**Mạng Docker** ([compose.yaml](../compose.yaml)):
- `edge`: web, api.
- `backend`: api, worker, db, qdrant.
- `ai`: api, ai-local. Mạng nội bộ, không ra Internet.
- `media`: web, api, worker, MinIO.

DB, MinIO và Qdrant chỉ mở cổng trên `127.0.0.1`.

### Luồng một câu hỏi AI Guide ([app/ai/agent.py](../src/backend/app/ai/agent.py))

1. **Chuẩn bị phiên** (`prepare`):
   - Đọc phiên và lịch sử, chỉ khi `sessionId` thuộc đúng `X-Client-Id`.
   - Nhận diện quốc gia: trong câu hỏi → ngữ cảnh trang → lượt trước.
2. **Phân tuyến** ([router.py](../src/backend/app/ai/router.py)):
   - `smalltalk`: chào hỏi.
   - `structured`: câu hỏi dữ kiện. Trả từ DB, không gọi LLM.
   - `rag`: câu hỏi văn hoá.
3. **Truy xuất** (với `rag`, [retrieval.py](../src/backend/app/ai/retrieval.py)):
   - Tìm vector ở Qdrant và tìm từ khoá FTS ở PostgreSQL, riêng cho từng nước.
   - Gộp bằng RRF, rerank ở ai-local, giữ đoạn vượt ngưỡng.
   - Song song, LLM viết lại câu hỏi thành truy vấn tiếng Anh ([query_rewriter.py](../src/backend/app/ai/query_rewriter.py)). Bước này chỉ dùng khi bằng chứng đầu còn yếu.
4. **Không có bằng chứng**: từ chối lịch sự và ghi `feedback.type = unanswered`.
5. **Sinh câu trả lời** (`run`):
   - LLM stream câu trả lời.
   - [citation_verifier.py](../src/backend/app/ai/citation_verifier.py) lọc nhãn `[c#]` bịa ngay khi stream.
   - Tính `confidence`.
6. **Gợi ý câu hỏi tiếp** ([suggestions.py](../src/backend/app/ai/suggestions.py)):
   - Theo quốc gia và chủ đề người dùng quan tâm.
   - LLM viết; LLM lỗi thì lấy từ ngân hàng câu hỏi.
   - Ghi `chat_logs`.

### Luồng so sánh văn hoá ([comparison_service.py](../src/backend/app/services/comparison_service.py))

1. Tìm bản đã lưu theo (A, B, chủ đề, ngôn ngữ), cả hai chiều. Bản `published` trả ngay, không gọi LLM; bản nháp cũng được dùng lại.
2. Chưa có: truy xuất bằng chứng riêng cho từng nước, LLM điền bảng theo nhãn `[c#]`.
3. Kiểm từng ô: ô của nước A chỉ nhận nguồn về A; điểm giống cần nguồn của cả hai nước. Không đạt → `null` ("Chưa đủ nguồn để kết luận").
4. Lưu `comparisons` ở trạng thái `draft`, `origin = ai_generated` để biên tập viên duyệt. Không có bằng chứng nào → không gọi LLM, không lưu.

### Luồng dữ liệu ([worker/cli.py](../src/backend/worker/cli.py))

`run`/`run-all` (thu thập) → `aggregate` → `load` (PostgreSQL + file media lên MinIO) → `seed-media` (ảnh giao diện) → `index` (đoạn văn → `entry_chunks`, vector → Qdrant).

## 3. Công nghệ

| Phần | Công nghệ |
|---|---|
| Frontend | Angular 22 (zoneless, standalone, signals), Vitest, d3-geo + world-atlas, nginx |
| Backend | Python 3.13, FastAPI, SQLAlchemy async + asyncpg (SQL tường minh), pydantic-settings, httpx, lỗi RFC 7807 |
| Worker | requests (HTTP "lịch sự": robots.txt, giãn cách, retry), BeautifulSoup, Selenium (trang JS), openpyxl, psycopg 3, minio |
| LLM | OpenAI `gpt-6-luna` (chính) + `gpt-4o` (dự phòng). Chỉ hai model này (`ALLOWED_LLM_MODELS`) |
| AI local | Python 3.12, onnxruntime, không có torch lúc chạy. STT Gipformer (sherpa-onnx), TTS VieNeu-TTS v3 Turbo, embedding + rerank AITeamVN. Xem [11-vietnamese-chat-stack.md](11-vietnamese-chat-stack.md) |
| Lưu trữ | PostgreSQL 16 (văn bản, metadata, FTS `ca_simple` không dấu); Qdrant 1.20 (vector, gọi qua REST); MinIO (file; bucket `culture-media` chỉ đọc từng object, `culture-raw` riêng tư) |
| Hạ tầng | Docker Compose, image multi-stage non-root read-only, quét Trivy, GitHub Actions |

## 4. Quy ước code

**Code sạch.** Mọi module, class và hàm public có docstring hoặc JSDoc nói rõ chức năng. Mọi tham số và giá trị trả về có type hint.
- Python: `ruff check` với luật `D1` và `ANN`, cấu hình ở `pyproject.toml`.
- Test được miễn luật này. Tên test và docstring module mô tả AC.
- Frontend: mỗi file có chú thích đầu file; export và phương thức public có `/** … */`.

**Test.** Mỗi thay đổi tính năng phải cập nhật test và chạy `scripts/test.sh` (ruff + pytest + vitest + kiểm tra file này).
- Test bám mã `ACxx.y`.
- `tests/test_traceability.py` fail nếu AC hoặc endpoint chưa có test.
- Bộ test không gọi mạng ngoài; mọi dịch vụ ngoài đi qua `tests/fakes.py`.

**Dependency injection.** LLM, embedder, AI local và Qdrant được lấy qua FastAPI dependency (`get_llm`, `get_embedder`, `get_local_ai`, `get_vector_store`). Test thay chúng bằng bản giả.

**Bảo mật và quyền riêng tư.**
- Âm thanh của người dùng không lưu, không gửi ra ngoài.
- Khoá và token che bằng `***` trong log và dữ liệu thô.
- Không mở MinIO ra ngoài `127.0.0.1`.
- Đăng nhập: JWT HS256 (`JWT_SECRET` ≥ 32 byte, thiếu thì `/api/auth/login` trả 503), mật khẩu Argon2. Mỗi request đọc lại người dùng từ DB nên khoá tài khoản / đổi vai trò có hiệu lực ngay. Phân quyền bằng `require_role("editor" | "admin")` ([security.py](../src/backend/app/core/security.py)).

Quy tắc đầy đủ: [CLAUDE.md](../CLAUDE.md).

## 5. Chạy và kiểm thử nhanh

| Việc | Lệnh |
|---|---|
| Chạy cả app (Docker) | `docker compose up -d --build`. Web chạy ở `:$WEB_PORT`, API docs ở `/api/docs` |
| Chạy dev từng phần | `scripts/dev.sh db\|api\|ai\|web` hoặc VS Code Tasks. Xem [Guide.md](../Guide.md) |
| Toàn bộ test | `scripts/test.sh` (hoặc `scripts/test.sh backend\|frontend\|ai-local`) |
| Hạ tầng test | `docker compose -f compose.test.yaml up -d --wait` |
| Thu thập và nạp dữ liệu | `docker compose run --rm worker python -m worker.cli run-all && … load && … index` |
| Quét lỗ hổng image | `scripts/scan-images.sh` |
| Cập nhật file này | `python3 scripts/project_overview.py` |

## 6. Thay đổi gần đây

Ghi ngắn, mới nhất ở trên.

- **2026-11-09** — So sánh văn hoá `POST /api/ai/compare` (AC11): cache bản đã duyệt, sinh nháp AI có nguồn theo từng nước, ô thiếu nguồn là `null`. Prompt `prompts/compare_vi.txt`, schema `app/schemas/compare.py`.
- **2026-11-09** — Auth JWT + RBAC (AC15): `POST /api/auth/login`, `GET /api/auth/me`, `GET/PATCH /api/admin/users` (chỉ admin; admin không tự hạ quyền / tự khoá). Báo cáo sai ghi người gửi khi đã đăng nhập. Biến mới `JWT_TTL_MINUTES`.
- **2026-11-09** — Content API (AC01–AC05, AC14): quốc gia + độ phủ, hồ sơ, bài viết, claim + bằng chứng, nguồn, di sản, tìm kiếm không dấu, chủ đề (thẻ `theme`), lễ hội theo tháng (thẻ `month`), báo cáo sai. SQL nằm ở `app/repositories/*`, tìm kiếm ở `app/services/content_service.py`.
- **2026-11-06** — Câu hỏi gợi ý của AI Guide theo quốc gia và chủ đề người dùng quan tâm (AC10.3, AC10.4):
  - Thêm `GET /api/ai/suggestions` và ngân hàng câu hỏi `prompts/suggestions_vi.json`.
  - Trang quốc gia truyền `?category=` sang AI Guide.
- **2026-11-06** — Chuẩn hoá code: bắt buộc docstring và type hint (ruff `D1`, `ANN`); thêm JSDoc cho frontend; thêm file tổng quan này.
- **2026-11-06** — Lưu trữ: file media chuyển sang MinIO (DB giữ metadata + URL), embedding chuyển sang Qdrant (migration 003, 004).
  - Ảnh nền AI Guide đổi theo quốc gia (AC01.4).
- **2026-11** — Docker Compose production-hardened; dịch vụ AI local (STT/TTS/embedding/rerank); AI Guide RAG với OpenAI.

## 7. Bản đồ file

Mô tả lấy từ docstring hoặc chú thích đầu mỗi file. Muốn sửa mô tả thì sửa trong chính file đó (hoặc `FILE_NOTES` của script), rồi chạy lại script.

<!-- FILE-MAP:BEGIN (tự sinh bởi scripts/project_overview.py — không sửa tay) -->

#### Gốc repo
_Gốc repo: cấu hình chạy toàn bộ app, quy tắc làm việc, hướng dẫn._

| File | Chức năng |
|---|---|
| [.env.example](../.env.example) | Mẫu biến môi trường (OpenAI, DB, S3/MinIO, Qdrant, AI local, cổng). Bản thật `.env` không commit. |
| [.gitignore](../.gitignore) | File / thư mục không đưa vào git. |
| [CLAUDE.md](../CLAUDE.md) | Quy tắc làm việc cho AI / người đóng góp: test bắt buộc, model được phép, Docker, lưu trữ, code sạch. |
| [Guide.md](../Guide.md) | Hướng dẫn chạy toàn bộ app (Cách A: conda/venv, Cách B: Docker Compose). |
| [README.md](../README.md) | Giới thiệu dự án. |
| [compose.test.yaml](../compose.test.yaml) | Hạ tầng cho bộ test: PostgreSQL 55432, MinIO 59000, Qdrant 56333 (dữ liệu trong RAM). |
| [compose.yaml](../compose.yaml) | Docker Compose chạy toàn bộ app: db, object-storage, qdrant, ai-local, api, worker, web. |
| [docker-production-skill.md](../docker-production-skill.md) | Chuẩn build Docker production (multi-stage, non-root, quét CVE…) mà các Dockerfile tuân theo. |

#### `.githooks/`

| File | Chức năng |
|---|---|
| [pre-commit](../.githooks/pre-commit) | Chặn commit nếu test của phần đã sửa fail (bật: git config core.hooksPath .githooks). |

#### `.github/workflows/`

| File | Chức năng |
|---|---|
| [tests.yml](../.github/workflows/tests.yml) | CI: ruff + pytest backend, ai-local; build + quét CVE image; test + build frontend. |

#### `.vscode/`

| File | Chức năng |
|---|---|
| [tasks.json](../.vscode/tasks.json) | VS Code Tasks chạy từng thành phần ở chế độ dev (scripts/dev.sh). |

#### `docs/`
_Tài liệu sản phẩm: phạm vi, tính năng, tiêu chí chấp nhận (AC), mô hình dữ liệu, lộ trình._

| File | Chức năng |
|---|---|
| [01-scope.md](../docs/01-scope.md) | Phạm vi MVP. |
| [02-features.md](../docs/02-features.md) | Danh sách tính năng F1–F10. |
| [03-use-cases.md](../docs/03-use-cases.md) | Use case. |
| [04-information-architecture.md](../docs/04-information-architecture.md) | Kiến trúc thông tin / sơ đồ trang. |
| [05-data-model.md](../docs/05-data-model.md) | Mô hình dữ liệu (giải thích). |
| [06-acceptance-criteria.md](../docs/06-acceptance-criteria.md) | Tiêu chí chấp nhận ACxx.y — test bám theo file này. |
| [08-invest-requirements.md](../docs/08-invest-requirements.md) | User story theo INVEST. |
| [09-data-ingestion.md](../docs/09-data-ingestion.md) | Thiết kế thu thập dữ liệu, nguồn, giấy phép. |
| [10-roadmap.md](../docs/10-roadmap.md) | Lộ trình nâng cấp. |
| [11-vietnamese-chat-stack.md](../docs/11-vietnamese-chat-stack.md) | Lựa chọn model AI (LLM OpenAI + AI local) và số đo. |
| [DATABASE.md](../docs/DATABASE.md) | Hướng dẫn DB: bảng, view, quy tắc. |
| [security-exceptions.md](../docs/security-exceptions.md) | Ngoại lệ bảo mật đã ghi nhận (EX-001: MinIO). |

#### `docs/api/`

| File | Chức năng |
|---|---|
| [openapi.yaml](../docs/api/openapi.yaml) | Hợp đồng API (OpenAPI 3) — nguồn sự thật cho backend và frontend. |

#### `docs/mindmap/`

| File | Chức năng |
|---|---|
| [mindmap-data.en.json](../docs/mindmap/mindmap-data.en.json) | Dữ liệu sơ đồ tư duy (tiếng Anh). |
| [mindmap-data.json](../docs/mindmap/mindmap-data.json) | Dữ liệu sơ đồ tư duy (tiếng Việt). |
| [mindmap.html](../docs/mindmap/mindmap.html) | Sơ đồ tư duy tương tác của dự án. |

#### `docs/requirements/`

| File | Chức năng |
|---|---|
| [business-rules.md](../docs/requirements/business-rules.md) | Quy tắc nghiệp vụ BR01–BR09. |
| [non-functional-requirements.md](../docs/requirements/non-functional-requirements.md) | Yêu cầu phi chức năng (hiệu năng, bảo mật…). |

#### `scripts/`
_Script vận hành: chạy dev, chạy test, quét lỗ hổng image, nạp model AI._

| File | Chức năng |
|---|---|
| [dev.sh](../scripts/dev.sh) | Chạy một thành phần của app ở chế độ dev (Cách A trong Guide.md). Dùng cho VS Code Tasks hoặc terminal thường. scripts/dev.sh db PostgreSQL (Docker) + theo dõi log |
| [project_overview.py](../scripts/project_overview.py) | Sinh mục "Bản đồ file" của docs/PROJECT_OVERVIEW.md từ chính mã nguồn. |
| [scan-images.sh](../scripts/scan-images.sh) | Quét lỗ hổng (CVE) các image của app bằng Trivy (docker-production-skill.md mục 20). |
| [seed-ai-models.sh](../scripts/seed-ai-models.sh) | Nạp volume Docker `ai-models` từ cache Hugging Face có sẵn trên máy chủ — KHÔNG cần Internet. |
| [test.sh](../scripts/test.sh) | Chạy toàn bộ bộ test CultureAtlas AI. Bắt buộc chạy trước khi commit / merge tính năng. scripts/test.sh backend + AI local + frontend (tự bật PostgreSQL test nếu cần) |

#### `src/ai-local/`
_Dịch vụ AI local (Python 3.12, ONNX, không torch lúc chạy): STT, TTS, embedding, rerank._

| File | Chức năng |
|---|---|
| [.dockerignore](../src/ai-local/.dockerignore) | File không gửi vào ngữ cảnh build Docker. |
| [Dockerfile](../src/ai-local/Dockerfile) | Image AI local: target setup (có torch, xuất ONNX) và runtime (không torch). |
| [README.md](../src/ai-local/README.md) | Hướng dẫn dịch vụ AI local: model, giấy phép, cách chạy. |
| [pyproject.toml](../src/ai-local/pyproject.toml) | Thư viện của dịch vụ AI local + cấu hình pytest / ruff. |
| [requirements-export.lock](../src/ai-local/requirements-export.lock) | Thư viện khoá cho bước xuất ONNX. |
| [requirements.lock](../src/ai-local/requirements.lock) | Thư viện khoá cho runtime. |

#### `src/ai-local/ai_local/`

| File | Chức năng |
|---|---|
| [__init__.py](../src/ai-local/ai_local/__init__.py) | CultureAtlas AI — dịch vụ AI local (CPU): STT, TTS, embedding, rerank tiếng Việt. |
| [audio.py](../src/ai-local/ai_local/audio.py) | Giải mã / mã hoá âm thanh bằng PyAV (thư viện ffmpeg đóng gói sẵn — không cần cài ffmpeg hệ thống). Âm thanh người dùng chỉ nằm trong bộ nhớ: không ghi ra đĩa (AC21.3). |
| [config.py](../src/ai-local/ai_local/config.py) | Cấu hình đọc từ biến môi trường (tiền tố AI_LOCAL_). |
| [download.py](../src/ai-local/ai_local/download.py) | Tải trước toàn bộ model (chạy một lần): python -m ai_local.download [stt tts embed rerank] |
| [embed.py](../src/ai-local/ai_local/embed.py) | Embedding tiếng Việt: Vietnamese_Embedding_v2 (XLM-R/BGE-M3, ONNX) — lấy CLS rồi chuẩn hoá L2, 1024 chiều. |
| [engines.py](../src/ai-local/ai_local/engines.py) | Nạp model lười (lần gọi đầu) và dùng chung cho mọi request. Test thay bằng engine giả qua `app.state.engines`. |
| [hfcache.py](../src/ai-local/ai_local/hfcache.py) | onnxruntime ≥ 1.2x từ chối file trọng số ngoài (model.onnx_data…) nếu đường dẫn thật nằm ngoài thư mục model. |
| [main.py](../src/ai-local/ai_local/main.py) | HTTP API của dịch vụ AI local. Chỉ backend gọi vào (mạng nội bộ), không mở ra Internet. |
| [rerank.py](../src/ai-local/ai_local/rerank.py) | Rerank tiếng Việt: Vietnamese_Reranker (cross-encoder gốc bge-reranker-v2-m3) chạy bằng ONNX Runtime — không cần torch. |
| [stt.py](../src/ai-local/ai_local/stt.py) | Nhận dạng giọng nói tiếng Việt: silero VAD cắt đoạn → Gipformer 1.5 (Zipformer RNN-T, ONNX) qua sherpa-onnx. |
| [text.py](../src/ai-local/ai_local/text.py) | Xử lý văn bản trước khi đọc (TTS) và sau khi nhận dạng (STT). |
| [tts.py](../src/ai-local/ai_local/tts.py) | Đọc văn bản tiếng Việt: VieNeu-TTS v3 Turbo (ONNX/CPU, 48 kHz, giọng Bắc & Nam). Có sẵn chuẩn hoá số, ngày tháng (sea-g2p). |

#### `src/ai-local/tests/`

| File | Chức năng |
|---|---|
| [__init__.py](../src/ai-local/tests/__init__.py) | Đánh dấu package Python. |
| [conftest.py](../src/ai-local/tests/conftest.py) | Engine giả cho test nhanh (không nạp model). Test model thật: pytest -m models. |
| [test_api.py](../src/ai-local/tests/test_api.py) | API dịch vụ AI local với engine giả — chạy nhanh, không cần model. |
| [test_models.py](../src/ai-local/tests/test_models.py) | Kiểm tra model thật (chậm, cần tải trước: python -m ai_local.download). Chạy: pytest -m models |
| [test_text.py](../src/ai-local/tests/test_text.py) | Làm sạch văn bản trước khi đọc TTS (bỏ markdown, nhãn trích dẫn, ký tự đặc biệt). |

#### `src/backend/`
_API FastAPI (app/) + worker thu thập dữ liệu (worker/) + bộ test chấp nhận (tests/). Python 3.13._

| File | Chức năng |
|---|---|
| [.dockerignore](../src/backend/.dockerignore) | File không gửi vào ngữ cảnh build Docker. |
| [Dockerfile](../src/backend/Dockerfile) | Image API + worker (multi-stage, non-root, read-only). |
| [pyproject.toml](../src/backend/pyproject.toml) | Thư viện Python của backend + cấu hình pytest / ruff (bắt buộc docstring, type hint). |
| [requirements.lock](../src/backend/requirements.lock) | Phiên bản thư viện khoá cho image Docker. |

#### `src/backend/app/`
_API phục vụ người dùng._

| File | Chức năng |
|---|---|
| [__init__.py](../src/backend/app/__init__.py) | CultureAtlas API (FastAPI). Điểm vào: app/main.py. Tổng quan kiến trúc: docs/PROJECT_OVERVIEW.md. |
| [main.py](../src/backend/app/main.py) | Điểm vào FastAPI: gắn router Content / AI / Auth / Admin, xử lý lỗi RFC 7807. |

#### `src/backend/app/ai/`
_AI Guide: phân tuyến câu hỏi, truy xuất lai, gọi LLM, kiểm tra trích dẫn, gợi ý câu hỏi._

| File | Chức năng |
|---|---|
| [__init__.py](../src/backend/app/ai/__init__.py) | AI Guide: router câu hỏi, truy xuất lai (Qdrant + FTS), LLM OpenAI, lọc trích dẫn, gợi ý câu hỏi. |
| [agent.py](../src/backend/app/ai/agent.py) | AI Cultural Guide — điều phối một lượt hỏi đáp: phiên + lịch sử → router (smalltalk \| structured \| rag) → truy xuất bằng chứng → LLM stream (lọc trích dẫn) → gợi ý →… |
| [citation_verifier.py](../src/backend/app/ai/citation_verifier.py) | Kiểm tra trích dẫn: mỗi [c#] phải trỏ tới bằng chứng đã truy xuất cho lượt hỏi này (AC07.2). |
| [llm_adapter.py](../src/backend/app/ai/llm_adapter.py) | LLM adapter: giao diện chung + bản cài đặt OpenAI (GPT-6 Luna chính, GPT-4o dự phòng). Xem docs/11-vietnamese-chat-stack.md. |
| [local_ai.py](../src/backend/app/ai/local_ai.py) | Client gọi dịch vụ AI local (src/ai-local): nhận dạng giọng nói, đọc văn bản, embedding, rerank. |
| [query_rewriter.py](../src/backend/app/ai/query_rewriter.py) | Viết lại câu hỏi hội thoại thành truy vấn tìm kiếm độc lập. |
| [reranker.py](../src/backend/app/ai/reranker.py) | Rerank đoạn bằng cross-encoder. KHUNG — chưa dùng: rerank thật chạy ở dịch vụ AI local (src/ai-local/ai_local/rerank.py), gọi qua app/ai/local_ai.py trong… |
| [retrieval.py](../src/backend/app/ai/retrieval.py) | Truy xuất bằng chứng cho AI Guide: lọc quốc gia → tìm vector (Qdrant) + từ khoá (FTS không dấu ở PostgreSQL) → gộp RRF → rerank (dịch vụ AI local) → giữ đoạn vượt… |
| [router.py](../src/backend/app/ai/router.py) | Phân loại câu hỏi: smalltalk (chào hỏi) \| structured (dữ kiện trả từ DB, không gọi LLM) \| rag (văn hoá, cần nguồn). |
| [suggestions.py](../src/backend/app/ai/suggestions.py) | Câu hỏi gợi ý của AI Guide theo quốc gia và mối quan tâm của người dùng (AC10.3, AC10.4). |
| [text.py](../src/backend/app/ai/text.py) | Tiện ích chuẩn hoá tiếng Việt cho router / truy xuất. |
| [tools.py](../src/backend/app/ai/tools.py) | Công cụ cho agent (search_culture, get_country_profile, compare_cultures, …). KHUNG — chưa triển khai (P2). |
| [vector_store.py](../src/backend/app/ai/vector_store.py) | Tìm kiếm vector cho AI Guide trên Qdrant (embedding lưu ở vector DB, không ở PostgreSQL). |

#### `src/backend/app/ai/prompts/`
_Prompt và dữ liệu tĩnh của AI Guide._

| File | Chức năng |
|---|---|
| [compare_vi.txt](../src/backend/app/ai/prompts/compare_vi.txt) | System prompt so sánh văn hoá: mỗi ô chỉ dựa trên bằng chứng của đúng nước đó, thiếu thì để trống. |
| [smalltalk_vi.txt](../src/backend/app/ai/prompts/smalltalk_vi.txt) | System prompt cho chào hỏi / hỏi về trợ lý (không đưa thông tin văn hoá). |
| [suggestions_vi.json](../src/backend/app/ai/prompts/suggestions_vi.json) | Ngân hàng câu hỏi gợi ý theo quốc gia × chủ đề (app/ai/suggestions.py). |
| [system_vi.txt](../src/backend/app/ai/prompts/system_vi.txt) | System prompt RAG: chỉ trả lời theo bằng chứng, trích dẫn [c#]. |

#### `src/backend/app/api/`

| File | Chức năng |
|---|---|
| [__init__.py](../src/backend/app/api/__init__.py) | Các router HTTP (FastAPI) — mỗi file một nhóm endpoint của docs/api/openapi.yaml. |
| [admin.py](../src/backend/app/api/admin.py) | Admin API (JWT, vai trò editor/admin). Đã có: users (admin). Còn lại (P3): review-queue, entries, claims, sources, feedback, coverage, ai/drafts, ingestion, benchmark. |
| [ai.py](../src/backend/app/api/ai.py) | AI API. - POST /chat (SSE mặc định; Accept: application/json → một ChatAnswer), POST /chat/messages/{id}/rating - GET /suggestions — câu hỏi gợi ý theo quốc gia + chủ… |
| [auth.py](../src/backend/app/api/auth.py) | Auth API: POST /login (email + mật khẩu → JWT), GET /me (người dùng của token). Xem app/core/security.py. |
| [content.py](../src/backend/app/api/content.py) | Content API (không gọi LLM, chỉ nội dung `published`): countries, entries, heritage, search, sources, themes, festivals, feedback. Quiz (P3) chưa có. |

#### `src/backend/app/core/`

| File | Chức năng |
|---|---|
| [__init__.py](../src/backend/app/core/__init__.py) | Hạ tầng dùng chung: cấu hình (.env), kết nối DB, lỗi RFC 7807, giới hạn lượt hỏi. |
| [config.py](../src/backend/app/core/config.py) | Cấu hình từ biến môi trường / file .env ở gốc repo (pydantic-settings). Biến môi trường luôn ưu tiên hơn .env. |
| [db.py](../src/backend/app/core/db.py) | Kết nối PostgreSQL async (SQLAlchemy + asyncpg). Dùng câu SQL tường minh qua text(). |
| [errors.py](../src/backend/app/core/errors.py) | Lỗi theo RFC 7807 (application/problem+json). Lỗi validate → 400; vi phạm nghiệp vụ → 422. |
| [rate_limit.py](../src/backend/app/core/rate_limit.py) | Giới hạn lượt hỏi AI cho khách theo anon_key (BR12, AC06.3) — đếm chat_logs trong ngày, không cần Redis. |
| [security.py](../src/backend/app/core/security.py) | JWT (Bearer, HS256 qua PyJWT), băm mật khẩu Argon2, dependency lấy người dùng và require_role (AC15). |

#### `src/backend/app/domain/`

| File | Chức năng |
|---|---|
| [__init__.py](../src/backend/app/domain/__init__.py) | Mô hình nghiệp vụ và quy tắc (BR01–BR09). KHUNG — chưa triển khai, API hiện dùng SQL trực tiếp. |
| [enums.py](../src/backend/app/domain/enums.py) | ContentStatus, CategoryCode, ClaimScope, Confidence, UserRole… KHUNG — chưa triển khai. |
| [models.py](../src/backend/app/domain/models.py) | ORM: Country, CultureEntry, Claim, Source, … KHUNG — chưa triển khai (API dùng SQL trực tiếp). |
| [policies.py](../src/backend/app/domain/policies.py) | Quy tắc nghiệp vụ: claim phải có nguồn (BR01), vòng đời trạng thái (BR04), nội dung AI bắt đầu draft (BR03). |

#### `src/backend/app/repositories/`

| File | Chức năng |
|---|---|
| [__init__.py](../src/backend/app/repositories/__init__.py) | Lớp truy cập dữ liệu: câu SQL tường minh, trả dict đúng hình dạng DTO của API. Truy vấn RAG nằm ở app/ai/*. |
| [chunk_repo.py](../src/backend/app/repositories/chunk_repo.py) | Truy vấn entry_chunks. KHUNG — chưa dùng: tìm kiếm lai (Qdrant + FTS, gộp RRF) nằm ở app/ai/retrieval.py. |
| [country_repo.py](../src/backend/app/repositories/country_repo.py) | Truy vấn countries + v_coverage: danh sách quốc gia có độ phủ, hồ sơ quốc gia (danh mục, điều cần biết). |
| [entry_repo.py](../src/backend/app/repositories/entry_repo.py) | culture_entries, claims, claim_sources, sources: bài viết đã xuất bản, claim kèm bằng chứng, chi tiết nguồn. |
| [feedback_repo.py](../src/backend/app/repositories/feedback_repo.py) | feedback: báo cáo sai / góp ý của người dùng (AC14). AI Guide tự ghi loại `unanswered` trong app/ai/agent.py. |
| [heritage_repo.py](../src/backend/app/repositories/heritage_repo.py) | heritage_items: di sản UNESCO theo quốc gia / loại, kèm ghi công theo giấy phép của nguồn (AC04.1, AC04.2). |
| [user_repo.py](../src/backend/app/repositories/user_repo.py) | users: danh sách người dùng và đổi vai trò / khoá tài khoản (chỉ admin gọi, AC15.1). |

#### `src/backend/app/schemas/`

| File | Chức năng |
|---|---|
| [__init__.py](../src/backend/app/schemas/__init__.py) | Pydantic DTO của API — khớp components.schemas trong docs/api/openapi.yaml. |
| [admin.py](../src/backend/app/schemas/admin.py) | EntryUpsert, ClaimUpsert, SourceUpsert, ReviewDecision, IngestionRun. KHUNG — chưa triển khai (P2). |
| [ai.py](../src/backend/app/schemas/ai.py) | Schema của AI API (xem docs/api/openapi.yaml: ChatRequest, ChatAnswer, Citation). |
| [auth.py](../src/backend/app/schemas/auth.py) | Schema của Auth API và quản lý người dùng (docs/api/openapi.yaml: TokenResponse, User, UserRole). |
| [compare.py](../src/backend/app/schemas/compare.py) | Schema của POST /api/ai/compare (docs/api/openapi.yaml: CompareRequest, SourcedText, Comparison). |
| [content.py](../src/backend/app/schemas/content.py) | Pydantic DTO cho Content API — khớp components.schemas trong docs/api/openapi.yaml. |

#### `src/backend/app/services/`

| File | Chức năng |
|---|---|
| [__init__.py](../src/backend/app/services/__init__.py) | Nghiệp vụ ghép nhiều bảng / nhiều bước: tìm kiếm (content), so sánh văn hoá. Quiz / Review: KHUNG (P3). |
| [comparison_service.py](../src/backend/app/services/comparison_service.py) | So sánh văn hoá 2 quốc gia × 1 chủ đề (F3, AC11): trả bản đã lưu nếu có, nếu không thì AI sinh bản nháp (BR07). |
| [content_service.py](../src/backend/app/services/content_service.py) | Tìm kiếm nội dung (AC05): quốc gia, bài viết đã xuất bản, di sản UNESCO, chủ đề — gõ không dấu vẫn tìm được. |
| [quiz_service.py](../src/backend/app/services/quiz_service.py) | Phục vụ quiz đã duyệt, chấm điểm, giải thích kèm nguồn. KHUNG — chưa triển khai (P2). |
| [review_service.py](../src/backend/app/services/review_service.py) | Duyệt / từ chối, tạo revision, kích hoạt re-index chunk. KHUNG — chưa triển khai (P2). |

#### `src/backend/eval/`

| File | Chức năng |
|---|---|
| [run_benchmark.py](../src/backend/eval/run_benchmark.py) | Chạy 100–150 câu hỏi: citation correctness, recall@8, tỷ lệ từ chối đúng, p95 TTFT — chạy trong CI. |

#### `src/backend/eval/benchmark/`

| File | Chức năng |
|---|---|
| [questions.jsonl](../src/backend/eval/benchmark/questions.jsonl) | Bộ câu hỏi benchmark chất lượng AI Guide. |

#### `src/backend/tests/`
_Bộ test (pytest). Test bám mã AC qua @ac / @route; dịch vụ ngoài được thay bằng bản giả._

| File | Chức năng |
|---|---|
| [README.md](../src/backend/tests/README.md) | Cách viết / chạy test, cơ chế PENDING và truy vết AC. |
| [__init__.py](../src/backend/tests/__init__.py) | Đánh dấu package Python. |
| [conftest.py](../src/backend/tests/conftest.py) | Hạ tầng chung cho bộ test CultureAtlas AI. |
| [fakes.py](../src/backend/tests/fakes.py) | LLM và embedding giả cho bộ test: không gọi mạng, kết quả xác định. |
| [test_health.py](../src/backend/tests/test_health.py) | Smoke test: /api/health trả ok (không cần DB). |
| [test_live.py](../src/backend/tests/test_live.py) | Kiểm tra dịch vụ thật — KHÔNG chạy mặc định (tốn tiền / cần dịch vụ chạy). |
| [test_llm_adapter.py](../src/backend/tests/test_llm_adapter.py) | OpenAIAdapter với client OpenAI giả (không gọi mạng): tham số theo model, dự phòng GPT-4o, chặn model lạ. |
| [test_traceability.py](../src/backend/tests/test_traceability.py) | Giữ bộ test đồng bộ với tài liệu. |
| [test_worker_parsers.py](../src/backend/tests/test_worker_parsers.py) | Kiểm thử parser và lớp lõi của worker — không gọi mạng. |

#### `src/backend/tests/acceptance/`
_Test chấp nhận theo nhóm tính năng F1–F10._

| File | Chức năng |
|---|---|
| [__init__.py](../src/backend/tests/acceptance/__init__.py) | Đánh dấu package Python. |
| [test_db_rules.py](../src/backend/tests/acceptance/test_db_rules.py) | Quy tắc nghiệp vụ được DB đảm bảo (src/database/culture_atlas.sql) — chạy được ngay, không cần API. |
| [test_f10_storage.py](../src/backend/tests/acceptance/test_f10_storage.py) | Lưu trữ: file phi cấu trúc ở object storage (MinIO/S3), embedding ở Qdrant, PostgreSQL giữ metadata + URL + văn bản. |
| [test_f1_explorer.py](../src/backend/tests/acceptance/test_f1_explorer.py) | F1 — Cultural Explorer: Content API (US01–US05, US14). Không gọi LLM. |
| [test_f2_ai_guide.py](../src/backend/tests/acceptance/test_f2_ai_guide.py) | F2 — AI Cultural Guide (US06–US10). LLM luôn là FakeLLM (tests/fakes.py), không gọi OpenAI. |
| [test_f2_suggestions.py](../src/backend/tests/acceptance/test_f2_suggestions.py) | F2 — Câu hỏi gợi ý của AI Guide theo quốc gia và mối quan tâm (AC10.3, AC10.4). LLM là FakeLLM. |
| [test_f3_compare.py](../src/backend/tests/acceptance/test_f3_compare.py) | F3 — Culture Comparison (US11). |
| [test_f5_quiz.py](../src/backend/tests/acceptance/test_f5_quiz.py) | F5 — Culture Quiz (US12–US13). |
| [test_f7_admin.py](../src/backend/tests/acceptance/test_f7_admin.py) | F7 — Xác thực & trang quản trị (US15–US19, US20 qua API). |
| [test_f8_ingestion.py](../src/backend/tests/acceptance/test_f8_ingestion.py) | F8 — Ingestion worker nạp dữ liệu vào PostgreSQL (US20). |
| [test_f9_voice.py](../src/backend/tests/acceptance/test_f9_voice.py) | F9 — Hỏi đáp bằng giọng nói (US21). Âm thanh xử lý ở dịch vụ AI local; test dùng FakeLocalAI. |

#### `src/backend/tests/fixtures/`

| File | Chức năng |
|---|---|
| [seed.sql](../src/backend/tests/fixtures/seed.sql) | Dữ liệu mẫu nạp lại trước mỗi test cần DB. |

#### `src/backend/worker/`
_Worker: thu thập nguồn mở → chuẩn hoá → gộp → nạp PostgreSQL / MinIO / Qdrant._

| File | Chức năng |
|---|---|
| [__init__.py](../src/backend/worker/__init__.py) | Worker thu thập dữ liệu: nguồn → raw → normalized → aggregated → PostgreSQL + MinIO + Qdrant. CLI: python -m worker.cli (xem worker/cli.py). |
| [cli.py](../src/backend/worker/cli.py) | CLI của worker. |
| [config.py](../src/backend/worker/config.py) | Cấu hình worker, đọc từ biến môi trường (xem .env.example ở gốc repo). |
| [scheduler.py](../src/backend/worker/scheduler.py) | Lịch đồng bộ định kỳ (APScheduler). Chạy: python -m worker.scheduler Tần suất theo mức thay đổi của nguồn: UNESCO cập nhật sau mỗi kỳ họp hằng năm; |

#### `src/backend/worker/core/`

| File | Chức năng |
|---|---|
| [__init__.py](../src/backend/worker/core/__init__.py) | Hạ tầng của worker: HTTP lịch sự, lưu file run, object storage (MinIO), Qdrant, model dữ liệu. |
| [browser.py](../src/backend/worker/core/browser.py) | Selenium (Chrome headless) cho các trang render bằng JavaScript. Không vượt CAPTCHA / đăng nhập / anti-bot. |
| [http.py](../src/backend/worker/core/http.py) | HTTP client "lịch sự": robots.txt, giới hạn tốc độ theo domain, retry có backoff, User-Agent định danh. |
| [models.py](../src/backend/worker/core/models.py) | Bản ghi chuẩn hoá — khớp các bảng trong src/database/culture_atlas.sql. Mọi bản ghi mang provenance. |
| [objectstore.py](../src/backend/worker/core/objectstore.py) | Object storage (S3 / MinIO) cho dữ liệu phi cấu trúc: ảnh, video, âm thanh, tài liệu, payload thô. |
| [storage.py](../src/backend/worker/core/storage.py) | Lưu dữ liệu thô (để chuẩn hoá lại mà không gọi lại nguồn), bản ghi chuẩn hoá (JSONL) và nhật ký mỗi lần chạy. |
| [vectors.py](../src/backend/worker/core/vectors.py) | Ghi embedding của chỉ mục RAG vào Qdrant (vector DB). |

#### `src/backend/worker/pipeline/`

| File | Chức năng |
|---|---|
| [__init__.py](../src/backend/worker/pipeline/__init__.py) | Các bước xử lý sau khi thu thập: gộp (aggregate), phân loại, nạp DB (loader), chỉ mục RAG (indexer), ảnh giao diện (media_seed). |
| [aggregate.py](../src/backend/worker/pipeline/aggregate.py) | Gộp bản ghi từ mọi nguồn → data/aggregated/*.json + báo cáo độ phủ (report.md). |
| [chunker.py](../src/backend/worker/pipeline/chunker.py) | Cắt đoạn theo ranh giới claim. KHUNG — chưa dùng: cắt đoạn hiện nằm ở worker/pipeline/indexer.py (split_text). |
| [classify.py](../src/backend/worker/pipeline/classify.py) | Gán danh mục văn hoá (12 mã cố định) cho đoạn văn bằng từ khoá — gợi ý cho biên tập viên, không phải kết luận. |
| [embedder.py](../src/backend/worker/pipeline/embedder.py) | Embedding. KHUNG — chưa dùng: indexer gọi dịch vụ AI local (indexer.http_embedder), vector lưu ở Qdrant (worker/core/vectors.py). |
| [indexer.py](../src/backend/worker/pipeline/indexer.py) | Lập chỉ mục RAG: chia đoạn + embedding → entry_chunks. |
| [loader.py](../src/backend/worker/pipeline/loader.py) | Nạp dữ liệu đã tổng hợp vào PostgreSQL (upsert, chạy lại không tạo trùng). Bảng: xem src/database/culture_atlas.sql. |
| [media_seed.py](../src/backend/worker/pipeline/media_seed.py) | Nạp bộ ảnh tuyển chọn của giao diện (src/media-seed) lên object storage + ghi metadata vào media_assets. |
| [normalize.py](../src/backend/worker/pipeline/normalize.py) | Khử trùng theo source_url / id nguồn, ánh xạ ISO 3166 và danh mục. KHUNG — hiện mỗi nguồn tự chuẩn hoá trong worker/sources/*.normalize(). |

#### `src/backend/worker/sources/`
_Mỗi file một nguồn dữ liệu (lớp con của Source)._

| File | Chức năng |
|---|---|
| [__init__.py](../src/backend/worker/sources/__init__.py) | Danh sách nguồn — thứ tự chạy mặc định. |
| [base.py](../src/backend/worker/sources/base.py) | Khung chung cho một nguồn dữ liệu: fetch → lưu thô → parse → ghi bản ghi chuẩn hoá → nhật ký. |
| [europeana.py](../src/backend/worker/sources/europeana.py) | Europeana Search API (`EUROPEANA_WSKEY`). |
| [official_sites.py](../src/backend/worker/sources/official_sites.py) | Trang du lịch / văn hoá chính thức render bằng JavaScript → Selenium + BeautifulSoup. |
| [rest_countries.py](../src/backend/worker/sources/rest_countries.py) | REST Countries v5 — cần token của người dùng (`REST_COUNTRIES_TOKEN`), gửi qua header `Authorization: Bearer`. |
| [scale.py](../src/backend/worker/sources/scale.py) | SCALE Cultural Data (Google Research, GitHub). |
| [smithsonian.py](../src/backend/worker/sources/smithsonian.py) | Smithsonian Open Access API (api.data.gov key: `SMITHSONIAN_API_KEY`, mặc định DEMO_KEY bị giới hạn lượt). |
| [unesco_datahub.py](../src/backend/worker/sources/unesco_datahub.py) | UNESCO DataHub (Opendatasoft API) — whc001 (World Heritage List) và ich001 (Intangible Heritage Lists), CC BY-SA 4.0. |
| [wikidata.py](../src/backend/worker/sources/wikidata.py) | Wikidata SPARQL — thông tin nền quốc gia (thủ đô, ngôn ngữ chính thức, tiền tệ, láng giềng, dân số). CC0, không cần xác thực. |
| [wikimedia_commons.py](../src/backend/worker/sources/wikimedia_commons.py) | Wikimedia Commons API — ảnh minh hoạ văn hoá theo quốc gia, kèm tác giả + giấy phép từ extmetadata. |
| [wikipedia.py](../src/backend/worker/sources/wikipedia.py) | Wikipedia (CC BY-SA 4.0) qua API chính thức. |

#### `src/database/`
_Schema PostgreSQL (nguồn sự thật: .dbml) và migration cho DB đã tạo trước._

| File | Chức năng |
|---|---|
| [culture_atlas.dbml](../src/database/culture_atlas.dbml) | Mô hình dữ liệu DBML — nguồn sự thật của schema. |
| [culture_atlas.sql](../src/database/culture_atlas.sql) | CultureAtlas AI — PostgreSQL 16 schema (MVP). Văn bản + metadata; embedding ở Qdrant, file ở object storage (MinIO). Nguồn sự thật mô hình: culture_atlas.dbml |

#### `src/database/migrations/`

| File | Chức năng |
|---|---|
| [002_entry_chunks_reference.sql](../src/database/migrations/002_entry_chunks_reference.sql) | Migration 002 — entry_chunks chứa thêm đoạn từ tài liệu tham khảo và di sản UNESCO (cho AI Guide). |
| [003_media_object_storage.sql](../src/database/migrations/003_media_object_storage.sql) | Migration 003 — media_assets chuyển sang mô hình object storage: file ở MinIO/S3, DB giữ metadata + URL. |
| [004_embeddings_to_qdrant.sql](../src/database/migrations/004_embeddings_to_qdrant.sql) | Migration 004 — embedding của chỉ mục RAG chuyển sang Qdrant (vector DB). |

#### `src/frontend/`
_Giao diện Angular 22 (zoneless, standalone components, Vitest)._

| File | Chức năng |
|---|---|
| [.dockerignore](../src/frontend/.dockerignore) | File không gửi vào ngữ cảnh build Docker. |
| [Dockerfile](../src/frontend/Dockerfile) | Image web: build Angular → nginx non-root. |
| [angular.json](../src/frontend/angular.json) | Cấu hình build / test Angular. |
| [nginx.conf](../src/frontend/nginx.conf) | nginx: phục vụ SPA, proxy /api → backend, /media → MinIO (chỉ GET/HEAD). |
| [package.json](../src/frontend/package.json) | Thư viện npm và script. |
| [proxy.conf.mjs](../src/frontend/proxy.conf.mjs) | Proxy của `ng serve` (dev): /api → API, /media → MinIO. |
| [tsconfig.app.json](../src/frontend/tsconfig.app.json) | TypeScript cho bản build. |
| [tsconfig.json](../src/frontend/tsconfig.json) | Cấu hình TypeScript chung. |
| [tsconfig.spec.json](../src/frontend/tsconfig.spec.json) | TypeScript cho test. |

#### `src/frontend/public/`

| File | Chức năng |
|---|---|
| [robots.txt](../src/frontend/public/robots.txt) | robots.txt của web. |

#### `src/frontend/src/`

| File | Chức năng |
|---|---|
| [index.html](../src/frontend/src/index.html) | Trang HTML gốc. |
| [main.ts](../src/frontend/src/main.ts) | Điểm vào trình duyệt: khởi động AppComponent với cấu hình appConfig. |
| [styles.css](../src/frontend/src/styles.css) | CSS toàn cục (biến màu, kiểu chung). |

#### `src/frontend/src/app/`

| File | Chức năng |
|---|---|
| [app.component.ts](../src/frontend/src/app/app.component.ts) | Khung ứng dụng: thanh điều hướng trên cùng + router-outlet + chân trang. |
| [app.config.ts](../src/frontend/src/app/app.config.ts) | Cấu hình ứng dụng: zoneless change detection, router (query param → input của component). |
| [app.routes.ts](../src/frontend/src/app/app.routes.ts) | Bảng định tuyến: mỗi trang tải lười (lazy) từ app/features/*. |

#### `src/frontend/src/app/core/mock/`

| File | Chức năng |
|---|---|
| [media.ts](../src/frontend/src/app/core/mock/media.ts) | Ảnh văn hoá từ Wikimedia Commons (giấy phép mở) — ghi công trong photo-credits.json (bản sao của src/media-seed/culture/credits.json). |
| [mock-data.ts](../src/frontend/src/app/core/mock/mock-data.ts) | DỮ LIỆU MẪU cho prototype giao diện — chưa qua biên tập, không dùng làm nội dung thật. |
| [photo-credits.json](../src/frontend/src/app/core/mock/photo-credits.json) | Ghi công ảnh — bản sao của src/media-seed/culture/credits.json. |
| [sources-snapshot.json](../src/frontend/src/app/core/mock/sources-snapshot.json) | Số liệu thật từ nguồn mở (worker sinh) cho giao diện. |

#### `src/frontend/src/app/core/models/`

| File | Chức năng |
|---|---|
| [culture.models.ts](../src/frontend/src/app/core/models/culture.models.ts) | Kiểu dữ liệu dùng chung, bám theo OpenAPI (docs/api/openapi.yaml). |

#### `src/frontend/src/app/core/services/`

| File | Chức năng |
|---|---|
| [chat-api.service.ts](../src/frontend/src/app/core/services/chat-api.service.ts) | Client HTTP của AI API (chat SSE, gợi ý câu hỏi, đánh giá, giọng nói). |
| [culture.service.ts](../src/frontend/src/app/core/services/culture.service.ts) | Nguồn dữ liệu của giao diện (hiện là dữ liệu mẫu + snapshot nguồn mở; sẽ thay bằng Content API ở P2). |

#### `src/frontend/src/app/features/admin/`

| File | Chức năng |
|---|---|
| [admin.page.css](../src/frontend/src/app/features/admin/admin.page.css) | CSS của trang. |
| [admin.page.html](../src/frontend/src/app/features/admin/admin.page.html) | Template của trang. |
| [admin.page.spec.ts](../src/frontend/src/app/features/admin/admin.page.spec.ts) | Test: Admin (US16–US19) |
| [admin.page.ts](../src/frontend/src/app/features/admin/admin.page.ts) | Trang quản trị nội dung (prototype): hàng đợi duyệt, nguồn dữ liệu, độ phủ. |

#### `src/frontend/src/app/features/ai-guide/`

| File | Chức năng |
|---|---|
| [ai-guide.page.css](../src/frontend/src/app/features/ai-guide/ai-guide.page.css) | CSS của trang. |
| [ai-guide.page.html](../src/frontend/src/app/features/ai-guide/ai-guide.page.html) | Template của trang. |
| [ai-guide.page.spec.ts](../src/frontend/src/app/features/ai-guide/ai-guide.page.spec.ts) | Test: AI Cultural Guide UI (US06–US10) |
| [ai-guide.page.ts](../src/frontend/src/app/features/ai-guide/ai-guide.page.ts) | Trang AI Guide: chat streaming có trích dẫn, gợi ý câu hỏi theo quốc gia + mối quan tâm, giọng nói, ảnh nền theo quốc gia. |

#### `src/frontend/src/app/features/compare/`

| File | Chức năng |
|---|---|
| [compare.page.css](../src/frontend/src/app/features/compare/compare.page.css) | CSS của trang. |
| [compare.page.html](../src/frontend/src/app/features/compare/compare.page.html) | Template của trang. |
| [compare.page.spec.ts](../src/frontend/src/app/features/compare/compare.page.spec.ts) | Test: Culture comparison (US11) |
| [compare.page.ts](../src/frontend/src/app/features/compare/compare.page.ts) | Trang so sánh văn hoá hai nước theo một chủ đề (prototype). |

#### `src/frontend/src/app/features/country/`

| File | Chức năng |
|---|---|
| [country.page.css](../src/frontend/src/app/features/country/country.page.css) | CSS của trang. |
| [country.page.html](../src/frontend/src/app/features/country/country.page.html) | Template của trang. |
| [country.page.spec.ts](../src/frontend/src/app/features/country/country.page.spec.ts) | Test: Country profile (US02, US03) |
| [country.page.ts](../src/frontend/src/app/features/country/country.page.ts) | Hồ sơ quốc gia: ảnh, mẹo lần đầu, bài viết theo danh mục, di sản UNESCO, chủ đề SCALE. |

#### `src/frontend/src/app/features/explorer/`

| File | Chức năng |
|---|---|
| [explorer.page.css](../src/frontend/src/app/features/explorer/explorer.page.css) | CSS của trang. |
| [explorer.page.html](../src/frontend/src/app/features/explorer/explorer.page.html) | Template của trang. |
| [explorer.page.spec.ts](../src/frontend/src/app/features/explorer/explorer.page.spec.ts) | Test: Explorer (US01, US05) |
| [explorer.page.ts](../src/frontend/src/app/features/explorer/explorer.page.ts) | Trang khám phá: bản đồ thế giới, tìm kiếm / lọc khu vực, thẻ quốc gia. |

#### `src/frontend/src/app/features/quiz/`

| File | Chức năng |
|---|---|
| [quiz.page.css](../src/frontend/src/app/features/quiz/quiz.page.css) | CSS của trang. |
| [quiz.page.html](../src/frontend/src/app/features/quiz/quiz.page.html) | Template của trang. |
| [quiz.page.spec.ts](../src/frontend/src/app/features/quiz/quiz.page.spec.ts) | Test: Culture quiz (US12, US13) |
| [quiz.page.ts](../src/frontend/src/app/features/quiz/quiz.page.ts) | Trang Culture Quiz (prototype): câu hỏi trắc nghiệm kèm giải thích có nguồn. |

#### `src/frontend/src/app/shared/components/`

| File | Chức năng |
|---|---|
| [badges.spec.ts](../src/frontend/src/app/shared/components/badges.spec.ts) | Test: Badges — claim có phạm vi (US03) |
| [badges.ts](../src/frontend/src/app/shared/components/badges.ts) | Nhãn dùng chung: phạm vi claim, độ tin cậy, chip trích dẫn nguồn. |
| [photo.ts](../src/frontend/src/app/shared/components/photo.ts) | Component ảnh có ghi công tác giả + giấy phép. |
| [world-map.css](../src/frontend/src/app/shared/components/world-map.css) | CSS của component. |
| [world-map.spec.ts](../src/frontend/src/app/shared/components/world-map.spec.ts) | Test: WorldMap (US01) |
| [world-map.ts](../src/frontend/src/app/shared/components/world-map.ts) | Bản đồ thế giới SVG, tô sáng 10 quốc gia có dữ liệu, phát sự kiện khi chọn nước. |

#### `src/frontend/src/testing/`

| File | Chức năng |
|---|---|
| [render.ts](../src/frontend/src/testing/render.ts) | Tiện ích test chung. Quy ước tên test: bắt đầu bằng mã tiêu chí "[ACxx.y]" (docs/06-acceptance-criteria.md) để test truy vết (src/backend/tests/test_traceability.py)… |

#### `src/media-seed/culture/`

| File | Chức năng |
|---|---|
| [credits.json](../src/media-seed/culture/credits.json) | Ghi công + giấy phép của ảnh văn hoá (Wikimedia Commons). |

#### `src/media-seed/objects/`

| File | Chức năng |
|---|---|
| [credits.json](../src/media-seed/objects/credits.json) | Ghi công của ảnh hiện vật (Smithsonian, CC0). |

#### `src/object-storage/`
_Image MinIO đã hardening (ngoại lệ bảo mật EX-001)._

| File | Chức năng |
|---|---|
| [.dockerignore](../src/object-storage/.dockerignore) | File không gửi vào ngữ cảnh build Docker. |
| [Dockerfile](../src/object-storage/Dockerfile) | Build MinIO từ image chủ dự án cung cấp: bỏ `mc`, chạy uid 10001. |

<!-- FILE-MAP:END -->
