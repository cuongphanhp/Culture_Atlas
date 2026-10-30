# 01 — Phân tích đề bài Top-down (Research)

> Bước 1 · Nguồn đầu vào: [CultureAtlas-AI.md](../CultureAtlas-AI.md)
> Phương pháp: đi từ **tầm nhìn → mục tiêu → năng lực → tính năng → chức năng → dữ liệu/kỹ thuật**, mỗi tầng chỉ trả lời câu hỏi của tầng trên.

## 1. Tóm tắt đề bài

CultureAtlas AI là nền tảng **học tập và khám phá văn hoá thế giới** có AI làm hướng dẫn viên. Khác với một từ điển văn hoá, sản phẩm trả lời ba câu hỏi:

| Câu hỏi | Năng lực sản phẩm tương ứng |
|---|---|
| **Vì sao** một nền văn hoá hình thành như vậy? | AI Cultural Guide giải thích bối cảnh, có trích dẫn |
| **Người dân thực hành như thế nào**? | Hồ sơ quốc gia gồm các *claim* có phạm vi (scope) |
| **Khác gì** với văn hoá của tôi? | Culture Comparison theo từng khía cạnh, có nguồn từng ô |

Nguyên tắc xuyên suốt: **"Có nguồn hoặc không khẳng định"**.

## 2. Phân rã Top-down

### Tầng 0 — Tầm nhìn

> Giúp người Việt (và người học nói chung) hiểu đúng, tôn trọng và ghi nhớ văn hoá các nước, bằng nội dung có nguồn kiểm chứng và AI giải thích theo ngữ cảnh.

### Tầng 1 — Mục tiêu sản phẩm (Goals)

| ID | Mục tiêu | Đo bằng |
|---|---|---|
| G1 | Người dùng **tìm được** nội dung đáng tin cậy | Độ phủ ≥ 80% ô quốc gia × danh mục; độ chính xác ≥ 95% |
| G2 | Người dùng **hiểu được** nội dung qua AI | Citation correctness ≥ 90%; 👍 ≥ 75% |
| G3 | Người dùng **ghi nhớ được** qua tương tác | Tỷ lệ hoàn thành quiz; quay lại sau 7 ngày |
| G4 | Vận hành **bền vững** về dữ liệu và chi phí | 100% tài sản có giấy phép; p95 TTFT < 3s; chi phí LLM/lượt hỏi trong ngân sách |

### Tầng 2 — Năng lực (Capabilities)

```text
CultureAtlas AI
├── C1 Khám phá (Discover)         → G1
├── C2 Hỏi đáp có căn cứ (Explain)  → G2
├── C3 Đối chiếu (Compare)          → G2
├── C4 Học & ghi nhớ (Learn)        → G3
├── C5 Quản trị tri thức (Curate)   → G1, G4
└── C6 Thu nạp dữ liệu (Ingest)     → G1, G4
```

### Tầng 3 — Tính năng (Features)

| Năng lực | Tính năng | MVP? |
|---|---|---|
| C1 | F1 Cultural Explorer — bản đồ, hồ sơ quốc gia, di sản UNESCO, chủ đề xuyên quốc gia | ✅ |
| C2 | F2 AI Cultural Guide — RAG song ngữ, trích dẫn, mức chắc chắn, từ chối có lý do | ✅ |
| C3 | F3 Culture Comparison — 2 quốc gia × 1 chủ đề, cache đã duyệt | ✅ |
| C4 | F5 Culture Quiz — câu hỏi đã duyệt, giải thích có nguồn | ✅ |
| C4 | F4 Cultural Scenario — học qua tình huống | ⏭ Sau MVP |
| C4 | F6 Cultural Passport — hành trình học, gợi ý | ⏭ Sau MVP |
| C5 | F7 Trang quản trị nội dung — duyệt, nguồn, báo cáo sai, độ phủ | ✅ |
| C6 | F8 Ingestion Worker — REST Countries, UNESCO, Natural Earth | ✅ (nền tảng) |

### Tầng 4 — Chức năng (Functions) — xem chi tiết [02-features.md](02-features.md)

### Tầng 5 — Dữ liệu & kỹ thuật

| Chức năng cần | Dữ liệu | Kỹ thuật |
|---|---|---|
| Hồ sơ quốc gia | `countries`, `culture_entries`, `claims`, `sources` | Content API, Angular SSR |
| Trả lời có trích dẫn | `entry_chunks` (tsv + embedding) | PostgreSQL FTS + pgvector, RRF, reranker, LLM adapter |
| So sánh | `comparisons` (JSONB, đã duyệt) | Tool `compare_cultures` |
| Quiz | `quiz_questions`, `user_progress` | Sinh nháp bằng LLM → duyệt |
| Kiểm soát chất lượng | `feedback`, `chat_logs`, `entry_revisions` | Admin API, benchmark trong CI |
| Đồng bộ nguồn | `ingestion_runs`, `raw_data` | Worker + APScheduler |

