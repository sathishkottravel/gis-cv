# Design

## Context

This is a greenfield project: `E:\Tut\vision` contains only OpenSpec scaffolding. It is developed on Windows 10 with a build budget of about 4 hours, and the user set the implementation order: Docker services, sample images in RustFS, the REST upload API, Swagger, GraphQL, then the frontend with GitHub login. Motivation and scope are in proposal.md; behavior is defined in `specs/sign-recognition`, `specs/sign-locations`, `specs/user-auth` and `specs/sign-map-ui`.

## Goals / Non-Goals

**Goals:**
- One Python process serves REST, GraphQL, the OAuth routes and the static UI (same origin, so there is no CORS setup and the session cookie just works).
- REST and GraphQL are thin adapters over one service layer, so behavior can't drift between them.
- PostGIS and RustFS run in Docker. The DB schema and the buckets are created automatically on first start.
- Inference uses a pretrained model as-is, on CPU.

**Non-Goals:**
- No ORM, migrations framework or frontend build step (no npm).
- No users table or roles. Identity is the GitHub login stored in the session and in `signs.uploaded_by`.
- No GPU support, batching or async inference queue.

## Decisions

### Layout
```
vision/
  docker-compose.yml        # db (postgis, :5433), storage (RustFS: :9000 S3, :9001 console), storage-init (mc)
  .env.example              # DB/storage creds, GITHUB_CLIENT_ID/SECRET, SESSION_SECRET, API_KEY
  db/init.sql               # signs table + GiST index (mounted into docker-entrypoint-initdb.d)
  app/
    main.py                 # FastAPI app: middleware, routers, /graphql, static at /
    service.py              # create_sign / list_signs / list_samples + domain errors
    rest.py                 # /api/* routes (Pydantic models -> OpenAPI/Swagger)
    schema.py               # Strawberry types, Query, Mutation (call service.py)
    auth.py                 # GitHub OAuth routes (/auth/*), current_user(), require_uploader()
    classifier.py           # model load (once) + predict(image)
    geo.py                  # EXIF GPS extraction
    db.py                   # psycopg connection + insert/query
    storage.py              # S3 client (`minio` package): put/get objects, url_for(bucket, key)
    labels.py               # 43 GTSRB class names
  scripts/
    fetch_samples.py        # GTSRB test set -> RustFS `samples` bucket (+ local samples/ copy)
    seed.py                 # samples from RustFS -> POST /api/signs with X-API-Key
  static/index.html         # Leaflet map + login bar + upload form, vanilla JS
  requirements.txt
  README.md
```

### Service layer shared by REST and GraphQL
`service.create_sign(image_bytes, lat, lng, uploaded_by) -> SignDTO` handles everything in order: validate image, then classify, then resolve location (EXIF first, then request coordinates, otherwise `LocationRequired`), then store the image in RustFS (`StorageUnavailable` on failure), then insert the row. The domain errors are `InvalidImage`, `LocationRequired`, `InvalidCoordinates` and `StorageUnavailable`. REST maps them to HTTP 400, 422, 422 and 503. GraphQL maps them to error `extensions.code` values (`INVALID_IMAGE`, `LOCATION_REQUIRED`, `INVALID_COORDINATES`, `STORAGE_UNAVAILABLE`). If the insert fails after the image is stored, an orphan object is left behind. That's accepted for a demo.

### REST API + Swagger: FastAPI routes
- `POST /api/signs` (multipart: `file: UploadFile`, `lat: float | None`, `lng: float | None`) returns 201 with a `Sign` model.
- `GET /api/signs?min_lng&min_lat&max_lng&max_lat&class_id` returns `list[Sign]`. The four bbox params must be given all together or not at all, otherwise 422.
- `GET /api/sign-types` returns `list[SignType]`. `GET /api/samples` returns `list[Sample]` (file, classId, label, url).
- FastAPI generates OpenAPI from the Pydantic models. Swagger UI at `/docs` comes for free. The app gets a title, a description and tags (`signs`, `samples`). An `APIKeyHeader("X-API-Key")` security scheme is declared on the upload route, so Swagger shows an "Authorize" button.
- Multipart (not base64) is used here because it is the natural REST/Swagger upload form: Swagger renders a file picker. It needs `python-multipart`.

### GraphQL: Strawberry on FastAPI
`GraphQLRouter` at `/graphql` (GraphiQL included). It offers `uploadSign(imageBase64: String!, lat: Float, lng: Float)`, `signs(bbox: BBoxInput, classId: Int)` and `signTypes`. The Strawberry context carries the `Request`, so the mutation can use the same `require_uploader` check. Base64 is used for the GraphQL upload so the frontend sends plain JSON without the GraphQL multipart spec. The 10 MB limit applies to the decoded bytes. Alternatives: Graphene (more boilerplate) and Ariadne (schema-first).

