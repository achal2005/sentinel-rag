"""Per-step audit trail. One row in `audit_log` for every meaningful step of a
graph run, plus every out-of-run human decision:

    router    -> the routing decision (route / intent / urgency)
    retrieve  -> the chunk ids pulled from the KB (+ citation ids, top similarity)
    tool      -> the tool selected and the params it was called with
    outcome   -> the final result of the run (reason / escalated / action status)
    approval  -> a human approve/reject decision on a queued high-risk action

Steps are collected during a run via a ContextVar (the same pattern trace.py
uses for token usage), then flushed to the DB in one batch once the run's
`runs` row exists, so each step can carry its `run_id`. Out-of-run events
(approve/reject) are written immediately via `event()`.

Design rule (shared with trace.py): **auditing must never break the request
path.** Every DB touch is wrapped so a logging failure degrades to a warning
and the agent still answers.
"""
from __future__ import annotations

import contextlib
import contextvars
import logging
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

from . import db
from .config import TRACE_ENABLED

log = logging.getLogger("sentinel.audit")


@dataclass
class Step:
    """One audit step: a short kind tag plus a JSON-serialisable payload."""

    step: str
    detail: dict[str, Any] = field(default_factory=dict)


# The active run's step list, or None when no run is in flight.
_current: contextvars.ContextVar[Optional[list[Step]]] = contextvars.ContextVar(
    "sentinel_audit", default=None
)


def step(kind: str, **detail: Any) -> None:
    """Record one audit step for the active run.

    No-op outside a run (so nodes can call it unconditionally). `detail` should
    be JSON-serialisable; non-serialisable values are stringified defensively.
    """
    steps = _current.get()
    if steps is None:
        return
    steps.append(Step(kind, _jsonable(detail)))


@contextlib.contextmanager
def collect() -> Iterator[list[Step]]:
    """Install a fresh step collector for one graph run and yield its list."""
    steps: list[Step] = []
    token = _current.set(steps)
    try:
        yield steps
    finally:
        _current.reset(token)


def flush(run_id: Optional[int], steps: list[Step], *, conn=None) -> None:
    """Persist all collected steps for a run to `audit_log`. Never raises."""
    if not TRACE_ENABLED or not steps:
        return
    from psycopg.types.json import Jsonb

    rows = [
        (run_id, seq, s.step, Jsonb(s.detail))
        for seq, s in enumerate(steps)
    ]
    try:
        own = conn is None
        conn = conn or db.connect()
        try:
            conn.cursor().executemany(
                "INSERT INTO audit_log (run_id, seq, step, detail) "
                "VALUES (%s, %s, %s, %s)",
                rows,
            )
        finally:
            if own:
                conn.close()
    except Exception as e:  # DB down, table missing, etc. -- log and move on.
        log.warning("audit.flush failed (%d steps not persisted): %s", len(steps), e)


def event(kind: str, *, approval_id: int | None = None, run_id: int | None = None,
          conn=None, **detail: Any) -> None:
    """Write a single audit row immediately (for out-of-run events like a human
    approve/reject). Never raises."""
    if not TRACE_ENABLED:
        return
    from psycopg.types.json import Jsonb

    try:
        own = conn is None
        conn = conn or db.connect()
        try:
            conn.execute(
                "INSERT INTO audit_log (run_id, approval_id, step, detail) "
                "VALUES (%s, %s, %s, %s)",
                (run_id, approval_id, kind, Jsonb(_jsonable(detail))),
            )
        finally:
            if own:
                conn.close()
    except Exception as e:
        log.warning("audit.event(%s) failed (not persisted): %s", kind, e)


def for_run(run_id: int, *, conn=None) -> list[dict[str, Any]]:
    """All audit steps for one run, in order (for `cli audit` / the API)."""
    own = conn is None
    conn = conn or db.connect()
    try:
        cur = conn.execute(
            "SELECT id, run_id, seq, step, detail, created_at FROM audit_log "
            "WHERE run_id = %s ORDER BY seq, id",
            (run_id,),
        )
        cols = [c.name for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        if own:
            conn.close()


def recent(limit: int = 20, *, conn=None) -> list[dict[str, Any]]:
    """The most recent audit rows across all runs (newest first)."""
    own = conn is None
    conn = conn or db.connect()
    try:
        cur = conn.execute(
            "SELECT id, run_id, approval_id, seq, step, detail, created_at "
            "FROM audit_log ORDER BY id DESC LIMIT %s",
            (limit,),
        )
        cols = [c.name for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        if own:
            conn.close()


def _jsonable(value: Any) -> Any:
    """Best-effort coercion to JSON-safe types (dicts/lists/scalars).

    Keeps the audit writer from ever raising on an odd value: anything that
    isn't a plain scalar/container is stringified.
    """
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
