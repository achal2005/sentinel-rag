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


# --- Tenant / knowledge-base identity ---
# Keep Meridian as the product default while allowing an isolated public-docs
# evaluation to reuse the same retrieval and answer pipeline without leaking
# the fictional product name into the result.
PRODUCT_NAME = _env("SUPPORT_PRODUCT_NAME", "Meridian")


# --- Postgres ---
DATABASE_URL = os.environ.get("DATABASE_URL") or (
    f"postgresql://{_env('POSTGRES_USER', 'sentinel')}:"
    f"{_env('POSTGRES_PASSWORD', 'sentinel')}@"
    f"{_env('POSTGRES_HOST', 'localhost')}:"
    f"{_env('POSTGRES_PORT', '5432')}/"
    f"{_env('POSTGRES_DB', 'sentinel')}"
)
DB_CONNECT_TIMEOUT = int(_env("DB_CONNECT_TIMEOUT", "5"))

# --- Model providers ---
LLM_PROVIDER = _env("LLM_PROVIDER", "ollama").strip().lower()
EMBED_PROVIDER = _env("EMBED_PROVIDER", "ollama").strip().lower()
OLLAMA_HOST = _env("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
GEMINI_API_KEY = _env("GEMINI_API_KEY", "")
GEMINI_API_BASE = _env(
    "GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta"
).rstrip("/")
GEMINI_TIMEOUT = int(_env("GEMINI_TIMEOUT", "90"))
EMBED_MODEL = _env("EMBED_MODEL", "nomic-embed-text")
CHAT_MODEL = _env("CHAT_MODEL", "llama3.2:3b")
EMBED_DIM = int(_env("EMBED_DIM", "768"))

# --- Retrieval / answering ---
RETRIEVAL_POOL = int(_env("RETRIEVAL_POOL", "20"))
RETRIEVAL_TOPK = int(_env("RETRIEVAL_TOPK", "5"))
RRF_K = int(_env("RRF_K", "60"))
# Minimum cosine similarity (0..1) of the top hit; below this -> escalate.
CONFIDENCE_MIN = float(_env("CONFIDENCE_MIN", "0.55"))

# --- Cost / trace logging ---
# Every graph run logs its token usage + latency to the `runs` table. Local
# Ollama is free, so cost defaults to $0; set these (USD per 1M tokens) to price
# the SAME token counts against a hypothetical hosted model for the cost table.
COST_PER_1M_INPUT = float(_env("COST_PER_1M_INPUT", "0.0"))
COST_PER_1M_OUTPUT = float(_env("COST_PER_1M_OUTPUT", "0.0"))
TRACE_ENABLED = _env("TRACE_ENABLED", "1").lower() not in {"0", "false", "no", ""}

# --- Langfuse tracing (self-hosted, optional) ---
# One rich trace per graph run (router -> chunks -> prompt -> tool -> cost),
# sent to a self-hosted Langfuse. Disabled automatically if keys are unset or
# the SDK/server is unavailable -- tracing never blocks the request path.
LANGFUSE_HOST = _env("LANGFUSE_HOST", "http://localhost:3001").rstrip("/")
LANGFUSE_PUBLIC_KEY = _env("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = _env("LANGFUSE_SECRET_KEY", "")
LANGFUSE_ENABLED = (
    _env("LANGFUSE_ENABLED", "1").lower() not in {"0", "false", "no", ""}
    and bool(LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY)
)
