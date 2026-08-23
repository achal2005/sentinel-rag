"""Run five support tickets against the attributed Render docs snapshot.

The caller must point ``DATABASE_URL`` at an isolated database containing
``docs/targets/render`` and set ``SUPPORT_PRODUCT_NAME=Render`` before Python
imports the application modules.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from app.config import DATABASE_URL, PRODUCT_NAME, ROOT
from app.graph import run


DEFAULT_REPORT_DIR = ROOT / "evals" / "reports" / "render_demo"
EXPECTED_DATABASE = "sentinel_render_demo"


@dataclass(frozen=True)
class DemoCase:
    id: str
    ticket: str
    expected_source: str
    allowed_sources: tuple[str, ...]
    official_url: str
    expected_answer: str
    required_concepts: tuple[tuple[str, ...], ...]
    forbidden_phrases: tuple[str, ...] = ()


CASES = (
    DemoCase(
        id="RENDER-001",
        ticket=(
            "My custom domain verification keeps failing and the DNS zone still "
            "has an AAAA record. What should I change, and what happens after verification?"
        ),
        expected_source="rnd-01",
        allowed_sources=("rnd-01", "rnd-02"),
        official_url="https://render.com/docs/custom-domains",
        expected_answer=(
            "Remove the AAAA record, confirm the required DNS records, wait for "
            "propagation, and retry verification; managed TLS follows verification."
        ),
        required_concepts=(("aaaa",), ("dns",), ("verify", "verification")),
    ),
    DemoCase(
        id="RENDER-002",
        ticket=(
            "Our new web-service deploy is failing its HTTP health check. What "
            "response counts as healthy, and will Render replace the currently working version?"
        ),
        expected_source="rnd-03",
        allowed_sources=("rnd-03", "rnd-04"),
        official_url="https://render.com/docs/health-checks",
        expected_answer=(
            "A 2xx or 3xx response within five seconds is healthy. A replacement "
            "that never becomes healthy is cancelled while the existing instance keeps traffic."
        ),
        required_concepts=(
            ("2xx", "3xx"),
            ("five seconds", "5 seconds"),
            (
                "will not replace the currently working",
                "does not replace the currently successful",
                "won't replace the currently working",
                "keeps traffic on the existing",
            ),
        ),
        forbidden_phrases=("unless",),
    ),
    DemoCase(
        id="RENDER-003",
        ticket=(
            "I changed an environment variable and want the running service to "
            "pick it up without rebuilding the code. Which save option should I use?"
        ),
        expected_source="rnd-05",
        allowed_sources=("rnd-05",),
        official_url="https://render.com/docs/configure-environment-variables",
        expected_answer=(
            "Use Save and deploy, which redeploys the existing build with the new "
            "environment values instead of creating a new build."
        ),
        required_concepts=(("save and deploy",), ("existing build", "without rebuild", "no rebuild")),
    ),
    DemoCase(
        id="RENDER-004",
        ticket=(
            "Can a Hobby workspace restore a paid Render Postgres database to "
            "five days ago? Would upgrading to Pro today make that older restore available?"
        ),
        expected_source="rnd-06",
        allowed_sources=("rnd-06",),
        official_url="https://render.com/docs/postgresql-backups",
        expected_answer=(
            "No. Hobby has a three-day PITR window, and an upgrade to Pro extends "
            "the window only going forward rather than backfilling older history."
        ),
        required_concepts=(
            ("three days", "3 days", "three-day", "3-day"),
            ("pro",),
            (
                "retroactive",
                "backfill",
                "going forward",
                "does not create",
                "would not make the older restore available",
                "not make the older restore available",
            ),
        ),
    ),
    DemoCase(
        id="RENDER-005",
        ticket=(
            "We need to move an existing Render service from Oregon to Frankfurt. "
            "Can its region be changed in place, or what migration path do the docs require?"
        ),
        expected_source="rnd-08",
        allowed_sources=("rnd-08",),
        official_url="https://render.com/docs/regions",
        expected_answer=(
            "Render does not support an in-place region change. Create a new "
            "resource in Frankfurt and migrate configuration and data."
        ),
        required_concepts=(
            ("not", "doesn't", "does not", "cannot", "can't"),
            ("new service", "new resource", "create a new"),
            ("migrate", "migration"),
        ),
    ),
)


def _contains_concepts(answer: str, groups: tuple[tuple[str, ...], ...]) -> tuple[bool, list[list[str]]]:
    lowered = answer.lower()
    missing = [list(group) for group in groups if not any(term in lowered for term in group)]
    return not missing, missing


def evaluate_case(case: DemoCase) -> dict[str, Any]:
    started = time.perf_counter()
    state = run(case.ticket)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    decision = state.get("decision")
    hits = state.get("hits") or []
    retrieved = [hit.citation_id for hit in hits if hit.citation_id]
    citations = list(state.get("citations") or [])
    answer_text = str(state.get("answer") or "")
    concepts_passed, missing_concepts = _contains_concepts(
        answer_text, case.required_concepts
    )
    forbidden = [
        phrase for phrase in case.forbidden_phrases if phrase in answer_text.lower()
    ]
    checks = {
        "routed_to_answer": state.get("route") == "answer",
        "answered_without_escalation": not bool(state.get("escalated", False)),
        "expected_source_retrieved": case.expected_source in retrieved,
        "expected_source_cited": case.expected_source in citations,
        "citations_grounded": bool(citations) and set(citations).issubset(set(retrieved)),
        "citations_relevant": bool(citations)
        and set(citations).issubset(set(case.allowed_sources)),
        "required_concepts_present": concepts_passed,
        "forbidden_phrases_absent": not forbidden,
    }
    return {
        "id": case.id,
        "ticket": case.ticket,
        "official_url": case.official_url,
        "expected_source": case.expected_source,
        "allowed_sources": list(case.allowed_sources),
        "expected_answer": case.expected_answer,
        "status": "PASSED" if all(checks.values()) else "FAILED",
        "checks": checks,
        "missing_concepts": missing_concepts,
        "forbidden_phrases_found": forbidden,
        "route": state.get("route"),
        "router_intent": getattr(decision, "intent", None),
        "escalated": bool(state.get("escalated", False)),
        "reason": state.get("reason"),
        "answer": answer_text,
        "citations": citations,
        "retrieved_sources": retrieved,
        "duration_ms": elapsed_ms,
        "usage": state.get("usage") or {},
    }


def rescore_result(case: DemoCase, result: dict[str, Any]) -> dict[str, Any]:
    """Apply the latest deterministic rubric to an already-generated answer."""
    updated = dict(result)
    citations = list(updated.get("citations") or [])
    retrieved = list(updated.get("retrieved_sources") or [])
    concepts_passed, missing_concepts = _contains_concepts(
        str(updated.get("answer") or ""), case.required_concepts
    )
    forbidden = [
        phrase
        for phrase in case.forbidden_phrases
        if phrase in str(updated.get("answer") or "").lower()
    ]
    checks = dict(updated.get("checks") or {})
    checks.update(
        {
            "routed_to_answer": updated.get("route") == "answer",
            "answered_without_escalation": not bool(updated.get("escalated", False)),
            "expected_source_retrieved": case.expected_source in retrieved,
            "expected_source_cited": case.expected_source in citations,
            "citations_grounded": bool(citations)
            and set(citations).issubset(set(retrieved)),
            "citations_relevant": bool(citations)
            and set(citations).issubset(set(case.allowed_sources)),
            "required_concepts_present": concepts_passed,
            "forbidden_phrases_absent": not forbidden,
        }
    )
    updated["allowed_sources"] = list(case.allowed_sources)
    updated["checks"] = checks
    updated["missing_concepts"] = missing_concepts
    updated["forbidden_phrases_found"] = forbidden
    updated["status"] = "PASSED" if all(checks.values()) else "FAILED"
    return updated


def build_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    passed = sum(item["status"] == "PASSED" for item in results)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_company": "Render",
        "product": PRODUCT_NAME,
        "database": urlsplit(DATABASE_URL).path.lstrip("/"),
        "corpus_dir": str((ROOT / "docs" / "targets" / "render").resolve()),
        "method": "application router -> hybrid retrieval -> cited answer",
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "pass_rate": passed / len(results) if results else 0.0,
        },
        "results": results,
        "limitations": [
            "The corpus is a hand-curated, attributed, paraphrased snapshot, not Render's complete documentation.",
            "Deterministic checks validate routing, retrieval, citation-ID membership, and required or forbidden phrases; they do not prove semantic entailment or human support quality.",
            "No Render account, private data, or production API was accessed.",
        ],
    }


def markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Render public-documentation ticket test",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "This is an independent technical demonstration using a small, hand-curated, attributed, paraphrased snapshot of Render's public documentation. It is not produced by or affiliated with Render.",
        "",
        "## Result",
        "",
        f"- Tickets: **{summary['total']}**",
        f"- Passed: **{summary['passed']}**",
        f"- Failed: **{summary['failed']}**",
        f"- Pass rate: **{summary['pass_rate']:.0%}**",
        "",
        "| Ticket | Result | Route | Expected source cited | Citations retrieved | Citations allowed | Duration |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for item in report["results"]:
        checks = item["checks"]
        lines.append(
            f"| {item['id']} | {item['status']} | {item['route']} | "
            f"{'yes' if checks['expected_source_cited'] else 'no'} | "
            f"{'yes' if checks['citations_grounded'] else 'no'} | "
            f"{'yes' if checks['citations_relevant'] else 'no'} | "
            f"{item['duration_ms'] / 1000:.1f}s |"
        )
    lines.extend(["", "## Ticket evidence", ""])
    for item in report["results"]:
        failed_checks = [name for name, ok in item["checks"].items() if not ok]
        lines.extend(
            [
                f"### {item['id']} — {item['status']}",
                "",
                f"**Ticket:** {item['ticket']}",
                "",
                f"**Official documentation:** {item['official_url']}",
                "",
                f"**Expected:** {item['expected_answer']}",
                "",
                f"**Retrieved:** {', '.join(item['retrieved_sources']) or 'none'}",
                "",
                f"**Cited:** {', '.join(item['citations']) or 'none'}",
                "",
                f"**Failed checks:** {', '.join(failed_checks) or 'none'}",
                "",
                "**Sentinel response:**",
                "",
                item["answer"],
                "",
            ]
        )
    lines.extend(["## Limitations", ""])
    lines.extend(f"- {item}" for item in report["limitations"])
    lines.append("")
    return "\n".join(lines)


def write_report(report: dict[str, Any], report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    json_text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    md_text = markdown_report(report)
    (report_dir / "latest.json").write_text(json_text, encoding="utf-8")
    (report_dir / "latest.md").write_text(md_text, encoding="utf-8")
    (report_dir / "in_progress.json").write_text(json_text, encoding="utf-8")


def validate_runtime() -> None:
    database = urlsplit(DATABASE_URL).path.lstrip("/")
    if PRODUCT_NAME != "Render":
        raise SystemExit(
            "Set SUPPORT_PRODUCT_NAME=Render before running this demonstration."
        )
    if database != EXPECTED_DATABASE:
        raise SystemExit(
            f"Refusing to run against database {database!r}; expected "
            f"the isolated {EXPECTED_DATABASE!r} database."
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument(
        "--cooldown-seconds",
        type=float,
        default=20.0,
        help="idle time after each ticket to reduce sustained local model load",
    )
    parser.add_argument(
        "--rescore-existing",
        action="store_true",
        help="reapply current checks to latest.json without calling the model",
    )
    parser.add_argument(
        "--case-id",
        choices=tuple(case.id for case in CASES),
        help=(
            "rerun one case and replace it in an existing complete report; useful "
            "for low-load corrective runs"
        ),
    )
    args = parser.parse_args(argv)
    if args.cooldown_seconds < 0:
        parser.error("--cooldown-seconds must be zero or greater")
    validate_runtime()

    if args.rescore_existing:
        latest = args.report_dir / "latest.json"
        if not latest.exists():
            raise SystemExit(f"No existing report found at {latest}")
        existing = json.loads(latest.read_text(encoding="utf-8"))
        by_id = {case.id: case for case in CASES}
        results = [
            rescore_result(by_id[item["id"]], item)
            for item in existing.get("results", [])
            if item.get("id") in by_id
        ]
        if len(results) != len(CASES):
            raise SystemExit(
                f"Expected {len(CASES)} saved cases, found {len(results)}"
            )
        report = build_report(results)
        write_report(report, args.report_dir)
        print(
            f"Rescored {len(results)} tickets: "
            f"{report['summary']['passed']} passed, "
            f"{report['summary']['failed']} failed"
        )
        return 0 if report["summary"]["failed"] == 0 else 1

    if args.case_id:
        latest = args.report_dir / "latest.json"
        if not latest.exists():
            raise SystemExit(
                f"--case-id requires an existing complete report at {latest}"
            )
        existing = json.loads(latest.read_text(encoding="utf-8"))
        saved = {
            item["id"]: item
            for item in existing.get("results", [])
            if item.get("id") in {case.id for case in CASES}
        }
        if len(saved) != len(CASES):
            raise SystemExit(
                f"Expected {len(CASES)} saved cases, found {len(saved)}"
            )
        selected = next(case for case in CASES if case.id == args.case_id)
        saved[selected.id] = evaluate_case(selected)
        results = [saved[case.id] for case in CASES]
        final = build_report(results)
        write_report(final, args.report_dir)
        result = saved[selected.id]
        print(
            f"Reran {selected.id}: {result['status']} "
            f"citations={','.join(result['citations']) or '-'} "
            f"duration={result['duration_ms'] / 1000:.1f}s",
            flush=True,
        )
        return 0 if final["summary"]["failed"] == 0 else 1

    results: list[dict[str, Any]] = []
    for index, case in enumerate(CASES, start=1):
        result = evaluate_case(case)
        results.append(result)
        report = build_report(results)
        write_report(report, args.report_dir)
        print(
            f"[{index}/{len(CASES)}] {result['status']:<6} {case.id} "
            f"citations={','.join(result['citations']) or '-'} "
            f"duration={result['duration_ms'] / 1000:.1f}s",
            flush=True,
        )
        if index < len(CASES) and args.cooldown_seconds:
            time.sleep(args.cooldown_seconds)

    final = build_report(results)
    write_report(final, args.report_dir)
    return 0 if final["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
