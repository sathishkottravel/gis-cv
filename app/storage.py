"""Object storage access (RustFS via the generic S3 `minio` client)."""
import io

import urllib3
from minio import Minio

from app import config

# Fail fast when storage is down instead of the client's default long retry loop.
_HTTP = urllib3.PoolManager(
    timeout=urllib3.Timeout(connect=3, read=30),
    retries=urllib3.Retry(total=1, backoff_factor=0.2, status_forcelist=[500, 502, 503, 504]),
)


def _client() -> Minio:
    return Minio(
        config.STORAGE_ENDPOINT,
        access_key=config.STORAGE_ACCESS_KEY,
        secret_key=config.STORAGE_SECRET_KEY,
        secure=False,
        http_client=_HTTP,
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
