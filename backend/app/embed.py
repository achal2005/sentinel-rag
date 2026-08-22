"""Provider-neutral embeddings and chat over Gemini or local Ollama."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Iterable

from . import lf, trace
from .config import (
    CHAT_MODEL,
    EMBED_DIM,
    EMBED_MODEL,
    EMBED_PROVIDER,
    GEMINI_API_BASE,
    GEMINI_API_KEY,
    GEMINI_TIMEOUT,
    LLM_PROVIDER,
    OLLAMA_HOST,
)


class ModelProviderError(RuntimeError):
    """A remote or local model provider could not serve the request."""


class OllamaError(ModelProviderError):
    pass


class GeminiError(ModelProviderError):
    pass


def _ollama_post(path: str, payload: dict, timeout: int) -> dict:
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
    return data


def _gemini_request(model: str, operation: str, payload: dict) -> dict:
    if not GEMINI_API_KEY:
        raise GeminiError("GEMINI_API_KEY is not configured")
    encoded_model = urllib.parse.quote(model.removeprefix("models/"), safe="")
    req = urllib.request.Request(
        f"{GEMINI_API_BASE}/models/{encoded_model}:{operation}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY,
        },
        method="POST",
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=GEMINI_TIMEOUT) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code in {429, 500, 502, 503, 504} and attempt < 2:
                time.sleep(2**attempt)
                continue
            raise GeminiError(
                f"Gemini {operation} failed with HTTP {exc.code}"
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt < 2:
                time.sleep(2**attempt)
                continue
            raise GeminiError(f"Gemini {operation} request failed") from exc
    raise GeminiError(f"Gemini {operation} request failed")


def _gemini_chat_post(payload: dict) -> dict:
    model = str(payload.get("model") or CHAT_MODEL)
    messages = list(payload.get("messages") or [])
    system_text = "\n\n".join(
        str(item.get("content") or "")
        for item in messages
        if item.get("role") == "system"
    )
    contents = [
        {
            "role": "model" if item.get("role") == "assistant" else "user",
            "parts": [{"text": str(item.get("content") or "")}],
        }
        for item in messages
        if item.get("role") != "system"
    ]
    options = dict(payload.get("options") or {})
    generation_config: dict[str, object] = {
        "temperature": float(options.get("temperature", 0.0)),
    }
    if payload.get("format") == "json":
        generation_config["responseMimeType"] = "application/json"
    request_payload: dict[str, object] = {
        "contents": contents,
        "generationConfig": generation_config,
    }
    if system_text:
        request_payload["systemInstruction"] = {"parts": [{"text": system_text}]}

    native = _gemini_request(model, "generateContent", request_payload)
    candidates = native.get("candidates") or []
    parts = (
        ((candidates[0].get("content") or {}).get("parts") or [])
        if candidates
        else []
    )
    content = "".join(str(part.get("text") or "") for part in parts).strip()
    if not content:
        raise GeminiError("Gemini returned no text content")
    usage = native.get("usageMetadata") or {}
    return {
        "model": model,
        "message": {"content": content},
        "prompt_eval_count": int(usage.get("promptTokenCount") or 0),
        "eval_count": int(usage.get("candidatesTokenCount") or 0),
    }


def _gemini_embed_post(payload: dict) -> dict:
    model = str(payload.get("model") or EMBED_MODEL)
    text = str(payload.get("prompt") or "")
    request_payload: dict[str, object] = {
        "model": f"models/{model.removeprefix('models/')}",
        "content": {"parts": [{"text": text}]},
        "outputDimensionality": EMBED_DIM,
    }
    if payload.get("task_type"):
        request_payload["taskType"] = str(payload["task_type"])
    native = _gemini_request(model, "embedContent", request_payload)
    vector = (native.get("embedding") or {}).get("values") or []
    if len(vector) != EMBED_DIM:
        raise GeminiError(
            f"Gemini returned {len(vector)} embedding values; expected {EMBED_DIM}"
        )
    return {"model": model, "embedding": vector}


def _post(path: str, payload: dict, timeout: int = 300) -> dict:
    """Compatibility gateway used by the router, answerer, and tests."""
    if path == "/api/chat":
        if LLM_PROVIDER == "gemini":
            data = _gemini_chat_post(payload)
        elif LLM_PROVIDER == "ollama":
            data = _ollama_post(path, payload, timeout)
        else:
            raise ModelProviderError(f"Unsupported LLM_PROVIDER={LLM_PROVIDER!r}")
    elif path in {"/api/embeddings", "/api/embed"}:
        if EMBED_PROVIDER == "gemini":
            data = _gemini_embed_post(payload)
        elif EMBED_PROVIDER == "ollama":
            data = _ollama_post(path, payload, timeout)
        else:
            raise ModelProviderError(
                f"Unsupported EMBED_PROVIDER={EMBED_PROVIDER!r}"
            )
    else:
        raise ModelProviderError(f"Unsupported model operation {path!r}")

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


def embed_document(text: str) -> list[float]:
    if EMBED_PROVIDER == "gemini":
        data = _post(
            "/api/embeddings",
            {
                "model": EMBED_MODEL,
                "prompt": text,
                "task_type": "RETRIEVAL_DOCUMENT",
            },
        )
        return list(data["embedding"])
    # nomic-embed-text expects asymmetric retrieval task prefixes.
    return embed(f"search_document: {text}")


def embed_query(text: str) -> list[float]:
    if EMBED_PROVIDER == "gemini":
        data = _post(
            "/api/embeddings",
            {
                "model": EMBED_MODEL,
                "prompt": text,
                "task_type": "RETRIEVAL_QUERY",
            },
        )
        return list(data["embedding"])
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