### Authentication: GitHub OAuth with Authlib + signed session cookie
- The developer registers a GitHub OAuth App (homepage `http://localhost:8000`, callback `http://localhost:8000/auth/callback`). Its ID and secret go in `.env`.
- Starlette `SessionMiddleware` (`itsdangerous`, `SESSION_SECRET`, `same_site="lax"`, `https_only=False` for localhost) and the Authlib Starlette client with GitHub endpoints and scope `read:user`.
- Routes: `/auth/login` redirects to GitHub (Authlib stores and checks `state`). `/auth/callback` exchanges the code, calls `GET https://api.github.com/user` and stores `{login, avatar_url}` in the session; on error it redirects to `/?auth_error=1`. `/auth/logout` clears the session and redirects. `/auth/me` returns `{user: {...} | null}`.
- `require_uploader(request)` returns the session login, or `"api-key"` if `X-API-Key` matches `API_KEY` (compared with `secrets.compare_digest`). Otherwise it raises 401, or `AUTH_REQUIRED` in GraphQL. If `API_KEY` is unset, API key auth is disabled.
- Only uploads are guarded. Reads stay public, per the spec.
- Alternatives: JWT bearer tokens (would need token storage in the frontend and refresh logic), or `fastapi-users` (heavy for one provider). A server-side session cookie is the least code for a same-origin app.

### Build order and the auth guard
Uploads are built in group 3 but auth arrives in group 6. To avoid rework, `rest.py` and `schema.py` call a `get_uploader` dependency from the start. Until group 6 it is a stub that returns `"api-key"`. Group 6 replaces the stub with `require_uploader` and adds the 401 tests. The seed script sends `X-API-Key` from day one, so it keeps working after the guard lands.

### Classifier: pretrained GTSRB model from Hugging Face
`transformers` `pipeline("image-classification", model=...)`, loaded once at startup. The first candidate is `bazyl/gtsrb-model` (ViT, 43 classes). Its output is mapped to `labels.py`, because some checkpoints only output `LABEL_n`. If it fails, the fallback is a small CNN trained on `torchvision.datasets.GTSRB` for 3–5 epochs on CPU (~10–15 min), saved as `model.pt`, with the same `predict()` interface. A confidence below 0.5 sets `low_conf`.

### Database: PostGIS + plain psycopg 3
```sql
CREATE TABLE signs (
  id           SERIAL PRIMARY KEY,
  class_id     INT NOT NULL,
  label        TEXT NOT NULL,
  confidence   REAL NOT NULL,
  low_conf     BOOLEAN NOT NULL,
  loc_source   TEXT NOT NULL CHECK (loc_source IN ('exif','manual')),
  geom         GEOMETRY(Point, 4326) NOT NULL,
  image_key    TEXT NOT NULL,          -- object key in the RustFS `signs` bucket
  uploaded_by  TEXT NOT NULL,          -- GitHub login or 'api-key'
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX signs_geom_idx ON signs USING GIST (geom);
```
- Insert: `ST_SetSRID(ST_MakePoint(lng, lat), 4326)`. Note the longitude-first order, kept in one helper.
- Query: `WHERE geom && ST_MakeEnvelope(minLng, minLat, maxLng, maxLat, 4326) [AND class_id = %s] ORDER BY created_at DESC LIMIT 500`. Lat/lng are read back via `ST_Y`/`ST_X`.
- Parameterized queries only. There are two queries, so no ORM.

