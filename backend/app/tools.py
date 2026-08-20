"""Tool registry: the side-effecting "hands" the agent can invoke.

Each tool is executed out-of-process by n8n (a Webhook workflow), so a tool here
is a *description* -- name, what it does, its input schema, and the webhook it
POSTs to. Calling `invoke(name, params)` validates the params with the tool's
Pydantic model and POSTs them to the webhook; the graph's action node uses this
to actually open tickets.

Keeping the registry as a small in-code config (rather than a DB table) means
the router, the action node, and the approval queue import one source of truth.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from .config import _env


@dataclass(frozen=True)
class ToolParam:
    name: str
    type: str                       # json type: string | integer | boolean | ...
    required: bool = False
    description: str = ""


# Risk tiers. "high" tools have a real, hard-to-undo side effect (money/data),
# so they are never executed automatically -- they are queued for human approval.
RISK_LEVELS = ("low", "medium", "high")
HIGH_RISK = "high"


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    webhook_path: str               # n8n webhook path, e.g. 'ticket' -> /webhook/ticket
    params: tuple[ToolParam, ...] = field(default_factory=tuple)
    method: str = "POST"
    risk_level: str = "low"         # low | medium | high (see RISK_LEVELS)

    def url(self, base: str | None = None) -> str:
        base = (base or N8N_WEBHOOK_BASE).rstrip("/")
        return f"{base}/{self.webhook_path.lstrip('/')}"

    def required_params(self) -> list[str]:
        return [p.name for p in self.params if p.required]


# Base URL of the n8n webhook listener. Inside the compose network use the
# service name ('http://n8n:5678/webhook'); from the host, localhost.
N8N_WEBHOOK_BASE = _env("N8N_WEBHOOK_BASE", "http://localhost:5679/webhook")


CREATE_TICKET = Tool(
    name="create_ticket",
    description=(
        "Open a support ticket for a request that needs human follow-up or a "
        "side effect the agent can't perform itself. Inserts one row into the "
        "'tickets' table via the n8n 'Webhook -> tickets' workflow."
    ),
    webhook_path="ticket",
    risk_level="low",               # opening a ticket is safe / easily reversible
    params=(
        ToolParam("subject", "string", required=True,
                  description="Short one-line summary of the request."),
        ToolParam("body", "string",
                  description="Full request text / context."),
        ToolParam("requester_email", "string",
                  description="Email of the person to follow up with."),
        ToolParam("route", "string",
                  description="Router branch: answer | action | escalate | spam."),
        ToolParam("urgency", "string",
                  description="low | normal | high."),
        ToolParam("reason", "string",
                  description="Short machine tag for tracing (e.g. router_escalate)."),
    ),
)


CANCEL_INVOICE = Tool(
    name="cancel_invoice",
    description=(
        "Cancel / void a customer invoice. A real financial side effect, so this "
        "is HIGH RISK: it is never executed automatically -- the agent queues it "
        "for a human to approve first (see the approval_queue table)."
    ),
    webhook_path="cancel-invoice",  # workflow need not exist yet: high-risk never auto-fires
    risk_level="high",
    params=(
        ToolParam("invoice_id", "string", required=True,
                  description="Invoice to cancel, e.g. INV-2231."),
        ToolParam("requester_email", "string",
                  description="Email of the requester."),
        ToolParam("reason", "string",
                  description="Why the invoice should be cancelled."),
    ),
)


# The registry itself: name -> Tool.
REGISTRY: dict[str, Tool] = {t.name: t for t in (CREATE_TICKET, CANCEL_INVOICE)}


def get_tool(name: str) -> Tool:
    """Look up a tool by name; raises KeyError if unknown."""
    return REGISTRY[name]


def list_tools() -> list[Tool]:
    return list(REGISTRY.values())


def describe(name: str) -> dict[str, Any]:
    """JSON-serialisable description of a tool (handy for the approval UI / logs)."""
    t = get_tool(name)
    return {
        "name": t.name,
        "description": t.description,
        "method": t.method,
        "url": t.url(),
        "risk_level": t.risk_level,
        "params": [
            {"name": p.name, "type": p.type,
             "required": p.required, "description": p.description}
            for p in t.params
        ],
    }


def requires_approval(tool: Tool) -> bool:
    """High-risk tools must be approved by a human before they run."""
    return tool.risk_level == HIGH_RISK


# Intent -> tool selection. Financial / destructive intents map to the high-risk
# tool (which is gated behind human approval); everything else opens a ticket.
# Conservative by design: unknown intents fall back to the low-risk create_ticket.
_INTENT_TOOL: dict[str, str] = {
    "billing_dispute": "cancel_invoice",
    "cancellation": "cancel_invoice",
    "refund_request": "cancel_invoice",
    "invoice_cancellation": "cancel_invoice",
}


def select(decision: Any) -> Tool:
    """Pick the tool for an action-routed request from its triage decision."""
    intent = (getattr(decision, "intent", "") or "").strip().lower()
    return get_tool(_INTENT_TOOL.get(intent, "create_ticket"))


# --- param schemas (Pydantic) ----------------------------------------------

_EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


def _clean_email(v: Optional[str]) -> Optional[str]:
    """Normalise an optional email: empty -> None, else validate the shape."""
    import re
    if v is None or v == "":
        return None
    if not re.match(_EMAIL_RE, v):
        raise ValueError(f"not a valid email address: {v!r}")
    return v


class CreateTicketParams(BaseModel):
    """Validated input for the create_ticket tool. Mirrors CREATE_TICKET.params;
    only `subject` is required, matching the tickets table's NOT NULL columns."""

    subject: str = Field(min_length=1, max_length=200)
    body: str = ""
    requester_email: Optional[str] = None
    route: Optional[str] = None
    urgency: Optional[str] = None
    reason: Optional[str] = None

    @field_validator("subject", "body")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @field_validator("requester_email")
    @classmethod
    def _check_email(cls, v: Optional[str]) -> Optional[str]:
        return _clean_email(v)


