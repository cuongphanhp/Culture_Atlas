# 08 — User stories theo INVEST

Backlog MVP gồm **20 user story**. Mỗi story được kiểm tra INVEST trước khi vào sprint, có tiêu chí chấp nhận tại [06-acceptance-criteria.md](06-acceptance-criteria.md).

## 1. Tiêu chí INVEST áp dụng cho CultureAtlas AI

| Tiêu chí | Ý nghĩa trong dự án |
|---|---|
| **I**ndependent | Story giao được giá trị riêng; phụ thuộc chỉ khi bắt buộc (ví dụ cần dữ liệu `published`) và được ghi rõ |
| **N**egotiable | Giao diện, thuật toán xếp hạng, mô hình có thể đổi, miễn giữ nguyên mục tiêu và nguyên tắc “có nguồn hoặc không khẳng định” |
| **V**aluable | Mang lại giá trị cho người học (hiểu, so sánh, ghi nhớ) hoặc cho đội nội dung (chất lượng, pháp lý) |
| **E**stimable | Đã rõ vai trò, đầu vào, đầu ra, API, bảng dữ liệu và trường hợp lỗi |
| **S**mall | Một năng lực chính; chia được thành task UI / API / dữ liệu / test trong ≤ 1 sprint (2 tuần) |
| **T**estable | Có tiêu chí Given–When–Then quan sát được, gồm cả trường hợp thiếu nguồn và phân quyền |

## 2. Nhóm story

```text
US01–US05   Cultural Explorer (bản đồ, hồ sơ, bài viết, di sản, tìm kiếm)
US06–US10   AI Cultural Guide (hỏi đáp, trích dẫn, từ chối, ngữ cảnh, đánh giá)
US11        Culture Comparison
US12–US13   Culture Quiz
US14        Báo cáo sai
US15–US19   Trang quản trị (đăng nhập, duyệt, soạn claim, nguồn, độ phủ)
US20        Đồng bộ dữ liệu
```

## 3. Backlog

