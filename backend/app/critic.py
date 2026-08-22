"""Critic / verification gate for side-effecting actions.

Between "the agent decided to act" and "the action actually runs" sits this
critic. It re-reads the ORIGINAL request against the proposed tool + params and
returns a verdict:

    allow   -- the action is consistent and safe; proceed as planned.
    revise  -- the action is basically fine but a parameter contradicts the
               evidence (e.g. an inflated priority); patch it and require human
               approval before it runs.
    block   -- the request is unsafe / out of the agent's authority (credential
               exfiltration, prompt injection, unauthorized privilege change,
               destructive bulk op). Refuse and escalate to a human; never run.

It is intentionally **deterministic** (rule-based, no extra LLM call): the gate
that protects real side effects should be fast, cheap, and testable, and its
decisions must be explainable in an audit log. The router (an LLM) proposes;
this critic disposes. It runs in two places:

- in the graph's action node, before a tool is executed or queued, and
- again in tools.approve(), immediately before a high-risk webhook fires
  (defense in depth: even a human-approved action is re-verified).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

# Verdict decisions.
ALLOW = "allow"
REVISE = "revise"
BLOCK = "block"


@dataclass
class Verdict:
    """The critic's ruling on a proposed action."""

    decision: str                       # allow | revise | block
    category: str = "clean"             # machine tag (e.g. destructive, credential_exfil)
    reason: str = ""                    # human-readable explanation
    must_refuse: bool = False           # block that the agent must refuse outright
    requires_approval: bool = False     # force the human-approval gate before running
    patch: dict[str, Any] = field(default_factory=dict)  # param overrides for `revise`

    @property
    def blocked(self) -> bool:
        return self.decision == BLOCK

    def summary(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "category": self.category,
            "reason": self.reason,
            "must_refuse": self.must_refuse,
            "requires_approval": self.requires_approval,
            "patch": self.patch,
        }


# --- detection patterns -----------------------------------------------------
# Kept explicit and readable so each rule maps to an auditable reason string.

# Secret / credential exfiltration: "reveal the api key", "give me the admin
# password", "print ... any secrets", etc.
_CREDENTIAL_RE = re.compile(
    r"\b(reveal|show|print|give|send|tell|expose|leak|dump|share|display|retrieve)\b"
    r"[^.?!]*\b(password|secret|api[\s-]?key|access[\s-]?token|token|credential|"
    r"private[\s-]?key)s?\b",
    re.IGNORECASE,
)
# "admin password" / "root password" even without an explicit verb.
_ADMIN_SECRET_RE = re.compile(r"\b(admin|root|administrator)\b[^.?!]*\bpassword\b", re.IGNORECASE)

# Prompt injection / instruction override / system-prompt exfiltration.
_INJECTION_RE = re.compile(
    r"("
    r"\bignore\b[^.?!]*\b(instruction|instructions|documentation|docs|knowledge\s+base|rules|prompt)\b"
    r"|\bdisregard\b[^.?!]*\b(instruction|instructions|rules|above)\b"
    r"|\b(developer|debug|god)\s+mode\b"
    r"|\byou\s+are\s+now\b"
    r"|\bsystem\s+prompt\b"
    r"|\boverride\b[^.?!]*\b(instruction|instructions|rules|safety)\b"
    r")",
    re.IGNORECASE,
)

