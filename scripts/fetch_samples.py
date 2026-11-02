"""Download the GTSRB test set and register sample sign images in the `samples` bucket.

The images come from the Hugging Face mirror `tanganke/gtsrb` (standard class ids
0-42); the original GTSRB host is often unreachable. Picks the first image of 20+
distinct classes (always including Speed limit 50, Yield, Stop and No entry),
upscales each to at least 128 px, saves as PNG, uploads them plus `manifest.json`,
and keeps a local copy in `samples/`. Safe to rerun: existing objects are overwritten.

Usage: python scripts/fetch_samples.py
"""
import io
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pyarrow.parquet as pq  # noqa: E402
from huggingface_hub import hf_hub_download  # noqa: E402
from PIL import Image  # noqa: E402

from app import config, storage  # noqa: E402
from app.labels import LABELS  # noqa: E402

HF_REPO = "tanganke/gtsrb"
HF_TEST_FILE = "data/test-00000-of-00001.parquet"
REQUIRED_CLASSES = [2, 13, 14, 17]
TARGET_COUNT = 20
MIN_SIDE = 128


def slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def pick_rows(labels: list[int]) -> dict[int, int]:
    """Return {class_id: row_index}: the required classes plus the first others seen."""
    first_by_class: dict[int, int] = {}
    for row, class_id in enumerate(labels):
        first_by_class.setdefault(class_id, row)
    chosen = {c: first_by_class[c] for c in REQUIRED_CLASSES}
    for class_id in labels:
        if len(chosen) >= TARGET_COUNT:
            break
        chosen.setdefault(class_id, first_by_class[class_id])
    return dict(sorted(chosen.items()))


def to_png(image_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    scale = MIN_SIDE / min(img.size)
    if scale > 1:
        img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def main() -> None:
    root = config.ROOT
    print(f"Fetching GTSRB test split from {HF_REPO} (~110 MB on first run)...")
    path = hf_hub_download(HF_REPO, HF_TEST_FILE, repo_type="dataset", local_dir=root / "data" / "gtsrb")
    table = pq.read_table(path, columns=["image", "label"])
    labels = table.column("label").to_pylist()
    images = table.column("image")

    local_dir = root / "samples"
    local_dir.mkdir(exist_ok=True)
    manifest = []
    for class_id, row in pick_rows(labels).items():
        name = f"{class_id}_{slug(LABELS[class_id])}.png"
        data = to_png(images[row].as_py()["bytes"])
        storage.put(config.SAMPLES_BUCKET, name, data, "image/png")
        (local_dir / name).write_bytes(data)
        manifest.append({"file": name, "classId": class_id, "label": LABELS[class_id]})
        print(f"  {name}")

    manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")
    storage.put(config.SAMPLES_BUCKET, "manifest.json", manifest_bytes, "application/json")
    (local_dir / "manifest.json").write_bytes(manifest_bytes)
    print(f"Registered {len(manifest)} samples + manifest.json in bucket '{config.SAMPLES_BUCKET}'")
    print(f"Example: {storage.url_for(config.SAMPLES_BUCKET, manifest[0]['file'])}")


if __name__ == "__main__":
    main()
