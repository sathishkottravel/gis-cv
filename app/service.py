"""Business logic shared by the REST and GraphQL adapters."""
import uuid

from app import classifier, config, db, storage
from app.errors import InvalidCoordinates, LocationRequired, StorageUnavailable
from app.geo import extract_gps
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


def list_signs(bbox: tuple[float, float, float, float] | None = None, class_id: int | None = None) -> list[dict]:
    return [_to_sign(row) for row in db.query_signs(bbox, class_id)]
