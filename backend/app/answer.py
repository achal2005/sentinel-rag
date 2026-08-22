"""Cited answer generation with the citations-or-escalate rule.

If retrieval confidence is too low, or the model cannot ground its answer in the
retrieved Meridian docs, we escalate instead of fabricating. Every grounded
answer must cite section ids like [key-06].
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from psycopg import Error as PostgresError

from . import lf
from .config import CONFIDENCE_MIN, PRODUCT_NAME
from .embed import ModelProviderError, chat
from .retrieve import Hit, search

CITATION_TOKEN = re.compile(r"\[([a-z]+-\d+)\]")
ESCALATE_MARKER = "ESCALATE"
log = logging.getLogger("sentinel.answer")

SYSTEM = (
    f"You are {PRODUCT_NAME}'s support assistant. Answer ONLY using the SOURCES provided by "
    "the user. Each source begins with an id in square brackets, e.g. [key-06].\n\n"
    "Citation rules (MANDATORY):\n"
    "- After every factual sentence, cite the id(s) it came from in square brackets, "
    "e.g. 'Rotate the key under Settings -> API Keys [key-06].'\n"
    "- Use ONLY ids that appear in the SOURCES. Never invent an id, URL, price, or step.\n"
    "- Use the smallest sufficient source set. Do not cite a retrieved source unless it "
    "directly supports a claim in your answer.\n"
    "- State operational conditions in direct if/then form. Avoid ambiguous 'unless' "
    "constructions that can reverse the documented outcome.\n"
    "- Match each condition in the question to the rule for that exact condition. Do not "
    "substitute a different caveat or exception from another source.\n"
    "- Answer every part of the question explicitly before adding optional context.\n"
    "- The final Sources line must list only ids cited in the answer body. Do not append "
    "notes or commentary after that line.\n"
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


def _finish_at_sources_line(text: str) -> str:
    """Enforce the prompt contract that ``Sources:`` is the final line.

    Small local models occasionally append a postscript that names retrieved
    IDs they deliberately did *not* use.  Counting those tokens as citations
    makes irrelevant references look grounded.  Keep the first explicit source
    list and discard anything after it.
    """
    lines = text.strip().splitlines()
    for index, line in enumerate(lines):
        if re.match(r"^\s*(?:\*\*)?sources(?:\*\*)?\s*:", line, re.I):
            return "\n".join(lines[: index + 1]).strip()
    return text.strip()


def answer(query: str, conn=None) -> Answer:
    try:
        hits = search(query, conn=conn)
    except (PostgresError, ModelProviderError, OSError) as exc:
        # Retrieval depends on both Postgres and Ollama embeddings.  Either
        # dependency being unavailable must fail closed: return a safe human
        # handoff rather than bubbling a 500 or fabricating an uncited answer.
        log.warning("retrieval dependency unavailable; escalating: %s", exc)
        return Answer(
            query=query,
            text=(
                "I can't reach the retrieval services right now, so I can't "
                f"verify an answer against the {PRODUCT_NAME} docs. I'm escalating "
                "this to a human."
            ),
            escalated=True,
            citations=[],
            hits=[],
            reason="retrieval_dependency_unavailable",
        )

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
            text=f"I don't have enough information in the {PRODUCT_NAME} docs to answer "
            "this confidently, so I'm escalating it to a human.",
            escalated=True,
            citations=[],
            hits=hits,
            reason="low_retrieval_confidence",
        )

    sources = _format_sources(hits)
    user = f"Question:\n{query}\n\nSources:\n{sources}"
    lf.label("answer")  # name this generation in the Langfuse trace
    raw = _finish_at_sources_line(chat(SYSTEM, user))

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
            text=f"I couldn't ground an answer in the {PRODUCT_NAME} docs, so I'm "
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
