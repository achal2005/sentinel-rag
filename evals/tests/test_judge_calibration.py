from __future__ import annotations

import json

from evals.judges.calibrate import (
    CALIBRATION_VERSION,
    calibration_anchors,
    prompt_fingerprint,
    run_calibration,
    validate_calibration_report,
)
from evals.judges.llm_judge import SemanticScores


class PassingJudge:
    def judge(self, case, observation) -> SemanticScores:
        values = {
            "CAL-CORRECT": (0.95, 0.95, False, 0.95, False),
            "CAL-WRONG": (0.1, 0.8, False, 0.8, False),
            "CAL-UNSUPPORTED": (0.6, 0.5, True, 0.8, False),
            "CAL-CITATION-MISMATCH": (0.8, 0.1, True, 0.8, False),
            "CAL-CLARIFY": (0.8, 1.0, False, 1.0, True),
            "CAL-REFUSAL": (0.9, 1.0, False, 0.95, False),
        }
        correctness, faithfulness, unsupported, policy, clarified = values[case.id]
        return SemanticScores(
            correctness=correctness,
            citation_faithfulness=faithfulness,
            unsupported_claims=unsupported,
            policy_compliance=policy,
            asked_clarifying_question=clarified,
            reason="scripted calibration result",
            provider="test",
            model="judge-test",
        )


def test_anchor_ids_are_stable_and_unique() -> None:
    ids = [anchor.case.id for anchor in calibration_anchors()]
    assert len(ids) == len(set(ids)) == 6


def test_passing_judge_produces_release_eligible_report(tmp_path) -> None:
    report = run_calibration(PassingJudge())
    assert report["passed"] is True
    assert report["anchors_passed"] == report["anchors_total"] == 6
    path = tmp_path / "calibration.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    assert validate_calibration_report(path, model="judge-test") == []


def test_report_rejected_after_model_or_prompt_mismatch(tmp_path) -> None:
    path = tmp_path / "calibration.json"
    path.write_text(
        json.dumps(
            {
                "calibration_version": CALIBRATION_VERSION,
                "judge_prompt_sha256": prompt_fingerprint(),
                "model": "judge-a",
                "passed": True,
            }
        ),
        encoding="utf-8",
    )
    errors = validate_calibration_report(path, model="judge-b")
    assert any("does not match" in error for error in errors)
