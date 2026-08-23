# Sentinel — Project Context (read this first)

> Session-orientation file. Anyone (or any AI session) picking up this project should
> read this to understand what Sentinel is, what's built, how to run it, and what's next —
> without re-deriving it from the code every time.
>
> **`README.md` is the authoritative, up-to-date description of the shipped system**
> (architecture, API surface, eval results, quickstart). This file is the narrative
> build log; where the two ever disagree, trust the README.

_Last updated: 2026-08-22_

---

## 1. What it is

**Sentinel** is a self-hosted, reliability-focused **AI support-operations agent**.
Positioning: *"LLM brain, n8n hands."* It ingests support requests, answers them with
**RAG over a knowledge base (mandatory citations, or it escalates)**, and *resolves* them
by calling **n8n workflows as tools** — with multi-model routing, human approval for
risky actions, cost tracking, and a full eval + tracing layer.

- Full design doc: `AgentOps_9-10_Final_Build_Plan.md` ("AgentOps"/"Relay" were earlier
  working names; **Sentinel** is the project name).
- It's a ₹0-cost portfolio project for AI/ML internship applications.

## 2. Current status (2026-08-22)

- ✅ **Week 1 (RAG core) — COMPLETE.** Ingest → hybrid retrieval → cited answers, exposed
  over HTTP via a FastAPI `/ask` endpoint.
- ✅ **Week 2 (Orchestration + Tools) — COMPLETE.** LangGraph StateGraph
  (`router → answer | action | escalate`), tool registry with Pydantic validation,
  two n8n workflows (`create_ticket`, `cancel_invoice`), per-request cost/token/latency
  logging to a `runs` table, and the full `/triage` endpoint.
- ✅ **Week 3 (Safety + Observability) — COMPLETE.** Risk-tiered tool execution (low-risk
  auto-fires, high-risk queues for human approval), `approval_queue` table, full
  approve/reject REST API, deterministic **critic** gate (defense-in-depth re-check in
  `tools.approve()`), idempotency ledger, a per-step **audit log**, and **self-hosted
  Langfuse** tracing — one rich trace per request.
- ✅ **Week 4 (Evals + provider + polish) — COMPLETE.**
  - **300-case golden suite** (`evals/`) with a deterministic runner and a separate,
    calibration-gated local **LLM-as-judge**; the deterministic PR gate is **245/245**.
  - **GitHub Actions eval gates** (`.github/workflows/evals.yml` PR gate +
    `evals-full.yml` weekly semantic run).
  - **Gemini provider** alongside Ollama (independent chat/embed providers, `embed.py`).
  - **Multi-turn** support (`conversation.py`) + reliability/fault-injection and opt-in
    physical-shutdown tests.
  - **Frontend rebuilt** into the "Nightwatch" operator console (landing + Inbox / Trace /
    Approvals / Usage / Console under the `app/(app)/` route group), wired to live API
    with honest offline states — no mock data.
  - **Render public-docs case study** (`case-studies/`) and a full README rewrite with
    architecture diagram, evidence tables, and demo GIF.
- ✅ **Router baseline (Week 2)** — prompted `llama3.2:3b` router, **88.6%** routing
  accuracy on the golden set.
- ✅ **LoRA fine-tuning experiment (Week 4 add-on)** — trained a 1B LoRA router on Kaggle
  T4; honest result: **85.7%**, i.e. −2.9 pts vs. the prompt (didn't beat it —
  expected & fine).
- ⬜ **Remaining** — only a public demo deployment link. No public endpoint is implied yet.

## 3. Architecture (6 layers)

```
[Channels]      [Ingest]      [Brain]                     [Hands]         [Safety]           [Glass]
 Web form ──┐               ┌ Router (llama3.2:3b) ────┐
             ├─ FastAPI ────►│ RAG Answerer              ├─► n8n tool    ┌ Human approval     Cost/trace
             │   /triage     │ (pgvector + citations)    │   webhooks    │ queue (high-risk)  logging
             │   /ask        └ Action Agent ─────────────┘               │ (Next.js UI)       (runs table)
             │                   (tool registry + Pydantic)              └ Confidence gate    Eval harness
             └── /approvals (Next.js proxy → FastAPI)
```

