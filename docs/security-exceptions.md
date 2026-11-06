# Ngoại lệ bảo mật đã ghi nhận

Quy tắc chung (CLAUDE.md, [docker-production-skill.md](../docker-production-skill.md) mục 24): **không chấp nhận lỗ hổng CRITICAL**. Mỗi ngoại lệ phải ghi rõ lý do, người chịu trách nhiệm, ngày xem lại, bằng chứng và biện pháp giảm thiểu.

## EX-001 — Object storage dùng MinIO `RELEASE.2025-09-07T16-13-09Z`

| Mục | Nội dung |
|---|---|
| Image | `culture-atlas/object-storage`, build từ `docker.io/phancuong12345/minio@sha256:a16cad48…` (MinIO chính thức `RELEASE.2025-09-07T16-13-09Z`, base Red Hat UBI9-micro) |
| Lý do dùng | Chủ dự án yêu cầu dùng MinIO và cung cấp image này (06/11/2026). MinIO bản cộng đồng đã ngừng phát hành Docker image từ tháng 10/2025 và repo đã bị lưu trữ năm 2026, nên **không còn bản vá** |
| Người chịu trách nhiệm | Chủ dự án (phancuonghphaui) |
| Ngày ghi nhận / xem lại | 06/11/2026 / **06/12/2026** (hoặc sớm hơn nếu đưa ra Internet công khai) |
| Kết quả quét (`scripts/scan-images.sh`, 06/11/2026) | **7 CRITICAL, 77 HIGH** (sau khi đã bỏ `mc`; image gốc là 9 CRITICAL, 127 HIGH) |

### Lỗ hổng CRITICAL còn lại và vì sao chưa khai thác được trong cấu hình hiện tại

| CVE | Thành phần | Điều kiện khai thác | Trạng thái trong CultureAtlas |
|---|---|---|---|
| CVE-2026-33322 | MinIO — nhầm thuật toán JWT trong đăng nhập OIDC | Phải bật OIDC | Không cấu hình OIDC |
| CVE-2026-33419 | MinIO — dò mật khẩu LDAP | Phải bật LDAP | Không cấu hình LDAP |
| CVE-2026-77405/77408/77411 | Thư viện AMQP (RabbitMQ) trong MinIO | Phải cấu hình thông báo sự kiện qua AMQP | Không cấu hình |
| CVE-2026-33186 | gRPC-Go (authz) | Dịch vụ gRPC có chính sách authz | MinIO không mở gRPC ra ngoài |
| CVE-2025-68121 | Go `crypto/tls` — kiểm tra chứng chỉ sai | Kết nối TLS đi ra (client) | MinIO không gọi TLS ra ngoài trong cấu hình này |

Các lỗi HIGH đáng chú ý nhất là **CVE-2026-40344 và CVE-2026-41145** (ghi object không cần xác thực).

### Biện pháp giảm thiểu đang áp dụng

1. **Không mở ra mạng:** cổng S3 (9100) và console (9101) chỉ nghe ở `127.0.0.1`. Bên ngoài chỉ truy cập được qua nginx.
2. **nginx chỉ cho đọc:** `location ^~ /media/` chỉ nhận `GET`/`HEAD`, chặn mọi query string (tham số S3) và xoá header `Authorization`. Lỗi trả về được che thành 404, không để lộ bucket. Đã kiểm thử: `PUT`, `POST`, liệt kê bucket và `?list-type=2` đều bị chặn (06/11/2026).
3. **Quyền tối thiểu:** chính sách bucket `culture-media` chỉ cho `s3:GetObject`, không có `s3:ListBucket`. Bucket `culture-raw` riêng tư.
4. **Hardening container:** chạy bằng uid 10001, root chỉ đọc, `cap_drop: ALL`, `no-new-privileges`, giới hạn 2 CPU / 1 GB / 256 tiến trình. Đã thu hồi `chmod 777 /usr/bin` của image gốc và bỏ binary `mc` (gỡ được 2 CRITICAL và khoảng 50 HIGH).
5. **Thông tin xác thực riêng:** `S3_ACCESS_KEY` và `S3_SECRET_KEY` ngẫu nhiên, nằm trong `.env`, không đưa vào image.

### Phương án thay thế khi xem lại

- **RustFS** (Apache 2.0, thay thế trực tiếp MinIO, chạy không cần root, đang được bảo trì; image `rustfs/rustfs` đã thử chạy tốt với code hiện tại) hoặc **SeaweedFS**.
- Hoặc build MinIO từ mã nguồn cuối cùng với Go và thư viện mới, để vá các lỗi stdlib và thư viện phụ thuộc.
- Code chỉ dùng API S3 chuẩn (thư viện `minio-py`), nên đổi sang bất kỳ storage tương thích S3 nào chỉ cần đổi image và `S3_ENDPOINT`.
