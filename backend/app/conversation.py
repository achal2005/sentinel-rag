"""Small, auditable multi-turn context resolver.

The production graph remains stateless per request. This module turns a short
conversation into one explicit request before routing it, resolving only the
references for which Sentinel has a safe, deterministic rule. It deliberately
does not ask a model to invent missing targets.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

_INVOICE_RE = re.compile(r"\bINV[-\s]?(\d+)\b", re.IGNORECASE)
_INVOICE_REFERENCE_RE = re.compile(
    r"\b(?:that|this|the)\s+invoice\b|\bit\b", re.IGNORECASE
)
_ISSUE_REFERENCE_RE = re.compile(r"\b(?:that|this|the)\s+issue\b", re.IGNORECASE)


def resolve_turns(turns: Sequence[Mapping[str, Any]]) -> tuple[str, dict[str, Any]]:
    """Resolve supported references in the last user turn.

    Missing context is left unchanged so the normal ambiguity guard asks for
    clarification instead of guessing.
    """
    normalized = [
        {
            "role": str(turn.get("role", "user")).strip().lower(),
            "content": str(turn.get("content", "")).strip(),
        }
        for turn in turns
        if isinstance(turn, Mapping) and str(turn.get("content", "")).strip()
    ]
    user_turns = [turn["content"] for turn in normalized if turn["role"] == "user"]
    if not user_turns:
        raise ValueError("a conversation needs at least one non-empty user turn")

    current = user_turns[-1]
    history = user_turns[:-1]
    resolved = current
    resolved_fields: dict[str, str] = {}

    invoice_id: str | None = None
    for prior in reversed(history):
        match = _INVOICE_RE.search(prior)
        if match:
            invoice_id = f"INV-{match.group(1)}"
            break
    if invoice_id and re.search(r"\b(cancel|void)\b", current, re.IGNORECASE):
        changed = _INVOICE_REFERENCE_RE.sub(f"invoice {invoice_id}", resolved, count=1)
        if changed != resolved:
            resolved = changed
            resolved_fields["invoice_id"] = invoice_id

    if _ISSUE_REFERENCE_RE.search(resolved):
        prior_issue = _latest_issue_context(history)
        if prior_issue:
            resolved = _ISSUE_REFERENCE_RE.sub(prior_issue, resolved, count=1)
            resolved_fields["issue"] = prior_issue

    return resolved, {
        "turns_processed": len(normalized),
        "user_turns_processed": len(user_turns),
        "context_resolved": bool(resolved_fields),
        "resolved_fields": resolved_fields,
        "original_request": current,
        "resolved_request": resolved,
    }


def _latest_issue_context(history: Sequence[str]) -> str | None:
    for prior in reversed(history):
        if _INVOICE_RE.search(prior):
            continue
        compact = " ".join(prior.split())
        if compact:
            return compact[:240]
    return None