**Weeks 1–3 built the full pipeline end-to-end:** Brain (RAG + Router), Hands (n8n tool
execution), Safety (approval queue + UI), and Glass (cost/trace logging). Channels are
web-form only for now.

## 4. Repo layout

```
Sentinel/
├── backend/
│   ├── app/
│   │   ├── config.py       # tiny .env loader + settings (DB, Ollama, retrieval, cost)
│   │   ├── db.py           # psycopg3 + pgvector schema/connection (chunks, tickets,
│   │   │                   #   runs, approval_queue, invoice_cancellations)
│   │   ├── chunking.py     # heading-aware Markdown chunking (keeps [citation-id]s)
│   │   ├── embed.py        # Ollama HTTP client (embeddings + chat), stdlib only
│   │   ├── ingest.py       # docs/ -> chunk -> embed -> upsert
│   │   ├── retrieve.py     # hybrid vector+FTS retrieval, RRF fusion
│   │   ├── answer.py       # cited answer generation, citations-or-escalate
│   │   ├── router.py       # triage router (route/intent/urgency/action_required)
│   │   ├── graph.py        # LangGraph StateGraph: router → answer|action|escalate
│   │   ├── tools.py        # tool registry, Pydantic param schemas, invoke/enqueue/
│   │   │                   #   approve/reject, n8n webhook execution, approval queue, idempotency
│   │   ├── critic.py       # deterministic safety critic: block/revise/allow before execution
│   │   ├── trace.py        # per-run cost/token/latency tracking (ContextVar + runs table)
│   │   ├── audit.py        # per-step audit trail (router→chunks→tool→outcome + approvals)
│   │   ├── lf.py           # Langfuse tracing (one trace/run: router→chunks→prompt→tool→cost)
│   │   ├── eval_routing.py # scores router vs golden.json
│   │   ├── eval_safety.py  # scores router+critic on adversarial cases (route/refuse/approval)
│   │   ├── cli.py          # init | ingest | search | route | ask | runs | approvals | audit
│   │   └── main.py         # FastAPI app: POST /ask, POST /triage, GET /approvals,
│   │                       #   POST /approvals/:id/approve|reject, GET /runs/:id/audit, GET /health
│   ├── requirements.txt    # psycopg[binary], fastapi, uvicorn[standard], langgraph, pydantic
│   └── .venv/              # Python 3.14 venv
├── frontend/               # Next.js 16 (React 19, Tailwind 4) "Nightwatch" console
│   ├── app/
│   │   ├── page.tsx        # public landing (live evals/system/stats via /api)
│   │   ├── (app)/          # operator console route group (shared app-shell layout)
│   │   │   ├── inbox/         # persisted runs list
│   │   │   ├── requests/[id]/ # one run's citations + usage + audit trail
│   │   │   ├── approvals/     # human approval queue (approve & run / reject)
│   │   │   ├── usage/         # cost / latency / eval observability
│   │   │   └── console/       # submit a request to the production graph
│   │   └── api/            # same-origin proxies → FastAPI (triage, health, system,
│   │       │               #   stats, runs, runs/:id, evals, approvals/:id/:action)
│   ├── components/
│   │   ├── shell/          # app-shell (sidebar nav + live approvals badge)
│   │   ├── console/        # pipeline-rail, request-console, triage-record, evidence-list,
│   │   │                   #   route/risk/status badges, stat-card, system-status
│   │   └── ui/             # button, border-beam, handwriting-svg
│   ├── lib/
│   │   ├── api.ts          # triage/fetchRuns/fetchRun/fetchStats/fetchEvals/fetchSystem/
│   │   │                   #   fetchApprovals/decideApproval/checkHealth
│   │   ├── types.ts        # TriageResult, RunRow/RunDetail, UsageStats, EvalSummary, ...
│   │   ├── format.ts       # display formatters
│   │   └── utils.ts        # cn() helper
│   └── package.json        # next 16, react 19, tailwindcss 4, lucide-react
├── n8n/
│   ├── workflows/
│   │   ├── webhook-to-tickets.json         # Webhook → tickets table (low-risk tool)
│   │   └── webhook-to-cancel-invoice.json  # Webhook → invoice_cancellations (high-risk)
│   ├── tickets.sql         # tickets table DDL
│   ├── cancel-invoice.sql  # invoice_cancellations table DDL
│   ├── credentials.local.json  # n8n Postgres credential (host: db, sentinel/sentinel)
│   └── README.md           # n8n setup guide
├── docs/                   # Meridian KB: 15 .md + README + 3 PDFs
├── evals/
│   ├── golden.json         # 35 labeled cases (held-out test set)
│   ├── baseline_routing.json
│   └── README.md
├── finetune/               # LoRA router experiment
│   ├── make_dataset.py     # synthetic routing dataset generator
│   ├── kaggle_train.py     # Kaggle T4 LoRA training + benchmark
│   ├── data/{train,val}.jsonl
│   └── README.md           # experiment + results
├── docker-compose.yml      # Postgres+pgvector (sentinel-db) + n8n (sentinel-n8n, 5679)
│                           #   + Langfuse (sentinel-langfuse, 3001) + its db (sentinel-langfuse-db)
├── .env / .env.example
├── context.md              # (this file)
└── README.md
```

