"""FastAPI HTTP entry point for Sentinel.

Exposes two POST endpoints:
- /ask     : Week-1 RAG answerer (cited answer or escalation).
- /triage  : Week-2 full graph (router -> answer | action | escalate), returning
             the routing decision + outcome + evidence in one structured payload.
             This is what the frontend console calls.
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import tools
from .answer import answer
from .config import (
    CHAT_MODEL,
    CONFIDENCE_MIN,
    EMBED_MODEL,
    EMBED_PROVIDER,
    LANGFUSE_ENABLED,
    LLM_PROVIDER,
    RETRIEVAL_TOPK,
    TRACE_ENABLED,
)
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
    # Cost / trace summary for this run (see app/trace.py).
    run_id: int | None = None
    llm_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    confidence_min: float = CONFIDENCE_MIN


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


@app.get("/system")
def system_info() -> dict[str, Any]:
    """Public, non-secret runtime facts used by the operator console.

    This keeps model, retrieval, and tool claims in the UI tied to the code that
    is actually running instead of duplicating them as marketing constants.
    """
    return {
        "service": app.title,
        "version": app.version,
        "provider": LLM_PROVIDER,
        "embed_provider": EMBED_PROVIDER,
        "chat_model": CHAT_MODEL,
        "embed_model": EMBED_MODEL,
        "retrieval_topk": RETRIEVAL_TOPK,
        "confidence_min": CONFIDENCE_MIN,
        "tools": [
            {
                "name": tool.name,
                "risk_level": tool.risk_level,
                "required_params": tool.required_params(),
            }
            for tool in tools.list_tools()
        ],
        "tracing_enabled": TRACE_ENABLED,
        "langfuse_enabled": LANGFUSE_ENABLED,
    }


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


# --- approval queue (Week 3 safety) ----------------------------------------

class ApprovalItem(BaseModel):
    id: int
    created_at: datetime
    tool: str
    risk_level: str
    status: str
    reason: str | None = None
    request: str | None = None
    urgency: str | None = None
    run_id: int | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class ApprovalDecision(BaseModel):
    decided_by: str = Field("operator", description="Who approved/rejected")


class ApprovalActionResult(BaseModel):
    id: int
    tool: str | None = None
    status: str
    executed: bool = False
    error: str | None = None


@app.get("/approvals", response_model=list[ApprovalItem])
def list_approvals(status: str = "pending", limit: int = 50) -> list[ApprovalItem]:
    """High-risk actions parked in the approval queue. `status=all` for every row."""
    rows = tools.list_approvals(
        status=None if status == "all" else status, limit=limit
    )
    return [ApprovalItem(**r) for r in rows]


@app.post("/approvals/{approval_id}/approve", response_model=ApprovalActionResult)
def approve_approval(
    approval_id: int, body: ApprovalDecision | None = None
) -> ApprovalActionResult:
    """Approve a queued action — this TRIGGERS its tool (fires the n8n webhook)."""
    who = body.decided_by if body else "operator"
    try:
        result = tools.approve(approval_id, decided_by=who)
    except tools.ApprovalNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except tools.ApprovalNotPending as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return ApprovalActionResult(**result)


@app.post("/approvals/{approval_id}/reject", response_model=ApprovalActionResult)
def reject_approval(
    approval_id: int, body: ApprovalDecision | None = None
) -> ApprovalActionResult:
    """Reject (close) a queued action without running its tool."""
    who = body.decided_by if body else "operator"
    try:
        result = tools.reject(approval_id, decided_by=who)
    except tools.ApprovalNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except tools.ApprovalNotPending as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return ApprovalActionResult(**result)


@app.get("/runs/{run_id}/audit")
def run_audit(run_id: int) -> list[dict[str, Any]]:
    """The per-step audit trail for one graph run (router → retrieve/tool → outcome)."""
    from . import audit
    return audit.for_run(run_id)


# --- runs / inbox / stats (Week 3 glass) -----------------------------------

class RunRow(BaseModel):
    id: int
    created_at: datetime
    channel: str = "web_form"
    sender: str | None = None
    request: str
    route: str = "escalate"
    reason: str | None = None
    escalated: bool = False
    model: str | None = None
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    action_status: str | None = None


class RunAuditStep(BaseModel):
    step: str
    detail: dict[str, Any] = Field(default_factory=dict)


class RunDetail(RunRow):
    citations: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    steps: list[RunAuditStep] = Field(default_factory=list)


class StatBreakdown(BaseModel):
    label: str
    count: int


class UsageStats(BaseModel):
    requests_today: int
    pending_approvals: int
    avg_latency_ms: int
    escalation_rate: float
    cost_today: float
    cost_mtd: float
    model_split: list[StatBreakdown]
    channel_split: list[StatBreakdown]


def _run_row(r: dict[str, Any]) -> RunRow:
    return RunRow(
        id=r["id"],
        created_at=r["created_at"],
        channel=r.get("channel") or "web_form",
        sender=r.get("sender"),
        request=r["request"],
        route=r.get("route") or "escalate",
        reason=r.get("reason"),
        escalated=bool(r.get("escalated", False)),
        model=r.get("model"),
        total_tokens=int(r.get("total_tokens") or 0),
        cost_usd=float(r.get("cost_usd") or 0),
        latency_ms=int(r.get("latency_ms") or 0),
        action_status=r.get("action_status"),
    )


@app.get("/runs", response_model=list[RunRow])
def list_runs(limit: int = 30) -> list[RunRow]:
    """Recent triage runs — the Inbox, newest first."""
    from . import trace
    return [_run_row(r) for r in trace.recent(limit=limit)]


@app.get("/runs/{run_id}", response_model=RunDetail)
def get_run(run_id: int) -> RunDetail:
    """One run's full trace: the run row + citations + per-step audit trail."""
    from . import audit, trace
    row = trace.get_run(run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="run not found")
    steps = [RunAuditStep(step=s["step"], detail=s.get("detail") or {}) for s in audit.for_run(run_id)]
    base = _run_row(row).model_dump()
    return RunDetail(**base, citations=list(row.get("citations") or []), sources=[], steps=steps)


@app.get("/stats", response_model=UsageStats)
def usage_stats() -> UsageStats:
    """Aggregate usage + cost stats for the dashboard (today + this month)."""
    from . import trace
    return UsageStats(**trace.stats())


@app.post("/triage", response_model=TriageResponse)
def handle_triage(req: TriageRequest) -> TriageResponse:
    """Route the request through the graph and return decision + outcome + evidence."""
    started = time.perf_counter()
    state = run_graph(req.query, channel=req.channel)
    latency_ms = int((time.perf_counter() - started) * 1000)

    decision = state.get("decision")
    action = state.get("action")
    usage = state.get("usage") or {}
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
        # The action dict holds ticket params (subject/body/...), not these fields,
        # so build the summary from the triage decision + action status.
        action=PlannedAction(
            intent=decision.intent if decision else "unspecified",
            urgency=action.get("urgency") or (decision.urgency if decision else "low"),
            status=action.get("status", "pending"),
            request=req.query,
        ) if action else None,
        latency_ms=latency_ms,
        run_id=state.get("run_id"),
        llm_calls=usage.get("llm_calls", 0),
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
        total_tokens=usage.get("total_tokens", 0),
        cost_usd=usage.get("cost_usd", 0.0),
        confidence_min=CONFIDENCE_MIN,
    )
