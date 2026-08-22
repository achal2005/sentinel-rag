"""Flexible data contracts for golden cases, observations, and results.

The golden file is intentionally allowed to evolve.  Known fields get convenient
accessors, while every unknown field is retained in the raw mappings so richer
domain bindings do not require a schema migration in the runner.
"""
from __future__ import annotations

import dataclasses
import enum
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping


class Status(str, enum.Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    ERROR = "ERROR"


@dataclass(frozen=True)
class GoldenCase:
    id: str
    category: str
    user_input: str
    expected: dict[str, Any]
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GoldenCase":
        # Support both the new skeleton (`user_input`) and the original Meridian
        # golden set (`input`).  Future fields remain available through `raw`.
        text = value.get("user_input", value.get("input", ""))
        return cls(
            id=str(value.get("id", "")).strip(),
            category=str(value.get("category", "uncategorized")).strip(),
            user_input=str(text or ""),
            expected=dict(value.get("expected") or {}),
            raw=dict(value),
        )


@dataclass
class Observation:
    router_route: str | None = None
    route: str | None = None
    intent: str | None = None
    retrieval_performed: bool = False
    retrieved_chunks: list[dict[str, Any]] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    selected_tool: str | None = None
    tool_parameters: dict[str, Any] = field(default_factory=dict)
    parameter_valid: bool | None = None
    approval_required: bool = False
    tool_executed: bool = False
    tool_execution_count: int = 0
    escalation: bool = False
    final_response: str = ""
    reason: str | None = None
    audit_steps: list[dict[str, Any]] = field(default_factory=list)
    latency_ms: int | None = None
    model: str | None = None
    provider: str | None = None
    llm_calls: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost_usd: float | None = None
    run_id: int | None = None
    fallback_used: bool | None = None
    retries: int | None = None
    duplicate_execution_count: int | None = None
    trace_metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class CheckResult:
    name: str
    status: Status
    expected: Any = None
    actual: Any = None
    reason: str = ""
    metric: str | None = None
    critical: bool = False


@dataclass
class CaseResult:
    case: GoldenCase
    observation: Observation | None
    checks: list[CheckResult]
    duration_ms: int = 0

    @property
    def status(self) -> Status:
        statuses = {check.status for check in self.checks}
        if Status.ERROR in statuses:
            return Status.ERROR
        if Status.FAILED in statuses:
            return Status.FAILED
        # A case is only a full pass when every required check was executable.
        # Capability-level pass metrics are still retained for checks that ran.
        if Status.NOT_IMPLEMENTED in statuses:
            return Status.NOT_IMPLEMENTED
        if Status.PASSED in statuses:
            return Status.PASSED
        return Status.NOT_IMPLEMENTED

    @property
    def failed_checks(self) -> list[CheckResult]:
        return [c for c in self.checks if c.status in {Status.FAILED, Status.ERROR}]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case.id,
            "category": self.case.category,
            "input": self.case.user_input,
            "expected": self.case.expected,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "checks": [_jsonable(c) for c in self.checks],
            "observation": _jsonable(self.observation),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any], case: GoldenCase) -> "CaseResult":
        observation_value = value.get("observation")
        observation = (
            Observation(**_known_fields(Observation, observation_value))
            if isinstance(observation_value, Mapping)
            else None
        )
        checks = [
            CheckResult(
                name=str(item.get("name", "checkpoint_check")),
                status=Status(str(item.get("status", Status.ERROR.value))),
                expected=item.get("expected"),
                actual=item.get("actual"),
                reason=str(item.get("reason", "")),
                metric=item.get("metric"),
                critical=bool(item.get("critical", False)),
            )
            for item in value.get("checks", [])
            if isinstance(item, Mapping)
        ]
        return cls(
            case=case,
            observation=observation,
            checks=checks,
            duration_ms=int(value.get("duration_ms", 0) or 0),
        )


def load_dataset(path: Path) -> tuple[dict[str, Any], list[GoldenCase]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        meta: dict[str, Any] = {}
        rows = payload
    else:
        meta = {key: value for key, value in payload.items() if key != "cases"}
        rows = payload.get("cases")
    if not isinstance(rows, list):
        raise ValueError(f"{path} must contain a top-level case list or a 'cases' list")
    cases = [GoldenCase.from_dict(row) for row in rows]
    missing_ids = [index for index, case in enumerate(cases) if not case.id]
    if missing_ids:
        raise ValueError(f"golden cases at indexes {missing_ids[:5]} have no id")
    ids = [case.id for case in cases]
    duplicates = sorted({case_id for case_id in ids if ids.count(case_id) > 1})
    if duplicates:
        raise ValueError(f"duplicate golden case ids: {duplicates[:10]}")
    declared = meta.get("total_cases")
    if declared is not None and int(declared) != len(cases):
        raise ValueError(f"dataset declares {declared} cases but contains {len(cases)}")
    return meta, cases


def filter_cases(
    cases: Iterable[GoldenCase],
    *,
    categories: set[str] | None = None,
    case_ids: set[str] | None = None,
    limit: int | None = None,
) -> list[GoldenCase]:
    selected = [
        case
        for case in cases
        if (not categories or case.category in categories)
        and (not case_ids or case.id in case_ids)
    ]
    return selected[:limit] if limit is not None else selected


def _jsonable(value: Any) -> Any:
    if value is None:
        return None
    if dataclasses.is_dataclass(value):
        return {key: _jsonable(val) for key, val in dataclasses.asdict(value).items()}
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _jsonable(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _known_fields(cls: type, value: Mapping[str, Any]) -> dict[str, Any]:
    names = {item.name for item in dataclasses.fields(cls)}
    return {key: val for key, val in value.items() if key in names}
