# Proposal

## Why

This is a small learning project that brings computer vision, a GIS database, REST + GraphQL APIs and OAuth login together in one app. A user signs in with GitHub, uploads a photo of a traffic sign, and the app recognizes the sign and places it on a map. The build budget is about 4 hours, so the scope is deliberately minimal.

## What Changes

- New greenfield app "Sign Spotter Map" (the repo currently holds only OpenSpec scaffolding). It is built in this order: Docker services, sample images, the REST upload API, Swagger docs, GraphQL, then the frontend with GitHub login.
- Docker Compose runs PostGIS and RustFS (S3-compatible object storage; official MinIO images are no longer published). The API runs locally with Python.
- Sample images: a script downloads the public GTSRB (German Traffic Sign Recognition Benchmark) test set and registers about 20 sign photos (one per class) plus a manifest in a RustFS `samples` bucket. A seed script uploads them through the REST API at preset coordinates.
- Traffic sign classification of an uploaded image using a pretrained GTSRB model. No training happens in this project.
- Location capture: the app reads GPS coordinates from the photo's EXIF metadata, or falls back to coordinates in the request (a click on the map in the UI).
- Each recognized sign is stored as a PostGIS `POINT` (SRID 4326) with its label, confidence, uploader and timestamp. The original image goes to RustFS and is exposed as `imageUrl`.
- REST API: `POST /api/signs` (file upload), `GET /api/signs`, `GET /api/sign-types` and `GET /api/samples`, with interactive Swagger docs at `/docs`.
- GraphQL API at `/graphql`, built on the same service layer: an `uploadSign` mutation and the `signs(bbox, classId)` and `signTypes` queries.
- GitHub OAuth login. Uploads require a signed-in user (or a dev API key, used by scripts and Swagger). Viewing signs stays public.
- The map and seed data are centred on Stockholm, Sweden. Sample images are GTSRB (German/European signs); no Swedish sign dataset is downloadable.
- A single-page web UI: GitHub sign-in/sign-out, an upload form shown only when signed in, and a Leaflet map with pins, image-thumbnail popups and a type filter.

Out of scope: user roles or permissions beyond "signed in", login providers other than GitHub, model training or fine-tuning, multiple signs per image (no object detection), editing or deleting signs, production deployment.

## Capabilities

### New Capabilities
- `sign-recognition`: classify a single uploaded traffic sign image into a sign type with a confidence score.
- `sign-locations`: store recognized signs as geographic points with their original image, expose them through REST (with Swagger docs) and GraphQL, and manage sample images.
- `user-auth`: GitHub sign-in/sign-out, the current-user endpoint, and authentication for uploads (session or dev API key).
- `sign-map-ui`: a browser page for signing in, uploading a sign photo and viewing stored signs on a map.

### Modified Capabilities
<!-- None: no existing specs. -->

## Impact

- New code: a Python backend (FastAPI with REST routes, Strawberry GraphQL and OAuth routes over a shared service layer), a static HTML/JS frontend, sample fetch and seed scripts, and `docker-compose.yml`.
- New dependencies: PostgreSQL + PostGIS, RustFS + `bitnamilegacy/minio-client` for bucket setup (Docker images), `minio` (generic S3 Python client), `torch`/`torchvision`/`transformers`, `huggingface_hub` + `pyarrow` (GTSRB mirror `tanganke/gtsrb`), `Pillow`, `psycopg` (v3, plain SQL), `python-multipart` (REST uploads), `Authlib` + `itsdangerous` (GitHub OAuth and session cookie), Leaflet (CDN).
- External setup: the developer creates a GitHub OAuth App (callback `http://localhost:8000/auth/callback`) and puts its client ID and secret in `.env`.
- The model weights (Hugging Face) and the GTSRB test set (~110 MB, Hugging Face mirror) are downloaded on first use, which needs network access once.
