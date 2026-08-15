"""Score the router against evals/golden.json and print a metrics table.

This is the baseline the LoRA fine-tuned router will be compared against.

    python -m app.eval_routing            # run all cases
    python -m app.eval_routing --limit 5  # quick smoke run
    python -m app.eval_routing --json out.json
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .config import ROOT
from .router import route

GOLDEN = ROOT / "evals" / "golden.json"


def _pct(num: int, den: int) -> str:
    return f"{(100.0 * num / den):5.1f}%  ({num}/{den})" if den else "  n/a"


def run(limit: int | None = None) -> dict:
    cases = json.loads(GOLDEN.read_text(encoding="utf-8"))["cases"]
    if limit:
        cases = cases[:limit]

    rows = []
    lat = []
    for c in cases:
        exp = c["expected"]
        t0 = time.perf_counter()
        d = route(c["input"])
        lat.append(time.perf_counter() - t0)
        rows.append(
            {
                "id": c["id"],
                "input": c["input"],
                "exp_route": exp["route"],
                "got_route": d.route,
                "route_ok": d.route == exp["route"],
                "exp_urg": exp.get("urgency"),
                "got_urg": d.urgency,
                "urg_ok": d.urgency == exp.get("urgency"),
                "must_escalate": exp.get("must_escalate", False),
                "got_intent": d.intent,
            }
        )

    n = len(rows)
    route_ok = sum(r["route_ok"] for r in rows)
    urg_den = sum(1 for r in rows if r["exp_urg"] is not None)
    urg_ok = sum(1 for r in rows if r["exp_urg"] is not None and r["urg_ok"])

    # Two-sided escalation guardrail (per evals/README):
    esc_must = [r for r in rows if r["must_escalate"]]
    esc_recall = sum(1 for r in esc_must if r["got_route"] == "escalate")
    ans_cases = [r for r in rows if r["exp_route"] == "answer"]
    over_esc = sum(1 for r in ans_cases if r["got_route"] == "escalate")

    metrics = {
        "n": n,
        "routing_accuracy": route_ok / n if n else 0.0,
        "urgency_accuracy": urg_ok / urg_den if urg_den else None,
        "escalation_recall": esc_recall / len(esc_must) if esc_must else None,
        "answerable_over_escalation": over_esc / len(ans_cases) if ans_cases else None,
        "latency_avg_s": sum(lat) / n if n else 0.0,
        "model": "prompted-baseline",
    }

    # ---- print report ----
    print(f"\nRouting eval — {n} cases (baseline: prompted {rows and ''})")
    print("-" * 72)
    print(f"{'id':10} {'exp→got route':22} {'urg exp→got':14} ok")
    for r in rows:
        flag = "OK " if r["route_ok"] else "XX "
        print(
            f"{r['id']:10} "
            f"{r['exp_route']:>8} -> {r['got_route']:<8}   "
            f"{str(r['exp_urg']):>6} -> {r['got_urg']:<6}  "
            f"{flag}{'' if r['urg_ok'] else 'u!'}"
        )
    print("-" * 72)
    print(f"Routing accuracy         : {_pct(route_ok, n)}")
    print(f"Urgency accuracy         : {_pct(urg_ok, urg_den)}")
    print(f"Escalation recall        : {_pct(esc_recall, len(esc_must))}")
    print(f"Answerable over-escalated: {_pct(over_esc, len(ans_cases))}  (lower is better)")
    print(f"Avg latency              : {metrics['latency_avg_s']*1000:.0f} ms/case")
    print()

    return {"metrics": metrics, "rows": rows}


def main() -> None:
    ap = argparse.ArgumentParser(description="Score the router on golden.json")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--json", type=str, default=None, help="write full results to this path")
    args = ap.parse_args()
    result = run(limit=args.limit)
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"Wrote {args.json}")


if __name__ == "__main__":
    main()
