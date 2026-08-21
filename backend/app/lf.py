"""Langfuse tracing: one rich trace per graph run, sent to a self-hosted
Langfuse for a visual, drill-down view of every request.

Per request the trace reads, in order:

    router   (generation) -- the routing LLM call: prompt + decision + tokens
    retrieve (span)       -- the chunk ids/headings pulled from the KB
    answer   (generation) -- the grounded-answer LLM call: prompt + output + tokens
    tool     (span)       -- the selected tool + params + result

and the trace aggregates token usage / cost across both generations. That's the
"router -> chunks -> prompt -> tool call -> cost" story in one place.

How it's wired (minimal, no new call graph):
- `start()` opens a trace for the run and stashes it in a ContextVar.
- Both LLM calls go through Ollama's single `_post` chokepoint, which calls
  `record_chat()`. A ContextVar `label` (set by the router / answerer just
  before their call) names the generation, so we don't thread anything through.
- `span()` records the retrieval and tool steps (called where the data lives).
- `finish()` sets the trace's final output + metadata and flushes.

Design rule (shared with trace.py / audit.py): **tracing must never break the
request path.** If the langfuse package isn't installed, keys aren't set, or the
server is unreachable, every function here degrades to a no-op.
"""
from __future__ import annotations

import contextvars
import logging
from typing import Any, Optional

from .config import (
    LANGFUSE_ENABLED,
    LANGFUSE_HOST,
    LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY,
)

log = logging.getLogger("sentinel.langfuse")

# Lazily-built singleton client. `_ready` guards a single init attempt so a
# missing package / bad config doesn't retry (and re-warn) on every request.
_client: Optional[Any] = None
_ready = False

# The active run's trace object, and the label for the next chat generation.
_trace: contextvars.ContextVar[Optional[Any]] = contextvars.ContextVar(
    "sentinel_lf_trace", default=None
)
_label: contextvars.ContextVar[str] = contextvars.ContextVar(
    "sentinel_lf_label", default="llm"
)


def _get_client() -> Optional[Any]:
    global _client, _ready
    if _ready:
        return _client
    _ready = True
    if not LANGFUSE_ENABLED:
        return None
    try:
        from langfuse import Langfuse

        _client = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_HOST,
        )
    except Exception as e:  # package missing / bad host -- disable, don't crash.
        log.warning("langfuse disabled (init failed): %s", e)
        _client = None
    return _client


def start(request: str) -> None:
    """Open a trace for one graph run (no-op if tracing is disabled)."""
    client = _get_client()
    if client is None:
        return
    try:
        _trace.set(client.trace(name="triage", input=request, tags=["sentinel"]))
    except Exception as e:
        log.warning("langfuse start failed: %s", e)
        _trace.set(None)


def label(name: str) -> None:
    """Name the next chat generation ('router' or 'answer'). Cheap; always safe."""
    _label.set(name)


def record_chat(payload: dict, data: dict) -> None:
    """Log one Ollama chat call as a generation on the active trace.

    Called from embed._post after every Ollama response. No-ops when no trace is
    active or the response has no token counts (i.e. it was an embedding call).
    """
    tr = _trace.get()
    if tr is None:
        return
    prompt = data.get("prompt_eval_count")
    completion = data.get("eval_count")
    if prompt is None and completion is None:
        return  # not a generative call (embeddings return neither)
    try:
        msg = data.get("message") or {}
        tr.generation(
            name=_label.get(),
            model=data.get("model") or payload.get("model"),
            input=payload.get("messages"),
            output=msg.get("content", ""),
            usage={
                "input": int(prompt or 0),
                "output": int(completion or 0),
                "total": int((prompt or 0) + (completion or 0)),
                "unit": "TOKENS",
            },
        )
    except Exception as e:
        log.warning("langfuse record_chat failed: %s", e)


def span(name: str, *, input: Any = None, output: Any = None, **metadata: Any) -> None:
    """Record a point-in-time step (retrieval / tool) on the active trace."""
    tr = _trace.get()
    if tr is None:
        return
    try:
        s = tr.span(name=name, input=input, output=output,
                    metadata=metadata or None)
        # Immediately close it -- these steps are recorded after the fact.
        try:
            s.end()
        except Exception:
            pass
    except Exception as e:
        log.warning("langfuse span(%s) failed: %s", name, e)


def finish(*, output: str = "", metadata: dict[str, Any] | None = None) -> None:
    """Set the trace's final output + metadata and flush it. Resets the run."""
    tr = _trace.get()
    if tr is None:
        return
    try:
        tr.update(output=output, metadata=metadata or {})
    except Exception as e:
        log.warning("langfuse finish/update failed: %s", e)
    finally:
        client = _get_client()
        if client is not None:
            try:
                client.flush()  # send synchronously so the trace lands promptly
            except Exception as e:
                log.warning("langfuse flush failed: %s", e)
        _trace.set(None)
