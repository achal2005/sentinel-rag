"""Embeddings + chat via the local Ollama HTTP API (stdlib only)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Iterable

from . import lf, trace
from .config import CHAT_MODEL, EMBED_MODEL, OLLAMA_HOST


class OllamaError(RuntimeError):
    pass


def _post(path: str, payload: dict, timeout: int = 300) -> dict:
    req = urllib.request.Request(
        f"{OLLAMA_HOST}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
    except urllib.error.URLError as e:  # connection refused, DNS, HTTP error
        raise OllamaError(
            f"Ollama request to {path} failed: {e}. "
            f"Is Ollama running at {OLLAMA_HOST} and the model pulled?"
        ) from e
    # Fold token usage into the active graph run (no-op for embeddings / no run).
    trace.record(data)
    # Mirror generative calls to Langfuse as a generation (no-op if disabled).
    lf.record_chat(payload, data)
    return data


def embed(text: str) -> list[float]:
    data = _post("/api/embeddings", {"model": EMBED_MODEL, "prompt": text})
    vec = data.get("embedding")
    if not vec:
        raise OllamaError(f"No embedding returned for model {EMBED_MODEL!r}")
    return vec


# nomic-embed-text is trained for asymmetric retrieval and expects task prefixes:
# documents are embedded with "search_document: ", queries with "search_query: ".
# Using them markedly improves query/doc separation.
def embed_document(text: str) -> list[float]:
    return embed(f"search_document: {text}")


def embed_query(text: str) -> list[float]:
    return embed(f"search_query: {text}")


def embed_many(texts: Iterable[str]) -> list[list[float]]:
    return [embed(t) for t in texts]


def chat(system: str, user: str, temperature: float = 0.0) -> str:
    data = _post(
        "/api/chat",
        {
            "model": CHAT_MODEL,
            "stream": False,
            "options": {"temperature": temperature},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
    )
    return data.get("message", {}).get("content", "").strip()