## 5. Tech stack + why

| Concern | Choice | Why |
|---|---|---|
| Vector store | **Postgres + pgvector** (Docker) | One less service; transactional consistency. |
| Embeddings | **Ollama `nomic-embed-text`** (768-d) | Local, free; uses `search_document:`/`search_query:` prefixes. |
| Generation | **Ollama `llama3.2:3b`** | Local, free. |
| DB driver | **psycopg 3** (`psycopg[binary]`) | Bundles libpq; has a cp314 wheel. |
| API | **FastAPI + uvicorn** | Typed, auto-docs, async-capable. |
| Orchestration | **LangGraph** (`StateGraph`) | Compiles to a deterministic router→worker graph. |
| Tool execution | **n8n** self-hosted (Docker) | Webhooks as tools; adding a tool = building a workflow, zero Python changes. |
| LLM calls | **stdlib `urllib`** to Ollama HTTP | No SDK needed. |
| Frontend | **Next.js 16** + React 19 + Tailwind 4 + shadcn | Triage console + approval queue UI. |
| Fine-tune | **PEFT LoRA** on Kaggle T4 | Local AMD GPU can't train (no CUDA). |

## 6. How to run

Prereqs: **Docker Desktop running**, **Ollama running** with models pulled
(`ollama pull nomic-embed-text` and `ollama pull llama3.2:3b`), Python 3.11+, Node.js 18+.

```bash
cp .env.example .env
docker compose up -d                       # Postgres + pgvector + n8n + Langfuse
# Langfuse UI: http://localhost:3001 (auto-provisioned on first boot via
# LANGFUSE_INIT_* — login admin@sentinel.local / sentinel-admin; project keys
# pk-lf-sentinel-local / sk-lf-sentinel-local are already wired into .env).

# --- Backend ---
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

.venv\Scripts\python -m app.cli init       # create schema (all tables)
.venv\Scripts\python -m app.cli ingest --reset   # load docs/ (175 chunks)

# API (port 8199 — ports 8000/8001 are taken on this machine)
.venv\Scripts\uvicorn app.main:app --port 8199

# --- Frontend ---
cd ../frontend
npm install
npm run dev                                # http://localhost:3000

# --- n8n workflows ---
# Open http://localhost:5679, import workflow JSONs from n8n/workflows/,
# set up the Sentinel Postgres credential (host: db, port: 5432,
# user/pass/db: sentinel), and activate both workflows.
# Or import credential: docker cp n8n/credentials.local.json sentinel-n8n:/tmp/credentials.json
#                       docker exec sentinel-n8n n8n import:credentials --input=/tmp/credentials.json
```

**Environment note:** The backend runs on port **8199** (configured in `frontend/.env.local`
as `SENTINEL_API_URL=http://localhost:8199`). n8n runs on host port **5679** (container port
5678). The frontend proxies all API calls through Next.js route handlers → backend.

