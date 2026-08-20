"""Per-request cost + trace logging.

Every graph run should leave a paper trail: which route it took, how many LLM
calls / tokens it burned, how long it took, and what it cost. We capture this
without threading usage through every function signature:

- `track()` is a context manager wrapped around one graph run. It installs a
  fresh `Usage` accumulator in a ContextVar and times the run.
- `record(data)` is called by the Ollama HTTP helper (`embed._post`) after every
  response. If a run is active AND the response carries token counts (i.e. it was
  a generative /api/chat call, not an embedding), it folds the counts in. Outside
  a run, or for responses without counts, it is a cheap no-op.
- `log_run(...)` writes one row to the `runs` table at the end of the run.

Design rule: **tracing must never break the request path.** Every DB touch is
wrapped so a logging failure (DB down, table missing) degrades to a warning and
the agent still answers.
"""
from __future__ import annotations

import contextlib
import contextvars
import logging
import time
from dataclasses import dataclass
from typing import Any, Iterator, Optional

from . import db
from .config import COST_PER_1M_INPUT, COST_PER_1M_OUTPUT, TRACE_ENABLED

log = logging.getLogger("sentinel.trace")


@dataclass
class Usage:
    """Token/latency tally for a single graph run."""

    llm_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str = ""
    latency_ms: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def cost_usd(self) -> float:
        """Hypothetical hosted cost for these tokens (0 with local defaults)."""
        return (
            self.prompt_tokens / 1_000_000 * COST_PER_1M_INPUT
            + self.completion_tokens / 1_000_000 * COST_PER_1M_OUTPUT
        )

    def summary(self) -> dict[str, Any]:
        """Compact dict for the API response / CLI output."""
        return {
            "llm_calls": self.llm_calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "latency_ms": self.latency_ms,
            "model": self.model,
        }


# The active run's accumulator, or None when no run is in flight.
_current: contextvars.ContextVar[Optional[Usage]] = contextvars.ContextVar(
    "sentinel_usage", default=None
)


def record(data: dict) -> None:
    """Fold one Ollama response's token counts into the active run, if any.

    No-ops when (a) no run is active, or (b) the response has no token counts
    (e.g. /api/embeddings), so it is safe to call after *every* Ollama request.
    """
    usage = _current.get()
    if usage is None:
        return
    prompt = data.get("prompt_eval_count")
    completion = data.get("eval_count")
    if prompt is None and completion is None:
        return  # not a generative call (embeddings return neither)
    usage.llm_calls += 1
    usage.prompt_tokens += int(prompt or 0)
    usage.completion_tokens += int(completion or 0)
    if not usage.model:
        usage.model = str(data.get("model", ""))


@contextlib.contextmanager
def track() -> Iterator[Usage]:
    """Wrap one graph run: install a fresh accumulator and time it."""
    usage = Usage()
    token = _current.set(usage)
    started = time.perf_counter()
    try:
        yield usage
    finally:
        usage.latency_ms = int((time.perf_counter() - started) * 1000)
        _current.reset(token)


def log_run(request: str, state: dict, usage: Usage, *, conn=None) -> Optional[int]:
    """Persist one row to `runs`. Returns the new id, or None if disabled/failed.

    Never raises: a tracing failure must not break the agent.
    """
    if not TRACE_ENABLED:
        return None
    action = state.get("action") or {}
    row = (
        request,
        state.get("route"),
        state.get("reason"),
        bool(state.get("escalated", False)),
        usage.model or None,
        usage.llm_calls,
        usage.prompt_tokens,
        usage.completion_tokens,
        usage.total_tokens,
        round(usage.cost_usd, 6),
        usage.latency_ms,
        state.get("citations") or None,
        action.get("status"),
        str(action.get("ticket_id")) if action.get("ticket_id") is not None else None,
    )
    try:
        own = conn is None
        conn = conn or db.connect()
        try:
            cur = conn.execute(
                """
                INSERT INTO runs (
                    request, route, reason, escalated, model, llm_calls,
                    prompt_tokens, completion_tokens, total_tokens, cost_usd,
                    latency_ms, citations, action_status, ticket_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                row,
            )
            return cur.fetchone()[0]
        finally:
            if own:
                conn.close()
    except Exception as e:  # DB down, table missing, etc. -- log and move on.
        log.warning("trace.log_run failed (run not persisted): %s", e)
        return None


def recent(limit: int = 20, *, conn=None) -> list[dict[str, Any]]:
    """Fetch the most recent runs (for `cli runs` / a future dashboard)."""
    own = conn is None
    conn = conn or db.connect()
    try:
        cur = conn.execute(
            """
            SELECT id, created_at, route, reason, escalated, model, llm_calls,
                   total_tokens, cost_usd, latency_ms, ticket_id
            FROM runs ORDER BY id DESC LIMIT %s
            """,
            (limit,),
        )
        cols = [c.name for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        if own:
            conn.close()
