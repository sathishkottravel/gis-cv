"""Needs the docker compose `storage` service running."""
import io
import uuid

import requests
from PIL import Image

from app import config, storage


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(buf, format="PNG")
    return buf.getvalue()


def test_put_then_fetch_over_http():
    key = f"test-{uuid.uuid4().hex}.png"
    data = _png_bytes()
    storage.put(config.SAMPLES_BUCKET, key, data, "image/png")
    try:
        resp = requests.get(storage.url_for(config.SAMPLES_BUCKET, key), timeout=10)
        assert resp.status_code == 200
        assert resp.headers["Content-Type"] == "image/png"
        assert resp.content == data
        assert storage.get(config.SAMPLES_BUCKET, key) == data
    finally:
        storage._client().remove_object(config.SAMPLES_BUCKET, key)
