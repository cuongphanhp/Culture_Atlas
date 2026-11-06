# Object storage (S3) cho ảnh / video / file của CultureAtlas.
# Base: image MinIO do chủ dự án cung cấp (phancuong12345/minio = MinIO RELEASE.2025-09-07T16-13-09Z, UBI9-micro), ghim digest.
# Lưu ý: MinIO bản cộng đồng đã ngừng phát hành → bản này không còn được vá; quét định kỳ bằng scripts/scan-images.sh.
ARG MINIO_IMAGE=docker.io/phancuong12345/minio@sha256:a16cad481969d7ddb6fcd2f1c58284af3d1266190b9bedc3ef0801aeb05a93a9
FROM ${MINIO_IMAGE}

# Image gốc đặt `chmod -R 777 /usr/bin` → thu hồi quyền ghi của nhóm/người khác trên binary;
# bỏ client `mc` (không dùng lúc chạy, mang 2 CVE CRITICAL + ~60 HIGH — xem docs/security-exceptions.md);
# /data thuộc uid 10001 để volume mới tạo nhận đúng chủ sở hữu; chạy non-root.
USER root
RUN rm -f /usr/bin/mc /usr/bin/mc.* \
    && chmod -R go-w /usr/bin \
    && mkdir -p /data /tmp/.mc \
    && chown 10001:10001 /data /tmp/.mc
USER 10001:10001
EXPOSE 9000 9001
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=6 \
    CMD ["curl", "-fsS", "http://127.0.0.1:9000/minio/health/live"]
CMD ["minio", "server", "/data", "--address", ":9000", "--console-address", ":9001"]
