# Yêu cầu phi chức năng (NFR)

| ID | Nhóm | Yêu cầu | Đo lường / mục tiêu MVP |
|---|---|---|---|
| NFR01 | Hiệu năng | Thời gian đến token đầu tiên của AI Guide | p95 < 3 s |
| NFR02 | Hiệu năng | Content API (hồ sơ, bài viết, tìm kiếm) | p95 < 500 ms |
| NFR03 | Hiệu năng | Trang quốc gia SSR — Largest Contentful Paint | < 2,5 s trên 4G |
| NFR04 | Chất lượng AI | Citation correctness | ≥ 90% |
| NFR05 | Chất lượng AI | Retrieval recall@8 | ≥ 85% |
| NFR06 | Chất lượng AI | Tỷ lệ từ chối đúng khi thiếu nguồn | ≥ 90% |
| NFR07 | Chất lượng nội dung | Độ chính xác claim (biên tập viên đối chiếu) | ≥ 95% |
| NFR08 | Chất lượng nội dung | Độ phủ quốc gia × danh mục (≥ 3 claim đã duyệt) | ≥ 80% |
| NFR09 | Bảo mật | JWT cho Editor/Admin; RBAC kiểm tra ở backend; mật khẩu băm Argon2 | Bắt buộc |
| NFR10 | Bảo mật | Rate limit AI API theo IP/thiết bị; lọc prompt injection đầu vào | Bắt buộc |
| NFR11 | Bảo mật | OWASP ASVS L1 cho API; HTTPS toàn bộ | Bắt buộc |
| NFR12 | Khả dụng | Uptime | ≥ 99% / tháng |
| NFR13 | Khả năng truy cập | WCAG 2.1 AA: tương phản, bàn phím, `aria-label` cho bản đồ | Bắt buộc |
| NFR14 | Đa ngôn ngữ | Giao diện và câu trả lời vi/en; tìm kiếm không dấu | Bắt buộc |
| NFR15 | Quan sát | Log có cấu trúc; tracing LLM (prompt, độ trễ, chi phí, trích dẫn) | Langfuse hoặc tương đương |
| NFR16 | Chi phí | Cache câu trả lời lặp lại; mô hình nhỏ cho router | Theo dõi chi phí / lượt hỏi |
| NFR17 | Bảo trì | Benchmark RAG chạy trong CI khi đổi prompt / mô hình / chunking / embedding | Bắt buộc |
| NFR18 | Di động | Giao diện responsive ≥ 360 px | Bắt buộc |
| NFR19 | Riêng tư | Không lưu thông tin cá nhân của Khách ngoài session id ẩn danh; log chat lưu tối đa 180 ngày | Bắt buộc |