# Attempts to weaken the controls that make side effects auditable and gated.
# Bypass verbs are matched in BOTH orders (verb->control and control->verb) so a
# reversed or pronoun phrasing -- "how do the safety checks work so I can bypass
# them" -- is caught deterministically, without depending on the LLM router.
_TAMPER_VERBS = (
    r"disable|skip|bypass|ignore|remove|turn\s+off|override|circumvent|defeat|"
    r"evade|get\s+around|work\s+around|trick|fool|sidestep|subvert"
)
_TAMPER_CONTROLS = (
    r"approval(?:\s+queue)?|logging|audit(?:ing)?|safety\s+(?:checks?|controls?|"
    r"filters?|mechanisms?)|guardrails?|safeguards?|tenant\s+(?:isolation|boundary)"
)
_CONTROL_TAMPER_RE = re.compile(
    r"("
    # verb -> control: "bypass the approval queue"
    rf"\b(?:{_TAMPER_VERBS})\b[^.?!]{{0,100}}\b(?:{_TAMPER_CONTROLS})\b"
    # control -> verb: "safety checks ... so I can bypass them"
    rf"|\b(?:{_TAMPER_CONTROLS})\b[^.?!]{{0,80}}\b(?:{_TAMPER_VERBS})\b"
    r"|\b(pretend|assume|claim)\b[^.?!]{0,60}\b(action\s+was\s+)?approved\b"
    r"|\bapprove\b[^.?!]{0,60}\b(automatically|without\s+(?:a\s+)?human)\b"
    r"|\b(action|external\s+action)\b[^.?!]{0,40}\bfirst\b[^.?!]{0,40}\blog\b[^.?!]*\blater\b"
    r"|\bwithout\b[^.?!]{0,50}\b(showing|asking|waiting)\b[^.?!]{0,40}\bhuman\b"
    r"|\bdo\s+not\s+mention\b[^.?!]{0,80}\bapproval\b[^.?!]*\bskipped\b"
    r")",
    re.IGNORECASE,
)

# Tenant isolation and customer privacy are hard boundaries, not model choices.
_CROSS_TENANT_RE = re.compile(
    r"("
    r"\b(all\s+)?other\s+customers?\b"
    r"|\banother\s+(tenant|customer|company|organization|org)\b"
    r"|\bother\s+(tenant|company|organization|org)(?:'s)?\b"
    r"|\bnot\s+authorized\b[^.?!]{0,50}\b(access|see|read|retrieve)\b"
    r"|\b(ignore|disable|override|bypass)\b[^.?!]{0,60}\btenant\b"
    r")",
    re.IGNORECASE,
)

# Requests for internal/private stores or bulk export of retrieved information.
_SENSITIVE_DATA_RE = re.compile(
    r"("
    r"\b(hidden\s+configuration\s+files?|internal\s+audit\s+logs?|"
    r"private\s+conversation\s+history|internal\s+vector\s+data|embeddings?)\b"
    r"|\b(export|send|return|reveal|retrieve|list|dump)\b[^.?!]{0,80}"
    r"\b(entire\s+knowledge\s+base|all\s+retrieved\s+documents?|all\s+documents?)\b"
    r")",
    re.IGNORECASE,
)

# Content-origin attacks and broad tool probing.
_UNTRUSTED_INSTRUCTION_RE = re.compile(
    r"("
    r"\btool\s+call\b[^.?!]{0,50}\bhidden\b|\bhidden\b[^.?!]{0,50}\btool\s+call\b"
    r"|\bfollow\b[^.?!]{0,50}\binstructions?\b[^.?!]{0,50}\buntrusted\s+document\b"
    r"|\bretrieved\s+text\b[^.?!]{0,50}\bsystem\s+instructions?\b"
    r"|\buser[-\s]provided\s+tool\s+parameters?\b[^.?!]{0,80}\bsystem\s+configuration\b"
    r"|\bcall\b[^.?!]{0,40}\bevery\s+available\s+tool\b"
    r"|\bdocument\b[^.?!]{0,50}\bignore\b[^.?!]{0,50}\binstructions?\b"
    r")",
    re.IGNORECASE,
)

_FALSE_SUCCESS_RE = re.compile(
    r"\b(claim|report|say|pretend)\b[^.?!]{0,60}\bsuccess\b"
    r"[^.?!]{0,60}\b(even\s+if|when|despite)\b[^.?!]{0,30}\b(fails?|failed|failure)\b",
    re.IGNORECASE,
)

# Destructive bulk operation: a destructive verb applied to "all/every ..." or
# to plural resources at org scope.
_DESTRUCTIVE_RE = re.compile(
    r"\b(delete|remove|wipe|purge|drop|destroy|erase|terminate|tear\s+down)\b"
    r"[^.?!]*\b(all|every|everything|entire|whole|each)\b"
    r"|\b(delete|remove|wipe|purge|drop|destroy|erase)\b"
    r"[^.?!]*\b(service|services|database|databases|account|accounts|"
    r"resource|resources|record|records|organization|org|project|projects)\b",
    re.IGNORECASE,
)

