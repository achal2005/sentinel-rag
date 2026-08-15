"""Configuration + a tiny .env loader (no python-dotenv dependency)."""
from __future__ import annotations

import os
from pathlib import Path

# repo root = .../Sentinel  (this file is backend/app/config.py)
ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "docs"


def _load_dotenv(path: Path) -> None:
    """Populate os.environ from a .env file without clobbering real env vars."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        # strip inline comments and surrounding quotes
        val = val.split("#", 1)[0].strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), val)


_load_dotenv(ROOT / ".env")


def _env(key: str, default: str) -> str:
    return os.environ.get(key, default)


# --- Postgres ---
DATABASE_URL = os.environ.get("DATABASE_URL") or (
    f"postgresql://{_env('POSTGRES_USER', 'sentinel')}:"
    f"{_env('POSTGRES_PASSWORD', 'sentinel')}@"
    f"{_env('POSTGRES_HOST', 'localhost')}:"
    f"{_env('POSTGRES_PORT', '5432')}/"
    f"{_env('POSTGRES_DB', 'sentinel')}"
)

# --- Ollama ---
OLLAMA_HOST = _env("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
EMBED_MODEL = _env("EMBED_MODEL", "nomic-embed-text")
CHAT_MODEL = _env("CHAT_MODEL", "llama3.2:3b")
EMBED_DIM = int(_env("EMBED_DIM", "768"))

# --- Retrieval / answering ---
RETRIEVAL_POOL = int(_env("RETRIEVAL_POOL", "20"))
RETRIEVAL_TOPK = int(_env("RETRIEVAL_TOPK", "5"))
RRF_K = int(_env("RRF_K", "60"))
# Minimum cosine similarity (0..1) of the top hit; below this -> escalate.
CONFIDENCE_MIN = float(_env("CONFIDENCE_MIN", "0.55"))
