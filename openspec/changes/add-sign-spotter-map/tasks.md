# Tasks

Implementation order (set by the user): Docker services, sample images in RustFS, upload via REST API, Swagger, GraphQL, then the frontend with GitHub login. Time budget: about 4 h. Rough estimates are in brackets.

## 1. Docker services and scaffold [25 min]

- [x] 1.1 Create the layout from design.md (`app/`, `scripts/`, `static/`, `db/`), `.gitignore` (`.env`, `samples/`, `data/`), `.env.example` and a `requirements.txt` with fastapi, uvicorn, python-multipart, strawberry-graphql, authlib, itsdangerous, httpx, psycopg[binary], minio, pillow, torch, torchvision, transformers, requests, pytest. Verify that `pip install -r requirements.txt` succeeds.
- [x] 1.2 Add the `db` service (postgis/postgis:16-3.4, host port 5433, named volume) and `db/init.sql` with the `signs` table (including `image_key` and `uploaded_by`) and the GiST index. Verify that after `docker compose up -d`, `docker compose exec db psql -U postgres -d signs -c "\d signs"` shows the table and `signs_geom_idx`.
- [x] 1.3 Add the `storage` service (`rustfs/rustfs:1.0.3`, ports 9000/9001, named volume, credentials from `.env`, console enabled) and a one-shot `storage-init` service (`bitnamilegacy/minio-client`: `mb -p` for `signs` and `samples`, `anonymous set download` on both). Verify that `mc ls` shows both buckets and the console at http://localhost:9001/rustfs/console/ loads, that anonymous PUT is refused, and that `curl -I http://localhost:9000/samples/missing.png` returns 404 (not 403).
- [x] 1.4 Start the README with prerequisites (Docker Desktop, Python 3.11+), copying `.env.example`, `docker compose up -d` and the service URLs. Verify by following it from a clean shell.

## 2. Sample images registered in RustFS [25 min]

- [x] 2.1 Add `app/labels.py` with the 43 GTSRB class names, indexed 0–42. Verify that `len(LABELS) == 43` and that index 14 is "Stop".
- [x] 2.2 Implement `app/storage.py` (`put`, `get`, `url_for` from env config). Verify with a test that putting a small PNG into `samples` makes it fetchable over HTTP at `url_for(...)` with status 200 and `image/png`.
- [x] 2.3 Implement `scripts/fetch_samples.py`: download the GTSRB test split (Hugging Face mirror `tanganke/gtsrb`), pick the first image of 20+ distinct classes (always including 2, 13, 14 and 17), upscale to at least 128 px, save as PNG, upload to the `samples` bucket with a `manifest.json`, and write a local `samples/` copy. Verify that the RustFS console shows 20+ PNGs plus `manifest.json`, that `http://localhost:9000/samples/14_stop.png` opens in a browser, and that a second run completes without errors.
- [x] 2.4 Add the fetch command and the dataset download note to the README. Verify that the command runs as written.

## 3. Upload images via the REST API [75 min]

- [x] 3.1 Implement `app/classifier.py`: load the GTSRB checkpoint once (try `bazyl/gtsrb-model` first) and have `predict(PIL.Image) -> (class_id, label, confidence, low_conf)` map model output to `labels.py` and set `low_conf = confidence < 0.5`. Verify with a script that the local `samples/14_stop.png` returns "Stop" and that at least 16 of 20 samples match the manifest.
- [x] 3.2 If 3.1 fails, switch to the fallback: train a small CNN on the GTSRB train split from the Hugging Face mirror `tanganke/gtsrb` for 3–5 epochs (timebox 20 min), save it to `model.pt` and keep the same `predict()` signature. Verify the same sample check. Skip this task and mark it done if 3.1 passed.
- [x] 3.3 Implement image validation (decodable JPEG/PNG, ≤ 10 MB, returns the content type) and `app/geo.py` `extract_gps()` (GPS IFD, DMS to decimal degrees, S/W sign, `None` on failure). Verify with unit tests: a text payload and an 11 MB payload are rejected, a sample PNG is accepted as `image/png`, GPS is read from an image with EXIF GPS written in the test, and an image without EXIF data gives `None`.
- [x] 3.4 Implement `app/db.py`: `insert_sign(...)` (including `image_key` and `uploaded_by`) with `ST_SetSRID(ST_MakePoint(lng, lat), 4326)`, and `query_signs(bbox, class_id)` with `&& ST_MakeEnvelope`, newest first, `LIMIT 500`, using `ST_Y`/`ST_X`. Verify that a test inserts a point at (59.329, 18.069) and reads back the same lat/lng.
- [x] 3.5 Implement `app/service.py` `create_sign(...)` in the order from design.md, with the domain errors `InvalidImage`, `LocationRequired`, `InvalidCoordinates` and `StorageUnavailable`. Verify with tests that a storage failure (RustFS endpoint pointed at an unused port) inserts no row, and that a request with no location raises `LocationRequired`.
- [x] 3.6 Implement `app/rest.py` `POST /api/signs` (multipart `file`, `lat`, `lng`; returns 201 `Sign`; errors mapped to 400/422/503) using a `get_uploader` dependency stub that returns `"api-key"`, and wire up `app/main.py` (model loaded at startup, router mounted, static files at `/`). Verify with `curl -F file=@samples/14_stop.png -F lat=59.329 -F lng=18.069 http://localhost:8000/api/signs` that it returns 201 with "Stop" and an `imageUrl` that opens in the browser.
- [x] 3.7 Implement `scripts/seed.py`: read `manifest.json` from RustFS, download each sample and send `POST /api/signs` with `X-API-Key` at grid coordinates around Stockholm (59.329, 18.069), then print a matched/total summary. Verify that after seeding an empty DB, `SELECT count(*), count(DISTINCT geom) FROM signs` equals the sample count for both values.
- [x] 3.8 Add REST upload tests (`tests/test_rest.py`, TestClient against running PostGIS and RustFS): upload with coordinates, upload without a location gives 422, a non-image gives 400, and the returned `imageUrl` gives 200. Verify that `pytest` passes.