## 7. Database tables

| Table | Purpose |
|---|---|
| `chunks` | RAG knowledge chunks with pgvector embeddings + tsvector FTS |
| `tickets` | Support tickets created by the `create_ticket` tool (via n8n) |
| `runs` | Per-graph-run cost/token/latency/route trace log |
| `approval_queue` | High-risk actions queued for human approval (pending → approved → executed); `run_id` FK links back to the originating `runs` row |
| `invoice_cancellations` | Records of approved invoice cancellations (via n8n) |
| `audit_log` | Per-step decision trail: one row per step (router/retrieve/critic/tool/outcome) keyed by `run_id`, plus human approve/reject events keyed by `approval_id` |
| `tool_executions` | Idempotency ledger: `idempotency_key` → stored result, so a duplicated/retried action reuses the prior result instead of a second side effect |

## 8. Tool registry

Two tools registered in `backend/app/tools.py`:

| Tool | Risk | n8n webhook | What it does |
|---|---|---|---|
| `create_ticket` | **low** | `/webhook/ticket` | Opens a support ticket (auto-executes) |
| `cancel_invoice` | **high** | `/webhook/cancel-invoice` | Cancels an invoice (queued for human approval first) |

The graph's `action_node` selects the tool by intent (`_INTENT_TOOL` map): financial intents
(`billing_dispute`, `cancellation`, `refund_request`, `invoice_cancellation`) → `cancel_invoice`;
everything else → `create_ticket`. High-risk tools are enqueued via `tools.enqueue()` and never
auto-execute. Low-risk tools fire immediately via `tools.invoke()`.

**Critic gate (Week 3).** Before anything is queued or executed, `critic.review()` re-reads the
request against the proposed tool+params and returns **allow | revise | block**: credential/secret
exfiltration, prompt injection, unauthorized privilege escalation, and destructive bulk ops are
**blocked** (refuse + escalate, never run); an inflated priority contradicting the evidence is
**revised** (downgraded + forced through human approval). The critic is deterministic (rule-based,
no LLM) and runs again inside `tools.approve()` right before a high-risk webhook fires (defense in
depth). Low/medium-risk executions go through `tools.invoke(idempotent=True)`, which dedupes a
duplicated/retried action via the `tool_executions` ledger so it never creates a second side effect.

## 9. Approval flow (end-to-end, verified working)

```
User submits "cancel invoice INV-4455" via triage console
  → Router: route=action, intent=billing_dispute
  → action_node: selects cancel_invoice (high risk)
  → tools.enqueue(): writes pending row to approval_queue
  → UI shows "queued for human approval (#N)"

Operator opens /approvals page
  → fetchApprovals("pending") → Next.js proxy → FastAPI GET /approvals
  → Sees the card with tool params (invoice_id, requester_email, reason)
  → Clicks "Approve & run"
  → decideApproval(id, "approve") → Next.js proxy → FastAPI POST /approvals/:id/approve
  → tools.approve(): status pending→approved, invokes cancel_invoice webhook
  → n8n workflow: inserts row into invoice_cancellations table
  → status approved→executed, returns {executed: true}
  → UI shows green banner: "Approved #N — cancel_invoice executed via n8n."
```

## 10. Key design decisions & gotchas (learned the hard way)

- **nomic-embed-text needs task prefixes** — embed docs with `search_document:` and queries
  with `search_query:`, or retrieval separation is weak.
- **Confidence gate uses cosine similarity, NOT the RRF score.** RRF scores are tiny
  (~0.016); gate on `1 - (embedding <=> q)` (~0.7 for good hits). `CONFIDENCE_MIN=0.55`.
- **Citations-or-escalate** — if top-hit similarity < threshold, or the model can't ground
  the answer, escalate instead of fabricating. Small models need a firm citation prompt.
- **Golden set (`evals/golden.json`) is the held-out TEST set** — never train on it. The
  LoRA dataset generator hard-checks for overlap.
- **FastAPI endpoint is sync `def`** on purpose — `answer()` is blocking I/O, so FastAPI runs
  it in a threadpool (async def would block the event loop).
