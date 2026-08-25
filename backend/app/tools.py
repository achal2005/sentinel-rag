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
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from .config import TOOLS_SIMULATE, _env


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


# Intent -> tool selection.  This is an allowlist: an unknown model-produced
# intent must never silently turn into a real side effect.  Explicit ticket
# requests are also recognized from the original request text because small
# routers sometimes label them generically as ``record_update``.
_INTENT_TOOL: dict[str, str] = {
    "create_ticket": "create_ticket",
    "open_ticket": "create_ticket",
    "ticket_creation": "create_ticket",
    "support_issue": "create_ticket",
    "incident_report": "create_ticket",
    "billing_dispute": "cancel_invoice",
    "cancellation": "cancel_invoice",
    "refund_request": "cancel_invoice",
    "invoice_cancellation": "cancel_invoice",
}


_EXPLICIT_TICKET_RE = re.compile(
    r"\b(open|create|file|submit|raise|log)\b[^.?!]{0,60}"
    r"\b(ticket|support\s+(?:ticket|case))\b",
    re.IGNORECASE,
)


class ToolSelectionError(LookupError):
    """No registered tool is authorized for the proposed intent/request."""


def select(decision: Any, *, request: str | None = None) -> Tool:
    """Pick an allowlisted tool or fail closed.

    Tool selection is a security boundary.  A free-form or hallucinated intent
    is not permission to execute the registry's safest-looking tool.
    """
    intent = (getattr(decision, "intent", "") or "").strip().lower()
    name = _INTENT_TOOL.get(intent)
    if name is None and request and _EXPLICIT_TICKET_RE.search(request):
        name = "create_ticket"
    if name is None:
        raise ToolSelectionError(
            f"no authorized tool mapping for intent {intent or 'unspecified'!r}"
        )
    return get_tool(name)


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


def invoke(name: str, params: dict[str, Any], *, timeout: int = 15,
           idempotent: bool = False, request: str | None = None) -> dict:
    """Validate `params` and POST them to the tool's webhook (direct execution).

    Returns the parsed JSON response (e.g. {"ok": true, "id": "1"}).
    Raises pydantic.ValidationError on bad params, ToolError on transport/HTTP
    failure, KeyError if the tool is unknown. Intended for low/medium-risk tools;
    high-risk tools should go through `enqueue` instead.

    When `idempotent=True`, a content hash of (tool + request/payload) is checked
    against the `tool_executions` ledger first: a duplicate request returns the
    prior result (tagged `idempotent_replay`) instead of firing the webhook again,
    so a retried/duplicated action never creates a second side effect.
    """
    tool = get_tool(name)
    payload = validate(name, params)

    key = _idempotency_key(name, request, payload) if idempotent else None
    if key is not None:
        prior = _idem_lookup(key)
        if prior is not None:
            return {**prior, "idempotent_replay": True}

    if TOOLS_SIMULATE:
        # Demo/public mode: record success without a real n8n side effect.
        import uuid

        result: dict[str, Any] = {
            "ok": True,
            "id": f"sim-{uuid.uuid4().hex[:8]}",
            "simulated": True,
        }
    else:
        result = _post_json(tool.url(), payload, timeout=timeout)

    # A 2xx transport status does not mean the tool succeeded: an n8n workflow can
    # return HTTP 200 with a body that reports failure (e.g. {"ok": false}). Treat
    # an explicit ok:false as a failure so the action is never reported as success.
    if isinstance(result, dict) and result.get("ok") is False:
        raise ToolError(
            f"webhook {tool.url()} reported failure: {result.get('error') or result}"
        )

    if key is not None:
        _idem_store(key, name, result)
    return result


def _idempotency_key(name: str, request: str | None, payload: dict) -> str:
    """Stable content hash identifying one logical tool call.

    Prefers the originating request text (so a re-submitted request dedupes even
    if param extraction differs slightly); falls back to the validated payload.
    """
    import hashlib

    basis = (request or "").strip().lower() or json.dumps(payload, sort_keys=True)
    return hashlib.sha256(f"{name}:{basis}".encode("utf-8")).hexdigest()


def _idem_lookup(key: str, *, conn=None) -> Optional[dict]:
    """Return the stored result for this key, or None. Never raises."""
    from . import db

    try:
        own = conn is None
        conn = conn or db.connect()
        try:
            cur = conn.execute(
                "SELECT result FROM tool_executions WHERE idempotency_key = %s", (key,)
            )
            row = cur.fetchone()
            return row[0] if row else None
        finally:
            if own:
                conn.close()
    except Exception:
        return None  # ledger unavailable -> treat as not-seen (fail open to execute)


def _idem_store(key: str, name: str, result: dict, *, conn=None) -> None:
    """Record a tool execution's result under its idempotency key. Never raises."""
    from psycopg.types.json import Jsonb

    from . import db

    try:
        own = conn is None
        conn = conn or db.connect()
        try:
            conn.execute(
                "INSERT INTO tool_executions (idempotency_key, tool, result) "
                "VALUES (%s, %s, %s) ON CONFLICT (idempotency_key) DO NOTHING",
                (key, name, Jsonb(result)),
            )
        finally:
            if own:
                conn.close()
    except Exception:
        pass


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


_APPROVAL_COLS = (
    "id, created_at, tool, risk_level, status, reason, request, urgency, params, "
    "run_id, decided_by, decided_at"
)


def set_run_id(approval_id: int, run_id: int, *, conn=None) -> None:
    """Link a queued approval back to the graph run that created it.

    Called once the run's `runs` row exists (run_id is only assigned after the
    graph finishes, i.e. after enqueue). Best-effort: never raises.
    """
    from . import db

    own = conn is None
    conn = conn or db.connect()
    try:
        conn.execute(
            "UPDATE approval_queue SET run_id = %s WHERE id = %s AND run_id IS NULL",
            (run_id, approval_id),
        )
    finally:
        if own:
            conn.close()


