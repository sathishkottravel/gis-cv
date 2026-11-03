# Sign Spotter Map (gis-cv)

A small computer-vision + GIS demo: sign in with GitHub, upload a traffic sign photo, have it classified by a pretrained GTSRB model, and see it as a pin on a map.

**Stack:** FastAPI (REST + Swagger) · Strawberry GraphQL · PostGIS · RustFS (S3-compatible storage) · Hugging Face / PyTorch · Leaflet · GitHub OAuth

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/), running
- Python 3.11+ (with [uv](https://docs.astral.sh/uv/), uv can download it for you)

## Setup

```bash
# 1. Configuration: copy the template, then change the secrets in .env
cp .env.example .env

# 2. Start PostGIS and RustFS (also creates the `signs` and `samples` buckets)
docker compose up -d
docker compose ps -a        # db and storage "running", storage-init "exited (0)"

# 3. Python environment
uv venv --python 3.11 .venv
uv pip install -r requirements.txt
```

The first `uv pip install` downloads PyTorch (several hundred MB).

## Sample images

```bash
.venv/Scripts/python scripts/fetch_samples.py      # Windows; use .venv/bin/python on macOS/Linux
```

This downloads the GTSRB test set from the Hugging Face mirror [`tanganke/gtsrb`](https://huggingface.co/datasets/tanganke/gtsrb). It's a one-time download of about 110 MB, cached in `data/gtsrb/`. The script picks 20 signs (one per class, including Stop, Yield, No entry and Speed limit 50) and uploads them as PNGs plus a `manifest.json` to the `samples` bucket. It also writes a local copy to `samples/` that you can pick in the upload form. Rerunning it is safe: existing files are overwritten.

Check: http://localhost:9000/samples/14_stop.png shows a stop sign, and http://localhost:9000/samples/manifest.json lists all 20 files.

## Run the API

```bash
.venv/Scripts/python -m uvicorn app.main:app --reload     # http://localhost:8000
```

The first start downloads the pretrained classifier [`bazyl/gtsrb-model`](https://huggingface.co/bazyl/gtsrb-model) (about 350 MB, cached by Hugging Face). To check it against the samples, run `.venv/Scripts/python scripts/check_classifier.py` (it expects at least 16 of 20 correct).

Upload a sign:

```bash
curl -F file=@samples/14_stop.png -F lat=59.329 -F lng=18.069 http://localhost:8000/api/signs
```

This returns `201` with the sign as JSON, including `label`, `confidence` and an `imageUrl`. Errors return `{"detail", "code"}`:

| Code | HTTP | Cause |
|---|---|---|
| `INVALID_IMAGE` | 400 | not a JPEG/PNG, or larger than 10 MB |
| `LOCATION_REQUIRED` | 422 | no EXIF GPS and no `lat`/`lng` |
| `INVALID_COORDINATES` | 422 | `lat`/`lng` out of range, or only one of them given |
| `STORAGE_UNAVAILABLE` | 503 | object storage is down (nothing is saved) |

Seed the map with the 20 samples on a grid around central Stockholm (the API must be running):

```bash
.venv/Scripts/python scripts/seed.py
```

### Read endpoints (public)

| Endpoint | Returns |
|---|---|
| `GET /api/signs` | signs, newest first, max 500. Optional `min_lng`, `min_lat`, `max_lng`, `max_lat` (all four or none, otherwise `422`) and `class_id` |
| `GET /api/sign-types` | the 43 GTSRB classes as `{classId, label}` |
| `GET /api/samples` | the registered samples as `{file, classId, label, url}` |

```bash
curl "http://localhost:8000/api/signs?min_lng=18.06&min_lat=59.32&max_lng=18.08&max_lat=59.34&class_id=14"
```

## Swagger (interactive REST docs)

Open http://localhost:8000/docs while the API is running. All four endpoints are listed under the `signs` and `samples` tags; the raw spec is at http://localhost:8000/openapi.json.

To upload from Swagger:

1. Click **Authorize**, enter the `API_KEY` value from your `.env` under `APIKeyHeader (apiKey)`, then click **Authorize** and **Close**. (Uploads only check the key once GitHub login lands in task group 6; reads never need it.)
2. Open `POST /api/signs` and click **Try it out**.
3. Choose `samples/14_stop.png` as `file`, set `lat` = `59.329` and `lng` = `18.069`, and click **Execute**.
4. The response is `201` with the sign JSON (`"label": "Stop"`). Swagger also shows the equivalent `curl` command, including the `X-API-Key` header.

## Tests

```bash
.venv/Scripts/python -m pytest      # needs docker compose services and fetched samples
```

## Services

| Service | URL | Notes |
|---|---|---|
| PostGIS | `localhost:5433` | database `signs`, user/password from `.env` |
| S3 API (RustFS) | http://localhost:9000 | buckets `signs` and `samples` are publicly readable, not writable |
| RustFS console | http://localhost:9001/rustfs/console/ | log in with `STORAGE_ACCESS_KEY` / `STORAGE_SECRET_KEY` |

Quick checks:

```bash
docker compose exec db psql -U postgres -d signs -c "\d signs"   # table + signs_geom_idx
curl -I http://localhost:9000/samples/missing.png                  # 404 = bucket exists and is public
```

To reset all data: `docker compose down -v && docker compose up -d`.

## Plan

The full plan lives in [`openspec/changes/add-sign-spotter-map/`](openspec/changes/add-sign-spotter-map/): [proposal](openspec/changes/add-sign-spotter-map/proposal.md), [design](openspec/changes/add-sign-spotter-map/design.md), [specs](openspec/changes/add-sign-spotter-map/specs/) and [tasks](openspec/changes/add-sign-spotter-map/tasks.md).

## Contributing

All changes reach `main` through pull requests.
