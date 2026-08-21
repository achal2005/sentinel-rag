"""Score the full router -> critic pipeline on the adversarial (and unsupported)
golden cases, checking the *safety* behavior the router-only eval can't:

    route              -- final route after the critic (a blocked action escalates)
    must_refuse        -- flagged for refusal when the golden says so
    requires_approval  -- routed through the human-approval gate when required

    python -m app.eval_safety                 # adversarial cases (default)
    python -m app.eval_safety --category all   # every case
    python -m app.eval_safety --json out.json

This complements app.eval_routing: that measures the router alone; this measures
the router + critic gate that Week 3 adds in front of high-risk execution.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import ROOT
from .graph import plan

GOLDEN = ROOT / "evals" / "golden.json"


def run(category: str = "adversarial", limit: int | None = None) -> dict:
    cases = json.loads(GOLDEN.read_text(encoding="utf-8"))["cases"]
    if category != "all":
        cases = [c for c in cases if c["category"] == category]
    if limit:
        cases = cases[:limit]

    rows = []
    for c in cases:
        exp = c["expected"]
        got = plan(c["input"])

        checks = {"route": got["route"] == exp["route"]}
        if exp.get("must_refuse"):
            checks["refuse"] = bool(got["must_refuse"])
        if "requires_human_approval" in exp:
            checks["approval"] = got["requires_approval"] == exp["requires_human_approval"]

        rows.append({
            "id": c["id"],
            "input": c["input"],
            "exp_route": exp["route"],
            "got_route": got["route"],
            "category": got["critic_category"],
            "checks": checks,
            "ok": all(checks.values()),
        })

    n = len(rows)
    passed = sum(r["ok"] for r in rows)

    print(f"\nSafety eval — {n} {category} cases (router + critic)")
    print("-" * 78)
    print(f"{'id':8} {'exp→got route':22} {'critic':18} {'checks':16} ok")
    for r in rows:
        failed = [k for k, v in r["checks"].items() if not v]
        chk = "all ok" if not failed else "FAIL:" + ",".join(failed)
        print(f"{r['id']:8} {r['exp_route']:>8} -> {r['got_route']:<8}   "
              f"{r['category']:18} {chk:16} {'OK ' if r['ok'] else 'XX'}")
    print("-" * 78)
    print(f"Passed: {passed}/{n}  ({100.0*passed/n:.1f}%)" if n else "no cases")
    print()

    return {"passed": passed, "n": n, "rows": rows}


def main() -> None:
    ap = argparse.ArgumentParser(description="Score router+critic on golden safety cases")
    ap.add_argument("--category", default="adversarial",
                    help="golden category to score (default: adversarial; 'all' for every case)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--json", type=str, default=None)
    args = ap.parse_args()
    result = run(category=args.category, limit=args.limit)
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"Wrote {args.json}")
    raise SystemExit(0 if result["passed"] == result["n"] else 1)


if __name__ == "__main__":
    main()
