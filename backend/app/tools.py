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


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    webhook_path: str               # n8n webhook path, e.g. 'ticket' -> /webhook/ticket
    params: tuple[ToolParam, ...] = field(default_factory=tuple)
    method: str = "POST"

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


# The registry itself: name -> Tool.
REGISTRY: dict[str, Tool] = {t.name: t for t in (CREATE_TICKET,)}


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
        "params": [
            {"name": p.name, "type": p.type,
             "required": p.required, "description": p.description}
            for p in t.params
        ],
    }


# --- param schemas (Pydantic) ----------------------------------------------

_EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


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
        import re
        if v is None or v == "":
            return None
        if not re.match(_EMAIL_RE, v):
            raise ValueError(f"not a valid email address: {v!r}")
        return v


# tool name -> its Pydantic param model
PARAM_MODELS: dict[str, type[BaseModel]] = {"create_ticket": CreateTicketParams}


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


def invoke(name: str, params: dict[str, Any], *, timeout: int = 15) -> dict:
    """Validate `params` against the tool's schema and POST them to its webhook.

    Returns the parsed JSON response (e.g. {"ok": true, "id": "1"}).
    Raises pydantic.ValidationError on bad params, ToolError on transport/HTTP
    failure, KeyError if the tool is unknown.
    """
    tool = get_tool(name)
    model = PARAM_MODELS[name]
    validated = model(**params)                      # -> ValidationError on bad input
    payload = validated.model_dump(exclude_none=True)
    return _post_json(tool.url(), payload, timeout=timeout)