| ID | User story | Ưu tiên | Ước lượng (SP) | Phụ thuộc |
|---|---|---|---|---|
| US01 | Là **người chuẩn bị đi nước ngoài**, tôi muốn **chọn một quốc gia trên bản đồ** để nhanh chóng mở hồ sơ văn hoá của nước đó. | Must | 5 | — |
| US02 | Là **người học**, tôi muốn **xem hồ sơ quốc gia với thông tin nền và 12 danh mục văn hoá** để biết nên tìm hiểu gì. | Must | 5 | US20 |
| US03 | Là **người học**, tôi muốn **đọc bài viết được tách thành các phát biểu có phạm vi và nguồn** để biết điều nào phổ biến, điều nào chỉ ở một vùng. | Must | 8 | US17 |
| US04 | Là **người yêu văn hoá**, tôi muốn **xem danh sách di sản UNESCO của một quốc gia** để khám phá di sản vật thể và phi vật thể. | Should | 3 | US20 |
| US05 | Là **người học**, tôi muốn **tìm kiếm theo tên quốc gia hoặc chủ đề, kể cả gõ không dấu** để tới nội dung cần thiết nhanh. | Must | 5 | — |
| US06 | Là **người chuẩn bị đi nước ngoài**, tôi muốn **hỏi AI bằng tiếng Việt và nhận câu trả lời dạng streaming** để không phải đọc nhiều trang. | Must | 13 | US03 |
| US07 | Là **người học**, tôi muốn **thấy nguồn cho từng ý trong câu trả lời và xem đoạn trích + giấy phép** để tự kiểm chứng. | Must | 8 | US06 |
| US08 | Là **người học**, tôi muốn **AI nói rõ khi kho dữ liệu chưa đủ nguồn** thay vì đoán, để tôi không bị hiểu sai. | Must | 5 | US06 |
| US09 | Là **người học đang xem trang Nhật Bản**, tôi muốn **AI hiểu câu hỏi của tôi là về Nhật Bản** mà không cần nhắc lại. | Should | 3 | US06 |
| US10 | Là **người học**, tôi muốn **đánh giá 👍/👎 và nhận 2–3 câu hỏi gợi ý** để tiếp tục tìm hiểu và giúp hệ thống cải thiện. | Should | 3 | US06 |
| US11 | Là **người làm việc với đối tác quốc tế**, tôi muốn **so sánh hai quốc gia theo một chủ đề trong bảng có nguồn từng ô** để biết điểm giống và khác. | Must | 13 | US03 |
| US12 | Là **sinh viên**, tôi muốn **làm quiz theo quốc gia, chủ đề và độ khó** để kiểm tra hiểu biết. | Must | 5 | US16 |
| US13 | Là **sinh viên**, tôi muốn **xem giải thích và nguồn ngay sau khi chọn đáp án** để học từ câu sai. | Must | 3 | US12 |
| US14 | Là **người dùng**, tôi muốn **báo cáo một nội dung hoặc câu trả lời sai** để đội biên tập sửa. | Must | 3 | — |
| US15 | Là **biên tập viên**, tôi muốn **đăng nhập và chỉ thấy chức năng đúng vai trò** để làm việc an toàn. | Must | 5 | — |
| US16 | Là **biên tập viên**, tôi muốn **duyệt, sửa hoặc từ chối nội dung do AI sinh** để chỉ nội dung đã kiểm chứng được xuất bản. | Must | 8 | US15 |
| US17 | Là **biên tập viên**, tôi muốn **soạn bài viết, tách claim và gắn nguồn kèm đoạn bằng chứng** để mọi phát biểu truy vết được. | Must | 8 | US15, US18 |
| US18 | Là **biên tập viên**, tôi muốn **quản lý nguồn với giấy phép, độ tin cậy và ngày truy xuất** để đảm bảo pháp lý. | Must | 5 | US15 |
| US19 | Là **biên tập viên**, tôi muốn **xem bảng độ phủ quốc gia × danh mục** để biết cần bổ sung nội dung ở đâu. | Should | 3 | US17 |
| US20 | Là **quản trị viên**, tôi muốn **đồng bộ dữ liệu REST Countries và UNESCO qua worker và xem nhật ký đồng bộ** để dữ liệu nền luôn cập nhật mà không gọi API ngoài trong luồng người dùng. | Must | 8 | — |

**Tổng:** 125 SP · Must: 16 story · Should: 4 story.

## 4. Kiểm tra INVEST chi tiết

| ID | I | N | V | E | S | T | Ghi chú tách nhỏ / rủi ro |
|---|---|---|---|---|---|---|---|
| US01 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Dùng dữ liệu mẫu nếu US20 chưa xong |
| US02 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| US03 | ⚠ | ✅ | ✅ | ✅ | ✅ | ✅ | Cần claim `published` từ US17 — có thể seed thủ công |
| US04 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| US05 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| US06 | ⚠ | ✅ | ✅ | ⚠ | ⚠ | ✅ | 13 SP — tách: (a) retrieval API, (b) LLM adapter + prompt, (c) SSE + UI chat |
| US07 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| US08 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Kiểm thử bằng nhóm “không có đủ nguồn” trong benchmark |
| US09 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| US10 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| US11 | ⚠ | ✅ | ✅ | ⚠ | ⚠ | ✅ | 13 SP — tách: (a) đọc cache đã duyệt, (b) sinh nháp + duyệt |
| US12 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| US13 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| US14 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| US15 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| US16 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| US17 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| US18 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| US19 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | |
| US20 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Bắt đầu với REST Countries + UNESCO WHC |

✅ đạt · ⚠ cần tách nhỏ hoặc có phụ thuộc đã ghi rõ.

## 5. Story sau MVP (Icebox)

| ID | Story |
|---|---|
| US21 | Là người học, tôi muốn giải tình huống “ăn tối tại nhà người Nhật” với lựa chọn và giải thích, để luyện ứng xử. |
| US22 | Là người học, tôi muốn có hộ chiếu văn hoá được đóng dấu khi hoàn thành bộ bài học, để có động lực. |
| US23 | Là người học, tôi muốn AI gợi ý chủ đề tiếp theo dựa trên lịch sử học. |
| US24 | Là giáo viên, tôi muốn xuất bộ quiz cho lớp học. |
