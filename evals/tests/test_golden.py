"""Parametrized pytest execution of the real AgentOps graph.

Environment filters keep local iterations small without changing the dataset:

    AGENTOPS_EVAL_CATEGORY=adversarial_security pytest evals/
    AGENTOPS_EVAL_LIMIT=5 pytest evals/
"""
from __future__ import annotations

import json
import os

import pytest

from evals.runners.agentops_adapter import AgentOpsAdapter, ROOT
from evals.runners.evaluator import Evaluator
from evals.schema import Status, filter_cases, load_dataset

DATASET = ROOT / "evals" / "golden" / "agentops_meridian_300_cases.json"
_, _ALL_CASES = load_dataset(DATASET)
_CATEGORY = os.getenv("AGENTOPS_EVAL_CATEGORY")
_LIMIT = int(os.environ["AGENTOPS_EVAL_LIMIT"]) if os.getenv("AGENTOPS_EVAL_LIMIT") else None
CASES = filter_cases(
    _ALL_CASES,
    categories={_CATEGORY} if _CATEGORY else None,
    limit=_LIMIT,
)


@pytest.fixture(scope="session")
def evaluator() -> Evaluator:
    # Semantic judging is opt-in through the CLI; pytest focuses on reproducible
    # deterministic assertions and shows semantic requirements as NI checks.
    return Evaluator(AgentOpsAdapter(export_langfuse=False))


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_golden_case(case, evaluator: Evaluator) -> None:
    result = evaluator.evaluate(case)
    if result.status == Status.NOT_IMPLEMENTED:
        pytest.skip("; ".join(check.reason for check in result.checks))
    if result.status in {Status.FAILED, Status.ERROR}:
        detail = {
            "case_id": case.id,
            "category": case.category,
            "input": case.user_input,
            "expected": case.expected,
            "actual": result.to_dict().get("observation"),
            "failed_checks": [
                {
                    "name": check.name,
                    "expected": check.expected,
                    "actual": check.actual,
                    "reason": check.reason,
                    "critical": check.critical,
                }
                for check in result.failed_checks
            ],
        }
        pytest.fail(json.dumps(detail, indent=2, ensure_ascii=False), pytrace=False)