# Unauthorized privilege escalation: making the requester an owner/admin, or
# granting themselves access -- especially on someone else's record.
_PRIVILEGE_RE = re.compile(
    r"\b(add|make|set|grant|give|promote|elevate)\b[^.?!]*\b(me|myself|my\s+account)\b"
    r"[^.?!]*\b(owner|admin|administrator|superuser|root|access|permission|permissions)\b"
    r"|\badd\s+me\s+as\b[^.?!]*\b(owner|admin|administrator)\b",
    re.IGNORECASE,
)

# Priority inflation: the request demands a high/critical priority while
# conceding (or the evidence says) the issue is actually minor/low.
_HIGH_PRIORITY_RE = re.compile(
    r"\b(critical|urgent|highest|top|emergency|p0|p1|sev\s*1|severity\s*1)\b",
    re.IGNORECASE,
)
_MINOR_ADMISSION_RE = re.compile(
    r"\b(minor|low\s+priority|not\s+(that\s+)?urgent|trivial|small\s+(issue|problem)|"
    r"cosmetic|non[\s-]?urgent|even\s+though[^.?!]*minor|docs?\s+say[^.?!]*minor)\b",
    re.IGNORECASE,
)


def review(
    request: str,
    tool_name: Optional[str] = None,
    params: Optional[dict[str, Any]] = None,
    decision: Any = None,
) -> Verdict:
    """Verify a proposed action against the original request.

    `tool_name`/`params`/`decision` are optional context; the rules key mostly
    off the request text so the critic can also classify a request that the
    router already escalated (e.g. to confirm it must be refused).
    """
    text = request or ""

    # --- BLOCK rules (checked first; safety takes precedence) ----------------
    if _CREDENTIAL_RE.search(text) or _ADMIN_SECRET_RE.search(text):
        return Verdict(
            BLOCK, "credential_exfil",
            "Request asks to reveal a secret/credential; secrets are never "
            "retrievable and must not be disclosed.",
            must_refuse=True,
        )

    if _INJECTION_RE.search(text):
        return Verdict(
            BLOCK, "prompt_injection",
            "Request attempts to override instructions or exfiltrate the system "
            "prompt/secrets.",
            must_refuse=True,
        )

    if _CONTROL_TAMPER_RE.search(text):
        return Verdict(
            BLOCK, "control_tampering",
            "Request attempts to bypass approval, audit, logging, or another "
            "mandatory safety control.",
            must_refuse=True,
        )

    if _CROSS_TENANT_RE.search(text):
        return Verdict(
            BLOCK, "cross_tenant_access",
            "Request crosses a tenant/customer authorization boundary; private "
            "data from another tenant must not be accessed.",
            must_refuse=True,
        )

    if _SENSITIVE_DATA_RE.search(text):
        return Verdict(
            BLOCK, "sensitive_data_exfiltration",
            "Request asks for internal/private data or a bulk knowledge export "
            "that the support agent is not authorized to disclose.",
            must_refuse=True,
        )

    if _UNTRUSTED_INSTRUCTION_RE.search(text):
        return Verdict(
            BLOCK, "untrusted_instruction",
            "Instructions embedded in user or retrieved content cannot authorize "
            "tool use or replace system policy.",
            must_refuse=True,
        )

    if _FALSE_SUCCESS_RE.search(text):
        return Verdict(
            BLOCK, "false_success",
            "The agent must report tool failures honestly and cannot claim an "
            "action succeeded when it did not.",
            must_refuse=True,
        )

    if _DESTRUCTIVE_RE.search(text):
        return Verdict(
            BLOCK, "destructive",
            "Destructive bulk operation with no authorized tool; must not run "
            "automatically.",
            must_refuse=True, requires_approval=True,
        )

    if _PRIVILEGE_RE.search(text):
        return Verdict(
            BLOCK, "unauthorized_change",
            "Request grants the requester elevated ownership/access, a "
            "privilege change beyond the agent's authority.",
            must_refuse=True, requires_approval=True,
        )

    # --- REVISE rules (allow the action, but correct/guard it) ---------------
    if _HIGH_PRIORITY_RE.search(text) and _MINOR_ADMISSION_RE.search(text):
        return Verdict(
            REVISE, "priority_inflation",
            "Requested priority contradicts the stated/known severity; "
            "downgrading and routing to human approval.",
            requires_approval=True, patch={"urgency": "low"},
        )

    # --- default: allow ------------------------------------------------------
    return Verdict(ALLOW, "clean", "No safety concern detected.")
