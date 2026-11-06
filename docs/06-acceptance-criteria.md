# 06 — Tiêu chí chấp nhận (Given – When – Then)

Mỗi tiêu chí có mã `ACxx.y`, ánh xạ tới user story trong [08-invest-requirements.md](08-invest-requirements.md).

## Cultural Explorer

**US01 — Chọn quốc gia trên bản đồ**
- AC01.1 *Given* trang Khám phá đã tải, *when* tôi bấm vào một quốc gia có nội dung, *then* panel xem nhanh hiện tên, thủ đô, ngôn ngữ, tiền tệ, % độ phủ và nút “Xem hồ sơ văn hoá”.
- AC01.2 *Given* quốc gia chưa có nội dung, *when* tôi bấm vào, *then* hệ thống không điều hướng và hiển thị “Chưa có trong giai đoạn này”.
- AC01.3 Bản đồ dùng được bằng bàn phím (Tab tới danh sách quốc gia thay thế) và có `aria-label`.
- AC01.4 Bấm chọn một quốc gia (ảnh nhỏ ở hero hoặc trên bản đồ) → ảnh nền đổi sang ảnh của quốc gia đó. Hồ sơ quốc gia dùng ảnh nền của nước đang xem. AI Guide đổi ảnh nền theo quốc gia đang được nói tới (hai nước → chia đôi).

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
- AC06.4 Chào hỏi / hỏi về trợ lý (“Xin chào”, “Bạn là ai?”, “Cảm ơn”) được trả lời tự nhiên, ngắn; `route = smalltalk`, `confidence = none`, không có trích dẫn và không đưa thông tin văn hoá.
- AC06.5 Hội thoại nhiều lượt: câu hỏi nối tiếp trong cùng `sessionId` (“Còn hoa thì sao?”) hiểu theo quốc gia của lượt trước, và LLM nhận các lượt hỏi–đáp trước làm ngữ cảnh. Phiên của khách khác không được đọc lịch sử.
- AC06.6 Mức giải thích `simple | normal | deep` thay đổi yêu cầu gửi LLM. Mức `deep` dùng nhiều bằng chứng hơn (tối đa 8 đoạn) và yêu cầu phân tích bối cảnh, ý nghĩa, khác biệt vùng miền.
- AC06.7 Dịch vụ AI local (embedding/rerank) hoặc vector DB (Qdrant) tạm ngừng → hỏi đáp văn bản vẫn chạy bằng tìm kiếm từ khoá.

**US07 — Trích dẫn**
- AC07.1 Mỗi đoạn có phát biểu thực tế chứa ≥ 1 `[c#]`; mỗi `c#` khớp một mục trong `citations[]`.
- AC07.2 Mỗi `citations[].chunk_id` thuộc tập chunk đã truy xuất cho lượt hỏi đó (kiểm tra sau sinh).
- AC07.3 Bấm chip trích dẫn làm nổi bật thẻ nguồn tương ứng ở cột phải.
- AC07.4 Bằng chứng có ba loại: `claim` (đã biên tập), `reference` (tài liệu tham khảo do worker thu thập), `heritage` (dữ liệu UNESCO). Mỗi trích dẫn có `kind`, `verified`, giấy phép và URL. Câu trả lời chỉ dựa trên tài liệu chưa biên tập có `confidence` tối đa là `inferred`.

**US08 — Từ chối khi thiếu nguồn**
- AC08.1 *Given* không có chunk vượt ngưỡng liên quan, *then* `confidence = insufficient`, câu trả lời chứa “chưa có đủ nguồn” và gợi ý nguồn ngoài.
- AC08.2 Câu hỏi được ghi vào hàng đợi biên tập (`feedback.type = unanswered`).
- AC08.4 Câu hỏi ngoài phạm vi văn hoá (không nhắc quốc gia nào, không có bằng chứng) được từ chối lịch sự, nói rõ phạm vi của trợ lý.
- AC08.3 Trên bộ benchmark nhóm “không đủ nguồn”, tỷ lệ từ chối đúng ≥ 90%.

**US09 — Ngữ cảnh trang**
- AC09.1 *Given* `context.country = JP`, *when* hỏi “Có nên tặng hoa cúc không?”, *then* truy xuất được lọc theo JP và chip ngữ cảnh hiển thị “Nhật Bản”.
- AC09.2 Câu hỏi dữ kiện không nêu tên nước (“Thủ đô là gì?”) dùng quốc gia của ngữ cảnh trang. Nhận diện quốc gia không nhầm với từ thường (“phương pháp”, “sinh nhật”, “ăn đồ”).
- AC09.3 Câu hỏi nhắc nhiều nước (so sánh) lấy bằng chứng riêng cho từng nước và xếp xen kẽ, để nước nào cũng có nguồn. Câu hỏi hội thoại được viết lại thành truy vấn tìm kiếm độc lập (tiếng Anh, mỗi nước một truy vấn) trước khi truy xuất.

