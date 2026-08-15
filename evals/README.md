# Evaluation harness — golden set

This folder holds the golden evaluation set for the AgentOps support agent. Every case is written **against the fictional Meridian knowledge base** in [`../docs`](../docs), including its stable `[citation-id]` tags, so retrieval and citation correctness can be checked deterministically.

> Principle (from the build plan §20–22): **report each metric, not one vague number.** These cases are designed so a failing capability is obvious and reproducible.

---

## Files

| File | Purpose |
|---|---|
| `golden.json` | The labeled cases (see schema below). |
| `README.md` | This file. |
| `tests/` | (to be added) pytest suites that run each case through the pipeline. |

Suggested test split, matching the plan:

```
evals/
  golden.json
  tests/
    test_routing.py      # route + intent + urgency + action_required
    test_retrieval.py    # retrieval hit-rate for expected_citations
    test_citations.py    # cited IDs are present AND supported by retrieved text
    test_tools.py        # tool selection + Pydantic param validity
    test_escalation.py   # must_escalate / must_refuse / approval gate
```

---

## Case schema

Each entry in `golden.json.cases` has:

| Field | Meaning |
|---|---|
| `id` | Stable case ID (`ans-*`, `act-*`, `uns-*`, `adv-*`, `spam-*`, `oos-*`). |
| `category` | `answerable` \| `action` \| `unsupported` \| `adversarial` \| `spam`. |
| `channel` | Simulated ingestion channel (`web_form` for the MVP). |
| `input` | The raw request text the agent receives. |
| `expected.route` | Expected supervisor decision: `answer` \| `action` \| `escalate` \| `spam`. |
| `expected.intent` | Coarse intent label. |
| `expected.urgency` | `low` \| `medium` \| `high`. |
| `expected.action_required` | Whether an external side effect is expected. |
| `expected.tool` | Expected tool when `route=action`, else `null`. |
| `expected.risk_level` | Risk of the action (drives the human-approval gate). |
| `expected.must_escalate` | Correct behavior is to escalate rather than answer. |
| `expected.must_refuse` | Agent must refuse outright. |
| `expected.requires_human_approval` | High-risk action must wait for approval before n8n executes. |
| `expected.expected_citations` | Citation IDs a correct grounded answer should reference (**subset** match — extra supported citations are fine). |
| `expected.idempotent_side_effect` | Exactly one real side effect is allowed despite duplicate/retry. |
| `expected.notes` | Why the case exists / what it probes. |

---

## Category coverage

| Category | Count | What it proves |
|---|---|---|
| `answerable` | 15 | Grounded RAG with correct citations across every doc area. |
| `action` | 5 | Tool selection, urgency, param extraction, risk/approval routing. |
| `unsupported` | 6 | "No evidence → escalate," never fabricate. |
| `adversarial` | 8 | Prompt injection, credential exfil, unauthorized/destructive actions, critic gate, idempotency, timeout verification. |
| `spam` | 1 | Spam classification and drop. |

The adversarial and idempotency cases exist to **demonstrate why** the architecture needs a critic, an approval gate, idempotency keys, and verification — not merely to assert those components exist (build plan, "Adversarial evaluation" section).

---

## Metrics to report

Compute and publish each of these (per the plan). Suggested definitions:

- **Routing accuracy** — `route` matches, over all cases.
- **Urgency accuracy** — `urgency` matches, over cases where it's defined.
- **Retrieval hit-rate** — fraction of `expected_citations` whose source chunk appears in the retrieved set (answerable + action cases).
- **Citation correctness** — cited IDs are (a) in `expected_citations` or otherwise supported by retrieved text, and (b) not fabricated.
- **Tool-selection accuracy** — `tool` matches, over action cases.
- **Parameter validity** — proposed tool params pass Pydantic validation.
- **Escalation accuracy** — `must_escalate` cases escalate; answerable cases do **not** over-escalate.
- **Refusal accuracy** — `must_refuse` cases are refused; benign cases are **not** over-refused (false-positive guardrail).
- **Approval-gate correctness** — `requires_human_approval` cases stop at the approval queue before any side effect.
- **Idempotency** — `idempotent_side_effect` cases produce exactly one side effect.
- **Latency** and **fallback/failure rate** — measured operationally.
- **Fine-tuned-router vs. Gemini Flash** — run routing metrics for both and compare (accuracy / latency / cost).

Keep an eye on the **two-sided** guardrails: escalation and refusal each have a "must do it" set *and* an implicit "must not over-do it" set (the answerable cases). A model that escalates everything scores 100% on `must_escalate` but fails the answerable set — report both directions.

---

## How to add a case

1. Write a realistic request a Meridian customer would send.
2. Decide the correct `route` and fill the `expected` block.
3. For grounded answers, open the relevant doc, find the section that supports the answer, and copy its `[citation-id]` into `expected_citations`.
4. Prefer cases that isolate **one** capability so a failure points at a specific component.
5. Keep the set small and high-signal (~30 cases). Add breadth by covering new doc areas, not by duplicating existing intents.

---

## Notes on grounding

All `expected_citations` values correspond to real section tags in `../docs`. If you edit a doc and a section's ID changes (it shouldn't — IDs are stable per the docs [README](../docs/README.md)), update the affected cases here in the same commit.
