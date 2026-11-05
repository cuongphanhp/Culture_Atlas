# Bộ test CultureAtlas AI

Bộ test kiểm chứng từng tính năng theo **tiêu chí chấp nhận** trong [docs/06-acceptance-criteria.md](../../../docs/06-acceptance-criteria.md) và **hợp đồng API** trong [docs/api/openapi.yaml](../../../docs/api/openapi.yaml).

## Chạy

```bash
scripts/test.sh            # backend + frontend (tự bật PostgreSQL test ở cổng 55432)
scripts/test.sh backend
scripts/test.sh frontend
ACCEPTANCE_STRICT=1 scripts/test.sh   # trước khi phát hành: test PENDING bị tính là FAIL
```

Git hook `pre-commit` tự chạy phần test liên quan tới file đã thay đổi. Hook được bật bằng lệnh `git config core.hooksPath .githooks`. CI chạy toàn bộ test qua `.github/workflows/tests.yml`.

## Cấu trúc

| Thư mục / file | Nội dung | Trạng thái |
|---|---|---|
| `acceptance/test_db_rules.py` | Quy tắc nghiệp vụ do DB đảm bảo: trigger, ràng buộc, FTS không dấu, view độ phủ | Chạy ngay |
| `acceptance/test_f8_ingestion.py` | Worker nạp dữ liệu: log lần chạy, idempotent, giữ raw, giấy phép media | Chạy ngay |
| `acceptance/test_f1_explorer.py` | Content API: quốc gia, bài viết, claim, di sản, tìm kiếm, báo cáo sai | PENDING tới khi có API |
| `acceptance/test_f2_ai_guide.py` | AI Guide: SSE, trích dẫn, từ chối, ngữ cảnh, rate limit, đánh giá | PENDING |
| `acceptance/test_f3_compare.py` | So sánh: cache đã duyệt, ô thiếu nguồn, sinh nháp | PENDING |
| `acceptance/test_f5_quiz.py` | Quiz: chỉ bản published, không lộ đáp án, giải thích + nguồn | PENDING |
| `acceptance/test_f7_admin.py` | Auth/RBAC, duyệt, claim–nguồn, nguồn, độ phủ, đồng bộ | PENDING |
| `test_traceability.py` | Mỗi AC phải có test, mỗi endpoint OpenAPI phải có test | Chạy ngay |
| `test_worker_parsers.py` | Parser từng nguồn dữ liệu (không gọi mạng) | Chạy ngay |
| `fixtures/seed.sql` | Dữ liệu mẫu cố định, nạp lại trước mỗi test | — |
| `fakes.py` | `FakeLLM`, `FakeEmbedder`: không gọi OpenAI, kết quả xác định | — |
| `src/frontend/src/**/*.spec.ts` | Test UI (Vitest); tên test bắt đầu bằng `[ACxx.y]` | Một phần PENDING (`it.skip`) |

## Cơ chế PENDING

Mỗi test API khai báo endpoint mình cần bằng decorator, ví dụ `@route("GET", "/api/countries/{iso}")`.

- Nếu app chưa có endpoint đó, test được **skip với nhãn PENDING**. Cuối mỗi lần chạy có bảng tổng hợp các AC còn chờ.
- Khi endpoint được code, test **tự chạy thật**. Không cần sửa test để "bật" nó.
- Với frontend, test UI chưa đạt được viết bằng `it.skip('[ACxx.y] PENDING …')`. Khi làm xong tính năng, phải bỏ `.skip`.

## Hợp đồng app ↔ test

Để test thay được các thành phần bên ngoài, app cần tuân theo các quy ước sau:

| Quy ước | Lý do |
|---|---|
| `app.ai.llm_adapter.get_llm` là FastAPI dependency trả `LLMAdapter` | Test thay bằng `FakeLLM` |
| `app.ai.retrieval.get_embedder` là dependency có `async embed(texts)` | Test thay bằng `FakeEmbedder` (1024 chiều) |
| Bằng chứng gán nhãn `c1..cN` trong prompt; câu trả lời trích bằng `[c#]` | Kiểm tra trích dẫn (AC07) |
| `complete_json(name=...)` với tên `follow_ups`, `comparison`, `quiz_drafts` | `FakeLLM` có kịch bản theo tên tác vụ |
| Cấu hình đọc từ biến môi trường `DATABASE_URL`, `JWT_SECRET`, `GUEST_DAILY_LIMIT` | conftest ghi đè các biến này cho môi trường test |
| Khách được nhận diện bằng header `X-Client-Id` (nếu không có thì dùng IP) | Mỗi test là một khách riêng, rate limit không lẫn giữa các test |
| JWT dùng HS256 với `JWT_SECRET`, có `exp` | Test tạo token hết hạn hoặc giả mạo (AC15.2) |
| Mọi lỗi trả `application/problem+json`. Lỗi validate trả **400**, vi phạm nghiệp vụ trả **422** | `assert_problem` |

Khi đổi một quy ước, cập nhật `conftest.py`, `fakes.py` và bảng này **trong cùng commit**.

## Khi thêm hoặc sửa tính năng

1. Thêm hoặc sửa tiêu chí trong `docs/06-acceptance-criteria.md` và endpoint trong `docs/api/openapi.yaml`.
2. Viết test **trước hoặc cùng lúc** với code:
   - Backend: dùng `@ac("ACxx.y")` và `@route(...)`.
   - Frontend: đặt tên test `[ACxx.y] …`.
3. Nếu cần dữ liệu mới, thêm vào `fixtures/seed.sql` và giữ id cố định.
4. Chạy `scripts/test.sh`. Không merge khi còn test FAIL. Test của tính năng vừa làm không được còn PENDING.