### Object storage: RustFS (S3-compatible) in Docker
- MinIO was the original choice, but its official images (`minio/minio`, `minio/mc`) are no longer published on Docker Hub or quay.io. RustFS is a MinIO-like S3 server with a web console, and the user picked it over the frozen Bitnami legacy MinIO images and SeaweedFS.
- `storage` (`rustfs/rustfs:1.0.3`, `RUSTFS_ACCESS_KEY`/`RUSTFS_SECRET_KEY` from `.env`, `RUSTFS_CONSOLE_ENABLE=true`, S3 on :9000, console at http://localhost:9001/rustfs/console/, named volume) and a one-shot `storage-init` (`bitnamilegacy/minio-client:2025.7.21`; `mc` works against any S3 server) that runs `mb -p local/signs local/samples` and `anonymous set download` on both buckets. Browsers can read the objects but not write them: anonymous PUT is refused with 403.
- The app talks to it through the `minio` Python package, which is a generic S3 client. RustFS supports only path-style addressing unless `RUSTFS_SERVER_DOMAINS` is set, which is what that client uses by default.
- `storage.py`: `put(bucket, key, bytes, content_type)`, `get(bucket, key)` and `url_for(bucket, key)` built as `${STORAGE_PUBLIC_URL}/<bucket>/<key>` (default `http://localhost:9000`). Uploaded images use the key `<uuid4>.<jpg|png>`, and only the key is stored in the DB.
- Alternatives: a local folder served by FastAPI, or Postgres `bytea`. Both were rejected earlier in favour of a real storage service.

### Sample images: GTSRB test set → RustFS
- `scripts/fetch_samples.py`: `torchvision.datasets.GTSRB(root="data", split="test", download=True)` (~90 MB, no key). It keeps the first image of each class until it has 20+ classes (always including Stop (14), Yield (13), Speed limit 50 (2) and No entry (17)), upscales each to at least 128 px and converts from PPM to PNG (the upload validation accepts only JPEG/PNG). Each image goes to `samples/<classId>_<slug>.png` in RustFS, and a `manifest.json` object holds `[{file, classId, label}]`. It also writes a local `samples/` copy so the user can pick files in the UI's file picker. The script is idempotent: it overwrites existing objects.
- `scripts/seed.py`: reads `manifest.json` from RustFS, downloads each object and sends `POST /api/signs` (multipart, `X-API-Key`) at grid coordinates around Munich centre (48.137, 11.575, about 150 m apart), then prints how many predictions matched the expected class. That doubles as an accuracy check.

### EXIF GPS
Pillow: `img.getexif().get_ifd(0x8825)`. Degree/minute/second rationals are converted to decimal degrees, negated for `S`/`W`. Any parse failure is treated as "no GPS".

### UI: one static HTML file
Leaflet 1.9.4 from a CDN with OSM tiles, centered on Munich. On load it calls `fetch('/auth/me')` to render the login bar ("Sign in with GitHub" link to `/auth/login`, or avatar + login + "Sign out" link to `/auth/logout`) and shows a message if `?auth_error=1` is in the URL. The upload form is shown only when signed in. The frontend uses GraphQL for its data (`signs` on `moveend`, `signTypes` for the filter, `uploadSign` for uploads), and the same-origin session cookie is sent automatically. REST is for scripts and Swagger. Popups show `<img src=imageUrl width=96>`, the label, confidence, uploader and time.

## Risks / Trade-offs

- [The pretrained checkpoint is missing, broken or mislabeled] → It is checked first in group 3, with the torchvision CNN as a fallback behind the same interface.
- [Real-world photos aren't tightly cropped like GTSRB] → Show confidence and the low-confidence flag. The README advises cropping to the sign.
- [GitHub OAuth App misconfigured (wrong callback URL), so login fails] → The README gives the exact App settings. The callback redirects to `/?auth_error=1`, and the UI shows a message instead of failing silently.
- [OAuth secrets leak into git] → `.env` is git-ignored, with only `.env.example` committed.
- [Session cookie without HTTPS] → Acceptable on localhost only. `https_only` is noted in the README as required for any deployment (out of scope).
- [A dev API key is a shared secret that bypasses GitHub login] → It is opt-in through `API_KEY` and disabled if unset. Uploads with it are recorded as `uploaded_by = 'api-key'`.
- [The buckets are missing or not public, so thumbnails and samples break] → `storage-init` runs on every `compose up` (`mb -p` is idempotent). The README includes a `curl -I` check.
- [Anyone on the LAN can read images from the anonymous-read buckets] → Acceptable for a local demo. Writes go only through credentials.
- [The GTSRB download fails] → It's a one-time ~90 MB download cached under `data/`. Any PNG/JPEG sign photos plus a hand-written manifest uploaded to the bucket work with `seed.py` unchanged.
- [Mixing up lat/lng order] → One helper, and a test asserts the coordinates round-trip.
- [A ~4 h budget is at risk if the model fallback is needed (+15 min)] → The fallback has a fixed timebox. If time runs short, the GraphQL upload mutation can be dropped (the UI would then use REST), since uploads already work over REST.

## Migration Plan

Not applicable (greenfield). To start: copy `.env.example` to `.env` and fill in the GitHub App and secrets, then `docker compose up -d`, then `pip install -r requirements.txt`, then `python scripts/fetch_samples.py`, then `uvicorn app.main:app --reload`, then `python scripts/seed.py`, then open http://localhost:8000 (Swagger at `/docs`, GraphiQL at `/graphql`, RustFS console at http://localhost:9001/rustfs/console/).
