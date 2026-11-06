"""Object storage (S3 / MinIO) cho dữ liệu phi cấu trúc: ảnh, video, âm thanh, tài liệu, payload thô.

Nguyên tắc lưu trữ:
- File nằm ở object storage; PostgreSQL chỉ giữ metadata (bucket, key, loại, kích thước, sha256, giấy phép…) + URL.
- Bucket `culture-media`: media đã xác minh giấy phép mở (BR09) — đọc công khai TỪNG object qua /media/<key>
  (nginx chuyển tới object storage), KHÔNG cho liệt kê bucket.
- Bucket `culture-raw`: payload thô của worker — riêng tư hoàn toàn.
- Khoá object theo nội dung (sha256) → tải lên lại không tạo bản trùng.
"""
from __future__ import annotations

import hashlib
import io
import json
import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path

KIND_BY_MIME = {"image": "image", "video": "video", "audio": "audio"}


@dataclass(frozen=True)
class StorageConfig:
    """Cấu hình object storage S3 (MinIO) đọc từ biến môi trường S3_*."""

    endpoint: str = ""                 # host:port, ví dụ object-storage:9000 (rỗng = không dùng object storage)
    access_key: str = ""
    secret_key: str = ""
    secure: bool = False
    media_bucket: str = "culture-media"
    raw_bucket: str = "culture-raw"
    public_base: str = "/media"        # URL công khai của bucket media (nginx: /media/* → object storage)

    @classmethod
    def from_env(cls) -> StorageConfig:
        """Đọc S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET_*, MEDIA_PUBLIC_BASE."""
        return cls(
            endpoint=os.getenv("S3_ENDPOINT", ""), access_key=os.getenv("S3_ACCESS_KEY", ""),
            secret_key=os.getenv("S3_SECRET_KEY", ""), secure=os.getenv("S3_SECURE", "0") == "1",
            media_bucket=os.getenv("S3_BUCKET_MEDIA", "culture-media"), raw_bucket=os.getenv("S3_BUCKET_RAW", "culture-raw"),
            public_base=os.getenv("MEDIA_PUBLIC_BASE", "/media").rstrip("/"))

    @property
    def enabled(self) -> bool:
        """Đủ endpoint + khoá để kết nối."""
        return bool(self.endpoint and self.access_key and self.secret_key)


@dataclass(frozen=True)
class StoredObject:
    """Kết quả tải lên: vị trí, URL, metadata file — các cột tương ứng của media_assets."""

    bucket: str
    key: str
    url: str                 # URL công khai (bucket media) hoặc s3://bucket/key (bucket riêng tư)
    content_type: str
    size: int
    sha256: str
    kind: str                # image | video | audio | document | data


def kind_of(content_type: str) -> str:
    """Content-type → loại media (image | video | audio | document | data)."""
    major = content_type.split("/", 1)[0]
    if major in KIND_BY_MIME:
        return KIND_BY_MIME[major]
    return "data" if content_type in ("application/json", "text/csv") else "document"


def guess_type(name: str) -> str:
    """Đoán content-type theo đuôi file."""
    return mimetypes.guess_type(name)[0] or "application/octet-stream"


class ObjectStore:
    """Ghi file lên MinIO/S3: bucket media công khai (chỉ GetObject) và bucket raw riêng tư."""

    def __init__(self, cfg: StorageConfig) -> None:
        from minio import Minio
        self.cfg = cfg
        self.client = Minio(cfg.endpoint, access_key=cfg.access_key, secret_key=cfg.secret_key, secure=cfg.secure)
        self._ready = False

    @classmethod
    def from_env(cls) -> ObjectStore | None:
        """ObjectStore theo biến môi trường, None nếu chưa cấu hình."""
        cfg = StorageConfig.from_env()
        return cls(cfg) if cfg.enabled else None

    def ensure_buckets(self) -> None:
        """Tạo bucket nếu chưa có và đặt chính sách chỉ-đọc-từng-object cho bucket media."""
        if self._ready:
            return
        for b in (self.cfg.media_bucket, self.cfg.raw_bucket):
            if not self.client.bucket_exists(b):
                self.client.make_bucket(b)
        # media: chỉ cho đọc từng object (s3:GetObject), không có s3:ListBucket → không liệt kê được bucket
        self.client.set_bucket_policy(self.cfg.media_bucket, json.dumps({
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Principal": {"AWS": ["*"]}, "Action": ["s3:GetObject"],
                           "Resource": [f"arn:aws:s3:::{self.cfg.media_bucket}/*"]}]}))
        self._ready = True

    def public_url(self, key: str) -> str:
        """URL công khai của object trong bucket media (/media/<key>, nginx chuyển tới MinIO)."""
        return f"{self.cfg.public_base}/{key}"

    def put_bytes(self, data: bytes, key: str, *, public: bool, content_type: str | None = None,
                  metadata: dict[str, str] | None = None) -> StoredObject:
        """Tải bytes lên bucket media (`public=True`) hoặc raw; metadata được ép về ASCII."""
        self.ensure_buckets()
        bucket = self.cfg.media_bucket if public else self.cfg.raw_bucket
        ctype = content_type or guess_type(key)
        meta = {k: str(v)[:1024].encode("ascii", "replace").decode() for k, v in (metadata or {}).items() if v}
        self.client.put_object(bucket, key, io.BytesIO(data), len(data), content_type=ctype, metadata=meta)
        url = self.public_url(key) if public else f"s3://{bucket}/{key}"
        return StoredObject(bucket, key, url, ctype, len(data), hashlib.sha256(data).hexdigest(), kind_of(ctype))

    def put_file(self, path: Path, *, public: bool, prefix: str, key: str | None = None,
                 metadata: dict[str, str] | None = None) -> StoredObject:
        """Tải file lên; mặc định khoá theo nội dung: <prefix>/<sha[:2]>/<sha><đuôi> (tải lại không tạo bản trùng)."""
        data = Path(path).read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        key = key or f"{prefix.strip('/')}/{sha[:2]}/{sha}{Path(path).suffix.lower()}"
        return self.put_bytes(data, key, public=public, content_type=guess_type(str(path)), metadata=metadata)

    def exists(self, bucket: str, key: str) -> bool:
        """Object đã tồn tại chưa."""
        from minio.error import S3Error
        try:
            self.client.stat_object(bucket, key)
            return True
        except S3Error:
            return False
