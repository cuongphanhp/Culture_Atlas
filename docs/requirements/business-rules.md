# Quy tắc nghiệp vụ (Business Rules)

| ID | Quy tắc | Áp dụng tại |
|---|---|---|
| BR01 | Mọi phát biểu thực tế hiển thị cho người dùng phải gắn ≥ 1 nguồn, hoặc được đánh dấu rõ “chưa kiểm chứng”. | Claim, AI Guide, Comparison |
| BR02 | Chỉ nội dung `published` được dùng cho truy xuất RAG và hiển thị công khai. | Retrieval, Content API |
| BR03 | Nội dung do AI sinh (quiz, so sánh, tóm tắt) luôn bắt đầu ở trạng thái `draft`. | Admin, Worker |
| BR04 | Vòng đời nội dung: `draft → in_review → published → (flagged) → in_review → published / archived`. | culture_entries, quiz, comparisons |
| BR05 | Mỗi claim có `scope` ∈ {common_practice, historical_tradition, regional, community_specific}; nếu `regional` thì bắt buộc `region`. | Claim |
| BR06 | Khi các nguồn mâu thuẫn, trình bày cả hai quan điểm; không tự chọn một. | Biên tập, prompt AI |
| BR07 | Ô so sánh không đủ bằng chứng hiển thị “Chưa đủ nguồn để kết luận”. | Comparison |
| BR08 | Nguồn bắt buộc có `license`, `retrieved_at`, `source_url`; dữ liệu CC BY-SA phải ghi công và chia sẻ tương tự với phần phái sinh. | Sources, Media |
| BR09 | Media chưa xác minh giấy phép chỉ được liên kết tới nguồn gốc, không sao chép vào object storage. | Media |
| BR10 | Không gọi API bên ngoài trong luồng người dùng; dữ liệu đi qua worker → DB. | Kiến trúc |
| BR11 | Câu hỏi dữ kiện có cấu trúc (thủ đô, ngôn ngữ, tiền tệ) trả lời từ DB, không gọi LLM. | AI Router |
| BR12 | Khách chưa đăng nhập: tối đa 10 lượt hỏi AI / ngày / thiết bị (cấu hình được). | AI API |
| BR13 | Câu hỏi khuôn mẫu hoặc xúc phạm được trả lời theo hướng điều chỉnh nhận thức, có nguồn; chủ đề nhạy cảm trả lời trung lập, dẫn nhiều nguồn. | Guardrail |
| BR14 | Mọi lần xuất bản tạo một bản ghi `entry_revisions` để truy vết. | Admin |
| BR15 | Báo cáo sai được mở ở `open`; ≥ 3 báo cáo cùng nội dung tự động chuyển nội dung sang `flagged`. | Feedback |
| BR16 | Mã quốc gia theo ISO 3166-1 alpha-2; danh mục theo bộ 12 mã cố định. | Toàn hệ thống |