## 4. Swagger and REST read endpoints [20 min]

- [x] 4.1 Add `GET /api/signs` (bbox params all or none, `class_id`), `GET /api/sign-types` and `GET /api/samples` (manifest from RustFS with URLs), all through `service.py`, with Pydantic response models. Verify with tests that a bbox around central Stockholm includes inside points and excludes outside points, that the type filter works, that sign-types has 43 entries, and that every sample URL gives 200.
- [x] 4.2 Add OpenAPI metadata (title, description, `signs`/`samples` tags, response models, an `APIKeyHeader` security scheme on the upload). Verify that `/docs` lists all four endpoints, that "Authorize" accepts the API key, and that "Try it out" on `POST /api/signs` with a sample file returns 201.
- [x] 4.3 Add a Swagger section to the README (URL, how to authorize, example upload). Verify by following it.

## 5. GraphQL [30 min]

- [x] 5.1 Implement `app/schema.py`: the `Sign` (including `imageUrl` and `uploadedBy`), `SignType` and `BBoxInput` types, `Query.signs`, `Query.signTypes`, and `Mutation.uploadSign(imageBase64, lat, lng)`, all calling `service.py`. Map domain errors to `extensions.code` and pass the request through the context so the mutation uses the same `get_uploader` dependency. Mount the `GraphQLRouter` at `/graphql`. Verify in GraphiQL that `signTypes` returns 43 entries, that `signs(bbox)` matches the REST results for the same box, and that `uploadSign` without coordinates returns `LOCATION_REQUIRED`.
- [x] 5.2 Add `tests/test_graphql.py`: an upload with coordinates returns the same fields as REST, the bbox and type filters work, and the error codes are correct. Verify that `pytest` passes.
- [x] 5.3 Add example GraphQL queries and the mutation to the README. Verify they run as written in GraphiQL.

## 6. Frontend with GitHub login [55 min]

- [x] 6.1 Implement `app/auth.py`: add `SessionMiddleware`, register the Authlib GitHub client, add the `/auth/login`, `/auth/callback` (on error redirect to `/?auth_error=1`), `/auth/logout` and `/auth/me` routes, and `require_uploader()` (session login, or `X-API-Key` matched with `compare_digest`, otherwise 401 / `AUTH_REQUIRED`). Replace the `get_uploader` stub with it. Verify manually with a GitHub OAuth App (created per the README) that login redirects back to `/` and `/auth/me` returns your login, and that logout makes `/auth/me` return `{"user": null}`.
- [x] 6.2 Add auth tests (`tests/test_auth.py`): an anonymous REST upload gives 401 and stores nothing, an anonymous GraphQL upload gives `AUTH_REQUIRED`, a wrong API key gives 401, an anonymous `GET /api/signs` gives 200, and an API key upload records `uploadedBy == "api-key"`. Verify that `pytest` (all suites) passes.
- [x] 6.3 Create `static/index.html` with a Leaflet 1.9.4 map (OSM, centered on Stockholm) that loads `signs(bbox)` through GraphQL on load and on `moveend`, plus popups showing the thumbnail, label, confidence %, low-confidence warning, uploader and time. Verify while signed out that the seeded markers appear, that panning away and back reloads them, and that a popup shows a GTSRB thumbnail.
- [x] 6.4 Add the login bar (from `/auth/me`: a "Sign in with GitHub" link, or avatar + login + "Sign out") and an `auth_error` message. Show the upload form only when signed in. Verify that signed out there is no form and a sign-in link, that signed in the avatar and form appear, and that a cancelled GitHub consent shows "sign-in failed".
- [x] 6.5 Add the upload flow (`FileReader` to base64, then the `uploadSign` mutation). A map click sets the pending coordinates with a temporary marker. On success, show the label and confidence, add the marker and center the map on it. Add the type filter from `signTypes` with "All", and an error area (invalid file, `LOCATION_REQUIRED` leading to the "click the map" prompt, `AUTH_REQUIRED` leading to "session expired, sign in again", storage unavailable). Verify by uploading `samples/13_yield.png` after a map click (the popup shows your GitHub login), by uploading without a click, by uploading a PDF, and by filtering to Yield.
- [x] 6.6 Add a GitHub OAuth App setup section to the README (homepage and callback URLs, where to put the ID, secret, `SESSION_SECRET` and `API_KEY`). Verify by following it with a fresh OAuth App.

## 7. End-to-end check [10 min]

- [ ] 7.1 From a fresh `docker compose down -v && docker compose up -d`, follow the README (fetch samples, run the API, seed), check the endpoints in Swagger and GraphiQL, sign in with GitHub, upload 3 photos from the UI, sign out and reload the page. Verify that all signs and thumbnails persist, that the upload form disappears after signing out, and that each `sign-map-ui` and `user-auth` scenario behaves as specified.

## Workflow follow-up

- Run `/opsx:archive` after implementation is reviewed, to promote the specs into `openspec/specs/`.