class ApprovalError(RuntimeError):
    """Base class for approval-queue state errors."""


class ApprovalNotFound(ApprovalError):
    """No approval_queue row with that id."""


class ApprovalNotPending(ApprovalError):
    """The row exists but has already been decided (not 'pending')."""


def list_approvals(*, status: str | None = "pending", limit: int = 50,
                   conn=None) -> list[dict[str, Any]]:
    """Approval-queue rows, newest first. `status=None` returns every status."""
    from . import db

    own = conn is None
    conn = conn or db.connect()
    try:
        if status is None:
            cur = conn.execute(
                f"SELECT {_APPROVAL_COLS} FROM approval_queue "
                "ORDER BY id DESC LIMIT %s",
                (limit,),
            )
        else:
            cur = conn.execute(
                f"SELECT {_APPROVAL_COLS} FROM approval_queue WHERE status = %s "
                "ORDER BY id DESC LIMIT %s",
                (status, limit),
            )
        cols = [c.name for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        if own:
            conn.close()


def get_approval(approval_id: int, *, conn=None) -> Optional[dict[str, Any]]:
    """One approval-queue row, or None if it doesn't exist."""
    from . import db

    own = conn is None
    conn = conn or db.connect()
    try:
        cur = conn.execute(
            f"SELECT {_APPROVAL_COLS} FROM approval_queue WHERE id = %s",
            (approval_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return dict(zip([c.name for c in cur.description], row))
    finally:
        if own:
            conn.close()


def approve(approval_id: int, *, decided_by: str = "operator", conn=None) -> dict[str, Any]:
    """Approve a pending item and RUN its tool (fires the n8n webhook).

    On success the row moves pending -> approved -> executed. If the tool call
    fails (e.g. the n8n workflow isn't set up), the row stays 'approved' with the
    error surfaced, so it can be retried. Raises ApprovalNotFound / NotPending.
    """
    from . import db

    own = conn is None
    conn = conn or db.connect()
    try:
        row = get_approval(approval_id, conn=conn)
        if row is None:
            raise ApprovalNotFound(f"approval {approval_id} not found")
        if row["status"] != "pending":
            raise ApprovalNotPending(
                f"approval {approval_id} is '{row['status']}', not pending"
            )
        # Critic gate: re-verify the action immediately BEFORE it executes, even
        # though a human approved it (defense in depth). A block here means the
        # request is unsafe regardless of approval -- do not run it.
        from . import critic

        verdict = critic.review(row.get("request") or "", row["tool"], row["params"])
        if verdict.blocked:
            conn.execute(
                "UPDATE approval_queue SET status='rejected', decided_by=%s, "
                "decided_at=now() WHERE id=%s",
                (f"critic:{verdict.category}", approval_id),
            )
            _audit_decision(approval_id, "blocked_by_critic", decided_by,
                            tool=row["tool"], params=row["params"], executed=False,
                            category=verdict.category, reason=verdict.reason,
                            run_id=row.get("run_id"), conn=conn)
            return {"id": approval_id, "tool": row["tool"], "status": "rejected",
                    "executed": False, "error": f"blocked by critic: {verdict.reason}"}

        # Record the human decision first.
        conn.execute(
            "UPDATE approval_queue SET status='approved', decided_by=%s, "
            "decided_at=now() WHERE id=%s",
            (decided_by, approval_id),
        )
        # Approving TRIGGERS the tool.
        try:
            result = invoke(row["tool"], row["params"])
        except ToolError as e:
            _audit_decision(approval_id, "approved", decided_by, tool=row["tool"],
                            params=row["params"], executed=False, error=str(e),
                            run_id=row.get("run_id"), conn=conn)
            return {"id": approval_id, "tool": row["tool"], "status": "approved",
                    "executed": False, "error": str(e)}
        conn.execute("UPDATE approval_queue SET status='executed' WHERE id=%s",
                     (approval_id,))
        _audit_decision(approval_id, "approved", decided_by, tool=row["tool"],
                        params=row["params"], executed=True,
                        run_id=row.get("run_id"), conn=conn)
        return {"id": approval_id, "tool": row["tool"], "status": "executed",
                "executed": True, "result": result}
    finally:
        if own:
            conn.close()


def reject(approval_id: int, *, decided_by: str = "operator", conn=None) -> dict[str, Any]:
    """Reject (close) a pending item without running its tool."""
    from . import db

    own = conn is None
    conn = conn or db.connect()
    try:
        row = get_approval(approval_id, conn=conn)
        if row is None:
            raise ApprovalNotFound(f"approval {approval_id} not found")
        if row["status"] != "pending":
            raise ApprovalNotPending(
                f"approval {approval_id} is '{row['status']}', not pending"
            )
        conn.execute(
            "UPDATE approval_queue SET status='rejected', decided_by=%s, "
            "decided_at=now() WHERE id=%s",
            (decided_by, approval_id),
        )
        _audit_decision(approval_id, "rejected", decided_by, tool=row["tool"],
                        params=row["params"], executed=False,
                        run_id=row.get("run_id"), conn=conn)
        return {"id": approval_id, "tool": row["tool"], "status": "rejected",
                "executed": False}
    finally:
        if own:
            conn.close()


def _audit_decision(approval_id: int, decision: str, decided_by: str, *,
                    run_id: int | None = None, conn=None, **detail: Any) -> None:
    """Record a human approve/reject decision to the audit trail (never raises)."""
    from . import audit

    audit.event("approval", approval_id=approval_id, run_id=run_id, conn=conn,
                decision=decision, decided_by=decided_by, **detail)
