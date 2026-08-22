# AgentOps evaluation framework

This directory contains evaluation and regression tests, **not model-training
data**. The 300-case suite is never imported by the fine-tuning code.

## How it connects to AgentOps

The runner invokes the production `backend/app/graph.py` graph. That keeps the
real router, retrieval, answer generation, critic, tool selection, parameter
validation, approval decision, trace accounting, and audit collection on the
execution path. The adapter replaces only unsafe external boundaries during an
evaluation:

- n8n/webhook calls are recorded in memory;
- approval-queue writes are validated, then recorded in memory;
- run/audit persistence is captured for assertions without polluting production
  tables;
- Langfuse export is off by default and can be enabled with `--langfuse`.

No case-specific fake agent or expected-answer lookup exists.

## Layout

```text
evals/
├── golden/
│   ├── agentops_300_golden_cases.json  # unchanged attached skeleton
│   ├── agentops_meridian_300_cases.json # executable default suite
│   └── build_meridian_suite.py          # reproducible suite generator
├── judges/
│   ├── deterministic.py                # exact/state/safety assertions
│   └── llm_judge.py                    # optional structured semantic judge
├── runners/
│   ├── agentops_adapter.py             # production graph + safe boundaries
│   ├── evaluator.py
│   └── run_golden.py
├── reports/                             # generated JSON + Markdown
├── tests/test_golden.py                 # pytest parametrization
├── reporting.py
└── schema.py                            # forward-compatible case contracts
```

## Run

From the repository root, with Postgres and Ollama running and the knowledge
base already ingested:

```bash
python -m evals.runners.run_golden
python -m evals.runners.run_golden --category intent_routing --limit 5
pytest evals/
```

The CLI writes `evals/reports/in_progress.json` atomically after every completed
case. After an interruption, rerun the identical command with `--resume`:

```bash
python -m evals.runners.run_golden --judge ollama --resume
```

The default is deterministic evaluation. Routing, approval, tool execution,
clarification, refusal, non-exfiltration, and out-of-scope decline checks use
observable production state and fixed response contracts. A generative judge
cannot override those safety facts.

Enable the structured local semantic judge only for meaning-level answer and
citation checks. The runner requires a passing model- and prompt-specific
calibration report by default:

```bash
python -m evals.judges.calibrate --model <judge-model>
python -m evals.runners.run_golden --judge ollama --judge-model <calibrated-model>
```

`--allow-uncalibrated-judge` exists only for local experimentation and must not
be used in a release gate.

Langfuse association is opt-in so normal regression runs do not create hundreds
of traces:

```bash
python -m evals.runners.run_golden --langfuse
```

## CI/regression gates

Every percentage comes from executed checks. `NOT_IMPLEMENTED` checks are shown
separately and excluded from pass-rate denominators.

```bash
python -m evals.runners.run_golden \
  --min-overall 0.85 \
  --min-routing 0.90 \
  --min-tool-selection 0.90 \
  --min-citations 0.90 \
  --min-approval-safety 1.0 \
  --min-reliability 1.0 \
  --min-multi-turn 1.0 \
  --max-not-implemented 0
```

Critical safety failures always produce a failing exit code, regardless of the
overall score. A prior JSON report can be compared with `--baseline` and
`--max-regression`.

Pull requests run the 245 offline production-graph cases in
`.github/workflows/evals.yml`. A weekly/manual self-hosted workflow runs the
complete 300-case RAG suite after ingesting the knowledge base and calibrating
the semantic judge.

## Evolving/domain-bound schema

Unknown fields are preserved, so cases can progressively add:

```json
{
  "expected_intent": "billing_question",
  "expected_sources": ["billing-03"],
  "expected_tool": "create_ticket",
  "expected_parameters": {"requester_email": "user@example.com"},
  "expected_answer": "...",
  "requires_approval": true,
  "turns": [{"role": "user", "content": "..."}],
  "fault_scenario": {"model": "primary", "error": "rate_limit", "attempt": 1}
}
```

The preserved v1 skeleton intentionally lacks many of these bindings. Missing
source IDs, answers, tool schemas, structured turns, and fault scenarios are
reported as `DOMAIN_BINDING_REQUIRED` or `NOT_IMPLEMENTED`; they are never
invented and never counted as passes.

Generic RAG, citation-faithfulness, and undocumented-escalation prompts are not
sent through answer generation until at least an expected source ID, expected
answer, or answer rubric is bound. This avoids evaluating an arbitrary answer
to an unspecified question while retaining every case in the suite.

Likewise, tool-selection, parameter, and approval cases require a named tool
that exists in the production registry. Generic actions or tools from another
domain are reported as `DOMAIN_BINDING_REQUIRED` instead of being mapped to an
arbitrary fallback tool or counted as production failures.

The default v2 Meridian suite supplies these bindings for all 300 cases. Its
RAG cases reference real `docs/` citation IDs, every tool case names a registered
schema, and reliability/multi-turn cases contain executable fault and turn data.

`intent_routing` cases run at the production router boundary. They contribute
real routing accuracy and model/latency metadata without triggering an
unbound answer or side effect; downstream behavior remains visibly unverified.
