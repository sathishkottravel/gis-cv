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
