"""Week 2 orchestration: a LangGraph StateGraph that wires the pieces together.

    router --(conditional edge)--> answer | action | escalate --> END

The router (Week 2 baseline) triages the request; a single conditional edge then
dispatches to exactly one worker node:

- answer   : run the cited RAG answerer (which may itself escalate if it can't
             ground an answer -- citations-or-escalate is enforced in answer()).
- action   : the request needs a real side effect. We extract ticket params,
             validate them with Pydantic, and fire the create_ticket tool (an
             n8n webhook that inserts a row). If the webhook is unreachable or
             params don't validate, we fall back to queuing for human approval.
- escalate : hand off to a human. Router "spam" is folded in here too, since the
             graph only fans out three ways.

The shared state is intentionally small -- just what flows between nodes.
"""
from __future__ import annotations

import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from . import tools, trace
from .answer import answer as rag_answer
from .retrieve import Hit
from .router import Decision, route as route_request

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


class GraphState(TypedDict, total=False):
    """What flows through the graph. Nodes read/merge these keys."""

    request: str            # the incoming support request (input)
    route: str              # router's chosen branch: answer | action | escalate
    decision: Decision      # full triage decision (intent / urgency / ...)
    hits: list[Hit]         # retrieved chunks (answer path)
    citations: list[str]    # grounded citation ids used in the answer
    answer: str             # final user-facing text (answer or escalation notice)
    action: dict[str, Any]  # planned action for the approval queue (action path)
    escalated: bool         # did we hand off to a human?
    reason: str             # short machine tag for tracing / evals
    run_id: int             # id of the persisted cost/trace row (if logged)
    usage: dict[str, Any]   # token/cost/latency summary for this run


# --- nodes -----------------------------------------------------------------

def router_node(state: GraphState) -> GraphState:
    """Triage the request into a routing decision."""
    d = route_request(state["request"])
    return {"route": d.route, "decision": d}


def answer_node(state: GraphState) -> GraphState:
    """Cited RAG answer (may self-escalate on low confidence)."""
    a = rag_answer(state["request"])
    return {
        "answer": a.text,
        "hits": a.hits,
        "citations": a.citations,
        "escalated": a.escalated,
        "reason": a.reason,
    }


def _extract_ticket_params(state: GraphState) -> dict[str, Any]:
    """Derive create_ticket params from the request + router decision.

    Deterministic (no extra LLM call): subject is a trimmed one-liner, body is
    the full request, and route/urgency/reason come from the triage decision.
    """
    request = (state.get("request") or "").strip()
    d = state.get("decision")
    first_line = request.splitlines()[0] if request else "Support request"
    subject = (first_line[:117] + "...") if len(first_line) > 120 else first_line
    email = _EMAIL_RE.search(request)
    return {
        "subject": subject or "Support request",
        "body": request,
        "requester_email": email.group(0) if email else None,
        "route": d.route if d else "action",
        "urgency": d.urgency if d else "low",
        "reason": d.intent if d else "action_request",
    }


def action_node(state: GraphState) -> GraphState:
    """Open a ticket for a side-effecting request via the create_ticket tool.

    Extract params -> validate with Pydantic -> POST to the n8n webhook. If the
    params don't validate or the webhook is unreachable, degrade gracefully by
    queuing the request for human approval instead of failing the graph.
    """
    params = _extract_ticket_params(state)
    try:
        result = tools.invoke("create_ticket", params)
    except ValidationError as e:
        return {
            "action": {**params, "status": "invalid", "error": e.errors()},
            "answer": "I couldn't structure this into a ticket; I've flagged it "
            "for a human to look at.",
            "escalated": False,
            "reason": "action_invalid_params",
        }
    except tools.ToolError as e:
        return {
            "action": {**params, "status": "pending_approval", "error": str(e)},
            "answer": "I couldn't open the ticket automatically (the tool was "
            "unavailable); I've queued it for human follow-up.",
            "escalated": False,
            "reason": "action_tool_unavailable",
        }

    ticket_id = result.get("id")
    return {
        "action": {**params, "status": "created", "ticket_id": ticket_id,
                   "tool": "create_ticket"},
        "answer": (f"I've opened ticket #{ticket_id} for this; a human will follow up."
                   if ticket_id else "I've opened a ticket for this; a human will follow up."),
        "escalated": False,
        "reason": "action_ticket_created",
    }


def escalate_node(state: GraphState) -> GraphState:
    """Hand off to a human (covers router 'escalate' and 'spam')."""
    spam = state.get("route") == "spam" or (
        state.get("decision") and state["decision"].route == "spam"
    )
    reason = "spam" if spam else "router_escalate"
    return {
        "escalated": True,
        "answer": "I'm escalating this to a human." if not spam
        else "This looks like spam; not actioning.",
        "reason": reason,
    }


# --- conditional edge ------------------------------------------------------

def _dispatch(state: GraphState) -> str:
    """Map the router's decision onto one of the three worker nodes."""
    route = state.get("route", "escalate")
    if route == "answer":
        return "answer"
    if route == "action":
        return "action"
    return "escalate"  # 'escalate' and 'spam' both land here


# --- graph assembly --------------------------------------------------------

def build_graph():
    g = StateGraph(GraphState)
    g.add_node("router", router_node)
    g.add_node("answer", answer_node)
    g.add_node("action", action_node)
    g.add_node("escalate", escalate_node)

    g.add_edge(START, "router")
    g.add_conditional_edges(
        "router",
        _dispatch,
        {"answer": "answer", "action": "action", "escalate": "escalate"},
    )
    for node in ("answer", "action", "escalate"):
        g.add_edge(node, END)

    return g.compile()


# Compile once; reuse across calls.
GRAPH = build_graph()


def run(request: str) -> GraphState:
    """Run the full router -> {answer|action|escalate} graph on one request.

    The run is wrapped in a cost/trace tracker: LLM token usage is accumulated
    across the router + answerer calls, timed, and persisted to the `runs` table.
    The returned state carries `usage` (summary) and `run_id` (the logged row).
    """
    with trace.track() as usage:
        state: GraphState = GRAPH.invoke({"request": request})
    state["usage"] = usage.summary()
    state["run_id"] = trace.log_run(request, state, usage)
    return state
