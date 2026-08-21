"""Cited answer generation with the citations-or-escalate rule.

If retrieval confidence is too low, or the model cannot ground its answer in the
retrieved Meridian docs, we escalate instead of fabricating. Every grounded
answer must cite section ids like [key-06].
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import lf
from .config import CONFIDENCE_MIN
from .embed import chat
from .retrieve import Hit, search

CITATION_TOKEN = re.compile(r"\[([a-z]+-\d+)\]")
ESCALATE_MARKER = "ESCALATE"

SYSTEM = (
    "You are Meridian's support assistant. Answer ONLY using the SOURCES provided by "
    "the user. Each source begins with an id in square brackets, e.g. [key-06].\n\n"
    "Citation rules (MANDATORY):\n"
    "- After every factual sentence, cite the id(s) it came from in square brackets, "
    "e.g. 'Rotate the key under Settings -> API Keys [key-06].'\n"
    "- Use ONLY ids that appear in the SOURCES. Never invent an id, URL, price, or step.\n"
    "- Finish with a line: 'Sources: [id], [id]' listing every id you used.\n"
    f"- If the SOURCES do not contain the answer, reply with exactly {ESCALATE_MARKER} "
    "and nothing else.\n\n"
    "Example answer:\n"
    "You can create a secret key from Settings -> API Keys [key-03]. Keys are shown "
    "once, so store them securely [key-09].\nSources: [key-03], [key-09]"
)


@dataclass
class Answer:
    query: str
    text: str
    escalated: bool
    citations: list[str]
    hits: list[Hit] = field(default_factory=list)
    reason: str = ""


def _format_sources(hits: list[Hit]) -> str:
    blocks = []
    for h in hits:
        tag = h.citation_id or "(no-id)"
        blocks.append(f"[{tag}] ({h.doc} — {h.heading})\n{h.content}")
    return "\n\n---\n\n".join(blocks)


def answer(query: str, conn=None) -> Answer:
    hits = search(query, conn=conn)

    # Langfuse: the retrieved chunks, logged BEFORE the answer generation so the
    # trace reads chunks -> prompt (no-op if tracing is disabled).
    lf.span(
        "retrieve",
        input=query,
        output=[h.citation_id or f"chunk:{h.id}" for h in hits],
        chunk_ids=[h.id for h in hits],
        headings=[h.heading for h in hits],
        top_similarity=round(hits[0].similarity, 4) if hits else None,
    )

    # Confidence gate: nothing retrieved, or top hit too weak -> escalate.
    if not hits or hits[0].similarity < CONFIDENCE_MIN:
        return Answer(
            query=query,
            text="I don't have enough information in the Meridian docs to answer "
            "this confidently, so I'm escalating it to a human.",
            escalated=True,
            citations=[],
            hits=hits,
            reason="low_retrieval_confidence",
        )

    sources = _format_sources(hits)
    user = f"Question:\n{query}\n\nSources:\n{sources}"
    lf.label("answer")  # name this generation in the Langfuse trace
    raw = chat(SYSTEM, user)

    raw_upper = raw.strip().upper()
    if (
        raw_upper.startswith(ESCALATE_MARKER)
        or "ESCALATE" in raw_upper
        or "NO INFORMATION PROVIDED" in raw_upper
        or "NOT MENTIONED" in raw_upper
        or "NOT CONTAIN" in raw_upper
        or "DOES NOT PROVIDE" in raw_upper
    ):
        return Answer(
            query=query,
            text="I couldn't ground an answer in the Meridian docs, so I'm "
            "escalating it to a human.",
            escalated=True,
            citations=[],
            hits=hits,
            reason="model_declined",
        )

    cited = list(dict.fromkeys(CITATION_TOKEN.findall(raw)))
    retrieved_ids = {h.citation_id for h in hits if h.citation_id}
    # Only keep citations that were actually in the retrieved set (no fabrication).
    grounded = [c for c in cited if c in retrieved_ids]

    return Answer(
        query=query,
        text=raw,
        escalated=False,
        citations=grounded,
        hits=hits,
        reason="answered" if grounded else "answered_without_valid_citation",
    )
