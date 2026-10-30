# 06 — Tiêu chí chấp nhận (Given – When – Then)

Mỗi tiêu chí có mã `ACxx.y`, ánh xạ tới user story trong [08-invest-requirements.md](08-invest-requirements.md).

## Cultural Explorer

**US01 — Chọn quốc gia trên bản đồ**
- AC01.1 *Given* trang Khám phá đã tải, *when* tôi bấm vào một quốc gia có nội dung, *then* panel xem nhanh hiện tên, thủ đô, ngôn ngữ, tiền tệ, % độ phủ và nút “Xem hồ sơ văn hoá”.
- AC01.2 *Given* quốc gia chưa có nội dung, *when* tôi bấm vào, *then* hệ thống không điều hướng và hiển thị “Chưa có trong giai đoạn này”.
- AC01.3 Bản đồ dùng được bằng bàn phím (Tab tới danh sách quốc gia thay thế) và có `aria-label`.

**US02 — Hồ sơ quốc gia**
- AC02.1 *Given* `/countries/JP`, *then* hiển thị thông tin nền + 12 chip danh mục + thẻ “5 điều cần biết”.
- AC02.2 *When* chọn một danh mục, *then* chỉ hiển thị bài viết `published` thuộc danh mục đó; nếu không có → trạng thái rỗng kèm gợi ý hỏi AI.
- AC02.3 Trang được render SSR, có `<title>` và meta description theo quốc gia.

**US03 — Claim có phạm vi và nguồn**
- AC03.1 Mỗi claim hiển thị nhãn scope (Phổ biến / Truyền thống lịch sử / Vùng miền / Cộng đồng cụ thể) và nhãn confidence.
- AC03.2 Mỗi claim có ≥ 1 chip nguồn; hover/nhấn hiện nhà xuất bản, tiêu đề, giấy phép, ngày truy xuất.
- AC03.3 Claim `unverified` không được hiển thị cho người dùng cuối.

**US04 — Di sản UNESCO**
- AC04.1 Danh sách có tên, loại (vật thể / phi vật thể), danh sách ghi danh, năm; lọc được theo loại.
- AC04.2 Dữ liệu từ UNESCO WHC hiển thị ghi công CC BY-SA 4.0.

**US05 — Tìm kiếm**
- AC05.1 *When* gõ “nhat ban” (không dấu), *then* kết quả có “Nhật Bản”.
- AC05.2 Kết quả trả về trong < 500 ms (p95) với kho MVP.

## AI Cultural Guide

**US06 — Hỏi đáp streaming**
- AC06.1 *When* gửi câu hỏi tiếng Việt, *then* token đầu tiên xuất hiện < 3 s (p95) và câu trả lời bằng tiếng Việt.
- AC06.2 Câu hỏi dữ kiện (“Thủ đô của Ấn Độ?”) được trả từ DB, `chat_logs.model = 'structured'`, không gọi LLM.
- AC06.3 Khách vượt 10 lượt/ngày nhận HTTP 429 và thông báo thân thiện.

**US07 — Trích dẫn**
- AC07.1 Mỗi đoạn có phát biểu thực tế chứa ≥ 1 `[c#]`; mỗi `c#` khớp một mục trong `citations[]`.
- AC07.2 Mỗi `citations[].chunk_id` thuộc tập chunk đã truy xuất cho lượt hỏi đó (kiểm tra sau sinh).
- AC07.3 Bấm chip trích dẫn làm nổi bật thẻ nguồn tương ứng ở cột phải.

**US08 — Từ chối khi thiếu nguồn**
- AC08.1 *Given* không có chunk vượt ngưỡng liên quan, *then* `confidence = insufficient`, câu trả lời chứa “chưa có đủ nguồn” và gợi ý nguồn ngoài.
- AC08.2 Câu hỏi được ghi vào hàng đợi biên tập (`feedback.type = unanswered`).
- AC08.3 Trên bộ benchmark nhóm “không đủ nguồn”, tỷ lệ từ chối đúng ≥ 90%.

**US09 — Ngữ cảnh trang**
- AC09.1 *Given* `context.country = JP`, *when* hỏi “Có nên tặng hoa cúc không?”, *then* truy xuất được lọc theo JP và chip ngữ cảnh hiển thị “Nhật Bản”.

**US10 — Đánh giá & gợi ý**
- AC10.1 Mỗi câu trả lời có 2–3 câu hỏi gợi ý; bấm vào gửi ngay câu hỏi đó.
- AC10.2 👍/👎 lưu vào `chat_logs.rating`; không đánh giá lại được cùng một tin nhắn.

## Culture Comparison

**US11**
- AC11.1 *Given* (VN, JP, gift_giving) có bản đã duyệt, *then* trả bản cache, hiển thị nhãn “Đã được biên tập viên duyệt”.
- AC11.2 Ô thiếu bằng chứng hiển thị “Chưa đủ nguồn để kết luận” — không bao giờ để LLM tự lấp.
- AC11.3 Không có cache → sinh mới, gắn nhãn “Chưa duyệt”, lưu `comparisons.status = draft`.
- AC11.4 Chọn A = B → nút So sánh bị vô hiệu kèm thông báo.

## Culture Quiz

**US12–US13**
- AC12.1 Chỉ câu hỏi `published` được phục vụ; lọc theo quốc gia, danh mục, độ khó.
- AC13.1 Sau khi chọn, đáp án đúng tô xanh, đáp án sai đã chọn tô đỏ, hiện giải thích + nguồn + liên kết bài gốc.
- AC13.2 Tổng kết phiên liệt kê chủ đề có câu sai.

## Báo cáo sai

**US14**
- AC14.1 Biểu mẫu gồm loại lỗi (sai sự thật / khuôn mẫu / thiếu nguồn / khác) và mô tả ≤ 1000 ký tự.
- AC14.2 Gửi thành công → HTTP 201, `feedback.status = open`, hiển thị lời cảm ơn.

## Trang quản trị

**US15** — AC15.1 Editor không truy cập được `/admin/users` (HTTP 403). AC15.2 Token hết hạn → chuyển trang đăng nhập.

**US16** — AC16.1 Duyệt → `status = published`, tạo `entry_revisions`, re-index chunk trong ≤ 1 phút. AC16.2 Từ chối bắt buộc nhập lý do. AC16.3 Nội dung AI sinh luôn vào hàng đợi ở `draft`.

**US17** — AC17.1 Không xuất bản được claim không có nguồn. AC17.2 Mỗi liên kết claim–nguồn có `evidence_excerpt`.

**US18** — AC18.1 Nguồn bắt buộc có `license` và `retrieved_at`. AC18.2 Media chưa xác minh giấy phép chỉ được lưu dạng liên kết.

**US19** — AC19.1 Ô có < 3 claim đã duyệt được tô cảnh báo. AC19.2 Bấm ô mở danh sách bài viết của quốc gia × danh mục.

**US20** — AC20.1 Mỗi lần chạy tạo `ingestion_runs` với số bản ghi vào/thay đổi/lỗi. AC20.2 Chạy lại không tạo bản ghi trùng (idempotent theo khoá nguồn). AC20.3 `raw_data` gốc được lưu.
