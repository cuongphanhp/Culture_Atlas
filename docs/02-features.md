# 02 — Danh mục tính năng và chức năng

Mỗi chức năng có mã `Fx.y`, được truy vết tới user story (US), màn hình (SCR) và API trong [master-traceability.md](traceability/master-traceability.md).

## F1 — Cultural Explorer *(MVP)*

| Mã | Chức năng | Ghi chú |
|---|---|---|
| F1.1 | Bản đồ thế giới tương tác, tô màu theo độ phủ nội dung | MapLibre GL + Natural Earth |
| F1.2 | Tìm quốc gia theo tên / khu vực / chủ đề | Không dấu vẫn tìm được (`unaccent`) |
| F1.3 | Hồ sơ quốc gia: thủ đô, khu vực, ngôn ngữ, tiền tệ, láng giềng | Snapshot từ REST Countries |
| F1.4 | Bài viết theo 12 danh mục, tách thành claim có scope + confidence + nguồn | Chỉ `published` |
| F1.5 | Thẻ “Lần đầu đến đây? Hãy biết 5 điều này” | Mỗi điều có nguồn |
| F1.6 | Lớp di sản UNESCO (vật thể / phi vật thể), lọc theo loại | |
| F1.7 | Khám phá theo chủ đề xuyên quốc gia | Ví dụ “Trà trên thế giới” |
| F1.8 | Lễ hội theo tháng (timeline) | |
| F1.9 | Báo cáo sai trên từng bài / claim | Tạo `feedback` |

## F2 — AI Cultural Guide *(MVP, cốt lõi)*

| Mã | Chức năng | Ghi chú |
|---|---|---|
| F2.1 | Chat song ngữ Việt – Anh, streaming SSE | |
| F2.2 | Trích dẫn cho từng ý, xem đoạn trích + giấy phép | `[c1]` → `citations[]` |
| F2.3 | Mức chắc chắn: có nguồn trực tiếp / suy luận / chưa đủ nguồn | |
| F2.4 | Từ chối có lý do + gợi ý nguồn ngoài; ghi câu hỏi vào hàng đợi biên tập | |
| F2.5 | Ngữ cảnh trang (đang xem Nhật Bản → mặc định hỏi về Nhật Bản) | `context` |
| F2.6 | Chọn mức giải thích: đơn giản / tiêu chuẩn / chuyên sâu | |
| F2.7 | 2–3 câu hỏi gợi ý sau mỗi câu trả lời | |
| F2.8 | Đánh giá 👍/👎 và báo cáo sai câu trả lời | |
| F2.9 | Trả lời dữ kiện đơn giản trực tiếp từ DB, không gọi LLM | Router |
| F2.10 | Guardrail câu hỏi khuôn mẫu / chủ đề nhạy cảm | |
| F2.11 | Giới hạn lượt hỏi cho khách | Rate limit |

## F3 — Culture Comparison *(MVP)*

| Mã | Chức năng |
|---|---|
| F3.1 | Chọn 2 quốc gia + 1 chủ đề |
| F3.2 | Bảng: tương đồng, khác biệt theo khía cạnh, bối cảnh, ngoại lệ, chưa đủ bằng chứng |
| F3.3 | Ô thiếu nguồn hiển thị “Chưa đủ nguồn để kết luận” |
| F3.4 | Trả bản đã duyệt (cache) nếu có; nếu không, sinh nháp và gắn nhãn “chưa duyệt” |

## F4 — Cultural Scenario *(sau MVP)*

Khung tình huống do biên tập viên viết, 3–4 lựa chọn mỗi bước, AI cá nhân hoá lời thoại, tóm tắt bài học cuối tình huống.

## F5 — Culture Quiz *(MVP)*

| Mã | Chức năng |
|---|---|
| F5.1 | Bộ câu hỏi theo quốc gia / chủ đề / độ khó |
| F5.2 | Giải thích đáp án ngay, kèm nguồn và liên kết bài gốc |
| F5.3 | Thống kê nội dung chưa nắm vững (theo phiên) |
| F5.4 | AI sinh câu hỏi nháp từ bài đã duyệt → biên tập viên duyệt |

## F6 — Cultural Passport *(sau MVP)*

Lưu quốc gia đã khám phá, đóng dấu hộ chiếu, gợi ý lộ trình học.

## F7 — Trang quản trị nội dung *(MVP)*

| Mã | Chức năng |
|---|---|
| F7.1 | Hàng đợi duyệt: bài viết, claim, quiz, so sánh do AI sinh |
| F7.2 | Soạn / sửa bài viết, tách claim, gắn nguồn + đoạn bằng chứng |
| F7.3 | Quản lý nguồn: giấy phép, độ tin cậy, ngày truy xuất |
| F7.4 | Quản lý media: tác giả, giấy phép, ghi công |
| F7.5 | Xử lý báo cáo sai (feedback) |
| F7.6 | Bảng độ phủ quốc gia × danh mục |
| F7.7 | Kích hoạt / theo dõi đồng bộ dữ liệu |
| F7.8 | Xem kết quả benchmark RAG |

## F8 — Ingestion Worker *(MVP, nền tảng)*

Nhập REST Countries, UNESCO WHC/ICH, Natural Earth; chuẩn hoá ISO 3166; chunking; embedding; ghi `ingestion_runs`.
