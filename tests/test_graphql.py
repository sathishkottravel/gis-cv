"""GraphQL API. Needs the docker compose `db` and `storage` services running."""
import base64
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import config, db
from app.main import app

STOP_PNG = (config.ROOT / "samples" / "14_stop.png").read_bytes()
STOP_B64 = base64.b64encode(STOP_PNG).decode()

SIGN_FIELDS = "id classId label confidence lowConfidence lat lng locationSource imageUrl uploadedBy createdAt"
UPLOAD = f"""mutation ($img: String!, $lat: Float, $lng: Float) {{
  uploadSign(imageBase64: $img, lat: $lat, lng: $lng) {{ {SIGN_FIELDS} }}
}}"""
SIGNS = f"""query ($bbox: BBoxInput, $classId: Int) {{
  signs(bbox: $bbox, classId: $classId) {{ {SIGN_FIELDS} }}
}}"""

BOX = {"minLng": 18.100, "minLat": 59.320, "maxLng": 18.110, "maxLat": 59.330}
INSIDE = [(59.322, 18.102), (59.325, 18.105), (59.328, 18.108)]
OUTSIDE = [(59.335, 18.105), (59.325, 18.115)]


@pytest.fixture(scope="module")
def client():
    with TestClient(app, headers={"X-API-Key": config.API_KEY}) as c:
        yield c


def gql(client, query, **variables):
    resp = client.post("/graphql", json={"query": query, "variables": variables})
    assert resp.status_code == 200
    return resp.json()


def norm(signs):
    """REST writes UTC as `Z`, GraphQL as `+00:00`; compare the instants."""
    return [{**s, "createdAt": datetime.fromisoformat(s["createdAt"].replace("Z", "+00:00"))} for s in signs]


def error_code(body):
    return body["errors"][0]["extensions"]["code"]


@pytest.fixture
def bbox_signs():
    ids = []
    for i, (lat, lng) in enumerate(INSIDE + OUTSIDE):
        class_id, label = (14, "Stop") if i % 2 == 0 else (13, "Yield")
        ids.append(db.insert_sign(class_id=class_id, label=label, confidence=0.9, low_conf=False,
                                  loc_source="manual", lat=lat, lng=lng, image_key="test.png",
                                  uploaded_by="test-bbox")["id"])
    yield ids
    for sign_id in ids:
        db.delete_sign(sign_id)


def test_upload_matches_rest_fields(client):
    body = gql(client, UPLOAD, img=STOP_B64, lat=59.329, lng=18.069)
    sign = body["data"]["uploadSign"]
    try:
        rest = client.get("/api/signs", params={"min_lng": 18.0689, "min_lat": 59.3289,
                                                "max_lng": 18.0691, "max_lat": 59.3291})
        same = next(s for s in rest.json() if s["id"] == sign["id"])
        assert norm([sign]) == norm([same])
        assert sign["label"] == "Stop" and sign["uploadedBy"] == "api-key"
        assert sign["locationSource"] == "manual"
    finally:
        db.delete_sign(sign["id"])


def test_sign_types(client):
    types = gql(client, "{ signTypes { classId label } }")["data"]["signTypes"]
    assert len(types) == 43 and {"classId": 14, "label": "Stop"} in types


def test_bbox_filter_matches_rest(client, bbox_signs):
    signs = gql(client, SIGNS, bbox=BOX)["data"]["signs"]
    assert {s["id"] for s in signs} == set(bbox_signs[:3])
    rest = client.get("/api/signs", params={"min_lng": 18.100, "min_lat": 59.320,
                                            "max_lng": 18.110, "max_lat": 59.330}).json()
    assert norm(signs) == norm(rest)


def test_bbox_and_type_filter(client, bbox_signs):
    signs = gql(client, SIGNS, bbox=BOX, classId=14)["data"]["signs"]
    assert {s["id"] for s in signs} == {bbox_signs[0], bbox_signs[2]}
    assert all(s["label"] == "Stop" for s in signs)


def test_upload_without_location(client):
    assert error_code(gql(client, UPLOAD, img=STOP_B64)) == "LOCATION_REQUIRED"


def test_upload_invalid_coordinates(client):
    assert error_code(gql(client, UPLOAD, img=STOP_B64, lat=120.0, lng=18.0)) == "INVALID_COORDINATES"


def test_upload_not_an_image(client):
    junk = base64.b64encode(b"definitely not an image").decode()
    assert error_code(gql(client, UPLOAD, img=junk, lat=59.3, lng=18.0)) == "INVALID_IMAGE"


def test_upload_bad_base64(client):
    assert error_code(gql(client, UPLOAD, img="***not base64***", lat=59.3, lng=18.0)) == "INVALID_IMAGE"


def test_invalid_bbox(client):
    bad = {**BOX, "minLng": 19.0}  # min > max
    assert error_code(gql(client, SIGNS, bbox=bad)) == "INVALID_COORDINATES"


def test_storage_down(client, monkeypatch):
    monkeypatch.setattr(config, "STORAGE_ENDPOINT", "localhost:1")
    before = len(db.query_signs())
    assert error_code(gql(client, UPLOAD, img=STOP_B64, lat=59.3, lng=18.0)) == "STORAGE_UNAVAILABLE"
    assert len(db.query_signs()) == before
