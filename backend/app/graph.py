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

from . import audit, critic, lf, tools, trace
from .answer import answer as rag_answer
from .retrieve import Hit
from .router import Decision, route as route_request

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_INVOICE_RE = re.compile(r"\bINV[-\s]?(\d+)\b", re.IGNORECASE)


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
    audit.step("router", route=d.route, intent=d.intent, urgency=d.urgency,
               action_required=d.action_required)
    return {"route": d.route, "decision": d}


def answer_node(state: GraphState) -> GraphState:
    """Cited RAG answer (may self-escalate on low confidence)."""
    a = rag_answer(state["request"])
    audit.step("retrieve",
               ids=[h.id for h in a.hits],
               citation_ids=[h.citation_id for h in a.hits if h.citation_id],
               top_similarity=round(a.hits[0].similarity, 4) if a.hits else None,
               grounded_citations=a.citations)
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


def _extract_cancel_invoice_params(state: GraphState) -> dict[str, Any]:
    """Derive cancel_invoice params (invoice id + requester) from the request."""
    request = (state.get("request") or "").strip()
    d = state.get("decision")
    invoice = _INVOICE_RE.search(request)
    email = _EMAIL_RE.search(request)
    return {
        # Empty when no INV-xxxx is present -> validation fails -> graceful fallback.
        "invoice_id": f"INV-{invoice.group(1)}" if invoice else "",
        "requester_email": email.group(0) if email else None,
        "reason": d.intent if d else "billing_dispute",
    }


def _extract_params(tool_name: str, state: GraphState) -> dict[str, Any]:
    """Dispatch to the right param extractor for the selected tool."""
    if tool_name == "cancel_invoice":
        return _extract_cancel_invoice_params(state)
    return _extract_ticket_params(state)


