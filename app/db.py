"""PostGIS access with plain parameterized SQL (psycopg 3)."""
import psycopg
from psycopg.rows import dict_row

from app import config

MAX_RESULTS = 500

# Point construction lives in one place: PostGIS wants (longitude, latitude).
_POINT = "ST_SetSRID(ST_MakePoint(%(lng)s, %(lat)s), 4326)"
_COLUMNS = """id, class_id, label, confidence, low_conf, loc_source,
              ST_Y(geom) AS lat, ST_X(geom) AS lng, image_key, uploaded_by, created_at"""


def _connect() -> psycopg.Connection:
    return psycopg.connect(config.DATABASE_URL, row_factory=dict_row, connect_timeout=5)


def insert_sign(*, class_id: int, label: str, confidence: float, low_conf: bool, loc_source: str,
                lat: float, lng: float, image_key: str, uploaded_by: str) -> dict:
    sql = f"""INSERT INTO signs (class_id, label, confidence, low_conf, loc_source, geom, image_key, uploaded_by)
              VALUES (%(class_id)s, %(label)s, %(confidence)s, %(low_conf)s, %(loc_source)s, {_POINT},
                      %(image_key)s, %(uploaded_by)s)
              RETURNING {_COLUMNS}"""
    params = dict(class_id=class_id, label=label, confidence=confidence, low_conf=low_conf,
                  loc_source=loc_source, lat=lat, lng=lng, image_key=image_key, uploaded_by=uploaded_by)
    with _connect() as conn:
        return conn.execute(sql, params).fetchone()


def query_signs(bbox: tuple[float, float, float, float] | None = None, class_id: int | None = None) -> list[dict]:
    """bbox is (min_lng, min_lat, max_lng, max_lat); newest first, at most 500 rows."""
    where, params = [], {"limit": MAX_RESULTS}
    if bbox is not None:
        where.append("geom && ST_MakeEnvelope(%(min_lng)s, %(min_lat)s, %(max_lng)s, %(max_lat)s, 4326)")
        params.update(zip(("min_lng", "min_lat", "max_lng", "max_lat"), bbox))
    if class_id is not None:
        where.append("class_id = %(class_id)s")
        params["class_id"] = class_id
    sql = f"SELECT {_COLUMNS} FROM signs"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC, id DESC LIMIT %(limit)s"
    with _connect() as conn:
        return conn.execute(sql, params).fetchall()


def delete_sign(sign_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM signs WHERE id = %s", (sign_id,))