## 3. Bối cảnh và đối thủ (research)

| Loại giải pháp | Ví dụ | Điểm mạnh | Khoảng trống CultureAtlas lấp |
|---|---|---|---|
| Bách khoa mở | Wikipedia, Wikidata | Phủ rộng, miễn phí | Không giải thích theo nhu cầu, không so sánh, chất lượng không đồng đều |
| Cổng di sản | UNESCO ICH / WHC | Nguồn chính thức | Thiên về di sản; yếu phong tục đời thường |
| Trang du lịch chính thức | JNTO, Vietnam Tourism | Thực hành, có phép lịch sự | Mỗi nước một nơi, không đối chiếu |
| Chatbot tổng quát | LLM đa dụng | Linh hoạt | Có thể bịa, không nguồn, khái quát hoá quá mức |
| Ứng dụng học ngôn ngữ | — | Gamification | Văn hoá chỉ là phụ |

**Kết luận:** giá trị khác biệt nằm ở *dữ liệu có nguồn + truy xuất chính xác + giải thích tôn trọng đa dạng + học tương tác*, không ở mô hình AI lớn nhất.

## 4. Người dùng mục tiêu

| Persona | Nhu cầu | Tính năng chính |
|---|---|---|
| **P1 — Người chuẩn bị đi nước ngoài** *(persona chính MVP)* | Phép lịch sự, tránh hiểu nhầm | AI Guide, Comparison, “5 điều cần biết” |
| P2 — Học sinh, sinh viên | Ôn kiến thức văn hoá – địa lý | Explorer, Quiz |
| P3 — Người làm việc với đối tác quốc tế | Giao tiếp, tiếp khách | Comparison |
| P4 — Giáo viên | Tài liệu có nguồn, bộ câu hỏi | Explorer, Quiz |
| P5 — Người yêu văn hoá | Khám phá tự do | Explorer, AI Guide |
| P6 — Biên tập viên / Quản trị | Duyệt nội dung, quản lý nguồn | Trang quản trị |

**Kịch bản điển hình (P1):** Lan, 24 tuổi, sắp sang Nhật làm việc. Lan mở bản đồ → chọn Nhật Bản → đọc “5 điều cần biết” → hỏi AI “Tặng quà ở Nhật khác Việt Nam thế nào?” → xem bảng so sánh → làm quiz 2 phút để ghi nhớ.

## 5. Phạm vi

### Trong MVP
- 10 quốc gia: VN, TH, JP, KR, CN, IN, FR, MX, EG, KE (bổ sung 1 nước châu Phi cận Sahara).
- 12 danh mục cố định: `greetings`, `etiquette`, `food_dining`, `gift_giving`, `festivals`, `religion_beliefs`, `clothing`, `arts_music`, `family_life`, `heritage`, `business_culture`, `taboos`.
- Song ngữ Việt – Anh.
- F1, F2, F3, F5, F7, F8.

### Ngoài MVP
F4 Scenario, F6 Passport, tài khoản người học đầy đủ, ứng dụng di động, offline, hiện vật bảo tàng (Smithsonian, Europeana).

## 6. Ràng buộc và giả định

| Loại | Nội dung |
|---|---|
| Công nghệ | Angular + TypeScript (SSR), FastAPI, PostgreSQL 16 + pgvector, Docker Compose |
| Pháp lý | Mỗi nguồn/ảnh lưu giấy phép, tác giả, URL; CC BY-SA phải ghi công & chia sẻ tương tự |
| Dữ liệu | Không gọi API ngoài trong luồng người dùng — mọi thứ qua worker → DB |
| Nhân lực | Nhóm 2–3 người; cần ngân sách biên tập nội dung phong tục |
| Giả định | Nguồn mở mạnh về di sản nhưng yếu về phong tục đời thường → phải tự viết bài có trích dẫn |

## 7. Rủi ro chính (tóm tắt)

AI bịa thông tin · khuôn mẫu văn hoá · bản quyền hình ảnh · mất cân bằng dữ liệu giữa quốc gia · chi phí LLM · thiếu biên tập viên. Chi tiết và cách xử lý: [CultureAtlas-AI.md §13](../CultureAtlas-AI.md#13-rủi-ro-và-cách-xử-lý).

## 8. Câu hỏi mở cần chốt ở Giai đoạn 0

1. Persona chính: P1 (đi nước ngoài) hay P2 (sinh viên)? — *khuyến nghị P1*.
2. Kenya hay Nigeria cho nhóm châu Phi cận Sahara?
3. Nhà cung cấp LLM và mô hình embedding (benchmark trên dữ liệu tiếng Việt).
4. Giới hạn lượt hỏi/ngày với khách chưa đăng nhập (đề xuất: 10).