**US10 — Đánh giá & gợi ý**
- AC10.1 Mỗi câu trả lời có 2–3 câu hỏi gợi ý; bấm vào gửi ngay câu hỏi đó.
- AC10.2 👍/👎 lưu vào `chat_logs.rating`; không đánh giá lại được cùng một tin nhắn.
- AC10.3 Câu hỏi gợi ý (lời chào, cột “Thử hỏi”, sau mỗi câu trả lời) bám theo quốc gia đang nói tới: *given* `context.country = JP` hoặc câu hỏi nhắc Nhật Bản, *then* mọi gợi ý đều về Nhật Bản và nêu nét văn hoá riêng của nước đó (vd. omiyage, kính ngữ keigo), không phải câu mẫu chung chỉ thay tên nước. Ngoài chủ đề người dùng quan tâm (AC10.4), chủ đề có dữ liệu trong kho của nước đó được gợi ý trước. `GET /api/ai/suggestions` trả về gợi ý mà không gọi LLM và không trừ lượt hỏi.
- AC10.4 Gợi ý ưu tiên chủ đề người dùng quan tâm: chủ đề suy ra từ các câu đã hỏi trong phiên (câu gần nhất nặng nhất) và mục đang xem (`category`). *Given* đã hỏi về tặng quà ở Nhật, *then* 2 gợi ý đầu đào sâu chủ đề tặng quà của Nhật, gợi ý còn lại mở sang chủ đề khác; không gợi ý lại câu đã hỏi. Lịch sử của phiên khách khác không được dùng.

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

**US18** — AC18.1 Nguồn bắt buộc có `license` và `retrieved_at`. AC18.2 Media chưa xác minh giấy phép chỉ được lưu dạng liên kết. AC18.3 File media (ảnh, video, âm thanh, tài liệu) nằm ở object storage S3 (MinIO); bảng `media_assets` chỉ lưu metadata (bucket, object_key, loại, content-type, kích thước, sha256, tác giả, giấy phép) + URL object storage cấp (`/media/<key>`). Nạp lại không tạo bản trùng (khoá theo nội dung). AC18.4 Bucket media cho đọc công khai từng object nhưng không liệt kê được bucket; bucket payload thô của worker riêng tư hoàn toàn. AC18.5 Ảnh của giao diện được nạp lên object storage bằng `worker.cli seed-media` (kèm metadata, ghi công); giao diện chỉ dùng URL `/media/...`, không đóng gói ảnh vào bản build.

**US19** — AC19.1 Ô có < 3 claim đã duyệt được tô cảnh báo. AC19.2 Bấm ô mở danh sách bài viết của quốc gia × danh mục.

**US20** — AC20.1 Mỗi lần chạy tạo `ingestion_runs` với số bản ghi vào/thay đổi/lỗi. AC20.2 Chạy lại không tạo bản ghi trùng (idempotent theo khoá nguồn). AC20.3 `raw_data` gốc được lưu. AC20.4 `worker.cli index` dựng chỉ mục RAG cho claim đã xuất bản, tài liệu tham khảo (chia đoạn ≤ 900 ký tự) và di sản UNESCO; mỗi đoạn gắn nguồn; chạy lại không tạo trùng. AC20.5 Embedding lưu ở vector DB Qdrant (point id = `entry_chunks.id`, payload `kind`, `countries`, `category` để lọc); PostgreSQL chỉ lưu văn bản + metadata của đoạn, không lưu vector.

## Hỏi đáp bằng giọng nói

**US21 — Hỏi bằng giọng nói và nghe câu trả lời** (AI local: Gipformer STT, VieNeu-TTS — xem [11-vietnamese-chat-stack.md](11-vietnamese-chat-stack.md))
- AC21.1 *Given* bản ghi âm tiếng Việt (webm/ogg/wav/mp3/m4a, ≤ 60 giây), *when* gửi lên, *then* nhận lại văn bản nhận dạng. Đoạn 15 giây xử lý < 2 s trên CPU. Âm thanh chỉ được xử lý bởi dịch vụ AI local, không gửi ra dịch vụ bên ngoài.
- AC21.2 File không phải âm thanh hoặc rỗng → HTTP 400. File > 10 MB hoặc dài > 60 giây → HTTP 413. Mọi lỗi kèm thông báo tiếng Việt.
- AC21.3 Không lưu âm thanh của người dùng: âm thanh chỉ nằm trong bộ nhớ hoặc file tạm và bị xoá ngay sau khi nhận dạng. DB chỉ lưu văn bản.
- AC21.4 Đọc câu trả lời thành giọng nói:
  - Bỏ nhãn trích dẫn `[c#]` và ký hiệu markdown trước khi đọc.
  - Số và ngày tháng được đọc thành chữ.
  - Chọn được giọng Bắc hoặc Nam từ danh sách; chọn giọng không tồn tại → HTTP 400.
  - Văn bản > 1.500 ký tự → HTTP 413.
- AC21.5 Dịch vụ AI local không chạy → HTTP 503. Hỏi đáp bằng văn bản vẫn hoạt động bình thường.
- AC21.6 Trong AI Guide:
  - Nút micro ghi âm; văn bản nhận dạng hiện vào ô nhập để người dùng sửa trước khi gửi.
  - Nút loa trên mỗi câu trả lời để nghe lại.
