"""Unit tests for honest evaluation denominators."""
from __future__ import annotations

from evals.runners.evaluator import _pipeline_binding_blockers
from evals.schema import GoldenCase


REGISTERED = {"create_ticket", "cancel_invoice"}


def _case(category: str, expected: dict) -> GoldenCase:
    return GoldenCase(
        id="binding-test",
        category=category,
        user_input="test request",
        expected=expected,
    )


def test_approval_case_without_named_tool_is_domain_binding_work() -> None:
    blockers = _pipeline_binding_blockers(
        _case(
            "approval_and_safety",
            {"requires_tool": True, "requires_approval": True},
        ),
        registered_tools=REGISTERED,
    )
    assert blockers
    assert blockers[0][0] == "domain_tool_binding"
    assert blockers[0][3] is True


def test_unregistered_expected_tool_is_domain_binding_work() -> None:
    blockers = _pipeline_binding_blockers(
        _case(
            "tool_selection",
            {"requires_tool": True, "tool": "send_external_message"},
        ),
        registered_tools=REGISTERED,
    )
    assert blockers
    assert "not registered" in blockers[0][1]


def test_registered_tool_case_remains_executable() -> None:
    blockers = _pipeline_binding_blockers(
        _case(
            "tool_selection",
            {"requires_tool": True, "tool": "create_ticket"},
        ),
        registered_tools=REGISTERED,
    )
    assert blockers == []
