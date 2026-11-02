"""Classify every image in samples/ and compare with samples/manifest.json.

Usage: python scripts/check_classifier.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image  # noqa: E402

from app import classifier, config  # noqa: E402


def main() -> int:
    samples = config.ROOT / "samples"
    manifest = json.loads((samples / "manifest.json").read_text(encoding="utf-8"))
    matched = 0
    for entry in manifest:
        pred = classifier.predict(Image.open(samples / entry["file"]))
        ok = pred.class_id == entry["classId"]
        matched += ok
        flag = " (low confidence)" if pred.low_conf else ""
        print(f"{'OK  ' if ok else 'MISS'} {entry['file']:<55} -> {pred.label} {pred.confidence:.2f}{flag}")
    print(f"{matched}/{len(manifest)} matched")
    return 0 if matched >= 16 else 1


if __name__ == "__main__":
    sys.exit(main())