- **n8n port 5679 not 5678** — another local n8n (AutoSharePics) already owns port 5678.
  Override with `N8N_HOST_PORT` in `.env`.
- **N8N_WEBHOOK_BASE defaults to `http://localhost:5679/webhook`** — the backend calls
  n8n webhooks from the host, not from inside Docker. This is configured in `tools.py`.
- **Kaggle LoRA working config** (see `finetune/kaggle_train.py`): `unsloth/Llama-3.2-1B-Instruct`
  (ungated), plain `transformers.Trainer` (not trl), pinned `transformers==4.46.3`+`peft==0.13.2`,
  `pip uninstall -y torchao`, tokenize via `apply_chat_template(tokenize=False)` then `tok(text)`.
- **Tracing never breaks the request path** — `trace.log_run()` wraps all DB touches in
  try/except so a logging failure degrades to a warning and the agent still answers.
- **Next.js route handlers proxy all API calls** to the FastAPI backend. This keeps the
  backend URL server-side only (`frontend/.env.local`) and sidesteps CORS entirely.
- **Tracing/audit/Langfuse never block the request path** — `trace.py`, `audit.py`, and
  `lf.py` all wrap their DB/network touches in try/except. If Langfuse is down or its keys
  are unset (`LANGFUSE_ENABLED`/`LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY`), `lf.py`
  silently no-ops. Langfuse cost shows **$0** for local Ollama (no model pricing) — that's
  honest; token usage is still tracked. Langfuse v3 is heavy (ClickHouse/Redis/Minio); we
  run **v2** which needs only its own Postgres.
- **Langfuse instrumentation hooks the single Ollama `_post` chokepoint** — both LLM calls
  (router + answer) become Langfuse *generations*; `lf.label()` names which one. The
  `retrieve`/`tool` steps are logged as spans where the data lives (answer.py / graph.py).

## 11. Numbers to remember

- Ingest: **175 chunks** from 16 markdown files.
- Legacy router golden set (`evals/golden.json`): **35 cases** — the held-out set the
  Week 2 router baseline and the LoRA experiment were scored against.
- Main eval suite (`evals/golden/agentops_meridian_300_cases.json`): **300 cases**; the
  **245** deterministically checkable ones are the PR gate — currently **245/245**
  (reproducible with the LLM offline; see `evals/reports/latest.md`).
- Router baseline (Week 2): **routing 88.6%, urgency 82.9%, escalation recall 81.8%, over-escalation 0%.**
- Router after Week 3 safety-rule (ticket-creation stays `action` even with an asserted
  priority): **routing 91.4%** (32/35), no regressions. NB: the LoRA experiment below was
  measured against the *88.6%* baseline, before this rule.
- LoRA router: **routing 85.7%** (−2.9 pts vs the 88.6% baseline) — negative result, honestly reported.
- Safety eval (`app.eval_safety`, router + critic): **8/8 adversarial cases pass** (route +
  must_refuse + requires_approval). Offline suites: `test_action_tool` 20/20, `test_critic` 12/12.
- n8n tools: **2** (create_ticket: low-risk, cancel_invoice: high-risk).
- Approval queue: end-to-end tested — approve fires webhook, row confirmed in DB.

## 12. Meridian (the fictional KB company) — consistency facts

API base `https://api.meridian.io/v1`; dashboard `dashboard.meridian.io`; keys `msk_live_`/
`msk_test_`/`mpk_live_`/`whsec_`/`mpat_`; plans Hobby/Pro($19)/Team($99)/Enterprise; support
Community/Standard/Priority/Premier; regions us-east/us-west/eu-central/ap-south/ap-southeast;
date-versioned API `Meridian-Version: 2025-08-01`. Every doc H2 ends with a stable
`[citation-id]` (prefix per doc, mapped in `docs/README.md`). Keep these stable if editing docs.

## 13. Next step

Weeks 1–4 are complete (evals-in-CI, semantic judge, Gemini provider, frontend rebuild,
case study, README polish all done). The only remaining item is a **public demo
deployment link**; a 2-min demo video and the personalized founder pitch emails are the
non-code follow-ups.
