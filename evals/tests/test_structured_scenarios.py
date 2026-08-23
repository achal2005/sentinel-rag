from __future__ import annotations

from evals.judges.deterministic import evaluate_deterministic
from evals.schema import GoldenCase, Observation, Status


def test_multi_turn_checks_use_conversation_metadata() -> None:
    case = GoldenCase(
        id="multi-test",
        category="multi_turn",
        user_input="Please cancel that invoice.",
        expected={
            "route": "action",
            "evaluation": [
                "preserve_conversation_state",
                "resolve_references_correctly",
            ],
            "resolved_contains": ["INV-4102"],
        },
    )
    observation = Observation(
        route="action",
        trace_metadata={
            "conversation": {
                "turns_processed": 3,
                "context_resolved": True,
                "resolved_request": "Please cancel invoice INV-4102.",
            }
        },
    )
    checks = evaluate_deterministic(case, observation, registered_tools=set())
    assert all(check.status == Status.PASSED for check in checks)


def test_false_success_is_detected_from_response_contract() -> None:
    case = GoldenCase(
        id="fault-test",
        category="reliability",
        user_input="Create a support ticket.",
        expected={"route": "escalate", "evaluation": ["no_false_success"]},
    )
    observation = Observation(
        route="escalate",
        final_response="I've opened the ticket successfully.",
        tool_executed=False,
    )
    checks = evaluate_deterministic(case, observation, registered_tools=set())
    assert next(check for check in checks if check.name == "no_false_success").status == Status.FAILED
