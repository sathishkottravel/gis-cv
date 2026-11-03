"""Upload every registered sample through the REST API on a grid around central Stockholm.

Reads samples/manifest.json from object storage, downloads each sample and sends
POST /api/signs with the dev API key, then prints how many predictions matched.

Usage: python scripts/seed.py   (the API must be running)
"""
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests  # noqa: E402

from app import config, storage  # noqa: E402

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
CENTER_LAT, CENTER_LNG = 59.329, 18.069  # central Stockholm
SPACING_M = 150
COLUMNS = 5


def grid_point(i: int, total: int) -> tuple[float, float]:
    rows = math.ceil(total / COLUMNS)
    row, col = divmod(i, COLUMNS)
    dlat = SPACING_M / 111_320
    dlng = SPACING_M / (111_320 * math.cos(math.radians(CENTER_LAT)))
    lat = CENTER_LAT + (row - (rows - 1) / 2) * dlat
    lng = CENTER_LNG + (col - (COLUMNS - 1) / 2) * dlng
    return round(lat, 6), round(lng, 6)


def main() -> int:
    manifest = json.loads(storage.get(config.SAMPLES_BUCKET, "manifest.json"))
    headers = {"X-API-Key": os.getenv("API_KEY", "")}
    matched = 0
    for i, entry in enumerate(manifest):
        lat, lng = grid_point(i, len(manifest))
        image = storage.get(config.SAMPLES_BUCKET, entry["file"])
        resp = requests.post(
            f"{API_URL}/api/signs",
            files={"file": (entry["file"], image, "image/png")},
            data={"lat": lat, "lng": lng},
            headers=headers,
            timeout=60,
        )
        if resp.status_code != 201:
            print(f"FAIL {entry['file']}: HTTP {resp.status_code} {resp.text}")
            return 1
        sign = resp.json()
        ok = sign["classId"] == entry["classId"]
        matched += ok
        print(f"{'OK  ' if ok else 'MISS'} {entry['file']:<55} -> {sign['label']} ({lat}, {lng})")
    print(f"Seeded {len(manifest)} signs; {matched}/{len(manifest)} predictions matched the expected class")
    return 0


if __name__ == "__main__":
    sys.exit(main())
