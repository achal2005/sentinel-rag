"""Measured summaries and human/machine-readable evaluation reports."""
from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from evals.schema import CaseResult, Status


def summarize(results: list[CaseResult], dataset_meta: dict[str, Any]) -> dict[str, Any]:
    statuses = Counter(result.status.value for result in results)
    check_metrics: dict[str, Counter[str]] = defaultdict(Counter)
    categories: dict[str, Counter[str]] = defaultdict(Counter)
    critical_failures: list[dict[str, Any]] = []
    critical_unverified: list[dict[str, Any]] = []

    for result in results:
        categories[result.case.category][result.status.value] += 1
        for check in result.checks:
            if check.metric:
                check_metrics[check.metric][check.status.value] += 1
            if check.critical and check.status in {Status.FAILED, Status.ERROR}:
                critical_failures.append(
                    {
                        "case_id": result.case.id,
                        "category": result.case.category,
                        "check": check.name,
                        "expected": check.expected,
                        "actual": check.actual,
                        "reason": check.reason,
                    }
                )
            elif check.critical and check.status == Status.NOT_IMPLEMENTED:
                critical_unverified.append(
                    {
                        "case_id": result.case.id,
                        "category": result.case.category,
                        "check": check.name,
                        "reason": check.reason,
                    }
                )

    metrics = {
        name: _metric(counter)
        for name, counter in sorted(check_metrics.items())
    }
    executed = statuses[Status.PASSED.value] + statuses[Status.FAILED.value] + statuses[Status.ERROR.value]
    overall_pass_rate = statuses[Status.PASSED.value] / executed if executed else None
    category_rows = {
        category: {
            "total": sum(counter.values()),
            "passed": counter[Status.PASSED.value],
            "failed": counter[Status.FAILED.value],
            "errors": counter[Status.ERROR.value],
            "not_implemented": counter[Status.NOT_IMPLEMENTED.value],
            "rate": _category_rate(counter),
        }
        for category, counter in sorted(categories.items())
    }
    headline_metrics = _headline_metrics(metrics, category_rows, overall_pass_rate)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": dataset_meta,
        "total": len(results),
        "executed": executed,
        "passed": statuses[Status.PASSED.value],
        "failed": statuses[Status.FAILED.value],
        "errors": statuses[Status.ERROR.value],
        "not_implemented": statuses[Status.NOT_IMPLEMENTED.value],
        "overall_pass_rate": overall_pass_rate,
        "critical_policy_passed": not critical_failures and not critical_unverified,
        "critical_failures": critical_failures,
        "critical_unverified": critical_unverified,
        "metrics": metrics,
        "headline_metrics": headline_metrics,
        "categories": category_rows,
    }


def write_reports(
    report_dir: Path,
    results: list[CaseResult],
    summary: dict[str, Any],
) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = report_dir / f"agentops_eval_{stamp}.json"
    markdown_path = report_dir / f"agentops_eval_{stamp}.md"
    payload = {"summary": summary, "results": [result.to_dict() for result in results]}
    json_text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    markdown_text = render_markdown(summary, results)
    json_path.write_text(json_text, encoding="utf-8")
    markdown_path.write_text(markdown_text, encoding="utf-8")
    (report_dir / "latest.json").write_text(json_text, encoding="utf-8")
    (report_dir / "latest.md").write_text(markdown_text, encoding="utf-8")
    return json_path, markdown_path


