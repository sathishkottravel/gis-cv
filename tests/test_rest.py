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


# --- Read endpoints (task group 4) ---------------------------------------

# A small box in central Stockholm (Djurgården side), away from the seed grid.
BOX = {"min_lng": "18.100", "min_lat": "59.320", "max_lng": "18.110", "max_lat": "59.330"}
INSIDE = [(59.322, 18.102), (59.325, 18.105), (59.328, 18.108)]
OUTSIDE = [(59.335, 18.105), (59.325, 18.115)]


@pytest.fixture
def bbox_signs():
    ids = []
    for i, (lat, lng) in enumerate(INSIDE + OUTSIDE):
        class_id, label = (14, "Stop") if i % 2 == 0 else (13, "Yield")
        row = db.insert_sign(class_id=class_id, label=label, confidence=0.9, low_conf=False,
                             loc_source="manual", lat=lat, lng=lng, image_key="test.png",
                             uploaded_by="test-bbox")
        ids.append(row["id"])
    yield ids
    for sign_id in ids:
        db.delete_sign(sign_id)


def test_bbox_returns_only_inside(client, bbox_signs):
    resp = client.get("/api/signs", params=BOX)
    assert resp.status_code == 200
    got = {s["id"] for s in resp.json()}
    assert got == set(bbox_signs[:3])


def test_bbox_combines_with_type_filter(client, bbox_signs):
    resp = client.get("/api/signs", params={**BOX, "class_id": 14})
    assert resp.status_code == 200
    signs = resp.json()
    assert {s["id"] for s in signs} == {bbox_signs[0], bbox_signs[2]}
    assert all(s["label"] == "Stop" for s in signs)


def test_list_without_bbox_is_public_and_newest_first(client, bbox_signs):
    resp = client.get("/api/signs")
    assert resp.status_code == 200
    signs = resp.json()
    assert set(bbox_signs) <= {s["id"] for s in signs}
    times = [s["createdAt"] for s in signs]
    assert times == sorted(times, reverse=True)


def test_partial_bbox_is_422(client):
    resp = client.get("/api/signs", params={"min_lng": "18.0", "min_lat": "59.3"})
    assert resp.status_code == 422
    assert resp.json()["code"] == "INVALID_COORDINATES"


def test_sign_types(client):
    types = client.get("/api/sign-types").json()
    assert len(types) == 43
    assert {"classId": 14, "label": "Stop"} in types


def test_samples_have_working_urls(client):
    resp = client.get("/api/samples")
    assert resp.status_code == 200
    samples = resp.json()
    assert len(samples) >= 20
    for s in samples:
        assert set(s) == {"file", "classId", "label", "url"}
        image = requests.get(s["url"], timeout=10)
        assert image.status_code == 200 and image.headers["Content-Type"] == "image/png"


def test_openapi_lists_endpoints_and_api_key(client):
    spec = client.get("/openapi.json").json()
    paths = spec["paths"]
    assert {"post", "get"} <= set(paths["/api/signs"])
    assert "get" in paths["/api/sign-types"] and "get" in paths["/api/samples"]
    assert spec["components"]["securitySchemes"]["APIKeyHeader"] == {
        "type": "apiKey", "in": "header", "name": "X-API-Key",
        "description": "Dev API key (`API_KEY` in `.env`) for scripts and Swagger."}
    assert paths["/api/signs"]["post"]["security"] == [{"APIKeyHeader": []}]
    assert "security" not in paths["/api/signs"]["get"]
