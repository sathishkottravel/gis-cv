"""Object storage access (RustFS via the generic S3 `minio` client)."""
import io

from minio import Minio

from app import config


def _client() -> Minio:
    return Minio(
        config.STORAGE_ENDPOINT,
        access_key=config.STORAGE_ACCESS_KEY,
        secret_key=config.STORAGE_SECRET_KEY,
        secure=False,
    )


def put(bucket: str, key: str, data: bytes, content_type: str) -> str:
    _client().put_object(bucket, key, io.BytesIO(data), len(data), content_type=content_type)
    return key


def get(bucket: str, key: str) -> bytes:
    resp = _client().get_object(bucket, key)
    try:
        return resp.read()
    finally:
        resp.close()
        resp.release_conn()


def url_for(bucket: str, key: str) -> str:
    """Public URL a browser can load without credentials (buckets are anonymous-read)."""
    return f"{config.STORAGE_PUBLIC_URL}/{bucket}/{key}"
