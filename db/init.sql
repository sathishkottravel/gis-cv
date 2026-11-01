-- Runs once, on first start of an empty database volume.
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS signs (
  id           SERIAL PRIMARY KEY,
  class_id     INT NOT NULL,
  label        TEXT NOT NULL,
  confidence   REAL NOT NULL,
  low_conf     BOOLEAN NOT NULL,
  loc_source   TEXT NOT NULL CHECK (loc_source IN ('exif', 'manual')),
  geom         GEOMETRY(Point, 4326) NOT NULL,
  image_key    TEXT NOT NULL,          -- object key in the MinIO `signs` bucket
  uploaded_by  TEXT NOT NULL,          -- GitHub login or 'api-key'
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS signs_geom_idx ON signs USING GIST (geom);
