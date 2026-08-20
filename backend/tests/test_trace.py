"""Unit tests for cost/trace logging (app/trace.py).

Fully offline -- no Ollama, Postgres, or n8n. We drive `trace.record` with fake
Ollama response dicts and monkeypatch the DB write, so this exercises the token
accounting, cost math, and the "never break the request path" guarantee without
any services running:

    cd backend && .venv\\Scripts\\python -m tests.test_trace
"""
from __future__ import annotations

import sys

from app import trace


def _check(desc: str, cond: bool) -> int:
    print(f"[{'PASS' if cond else 'FAIL'}] {desc}")
    return 0 if cond else 1


# A chat response carries token counts; an embedding response does not.
CHAT_RESP = {"model": "llama3.2:3b", "prompt_eval_count": 120, "eval_count": 30,
             "message": {"content": "..."}}
EMBED_RESP = {"embedding": [0.1, 0.2, 0.3]}


def main() -> int:
    fails = 0

    # --- record() only counts inside an active run --------------------------
    trace.record(CHAT_RESP)  # no active run -> must be a no-op (no crash)
    fails += _check("record() outside a run is a no-op", trace._current.get() is None)

    # --- accounting across calls, embeddings ignored ------------------------
    with trace.track() as usage:
        trace.record(CHAT_RESP)   # router call
        trace.record(EMBED_RESP)  # retrieval embedding -- no token counts
        trace.record(CHAT_RESP)   # answerer call
    fails += _check("counts only generative calls", usage.llm_calls == 2)
    fails += _check("sums prompt tokens", usage.prompt_tokens == 240)
    fails += _check("sums completion tokens", usage.completion_tokens == 60)
    fails += _check("total_tokens = prompt + completion", usage.total_tokens == 300)
    fails += _check("captures model name", usage.model == "llama3.2:3b")
    fails += _check("times the run", usage.latency_ms >= 0)

    # --- cost math honours configured rates ---------------------------------
    orig_in, orig_out = trace.COST_PER_1M_INPUT, trace.COST_PER_1M_OUTPUT
    trace.COST_PER_1M_INPUT, trace.COST_PER_1M_OUTPUT = 1.0, 2.0
    try:
        with trace.track() as u2:
            trace.record(CHAT_RESP)  # 120 in, 30 out
        # 120/1e6 * 1.0 + 30/1e6 * 2.0 = 0.00018
        fails += _check("cost_usd uses per-1M rates", abs(u2.cost_usd - 0.00018) < 1e-9)
    finally:
        trace.COST_PER_1M_INPUT, trace.COST_PER_1M_OUTPUT = orig_in, orig_out

    # --- default (local) cost is zero ---------------------------------------
    with trace.track() as u3:
        trace.record(CHAT_RESP)
    fails += _check("local default cost is $0", u3.cost_usd == 0.0)

    # --- runs unwind cleanly (contextvar reset) -----------------------------
    fails += _check("contextvar reset after run", trace._current.get() is None)

    # --- log_run never raises when the DB is unreachable --------------------
    def boom():
        raise RuntimeError("db down")

    orig_connect = trace.db.connect
    trace.db.connect = boom
    try:
        rid = trace.log_run("hi", {"route": "answer", "reason": "answered"}, u3)
        fails += _check("log_run swallows DB failure -> None", rid is None)
    finally:
        trace.db.connect = orig_connect

    # --- disabled tracing skips persistence entirely ------------------------
    orig_enabled = trace.TRACE_ENABLED
    trace.TRACE_ENABLED = False
    try:
        rid = trace.log_run("hi", {"route": "answer"}, u3)
        fails += _check("log_run returns None when disabled", rid is None)
    finally:
        trace.TRACE_ENABLED = orig_enabled

    total = 12
    print(f"\n{total - fails}/{total} checks passed.")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
