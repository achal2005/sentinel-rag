"""Unit tests for the action branch: param validation + tool invocation.

Fully offline -- the n8n webhook POST is monkeypatched, so this needs neither
n8n nor Ollama running:

    cd backend && .venv\\Scripts\\python -m tests.test_action_tool
"""
from __future__ import annotations

import sys

from pydantic import ValidationError

from app import tools
from app.graph import (
    _extract_cancel_invoice_params,
    _extract_ticket_params,
    action_node,
)
from app.router import Decision


def _check(desc: str, cond: bool) -> int:
    print(f"[{'PASS' if cond else 'FAIL'}] {desc}")
    return 0 if cond else 1


def main() -> int:
    fails = 0

    # --- Pydantic validation ------------------------------------------------
    try:
        tools.CreateTicketParams(body="no subject")
        fails += _check("missing subject rejected", False)
    except ValidationError:
        fails += _check("missing subject rejected", True)

    try:
        tools.CreateTicketParams(subject="hi", requester_email="not-an-email")
        fails += _check("bad email rejected", False)
    except ValidationError:
        fails += _check("bad email rejected", True)

    p = tools.CreateTicketParams(subject="  trim me  ", requester_email="a@b.com")
    fails += _check("subject stripped", p.subject == "trim me")
    fails += _check("exclude_none drops empty fields",
                    "route" not in p.model_dump(exclude_none=True))

    # --- tools.invoke posts the validated payload ---------------------------
    captured: dict = {}

    def fake_post(url, payload, timeout):
        captured["url"] = url
        captured["payload"] = payload
        return {"ok": True, "id": "42"}

    orig = tools._post_json
    tools._post_json = fake_post
    try:
        res = tools.invoke("create_ticket",
                           {"subject": "Cancel INV-2231", "route": "action"})
        fails += _check("invoke returns webhook id", res.get("id") == "42")
        fails += _check("invoke hit the create_ticket url",
                        captured["url"].endswith("/webhook/ticket"))
        fails += _check("invoke sent validated subject",
                        captured["payload"]["subject"] == "Cancel INV-2231")

        # ToolError propagates when the webhook is down
        def boom(url, payload, timeout):
            raise tools.ToolError("connection refused")

        tools._post_json = boom
        try:
            tools.invoke("create_ticket", {"subject": "x"})
            fails += _check("ToolError surfaces on transport failure", False)
        except tools.ToolError:
            fails += _check("ToolError surfaces on transport failure", True)
    finally:
        tools._post_json = orig

    # --- action_node: extraction + success + graceful fallback --------------
    # Use a support_issue intent so this exercises the low-risk create_ticket
    # (execute) path; billing_dispute would route to the high-risk queue path.
    state = {
        "request": "Our dashboard is down, reach me at user@meridian.co",
        "decision": Decision("action", "support_issue", "medium", True),
    }
    params = _extract_ticket_params(state)
    fails += _check("extract pulls email", params["requester_email"] == "user@meridian.co")
    fails += _check("extract carries route/urgency from decision",
                    params["route"] == "action" and params["urgency"] == "medium")

    orig_invoke = tools.invoke
    tools.invoke = lambda name, prm, **kw: {"ok": True, "id": "7"}
    try:
        out = action_node(state)
        fails += _check("action_node reports created",
                        out["action"]["status"] == "created"
                        and out["action"]["ticket_id"] == "7"
                        and out["reason"] == "action_ticket_created"
                        and "#7" in out["answer"])

        def raise_tool(name, prm, **kw):
            raise tools.ToolError("n8n down")

        tools.invoke = raise_tool
        out = action_node(state)
        fails += _check("action_node degrades to approval queue on ToolError",
                        out["action"]["status"] == "pending_approval"
                        and out["reason"] == "action_tool_unavailable"
                        and out["escalated"] is False)
    finally:
        tools.invoke = orig_invoke

    # --- risk levels + tool selection ---------------------------------------
    fails += _check("create_ticket is low risk",
                    tools.get_tool("create_ticket").risk_level == "low")
    fails += _check("cancel_invoice is high risk",
                    tools.get_tool("cancel_invoice").risk_level == "high")
    fails += _check("requires_approval true only for high risk",
                    tools.requires_approval(tools.get_tool("cancel_invoice"))
                    and not tools.requires_approval(tools.get_tool("create_ticket")))
    fails += _check("select() routes billing_dispute -> cancel_invoice",
                    tools.select(Decision("action", "billing_dispute", "medium", True)).name
                    == "cancel_invoice")
    fails += _check("select() defaults unknown intent -> create_ticket",
                    tools.select(Decision("action", "support_issue", "high", True)).name
                    == "create_ticket")

    inv_state = {
        "request": "Please cancel invoice INV-2231, reach me at user@meridian.co",
        "decision": Decision("action", "billing_dispute", "medium", True),
    }
    ci = _extract_cancel_invoice_params(inv_state)
    fails += _check("cancel_invoice extraction pulls invoice id",
                    ci["invoice_id"] == "INV-2231")

    # --- high-risk path enqueues, never executes ----------------------------
    orig_invoke, orig_enqueue = tools.invoke, tools.enqueue
    invoked = {"called": False}
    tools.invoke = lambda *a, **k: invoked.__setitem__("called", True) or {"id": "X"}
    tools.enqueue = lambda name, prm, **kw: 99
    try:
        out = action_node(inv_state)
        fails += _check("high-risk action is queued for approval",
                        out["action"]["status"] == "pending_approval"
                        and out["action"]["queue_id"] == 99
                        and out["action"]["risk_level"] == "high"
                        and out["reason"] == "action_queued_for_approval")
        fails += _check("high-risk action does NOT auto-execute",
                        invoked["called"] is False)
    finally:
        tools.invoke, tools.enqueue = orig_invoke, orig_enqueue

    total = 20
    print(f"\n{total - fails}/{total} checks passed.")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