class CancelInvoiceParams(BaseModel):
    """Validated input for the high-risk cancel_invoice tool."""

    invoice_id: str = Field(min_length=1, max_length=64)
    requester_email: Optional[str] = None
    reason: Optional[str] = None

    @field_validator("invoice_id")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @field_validator("requester_email")
    @classmethod
    def _check_email(cls, v: Optional[str]) -> Optional[str]:
        return _clean_email(v)


# tool name -> its Pydantic param model
PARAM_MODELS: dict[str, type[BaseModel]] = {
    "create_ticket": CreateTicketParams,
    "cancel_invoice": CancelInvoiceParams,
}


# --- invocation ------------------------------------------------------------

class ToolError(RuntimeError):
    """Raised when a tool's webhook is unreachable or returns a non-2xx status."""


def _post_json(url: str, payload: dict, timeout: int) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8").strip()
    except urllib.error.HTTPError as e:
        raise ToolError(f"webhook {url} returned HTTP {e.code}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise ToolError(
            f"webhook {url} unreachable: {e.reason}. Is n8n up and the workflow active?"
        ) from e
    if not body:
        return {}
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"raw": body}


def validate(name: str, params: dict[str, Any]) -> dict[str, Any]:
    """Validate `params` against the tool's schema; return the JSON payload dict.

    Raises pydantic.ValidationError on bad input, KeyError if the tool is unknown.
    """
    model = PARAM_MODELS[name]
    return model(**params).model_dump(exclude_none=True)


def invoke(name: str, params: dict[str, Any], *, timeout: int = 15) -> dict:
    """Validate `params` and POST them to the tool's webhook (direct execution).

    Returns the parsed JSON response (e.g. {"ok": true, "id": "1"}).
    Raises pydantic.ValidationError on bad params, ToolError on transport/HTTP
    failure, KeyError if the tool is unknown. Intended for low/medium-risk tools;
    high-risk tools should go through `enqueue` instead.
    """
    tool = get_tool(name)
    payload = validate(name, params)
    return _post_json(tool.url(), payload, timeout=timeout)


# --- approval queue (high-risk actions) ------------------------------------

def enqueue(name: str, params: dict[str, Any], *, request: str = "",
            route: str | None = None, urgency: str | None = None,
            reason: str | None = None, conn=None) -> int:
    """Validate `params` and queue the action for human approval instead of
    running it. Writes one row to `approval_queue` and returns its id.

    This is the gate for high-risk tools: nothing side-effecting happens here,
    the request is just recorded (status 'pending') for a human to approve later.
    """
    from psycopg.types.json import Jsonb

    from . import db

    tool = get_tool(name)
    payload = validate(name, params)                 # -> ValidationError on bad input
    own = conn is None
    conn = conn or db.connect()
    try:
        cur = conn.execute(
            """
            INSERT INTO approval_queue
                (tool, risk_level, params, request, route, urgency, reason)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (name, tool.risk_level, Jsonb(payload), request, route, urgency, reason),
        )
        return cur.fetchone()[0]
    finally:
        if own:
            conn.close()


def pending_approvals(limit: int = 20, *, conn=None) -> list[dict[str, Any]]:
    """Most recent approval-queue rows (for `cli approvals` / a future UI)."""
    from . import db

    own = conn is None
    conn = conn or db.connect()
    try:
        cur = conn.execute(
            """
            SELECT id, created_at, tool, risk_level, status, reason, params
            FROM approval_queue ORDER BY id DESC LIMIT %s
            """,
            (limit,),
        )
        cols = [c.name for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        if own:
            conn.close()
