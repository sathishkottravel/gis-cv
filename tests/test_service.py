"""Needs the docker compose `db` and `storage` services running."""
import pytest
import requests

from app import config, db, service
from app.errors import InvalidCoordinates, LocationRequired, StorageUnavailable

STOP_PNG = (config.ROOT / "samples" / "14_stop.png").read_bytes()


def _count() -> int:
    return len(db.query_signs())


def test_create_sign_with_coordinates():
    sign = service.create_sign(STOP_PNG, 59.329, 18.069, "test")
    try:
        assert sign["label"] == "Stop" and sign["loc_source"] == "manual"
        assert sign["lat"] == pytest.approx(59.329) and sign["lng"] == pytest.approx(18.069)
        assert requests.get(sign["image_url"], timeout=10).status_code == 200
    finally:
        db.delete_sign(sign["id"])


def test_no_location_raises_location_required():
    before = _count()
    with pytest.raises(LocationRequired):
        service.create_sign(STOP_PNG, None, None, "test")
    assert _count() == before


def test_out_of_range_coordinates_rejected():
    with pytest.raises(InvalidCoordinates):
        service.create_sign(STOP_PNG, 120, 18.0, "test")


def test_storage_failure_inserts_no_row(monkeypatch):
    monkeypatch.setattr(config, "STORAGE_ENDPOINT", "localhost:1")  # nothing listens here
    before = _count()
    with pytest.raises(StorageUnavailable):
        service.create_sign(STOP_PNG, 59.329, 18.069, "test")
    assert _count() == before
