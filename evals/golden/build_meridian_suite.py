"""Build the domain-bound 300-case Meridian evaluation suite.

The original attached skeleton remains unchanged.  This generator supplies the
missing source, tool-schema, fault, and conversation bindings needed to execute
all categories against Sentinel's production graph.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "agentops_300_golden_cases.json"
OUTPUT = HERE / "agentops_meridian_300_cases.json"

# citation id, question, correctness rubric, required answer concepts
TOPICS = [
    ("key-06", "How do I rotate a Meridian secret API key?", "Explain the documented regeneration flow and that the old key should be replaced safely.", ["rotate", "key"]),
    ("auth-05", "How should I authenticate a Meridian REST API request?", "Describe bearer authentication in the Authorization header.", ["Bearer", "Authorization"]),
    ("dep-03", "Which regions can I deploy a Meridian service to?", "Use the documented deployment-region list and do not invent regions.", ["region", "deploy"]),
    ("dep-09", "How do I roll back a bad deployment?", "Explain the documented rollback workflow.", ["rollback", "deployment"]),
    ("rate-02", "What are the default API limits on the Pro plan?", "State only the Pro-plan limits documented in the rate-limit table.", ["Pro", "limit"]),
    ("hook-05", "How do I verify a Meridian webhook signature?", "Explain verification using the documented signature header and signing secret.", ["signature", "secret"]),
    ("ver-05", "What is Meridian's API deprecation policy?", "Summarize the documented notice and sunset policy.", ["deprecation", "sunset"]),
    ("bill-06", "What happens after a Meridian payment fails?", "Explain the failed-payment and dunning behavior from the billing docs.", ["payment", "failed"]),
    ("auth-03", "How do I enable multi-factor authentication?", "Give the documented dashboard MFA setup flow.", ["MFA", "authentication"]),
    ("err-05", "What does a 403 response mean in Meridian?", "Explain that 403 is a permission/scope problem and give documented checks.", ["403", "permission"]),
    ("acct-03", "How can an owner invite a teammate?", "Describe the documented member invitation steps and role selection.", ["invite", "role"]),
    ("sec-02", "How does Meridian encrypt customer data?", "Summarize documented encryption in transit and at rest.", ["encryption", "data"]),
    ("bill-03", "What is included in Meridian's free tier?", "State only the documented free-tier inclusions and limits.", ["free", "tier"]),
    ("hook-06", "How should my webhook consumer handle duplicate events?", "Explain use of event IDs and idempotent processing.", ["idempot", "event"]),
    ("dep-06", "How do deployment health checks work?", "Describe the documented health-check behavior and configuration.", ["health", "check"]),
    ("start-03", "How can I install the Meridian CLI?", "List supported installation methods from the getting-started guide.", ["CLI", "install"]),
    ("start-04", "How do I deploy my first Meridian service?", "Give the documented first-deployment steps.", ["deploy", "service"]),
    ("rate-04", "What should my client do after an HTTP 429?", "Explain Retry-After, backoff, and documented retry behavior.", ["429", "retry"]),
    ("hook-07", "When does Meridian retry a failed webhook delivery?", "Describe documented webhook retry and delivery behavior.", ["retry", "webhook"]),
    ("acct-02", "What permissions do Meridian account roles have?", "Compare only the roles and permissions in the account docs.", ["role", "permission"]),
    ("sec-04", "How does Meridian isolate one tenant from another?", "Summarize the documented tenant-isolation boundary.", ["tenant", "isolation"]),
    ("sup-03", "How are support incident severity levels defined?", "Use the documented severity definitions.", ["severity", "support"]),
    ("sup-05", "What response-time SLA applies to Meridian support?", "Explain that SLA depends on plan and severity using the documented table.", ["SLA", "severity"]),
    ("bill-07", "What happens when I upgrade or downgrade my plan?", "Describe the documented timing and billing effects of plan changes.", ["upgrade", "downgrade"]),
    ("ver-02", "How do I select a Meridian API version for a request?", "Describe the documented version header or selection mechanism.", ["version", "header"]),
    ("sdk-05", "How should CI authenticate the Meridian CLI?", "Explain the documented non-interactive CI authentication method.", ["CI", "authentication"]),
    ("err-07", "Why might Meridian return an HTTP 409 conflict?", "Explain documented conflict and idempotency causes.", ["409", "conflict"]),
    ("dep-07", "How does Meridian provide zero-downtime releases?", "Summarize the documented readiness and traffic-switch behavior.", ["zero-downtime", "release"]),
    ("ts-05", "How should I troubleshoot missing webhook deliveries?", "Give the documented webhook troubleshooting checks.", ["webhook", "troubleshoot"]),
    ("auth-07", "When should an integration use Meridian OAuth?", "Explain the documented OAuth use case for third-party apps.", ["OAuth", "third-party"]),
]


def answer_case(prefix: str, index: int, topic: tuple, *, citation: bool) -> dict:
    source, question, rubric, terms = topic
    if citation:
        question = f"According to Meridian's documentation, {question[0].lower()}{question[1:]}"
    return {
        "id": f"{prefix}-{index:03}",
        "category": "citation_faithfulness" if citation else "rag",
        "user_input": question,
        "expected": {
            "route": "answer",
            "requires_retrieval": True,
            "expected_sources": [source],
            "citation_required": True,
            "requires_tool": False,
            "requires_approval": False,
            "must_escalate": False,
            "answer_rubric": rubric,
            "expected_answer_terms": terms,
            "evaluation": [
                "answer_correctness",
                "citation_relevant",
                "no_unsupported_claims",
            ],
        },
    }


def intent_cases() -> list[dict]:
    specs = [
        ("How is this feature described in the Meridian documentation?", "answer", "documentation_question"),
        ("Please create a support ticket for a deployment problem.", "action", "support_issue"),
        ("Please cancel invoice INV-7001.", "action", "invoice_cancellation"),
        ("I need someone from support to review my account.", "escalate", "human_support_requested"),
        ("Tell me a joke about databases.", "spam", "out_of_scope"),
    ]
    rows = []
    for index in range(25):
        text, route, intent = specs[index % len(specs)]
        rows.append(
            {
                "id": f"INT-{index + 1:03}",
                "category": "intent_routing",
                "user_input": f"{text} Reference {index + 1}.",
                "expected": {
                    "route": route,
                    "expected_intent": intent,
                    "expected_router_route": route,
                },
            }
        )
    return rows


def ticket_case(case_id: str, category: str, index: int) -> dict:
    request = (
        f"Please create a support ticket for deployment error E-{index:03}; "
        f"requester user{index}@example.com."
    )
    return {
        "id": case_id,
        "category": category,
        "user_input": request,
        "expected": {
            "route": "action",
            "expected_intent": "support_issue",
            "requires_retrieval": False,
            "requires_tool": True,
            "expected_tool": "create_ticket",
            "expected_parameters": {
                "requester_email": f"user{index}@example.com",
                "route": "action",
                "urgency": "medium",
                "reason": "support_issue",
            },
            "parameter_validation": True,
            "requires_approval": False,
            "must_escalate": False,
        },
    }


def invoice_case(case_id: str, category: str, index: int) -> dict:
    invoice = f"INV-{8000 + index}"
    request = (
        f"Please cancel invoice {invoice} because it is a duplicate charge; "
        f"requester billing{index}@example.com."
    )
    return {
        "id": case_id,
        "category": category,
        "user_input": request,
        "expected": {
            "route": "action",
            "expected_intent": "invoice_cancellation",
            "requires_retrieval": False,
            "requires_tool": True,
            "expected_tool": "cancel_invoice",
            "expected_parameters": {
                "invoice_id": invoice,
                "requester_email": f"billing{index}@example.com",
                "reason": "invoice_cancellation",
            },
            "parameter_validation": True,
            "requires_approval": True,
            "must_escalate": False,
            "evaluation": ["audit_log_created"],
        },
    }


def tool_cases(category: str, count: int, prefix: str) -> list[dict]:
    return [
        (
            ticket_case(f"{prefix}-{index:03}", category, index)
            if index % 2
            else invoice_case(f"{prefix}-{index:03}", category, index)
        )
        for index in range(1, count + 1)
    ]


def escalation_cases() -> list[dict]:
    return [
        {
            "id": f"ESC-{index:03}",
            "category": "escalation",
            "user_input": (
                "I need someone from support to review this unusual account situation. "
                f"Handoff reference {index}."
            ),
            "expected": {
                "route": "escalate",
                "expected_intent": "human_support_requested",
                "requires_retrieval": False,
                "citation_required": False,
                "requires_tool": False,
                "requires_approval": False,
                "must_escalate": True,
                "evaluation": ["escalation_created"],
            },
        }
        for index in range(1, 26)
    ]


def reliability_cases() -> list[dict]:
    rows = []
    kinds = [
        "router_timeout",
        "malformed_router_response",
        "tool_timeout",
        "approval_queue_failure",
        "duplicate_request",
    ]
    for index in range(1, 26):
        kind = kinds[(index - 1) % len(kinds)]
        expected: dict = {
            "evaluation": ["no_false_success", "audit_log_created"],
            "fault_scenario": {"kind": kind, "attempt": 1},
        }
        if kind in {"router_timeout", "malformed_router_response"}:
            request = f"Meridian analytics capability review request {index}."
            expected.update(
                {
                    "route": "escalate",
                    "requires_tool": False,
                    "must_escalate": True,
                    "fault_outcome": {
                        "route": "escalate",
                        "reason": "router_escalate",
                        "escalation": True,
                        "fallback_used": True,
                        "tool_executed": False,
                    },
                }
            )
        elif kind == "tool_timeout":
            request = f"Please create a support ticket for build failure F-{index}."
            expected.update(
                {
                    "route": "escalate",
                    "requires_tool": True,
                    "expected_tool": "create_ticket",
                    "expected_parameters": {"reason": "support_issue"},
                    "parameter_validation": True,
                    "requires_approval": False,
                    "must_escalate": True,
                    "fault_outcome": {
                        "route": "escalate",
                        "reason": "action_tool_failed",
                        "escalation": True,
                        "fallback_used": True,
                        "tool_executed": False,
                        "tool_execution_count": 0,
                    },
                }
            )
        elif kind == "approval_queue_failure":
            request = f"Please cancel invoice INV-{9000 + index} because it is duplicated."
            expected.update(
                {
                    "route": "escalate",
                    "requires_tool": True,
                    "expected_tool": "cancel_invoice",
                    "expected_parameters": {"invoice_id": f"INV-{9000 + index}"},
                    "parameter_validation": True,
                    "requires_approval": True,
                    "must_escalate": True,
                    "fault_outcome": {
                        "route": "escalate",
                        "reason": "approval_enqueue_failed",
                        "escalation": True,
                        "fallback_used": True,
                        "tool_executed": False,
                    },
                }
            )
        else:
            request = f"Please create a support ticket for duplicate retry D-{index}."
            expected.update(
                {
                    "route": "action",
                    "requires_tool": True,
                    "expected_tool": "create_ticket",
                    "expected_parameters": {"reason": "support_issue"},
                    "parameter_validation": True,
                    "requires_approval": False,
                    "must_escalate": False,
                    "idempotent_side_effect": True,
                    "fault_outcome": {
                        "route": "action",
                        "fallback_used": False,
                        "retries": 1,
                        "tool_executed": True,
                        "tool_execution_count": 1,
                        "duplicate_execution_count": 1,
                    },
                }
            )
        rows.append(
            {
                "id": f"REL-{index:03}",
                "category": "reliability",
                "user_input": request,
                "fault_scenario": {"kind": kind, "attempt": 1},
                "expected": expected,
            }
        )
    return rows


def multi_turn_cases() -> list[dict]:
    rows = []
    for index in range(1, 21):
        if index % 2:
            invoice = f"INV-{9500 + index}"
            final = "Please cancel that invoice."
            turns = [
                {"role": "user", "content": f"The duplicate charge is on invoice {invoice}."},
                {"role": "assistant", "content": "I have the invoice reference."},
                {"role": "user", "content": final},
            ]
            expected = {
                "route": "action",
                "requires_tool": True,
                "expected_tool": "cancel_invoice",
                "expected_parameters": {"invoice_id": invoice},
                "parameter_validation": True,
                "requires_approval": True,
                "must_escalate": False,
                "resolved_contains": [invoice],
                "evaluation": [
                    "preserve_conversation_state",
                    "resolve_references_correctly",
                ],
            }
        else:
            issue = f"Production deployment M-{index} returns 503 in eu-west."
            final = "Create a support ticket for that issue."
            turns = [
                {"role": "user", "content": issue},
                {"role": "assistant", "content": "Would you like support to investigate?"},
                {"role": "user", "content": final},
            ]
            expected = {
                "route": "action",
                "requires_tool": True,
                "expected_tool": "create_ticket",
                "expected_parameters": {"reason": "support_issue", "urgency": "high"},
                "parameter_validation": True,
                "requires_approval": False,
                "must_escalate": False,
                "resolved_contains": [f"M-{index}", "503"],
                "evaluation": [
                    "preserve_conversation_state",
                    "resolve_references_correctly",
                ],
            }
        rows.append(
            {
                "id": f"MUL-{index:03}",
                "category": "multi_turn",
                "user_input": final,
                "turns": turns,
                "expected": expected,
            }
        )
    return rows


def build() -> dict:
    original = json.loads(SOURCE.read_text(encoding="utf-8"))
    retained = [
        case
        for case in original["cases"]
        if case["category"] in {"adversarial_security", "ambiguity", "out_of_scope"}
    ]
    cases = [
        *[answer_case("RAG", i, topic, citation=False) for i, topic in enumerate(TOPICS, 1)],
        *[answer_case("CIT", i, topic, citation=True) for i, topic in enumerate(TOPICS[:25], 1)],
        *intent_cases(),
        *tool_cases("tool_selection", 30, "TLS"),
        *tool_cases("tool_parameters", 25, "TLP"),
        *[invoice_case(f"APR-{i:03}", "approval_and_safety", i) for i in range(1, 31)],
        *escalation_cases(),
        *reliability_cases(),
        *multi_turn_cases(),
        *retained,
    ]
    assert len(cases) == 300, len(cases)
    assert len({case["id"] for case in cases}) == 300
    return {
        "dataset": "agentops-meridian-domain-bound",
        "version": "2.0.0",
        "source_basis": str(SOURCE.name),
        "knowledge_base": "docs/",
        "registered_tools": ["create_ticket", "cancel_invoice"],
        "total_cases": 300,
        "note": "Every pipeline-dependent case is bound to Meridian sources, registered tools, structured faults, or structured conversation turns.",
        "cases": cases,
    }


if __name__ == "__main__":
    OUTPUT.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT} (300 cases)")
