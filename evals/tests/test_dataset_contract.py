from __future__ import annotations

import re
from collections import Counter

from evals.runners.agentops_adapter import ROOT
from evals.runners.evaluator import _pipeline_binding_blockers
from evals.schema import load_dataset
from app import tools

DATASET = ROOT / "evals" / "golden" / "agentops_meridian_300_cases.json"
EXPECTED_COUNTS = {
    "rag": 30,
    "citation_faithfulness": 25,
    "intent_routing": 25,
    "tool_selection": 30,
    "tool_parameters": 25,
    "approval_and_safety": 30,
    "escalation": 25,
    "adversarial_security": 30,
    "reliability": 25,
    "multi_turn": 20,
    "ambiguity": 20,
    "out_of_scope": 15,
}


def test_domain_bound_suite_has_expected_shape() -> None:
    metadata, cases = load_dataset(DATASET)
    assert metadata["total_cases"] == 300
    assert Counter(case.category for case in cases) == EXPECTED_COUNTS


def test_every_pipeline_case_is_bound() -> None:
    _, cases = load_dataset(DATASET)
    registered = set(tools.REGISTRY)
    blockers = {
        case.id: _pipeline_binding_blockers(case, registered_tools=registered)
        for case in cases
    }
    assert {case_id: value for case_id, value in blockers.items() if value} == {}


def test_sources_and_tool_parameters_exist_in_production_contracts() -> None:
    _, cases = load_dataset(DATASET)
    citation_ids: set[str] = set()
    for path in (ROOT / "docs").glob("*.md"):
        citation_ids.update(re.findall(r"\[([a-z]+-\d+)\]", path.read_text(encoding="utf-8")))

    for case in cases:
        for source in case.expected.get("expected_sources", []):
            assert source in citation_ids, f"{case.id}: unknown citation {source}"
        expected_tool = case.expected.get("expected_tool")
        if expected_tool:
            assert expected_tool in tools.REGISTRY
            schema_fields = set(tools.PARAM_MODELS[expected_tool].model_fields)
            assert set(case.expected.get("expected_parameters", {})) <= schema_fields


def test_structured_scenarios_have_executable_contracts() -> None:
    _, cases = load_dataset(DATASET)
    for case in cases:
        if case.category == "reliability":
            scenario = case.raw.get("fault_scenario")
            assert isinstance(scenario, dict) and scenario.get("kind")
            assert isinstance(case.expected.get("fault_outcome"), dict)
        if case.category == "multi_turn":
            turns = case.raw.get("turns")
            assert isinstance(turns, list) and len(turns) >= 2
            assert case.expected.get("resolved_contains")
