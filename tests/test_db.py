"""Needs the docker compose `db` service running."""
import uuid

import pytest

from app import db

STOCKHOLM = (59.329, 18.069)


def _insert(lat, lng, class_id=14):
    return db.insert_sign(class_id=class_id, label="Stop", confidence=0.9, low_conf=False,
                          loc_source="manual", lat=lat, lng=lng,
                          image_key=f"test-{uuid.uuid4().hex}.png", uploaded_by="test")


def test_lat_lng_round_trip():
    row = _insert(*STOCKHOLM)
    try:
        assert row["lat"] == pytest.approx(59.329)
        assert row["lng"] == pytest.approx(18.069)
        bbox = (18.06, 59.32, 18.08, 59.34)  # (min_lng, min_lat, max_lng, max_lat)
        found = [r for r in db.query_signs(bbox) if r["id"] == row["id"]]
        assert found and found[0]["lat"] == pytest.approx(59.329) and found[0]["lng"] == pytest.approx(18.069)
    finally:
        db.delete_sign(row["id"])


def test_bbox_and_class_filter():
    inside = _insert(59.33, 18.07, class_id=13)
    outside = _insert(57.707, 11.967, class_id=13)  # Gothenburg
    try:
        ids = {r["id"] for r in db.query_signs((18.0, 59.3, 18.1, 59.4), class_id=13)}
        assert inside["id"] in ids and outside["id"] not in ids
        assert all(r["class_id"] == 13 for r in db.query_signs(class_id=13))
    finally:
        db.delete_sign(inside["id"])
        db.delete_sign(outside["id"])
