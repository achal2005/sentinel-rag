"""CLI entry point for the 300-case AgentOps golden suite.

From the repository root:

    python -m evals.runners.run_golden
    python -m evals.runners.run_golden --category adversarial_security --limit 5
    python -m evals.runners.run_golden --judge ollama
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from evals.judges.llm_judge import OllamaSemanticJudge
from evals.judges.calibrate import DEFAULT_REPORT as DEFAULT_CALIBRATION_REPORT
from evals.judges.calibrate import validate_calibration_report
from evals.reporting import (
    load_checkpoint,
    print_summary,
    summarize,
    threshold_failures,
    write_checkpoint,
    write_reports,
)
from evals.runners.agentops_adapter import AgentOpsAdapter, ROOT
from evals.runners.evaluator import Evaluator
from evals.schema import Status, filter_cases, load_dataset

DEFAULT_DATASET = ROOT / "evals" / "golden" / "agentops_meridian_300_cases.json"
DEFAULT_REPORT_DIR = ROOT / "evals" / "reports"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run AgentOps golden evaluations")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--category", action="append", default=[], help="category (repeatable)")
    parser.add_argument("--case-id", action="append", default=[], help="case id (repeatable)")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=DEFAULT_REPORT_DIR / "in_progress.json",
        help="atomic partial-results file",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="resume from --checkpoint after validating the run configuration",
    )
    parser.add_argument(
        "--rerun-errors",
        action="store_true",
        help="with --resume, retry checkpointed ERROR cases instead of skipping them",
    )
    parser.add_argument(
        "--pause-between-cases",
        type=float,
        default=0.0,
        help="cooldown seconds after each completed case (does not affect resume compatibility)",
    )
    parser.add_argument(
        "--pause-if-duration-ms",
        type=int,
        default=0,
        help="only cool down after cases taking at least this many milliseconds",
    )
    parser.add_argument("--judge", choices=("none", "ollama"), default="none")
    parser.add_argument("--judge-model", default=None)
    parser.add_argument(
        "--calibration-report",
        type=Path,
        default=DEFAULT_CALIBRATION_REPORT,
        help="passing calibration report required when --judge ollama is used",
    )
    parser.add_argument(
        "--allow-uncalibrated-judge",
        action="store_true",
        help="experimental override; never use this for release gates",
    )
    parser.add_argument("--semantic-threshold", type=float, default=0.8)
    parser.add_argument(
        "--langfuse",
        action="store_true",
        help="export evaluation executions to the configured Langfuse instance",
    )
    parser.add_argument("--min-overall", type=float)
    parser.add_argument("--min-routing", type=float)
    parser.add_argument("--min-tool-selection", type=float)
    parser.add_argument("--min-citations", type=float)
    parser.add_argument("--min-approval-safety", type=float)
    parser.add_argument("--min-reliability", type=float)
    parser.add_argument("--min-multi-turn", type=float)
    parser.add_argument("--min-adversarial-safety", type=float)
    parser.add_argument("--min-answer-correctness", type=float)
    parser.add_argument("--min-citation-faithfulness", type=float)
    parser.add_argument("--max-not-implemented", type=int)
    parser.add_argument("--baseline", type=Path, help="prior JSON report")
    parser.add_argument("--max-regression", type=float)
    parser.add_argument(
        "--allow-failures",
        action="store_true",
        help="write measured reports but exit zero despite case/threshold failures",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.pause_between_cases < 0 or args.pause_if_duration_ms < 0:
        print("cooldown values must be zero or greater", file=sys.stderr)
        return 2
    meta, all_cases = load_dataset(args.dataset)
    cases = filter_cases(
        all_cases,
        categories=set(args.category) or None,
        case_ids=set(args.case_id) or None,
        limit=args.limit,
    )
    if not cases:
        print("No golden cases matched the requested filters.", file=sys.stderr)
        return 2

    judge = (
        OllamaSemanticJudge(model=args.judge_model)
        if args.judge == "ollama"
        else None
    )
    if judge is not None and not args.allow_uncalibrated_judge:
        calibration_errors = validate_calibration_report(
            args.calibration_report,
            model=judge.model,
        )
        if calibration_errors:
            print("Semantic judge is not calibrated for release use:", file=sys.stderr)
            for error in calibration_errors:
                print(f"  - {error}", file=sys.stderr)
            print(
                "Run `python -m evals.judges.calibrate --model "
                f"{judge.model}` first.",
                file=sys.stderr,
            )
            return 2
    adapter = AgentOpsAdapter(export_langfuse=args.langfuse)
    evaluator = Evaluator(
        adapter,
        semantic_judge=judge,
        semantic_threshold=args.semantic_threshold,
    )
    run_config = {
        "evaluator_version": 3,
        "dataset": str(args.dataset.resolve()),
        "case_ids": [case.id for case in cases],
        "judge": args.judge,
        "judge_model": judge.model if judge is not None else None,
        "calibration_report": (
            str(args.calibration_report.resolve()) if judge is not None else None
        ),
        "semantic_threshold": args.semantic_threshold,
        "langfuse": args.langfuse,
    }
    if args.resume and args.checkpoint.exists():
        try:
            results = load_checkpoint(
                args.checkpoint,
                cases_by_id={case.id: case for case in cases},
                expected_config=run_config,
            )
        except ValueError as exc:
            print(f"Cannot resume: {exc}", file=sys.stderr)
            return 2
        if args.rerun_errors:
            before = len(results)
            results = [result for result in results if result.status is not Status.ERROR]
            print(f"Retrying {before - len(results)} checkpointed error case(s).", flush=True)
        print(f"Resumed {len(results)}/{len(cases)} cases from {args.checkpoint}", flush=True)
    else:
        results = []
    completed = {result.case.id for result in results}
    for index, case in enumerate(cases, start=1):
        if case.id in completed:
            continue
        result = evaluator.evaluate(case)
        results.append(result)
        failed = ",".join(check.name for check in result.failed_checks)
        suffix = f" failed={failed}" if failed else ""
        print(
            f"[{index:03}/{len(cases):03}] {result.status.value:15} "
            f"{case.id:12} {case.category}{suffix}",
            flush=True,
        )
        write_checkpoint(args.checkpoint, results, run_config=run_config)
        if (
            args.pause_between_cases
            and result.duration_ms >= args.pause_if_duration_ms
            and index < len(cases)
        ):
            time.sleep(args.pause_between_cases)

    selected_meta = {
        **meta,
        "source_file": str(args.dataset.resolve()),
        "selected_cases": len(cases),
        "filters": {"categories": args.category, "case_ids": args.case_id, "limit": args.limit},
        "semantic_judge": args.judge,
        "langfuse_export": args.langfuse,
        "external_side_effects": "recorded in memory; never sent to n8n/CRM/customer systems",
    }
    summary = summarize(results, selected_meta)
    json_path, markdown_path = write_reports(args.report_dir, results, summary)
    if args.checkpoint.exists():
        args.checkpoint.unlink()
    print_summary(summary)
    print(f"\nJSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")

    baseline = None
    if args.baseline:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    gates = threshold_failures(
        summary,
        minimums={
            "overall": args.min_overall,
            "routing": args.min_routing,
            "tool_selection": args.min_tool_selection,
            "citations": args.min_citations,
            "approval_safety": args.min_approval_safety,
            "reliability_fallback": args.min_reliability,
            "multi_turn": args.min_multi_turn,
            "adversarial_safety": args.min_adversarial_safety,
            "answer_correctness": args.min_answer_correctness,
            "citation_faithfulness": args.min_citation_faithfulness,
        },
        baseline=baseline,
        max_regression=args.max_regression,
    )
    # Case failures matter even when no explicit threshold is supplied. Missing
    # domain bindings do not make the command fail; they remain visible as NI.
    if summary["failed"] or summary["errors"]:
        gates.append(f"case results: {summary['failed']} failed, {summary['errors']} errored")
    if (
        args.max_not_implemented is not None
        and summary["not_implemented"] > args.max_not_implemented
    ):
        gates.append(
            f"not implemented: {summary['not_implemented']} exceeds "
            f"{args.max_not_implemented}"
        )
    if gates:
        print("\nRegression gates:")
        for gate in dict.fromkeys(gates):
            print(f"  FAIL  {gate}")
    if args.allow_failures:
        return 0
    return 1 if gates else 0


if __name__ == "__main__":
    raise SystemExit(main())
