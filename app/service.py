"""Business logic shared by the REST and GraphQL adapters."""
import json
import uuid

from app import classifier, config, db, storage
from app.errors import InvalidCoordinates, LocationRequired, StorageUnavailable
from app.geo import extract_gps
from app.labels import LABELS
from app.images import load_image

_EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png"}


def _to_sign(row: dict) -> dict:
    sign = dict(row)
    sign["image_url"] = storage.url_for(config.SIGNS_BUCKET, sign.pop("image_key"))
    return sign


def _resolve_location(img, lat: float | None, lng: float | None) -> tuple[float, float, str]:
    gps = extract_gps(img)
    if gps is not None:
        return gps[0], gps[1], "exif"
    if lat is None and lng is None:
        raise LocationRequired("No location: the photo has no GPS data. Choose a location on the map.")
    if lat is None or lng is None:
        raise InvalidCoordinates("Both latitude and longitude are required.")
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise InvalidCoordinates("Latitude must be within -90..90 and longitude within -180..180.")
    return lat, lng, "manual"


def create_sign(image_bytes: bytes, lat: float | None, lng: float | None, uploaded_by: str) -> dict:
    """Validate, classify, locate, store the image, then record the sign."""
    img, content_type = load_image(image_bytes)
    pred = classifier.predict(img)
    lat, lng, loc_source = _resolve_location(img, lat, lng)

    key = f"{uuid.uuid4().hex}.{_EXTENSIONS[content_type]}"
    try:
        storage.put(config.SIGNS_BUCKET, key, image_bytes, content_type)
    except Exception as exc:
        raise StorageUnavailable("Image storage is unavailable; the sign was not saved.") from exc

    row = db.insert_sign(class_id=pred.class_id, label=pred.label, confidence=pred.confidence,
                         low_conf=pred.low_conf, loc_source=loc_source, lat=lat, lng=lng,
                         image_key=key, uploaded_by=uploaded_by)
    return _to_sign(row)


def make_bbox(min_lng: float | None, min_lat: float | None,
              max_lng: float | None, max_lat: float | None) -> tuple[float, float, float, float] | None:
    """Return a bbox tuple, None if no bound is given, or raise if only some are given or they are invalid."""
    bounds = (min_lng, min_lat, max_lng, max_lat)
    if all(b is None for b in bounds):
        return None
    if any(b is None for b in bounds):
        raise InvalidCoordinates("Give all four bounding box values (min_lng, min_lat, max_lng, max_lat) or none.")
    if not (-180 <= min_lng <= max_lng <= 180 and -90 <= min_lat <= max_lat <= 90):
        raise InvalidCoordinates("Bounding box must have min <= max, longitudes within -180..180 and latitudes within -90..90.")
    return bounds


def list_signs(bbox: tuple[float, float, float, float] | None = None, class_id: int | None = None) -> list[dict]:
    """Newest first, capped at 500; bbox is (min_lng, min_lat, max_lng, max_lat)."""
    return [_to_sign(row) for row in db.query_signs(bbox, class_id)]


def list_sign_types() -> list[dict]:
    return [{"class_id": i, "label": label} for i, label in enumerate(LABELS)]


def list_samples() -> list[dict]:
    """Manifest entries from the samples bucket, each with a public URL."""
    try:
        manifest = json.loads(storage.get(config.SAMPLES_BUCKET, "manifest.json"))
    except Exception as exc:
        raise StorageUnavailable("Sample manifest could not be read from object storage.") from exc
    return [{"file": e["file"], "class_id": e["classId"], "label": e["label"],
             "url": storage.url_for(config.SAMPLES_BUCKET, e["file"])} for e in manifest]