def action_node(state: GraphState) -> GraphState:
    """Carry out a side-effecting request by selecting and running a tool.

    Flow: pick the tool for this intent -> extract + validate its params. If the
    tool is HIGH RISK, queue it for human approval (it never auto-executes);
    otherwise POST to its n8n webhook. Every failure mode degrades gracefully
    (invalid params / webhook down / queue write failure) rather than crashing
    the graph.
    """
    d = state.get("decision")
    tool = tools.select(d)
    params = _extract_params(tool.name, state)
    ctx = {
        "request": (state.get("request") or "").strip(),
        "route": d.route if d else "action",
        "urgency": d.urgency if d else "low",
        "reason": d.intent if d else "action_request",
    }
    # --- critic gate: verify the request BEFORE anything is queued/executed --
    verdict = critic.review(ctx["request"], tool.name, params, d)
    audit.step("critic", decision=verdict.decision, category=verdict.category,
               reason=verdict.reason, must_refuse=verdict.must_refuse,
               requires_approval=verdict.requires_approval)
    lf.span("critic", input=ctx["request"], output=verdict.decision,
            category=verdict.category, reason=verdict.reason,
            requires_approval=verdict.requires_approval)

    # BLOCK: unsafe / beyond authority -> refuse + escalate, never run.
    if verdict.blocked:
        return {
            "action": {"tool": tool.name, "risk_level": tool.risk_level, **params,
                       "status": "blocked", "critic": verdict.summary()},
            "answer": ("I can't carry out this request — " + verdict.reason
                       + " I've escalated it to a human."),
            "escalated": True,
            "reason": f"critic_blocked_{verdict.category}",
        }

    # REVISE: correct a contradicted parameter (e.g. an inflated priority).
    if verdict.decision == critic.REVISE:
        for k, v in verdict.patch.items():
            if k in params:
                params[k] = v
            ctx[k] = v

    # A high-risk tool always needs approval; the critic can also force it.
    need_approval = tools.requires_approval(tool) or verdict.requires_approval

    audit.step("tool", tool=tool.name, risk_level=tool.risk_level,
               requires_approval=need_approval, params=params)
    lf.span("tool", input=params, output=tool.name, risk_level=tool.risk_level,
            requires_approval=need_approval)

    # --- needs human approval: queue it, never execute now ------------------
    if need_approval:
        try:
            queue_id = tools.enqueue(tool.name, params, **ctx)
        except ValidationError as e:
            return {
                "action": {"tool": tool.name, "risk_level": tool.risk_level,
                           **params, "status": "invalid", "error": e.errors()},
                "answer": "I couldn't safely structure this action, so "
                "I've flagged it for a human.",
                "escalated": True,
                "reason": "action_invalid_params",
            }
        except Exception as e:  # approval_queue write failed -> don't lose it
            return {
                "action": {"tool": tool.name, "risk_level": tool.risk_level,
                           **params, "status": "pending_approval", "error": str(e)},
                "answer": "I couldn't record this action for approval, so "
                "I'm escalating it to a human.",
                "escalated": True,
                "reason": "approval_enqueue_failed",
            }
        gated_by = ("high-risk tool" if tools.requires_approval(tool)
                    else f"critic:{verdict.category}")
        return {
            "action": {"tool": tool.name, "risk_level": tool.risk_level, **params,
                       "status": "pending_approval", "queue_id": queue_id,
                       "critic": verdict.summary()},
            "answer": (f"This action needs human sign-off ({gated_by}), so I've queued "
                       f"it for approval (approval #{queue_id}) before anything runs."),
            "escalated": False,
            "reason": "action_queued_for_approval",
        }

    # --- clean + low/medium risk: execute directly via the tool's webhook ---
    try:
        result = tools.invoke(tool.name, params, idempotent=True,
                              request=ctx["request"])
    except ValidationError as e:
        return {
            "action": {"tool": tool.name, **params, "status": "invalid",
                       "error": e.errors()},
            "answer": "I couldn't structure this into a ticket; I've flagged it "
            "for a human to look at.",
            "escalated": False,
            "reason": "action_invalid_params",
        }
    except tools.ToolError as e:
        return {
            "action": {"tool": tool.name, **params, "status": "pending_approval",
                       "error": str(e)},
            "answer": "I couldn't open the ticket automatically (the tool was "
            "unavailable); I've queued it for human follow-up.",
            "escalated": False,
            "reason": "action_tool_unavailable",
        }

    ticket_id = result.get("id")
    return {
        "action": {"tool": tool.name, "risk_level": tool.risk_level, **params,
                   "status": "created", "ticket_id": ticket_id},
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


def plan(request: str) -> dict[str, Any]:
    """Dry-run planner (router -> critic) WITHOUT executing any tool.

    Returns the final decision the agent would reach: the route after the critic
    may turn a proposed action into an escalation, plus the safety flags the
    golden set checks (must_refuse, requires human approval). Used by the safety
    eval so adversarial behavior can be scored without side effects.
    """
    d = route_request(request)
    tool = tool_name = params = None
    if d.route == "action":
        tool = tools.select(d)
        params = _extract_params(tool.name, {"request": request, "decision": d})
        tool_name = tool.name

    v = critic.review(request, tool_name, params, d)

    route_final = d.route
    requires_approval = v.requires_approval
    if v.blocked:
        route_final = "escalate"
    elif d.route == "action":
        requires_approval = tools.requires_approval(tool) or v.requires_approval

    urgency = v.patch.get("urgency", d.urgency) if v.decision == critic.REVISE else d.urgency
    return {
        "route": route_final,
        "intent": d.intent,
        "urgency": urgency,
        "must_refuse": v.must_refuse,
        "requires_approval": requires_approval,
        "critic_category": v.category,
        "critic_decision": v.decision,
    }


def run(request: str) -> GraphState:
    """Run the full router -> {answer|action|escalate} graph on one request.

    The run is wrapped in a cost/trace tracker: LLM token usage is accumulated
    across the router + answerer calls, timed, and persisted to the `runs` table.
    The returned state carries `usage` (summary) and `run_id` (the logged row).
    """
    with trace.track() as usage, audit.collect() as steps:
        lf.start(request)  # open the Langfuse trace for this run
        state: GraphState = GRAPH.invoke({"request": request})
        action = state.get("action") or {}
        audit.step("outcome",
                   route=state.get("route"),
                   reason=state.get("reason"),
                   escalated=bool(state.get("escalated", False)),
                   action_status=action.get("status"),
                   ticket_id=action.get("ticket_id"),
                   queue_id=action.get("queue_id"))
    state["usage"] = usage.summary()
    run_id = trace.log_run(request, state, usage)
    state["run_id"] = run_id
    # Backfill the run_id onto any approval this run queued, so the run <-> approval
    # link is a real FK column (not just outcome.detail.queue_id). Best-effort.
    queue_id = (state.get("action") or {}).get("queue_id")
    if run_id and queue_id:
        try:
            tools.set_run_id(queue_id, run_id)
        except Exception:
            pass
    audit.flush(run_id, steps)
    # Close the Langfuse trace with the final outcome + cost/token summary.
    lf.finish(
        output=state.get("answer", ""),
        metadata={
            "run_id": run_id,
            "route": state.get("route"),
            "reason": state.get("reason"),
            "escalated": bool(state.get("escalated", False)),
            "action_status": (state.get("action") or {}).get("status"),
            **usage.summary(),
        },
    )
    return state
