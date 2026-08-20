"""Sentinel RAG CLI.

    python -m app.cli init                # create schema
    python -m app.cli ingest [--reset]    # load docs/ into pgvector
    python -m app.cli search "question"   # show hybrid retrieval hits
    python -m app.cli ask "question"      # full cited answer (or escalation)
    python -m app.cli graph "request"     # router -> answer|action|escalate
    python -m app.cli runs [--limit N]    # recent cost/trace log rows
"""
from __future__ import annotations

import argparse
import sys

from . import db
from .answer import answer
from .ingest import ingest
from .retrieve import search
from .router import route as route_request


def cmd_init(_args) -> None:
    db.init_db()
    print("Schema ready (extension + chunks table + indexes).")


def cmd_ingest(args) -> None:
    ingest(reset=args.reset)


def cmd_search(args) -> None:
    hits = search(args.query)
    if not hits:
        print("No hits.")
        return
    for i, h in enumerate(hits, 1):
        cid = h.citation_id or "(no-id)"
        print(
            f"{i}. [{cid}] {h.doc} — {h.heading}\n"
            f"   sim={h.similarity:.3f}  rrf={h.score:.4f}  "
            f"vec_rank={h.vector_rank}  fts_rank={h.fts_rank}"
        )


def cmd_route(args) -> None:
    d = route_request(args.query)
    print(
        f"route={d.route}  urgency={d.urgency}  action_required={d.action_required}\n"
        f"intent={d.intent}"
    )


def cmd_ask(args) -> None:
    a = answer(args.query)
    print(f"Q: {a.query}\n")
    print(a.text)
    print()
    if a.escalated:
        print(f"[ESCALATED — {a.reason}]")
    else:
        print(f"Citations: {', '.join(a.citations) if a.citations else '(none)'}  [{a.reason}]")
    print("\nRetrieved:")
    for h in a.hits:
        print(f"  - [{h.citation_id or '(no-id)'}] {h.doc} — {h.heading} (sim={h.similarity:.3f})")


def cmd_graph(args) -> None:
    from .graph import run  # lazy import so other commands don't need langgraph

    s = run(args.query)
    d = s.get("decision")
    print(f"Request: {args.query}\n")
    if d:
        print(f"[router] route={d.route}  urgency={d.urgency}  intent={d.intent}")
    print(f"[branch] {s.get('route')} -> reason={s.get('reason')}  "
          f"escalated={s.get('escalated', False)}\n")
    print(s.get("answer", "(no answer)"))
    if s.get("action"):
        print(f"\nPlanned action: {s['action']}")
    hits = s.get("hits") or []
    if hits:
        print("\nRetrieved:")
        for h in hits:
            print(f"  - [{h.citation_id or '(no-id)'}] {h.doc} — {h.heading} "
                  f"(sim={h.similarity:.3f})")
    u = s.get("usage") or {}
    if u:
        print(f"\n[cost] calls={u.get('llm_calls', 0)}  "
              f"tokens={u.get('total_tokens', 0)} "
              f"(in={u.get('prompt_tokens', 0)} out={u.get('completion_tokens', 0)})  "
              f"${u.get('cost_usd', 0):.6f}  {u.get('latency_ms', 0)}ms"
              + (f"  run_id={s['run_id']}" if s.get("run_id") else ""))


def cmd_runs(args) -> None:
    from . import trace

    rows = trace.recent(args.limit)
    if not rows:
        print("No runs logged yet.")
        return
    print(f"{'id':>4}  {'route':<8} {'tokens':>7} {'cost$':>9} {'ms':>6}  reason")
    for r in rows:
        print(f"{r['id']:>4}  {str(r['route'] or '-'):<8} "
              f"{r['total_tokens']:>7} {float(r['cost_usd']):>9.6f} "
              f"{r['latency_ms'] or 0:>6}  {r['reason'] or ''}"
              + ("  [escalated]" if r['escalated'] else "")
              + (f"  ticket#{r['ticket_id']}" if r['ticket_id'] else ""))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="app.cli", description="Sentinel RAG core CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="create schema").set_defaults(func=cmd_init)

    p_ing = sub.add_parser("ingest", help="load docs/ into pgvector")
    p_ing.add_argument("--reset", action="store_true", help="truncate first")
    p_ing.set_defaults(func=cmd_ingest)

    p_search = sub.add_parser("search", help="show retrieval hits")
    p_search.add_argument("query")
    p_search.set_defaults(func=cmd_search)

    p_route = sub.add_parser("route", help="triage a single request")
    p_route.add_argument("query")
    p_route.set_defaults(func=cmd_route)

    p_ask = sub.add_parser("ask", help="cited answer or escalation")
    p_ask.add_argument("query")
    p_ask.set_defaults(func=cmd_ask)

    p_graph = sub.add_parser("graph", help="router -> answer|action|escalate")
    p_graph.add_argument("query")
    p_graph.set_defaults(func=cmd_graph)

    p_runs = sub.add_parser("runs", help="recent cost/trace log rows")
    p_runs.add_argument("--limit", type=int, default=20, help="how many rows")
    p_runs.set_defaults(func=cmd_runs)

    args = ap.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
