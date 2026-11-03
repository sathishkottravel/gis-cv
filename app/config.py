"""Settings from environment variables, with `.env` in the project root loaded first.

Real environment variables win over `.env`; defaults match `.env.example`.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv(ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/signs")

STORAGE_ENDPOINT = os.getenv("STORAGE_ENDPOINT", "localhost:9000")
STORAGE_ACCESS_KEY = os.getenv("STORAGE_ACCESS_KEY", "rustfsadmin")
STORAGE_SECRET_KEY = os.getenv("STORAGE_SECRET_KEY", "change-me-storage")
STORAGE_PUBLIC_URL = os.getenv("STORAGE_PUBLIC_URL", "http://localhost:9000").rstrip("/")

SAMPLES_BUCKET = "samples"
SIGNS_BUCKET = "signs"

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
SESSION_SECRET = os.getenv("SESSION_SECRET", "change-me-session-secret")
API_KEY = os.getenv("API_KEY", "")  # empty disables API key auth
