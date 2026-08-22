from __future__ import annotations

from pathlib import Path

from app.chunking import chunk_markdown
from evals.targets.render_demo import CASES


ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "docs" / "targets" / "render"


def test_render_demo_has_five_unique_officially_sourced_cases() -> None:
    assert len(CASES) == 5
    assert len({case.id for case in CASES}) == 5
    assert all(case.official_url.startswith("https://render.com/docs/") for case in CASES)
    assert all(case.expected_source in case.allowed_sources for case in CASES)


def test_every_expected_source_exists_in_the_attributed_corpus() -> None:
    source_ids: set[str] = set()
    for path in CORPUS.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        assert "Official source" in text or "Official sources" in text
        assert "Verified: 2026-08-22" in text
        source_ids.update(
            chunk.citation_id
            for chunk in chunk_markdown(path.name, text)
            if chunk.citation_id
        )

    assert {case.expected_source for case in CASES}.issubset(source_ids)


def test_required_concept_groups_are_nonempty() -> None:
    for case in CASES:
        assert case.required_concepts
        assert all(group and all(term.strip() for term in group) for group in case.required_concepts)


def test_health_case_rejects_the_ambiguous_conditional_found_by_reader_review() -> None:
    case = next(case for case in CASES if case.id == "RENDER-002")

    assert "unless" in case.forbidden_phrases
    assert any(
        "will not replace" in phrase or "keeps traffic" in phrase
        for phrase in case.required_concepts[-1]
    )
