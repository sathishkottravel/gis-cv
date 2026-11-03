"""Needs the docker compose `db` and `storage` services running."""
import pytest
import requests
from fastapi.testclient import TestClient

from app import config, db
from app.main import app

STOP_PNG = (config.ROOT / "samples" / "14_stop.png").read_bytes()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # runs the lifespan, which loads the model
        yield c


def _upload(client, data, **form):
    return client.post("/api/signs", files={"file": ("sign.png", data, "image/png")}, data=form)


def test_upload_with_coordinates(client):
    resp = _upload(client, STOP_PNG, lat="59.329", lng="18.069")
    assert resp.status_code == 201
    sign = resp.json()
    try:
        assert sign["label"] == "Stop" and sign["classId"] == 14
        assert sign["locationSource"] == "manual" and sign["uploadedBy"] == "api-key"
        assert sign["lat"] == pytest.approx(59.329) and sign["lng"] == pytest.approx(18.069)
        image = requests.get(sign["imageUrl"], timeout=10)
        assert image.status_code == 200 and image.headers["Content-Type"] == "image/png"
    finally:
        db.delete_sign(sign["id"])


def test_upload_without_location_is_422(client):
    resp = _upload(client, STOP_PNG)
    assert resp.status_code == 422
    assert resp.json()["code"] == "LOCATION_REQUIRED"


def test_non_image_is_400(client):
    resp = _upload(client, b"definitely not an image", lat="59.3", lng="18.0")
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_IMAGE"


def test_invalid_coordinates_is_422(client):
    resp = _upload(client, STOP_PNG, lat="120", lng="18.0")
    assert resp.status_code == 422
    assert resp.json()["code"] == "INVALID_COORDINATES"
