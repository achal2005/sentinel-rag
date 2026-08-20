"""FastAPI HTTP entry point for Sentinel.

Exposes two POST endpoints:
- /ask     : Week-1 RAG answerer (cited answer or escalation).
- /triage  : Week-2 full graph (router -> answer | action | escalate), returning
             the routing decision + outcome + evidence in one structured payload.
             This is what the frontend console calls.
"""
from __future__ import annotations

import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .answer import answer
from .graph import run as run_graph

app = FastAPI(
    title="Sentinel API",
    description="Agentic support-operations API: routing, grounded citations, escalation.",
    version="0.2.0",
)

# The Next.js console talks to us over HTTP (direct, or via its proxy route).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- shared models ---------------------------------------------------------

class Source(BaseModel):
    citation_id: str | None = None
    doc: str
    heading: str
    similarity: float


# --- /ask (Week 1) ---------------------------------------------------------

class AskRequest(BaseModel):
    query: str = Field(..., description="The user question or support request")
    channel: str = Field("web_form", description="Channel origin (web_form, email, whatsapp)")


class AskResponse(BaseModel):
    query: str
    text: str
    escalated: bool
    citations: list[str]
    reason: str
    sources: list[Source]


# --- /triage (Week 2 graph) ------------------------------------------------

class TriageRequest(BaseModel):
    query: str = Field(..., description="The incoming support request")
    channel: str = Field("web_form", description="Channel origin")


class PlannedAction(BaseModel):
    intent: str
    urgency: str
    status: str
    request: str


class TriageResponse(BaseModel):
    query: str
    route: str = Field(..., description="answer | action | escalate | spam")
    intent: str
    urgency: str
    action_required: bool
    answer: str
    escalated: bool
    reason: str
    citations: list[str]
    sources: list[Source]
    action: PlannedAction | None = None
    latency_ms: int


def _sources(hits) -> list[Source]:
    return [
        Source(
            citation_id=h.citation_id,
            doc=h.doc,
            heading=h.heading,
            similarity=round(h.similarity, 3),
        )
        for h in hits
    ]


@app.get("/health")
def health() -> dict[str, str]:
    """Simple health check endpoint."""
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def handle_ask(req: AskRequest) -> AskResponse:
    """Run RAG retrieval and cited answer generation."""
    ans = answer(req.query)
    return AskResponse(
        query=ans.query,
        text=ans.text,
        escalated=ans.escalated,
        citations=ans.citations,
        reason=ans.reason,
        sources=_sources(ans.hits),
    )


@app.post("/triage", response_model=TriageResponse)
def handle_triage(req: TriageRequest) -> TriageResponse:
    """Route the request through the graph and return decision + outcome + evidence."""
    started = time.perf_counter()
    state = run_graph(req.query)
    latency_ms = int((time.perf_counter() - started) * 1000)

    decision = state.get("decision")
    action = state.get("action")
    return TriageResponse(
        query=req.query,
        route=state.get("route", "escalate"),
        intent=decision.intent if decision else "unspecified",
        urgency=decision.urgency if decision else "low",
        action_required=bool(decision.action_required) if decision else False,
        answer=state.get("answer", ""),
        escalated=bool(state.get("escalated", False)),
        reason=state.get("reason", ""),
        citations=state.get("citations", []),
        sources=_sources(state.get("hits") or []),
        action=PlannedAction(**action) if action else None,
        latency_ms=latency_ms,
    )