def write_checkpoint(
    path: Path,
    results: list[CaseResult],
    *,
    run_config: dict[str, Any],
) -> None:
    """Atomically persist partial results so an interrupted run can resume."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "checkpoint_version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "run_config": run_config,
        "completed_case_ids": [result.case.id for result in results],
        "results": [result.to_dict() for result in results],
    }
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    # OneDrive/antivirus can briefly hold the destination on Windows. Retry the
    # atomic replace, then fall back to a direct checkpoint write rather than
    # aborting an otherwise valid multi-hour evaluation.
    for attempt in range(5):
        try:
            temporary.replace(path)
            break
        except PermissionError:
            if attempt == 4:
                path.write_text(
                    json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                temporary.unlink(missing_ok=True)
                break
            time.sleep(0.05 * (attempt + 1))


def load_checkpoint(
    path: Path,
    *,
    cases_by_id: dict[str, Any],
    expected_config: dict[str, Any],
) -> list[CaseResult]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    actual_config = payload.get("run_config") or {}
    if actual_config != expected_config:
        raise ValueError(
            "checkpoint run configuration differs from this invocation; "
            "remove it or rerun with the same dataset, filters, and judge settings"
        )
    restored: list[CaseResult] = []
    for row in payload.get("results", []):
        case_id = str(row.get("case_id", ""))
        case = cases_by_id.get(case_id)
        if case is None:
            raise ValueError(f"checkpoint contains case {case_id!r} outside this selection")
        restored.append(CaseResult.from_dict(row, case))
    return restored


def render_markdown(summary: dict[str, Any], results: list[CaseResult]) -> str:
    rate = _pct(summary.get("overall_pass_rate"))
    lines = [
        "# AgentOps Evaluation",
        "",
        f"Generated: {summary['generated_at']}",
        "",
        "| Result | Count |",
        "|---|---:|",
        f"| Total cases | {summary['total']} |",
        f"| Executed | {summary['executed']} |",
        f"| Passed | {summary['passed']} |",
        f"| Failed | {summary['failed']} |",
        f"| Errors | {summary['errors']} |",
        f"| Not implemented / domain binding | {summary['not_implemented']} |",
        f"| Overall pass rate (executed only) | {rate} |",
        f"| Critical policy | {'PASS' if summary['critical_policy_passed'] else 'FAIL'} |",
        f"| Critical checks unverified | {len(summary['critical_unverified'])} |",
        "",
        "## Capability metrics",
        "",
        "Denominators include only checks that actually ran; `NOT_IMPLEMENTED` is never counted as a pass.",
        "",
        "| Capability | Passed | Failed/error | Not implemented | Rate |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, metric in summary["metrics"].items():
        lines.append(
            f"| {name} | {metric['passed']} | {metric['failed'] + metric['errors']} | "
            f"{metric['not_implemented']} | {_pct(metric['rate'])} |"
        )
    lines.extend(
        [
            "",
            "## Categories",
            "",
            "| Category | Total | Passed | Failed | Errors | Not implemented |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for name, row in summary["categories"].items():
        lines.append(
            f"| {name} | {row['total']} | {row['passed']} | {row['failed']} | "
            f"{row['errors']} | {row['not_implemented']} |"
        )
    lines.extend(["", "## Critical failures", ""])
    if summary["critical_failures"]:
        lines.extend(["| Case | Category | Check | Detail |", "|---|---|---|---|"])
        for item in summary["critical_failures"]:
            detail = str(item.get("reason") or "mismatch").replace("|", "\\|")
            lines.append(
                f"| {item['case_id']} | {item['category']} | {item['check']} | {detail} |"
            )
    else:
        lines.append("None.")
    lines.extend(["", "## Critical checks not yet verifiable", ""])
    if summary["critical_unverified"]:
        lines.extend(["| Case | Category | Check | Reason |", "|---|---|---|---|"])
        for item in summary["critical_unverified"]:
            reason = str(item.get("reason") or "not implemented").replace("|", "\\|")
            lines.append(
                f"| {item['case_id']} | {item['category']} | {item['check']} | {reason} |"
            )
    else:
        lines.append("None.")
    lines.extend(["", "## Failed and errored cases", ""])
    failed = [result for result in results if result.status in {Status.FAILED, Status.ERROR}]
    if not failed:
        lines.append("None.")
    else:
        lines.extend(["| Case | Category | Failed checks |", "|---|---|---|"])
        for result in failed:
            detail = "; ".join(
                f"{check.name}: {check.reason or 'mismatch'}" for check in result.failed_checks
            ).replace("|", "\\|")
            lines.append(f"| {result.case.id} | {result.case.category} | {detail} |")
    return "\n".join(lines) + "\n"


def print_summary(summary: dict[str, Any]) -> None:
    print("\nAgentOps Evaluation")
    print("-" * 72)
    print(f"Total:             {summary['total']:>5}")
    print(f"Executed:          {summary['executed']:>5}")
    print(f"Passed:            {summary['passed']:>5}")
    print(f"Failed:            {summary['failed']:>5}")
    print(f"Errors:            {summary['errors']:>5}")
    print(f"Not implemented:   {summary['not_implemented']:>5}")
    print(f"Overall pass rate:  {_pct(summary['overall_pass_rate'])}")
    print(f"Critical policy:    {'PASS' if summary['critical_policy_passed'] else 'FAIL'}")
    if summary["critical_unverified"]:
        print(f"Critical unverified:{len(summary['critical_unverified']):>6}")
    print("\nCapabilities (actual denominators only)")
    for name, metric in summary["metrics"].items():
        print(
            f"  {name:28} {metric['passed']:>3}/{metric['denominator']:<3} "
            f"{_pct(metric['rate']):>8}  NI={metric['not_implemented']}"
        )


def threshold_failures(
    summary: dict[str, Any],
    *,
    minimums: dict[str, float | None],
    baseline: dict[str, Any] | None = None,
    max_regression: float | None = None,
) -> list[str]:
    failures: list[str] = []
    for name, minimum in minimums.items():
        if minimum is None:
            continue
        value = summary["overall_pass_rate"] if name == "overall" else summary["metrics"].get(name, {}).get("rate")
        if value is None:
            failures.append(f"{name}: no executable denominator (minimum {minimum:.3f})")
        elif value < minimum:
            failures.append(f"{name}: {value:.3f} is below {minimum:.3f}")
    if not summary["critical_policy_passed"]:
        failures.append(
            "critical policy: "
            f"{len(summary['critical_failures'])} failure(s), "
            f"{len(summary['critical_unverified'])} unverified"
        )
    if baseline is not None and max_regression is not None:
        current = summary.get("overall_pass_rate")
        previous = baseline.get("summary", baseline).get("overall_pass_rate")
        if current is not None and previous is not None and previous - current > max_regression:
            failures.append(
                f"overall regression: {previous - current:.3f} exceeds {max_regression:.3f}"
            )
    return failures


def _metric(counter: Counter[str]) -> dict[str, Any]:
    passed = counter[Status.PASSED.value]
    failed = counter[Status.FAILED.value]
    errors = counter[Status.ERROR.value]
    denominator = passed + failed + errors
    return {
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "not_implemented": counter[Status.NOT_IMPLEMENTED.value],
        "denominator": denominator,
        "rate": passed / denominator if denominator else None,
    }


def _category_rate(counter: Counter[str]) -> float | None:
    denominator = (
        counter[Status.PASSED.value]
        + counter[Status.FAILED.value]
        + counter[Status.ERROR.value]
    )
    return counter[Status.PASSED.value] / denominator if denominator else None


def _headline_metrics(
    metrics: dict[str, dict[str, Any]],
    categories: dict[str, dict[str, Any]],
    overall: float | None,
) -> dict[str, Any]:
    def rate(name: str) -> float | None:
        return metrics.get(name, {}).get("rate")

    citation_basis = next(
        (name for name in ("citation_faithfulness", "citation_grounding", "citations") if rate(name) is not None),
        None,
    )
    adversarial = rate("adversarial_safety")
    if adversarial is None:
        adversarial = categories.get("adversarial_security", {}).get("rate")
    return {
        "overall_pass_rate": overall,
        "routing_accuracy": rate("routing"),
        "tool_selection_accuracy": rate("tool_selection"),
        "approval_safety_success_rate": rate("approval_safety"),
        "citation_success_rate": rate(citation_basis) if citation_basis else None,
        "citation_success_basis": citation_basis,
        "escalation_accuracy": rate("escalation"),
        "adversarial_success_rate": adversarial,
        "reliability_fallback_success_rate": rate("reliability_fallback"),
    }


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"
