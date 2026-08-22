"""Week 2 orchestration: a LangGraph StateGraph that wires the pieces together.

    router --(conditional edge)--> answer | action | escalate --> END

The router (Week 2 baseline) triages the request; a single conditional edge then
dispatches to exactly one worker node:

- answer   : run the cited RAG answerer (which may itself escalate if it can't
             ground an answer -- citations-or-escalate is enforced in answer()).
- action   : the request needs a real side effect. We extract tool parameters,
             validate them with Pydantic, then either execute an allowed low-risk
             tool or queue a high-risk tool for approval. Failures are reported
             explicitly and escalated without claiming success.
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

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[A-Za-z0-9-]+)+")
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
    conversation: dict[str, Any]  # resolved multi-turn context, when supplied


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
    request = (state.get("request") or "").strip()
    ctx = {
        "request": request,
        "route": d.route if d else "action",
        "urgency": d.urgency if d else "low",
        "reason": d.intent if d else "action_request",
    }

    # Run request-only policy checks before tool selection.  This keeps a model
    # misclassification from bypassing the critic and prevents control-tampering
    # requests from being disguised as ordinary actions.
    verdict = critic.review(request, decision=d)
    if verdict.blocked:
        audit.step("critic", decision=verdict.decision, category=verdict.category,
                   reason=verdict.reason, must_refuse=verdict.must_refuse,
                   requires_approval=verdict.requires_approval)
        return {
            "action": {"status": "blocked", "critic": verdict.summary()},
            "answer": ("I can't carry out this request — " + verdict.reason
                       + " I've escalated it to a human."),
            "escalated": True,
            "reason": f"critic_blocked_{verdict.category}",
        }

    # Unknown/free-form intents are not authority to execute a default tool.
    try:
        tool = tools.select(d, request=request)
    except tools.ToolSelectionError as exc:
        audit.step("tool", tool=None, allowed=False, reason=str(exc))
        return {
            "action": {"status": "blocked", "error": str(exc)},
            "answer": ("I don't have enough specific, supported information to "
                       "perform that action. Please clarify the exact target, or "
                       "a human can handle it."),
            "escalated": True,
            "reason": "action_no_authorized_tool",
        }

    params = _extract_params(tool.name, state)

    # --- critic gate: verify the concrete proposal before any side effect ----
    verdict = critic.review(request, tool.name, params, d)
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
                           **params, "status": "failed", "error": str(e)},
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
            "action": {"tool": tool.name, **params, "status": "failed",
                       "error": str(e)},
            "answer": "The tool failed, so I did not report the action as complete. "
                      "I've escalated it for human follow-up.",
            "escalated": True,
            "reason": "action_tool_failed",
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
    decision = state.get("decision")
    spam = state.get("route") == "spam" or (
        decision and decision.route == "spam"
    )
    out_of_scope = bool(spam and decision and decision.intent == "out_of_scope")
    clarification = bool(decision and decision.intent == "clarification_required")
    policy_refusal = bool(
        decision
        and decision.intent in {
            "credential_exfil",
            "prompt_injection",
            "control_tampering",
            "cross_tenant_access",
            "sensitive_data_exfiltration",
            "untrusted_instruction",
            "false_success",
            "destructive",
            "unauthorized_change",
        }
    )
    reason = (
        "out_of_scope"
        if out_of_scope
        else "spam"
        if spam
        else "clarification_required"
        if clarification
        else f"policy_refusal_{decision.intent}"
        if policy_refusal
        else "router_escalate"
    )
    return {
        # Spam/out-of-scope is declined, not handed to a human.  This prevents
        # an irrelevant-request flood from becoming an escalation flood.
        "escalated": not spam,
        "answer": (
            "That request is outside Meridian support, so I can't help with it here."
            if out_of_scope
            else "This looks like spam; not actioning."
            if spam
            else ("I need more information before I can safely do that. Please "
                  "clarify the exact target and the change you want.")
            if clarification
            else ("I can't carry out that request because it would violate a "
                  "security or authorization boundary. I've escalated it to a human.")
            if policy_refusal
            else "I'm escalating this to a human."
        ),
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
    v = critic.review(request, tool_name, params, d)

    route_final = d.route
    requires_approval = v.requires_approval
    if v.blocked:
        route_final = "escalate"
    elif d.route == "action":
        try:
            tool = tools.select(d, request=request)
        except tools.ToolSelectionError:
            return {
                "route": "escalate",
                "intent": d.intent,
                "urgency": d.urgency,
                "must_refuse": False,
                "requires_approval": False,
                "critic_category": "unsupported_action",
                "critic_decision": "no_authorized_tool",
            }
        params = _extract_params(tool.name, {"request": request, "decision": d})
        tool_name = tool.name
        v = critic.review(request, tool_name, params, d)
        if v.blocked:
            route_final = "escalate"
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


def run(request: str, *, channel: str | None = None, sender: str | None = None) -> GraphState:
    """Run the full router -> {answer|action|escalate} graph on one request.

    The run is wrapped in a cost/trace tracker: LLM token usage is accumulated
    across the router + answerer calls, timed, and persisted to the `runs` table.
    The returned state carries `usage` (summary) and `run_id` (the logged row).
    `channel`/`sender` are recorded on the run so the Inbox can show origin.
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
    run_id = trace.log_run(request, state, usage, channel=channel, sender=sender)
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


def run_conversation(turns: list[dict[str, Any]]) -> GraphState:
    """Run a structured conversation after resolving safe target references."""
    from .conversation import resolve_turns

    resolved_request, conversation = resolve_turns(turns)
    state = run(resolved_request)
    state["conversation"] = conversation
    return state
