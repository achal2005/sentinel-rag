# Sentinel — Project Context (read this first)

> Session-orientation file. Anyone (or any AI session) picking up this project should
> read this to understand what Sentinel is, what's built, how to run it, and what's next —
> without re-deriving it from the code every time.

_Last updated: 2026-08-15_

---

## 1. What it is

**Sentinel** is a self-hosted, reliability-focused **AI support-operations agent**.
Positioning: *"LLM brain, n8n hands."* It ingests support requests, answers them with
**RAG over a knowledge base (mandatory citations, or it escalates)**, and is designed to
*resolve* them by calling **n8n workflows as tools** — with multi-model routing, human
approval for risky actions, cost tracking, and a full eval + tracing layer.

- Full design doc: `AgentOps_9-10_Final_Build_Plan.md` ("AgentOps"/"Relay" were earlier
  working names; **Sentinel** is the project name).
- It's a ₹0-cost portfolio project for AI/ML internship applications.

## 2. Current status (2026-08-15)

- ✅ **Week 1 (RAG core) — COMPLETE.** Ingest → hybrid retrieval → cited answers, exposed
  over HTTP via a FastAPI `/ask` endpoint.
- ✅ **Router agent + baseline (Week 2 start)** — prompted `llama3.2:3b` router, **88.6%**
  routing accuracy on the golden set.
- ✅ **LoRA fine-tuning experiment (Week-4 add-on)** — trained a 1B LoRA router on Kaggle T4;
  honest result: **85.7%**, i.e. −2.9 pts vs. the prompt (didn't beat it — expected & fine).
- ⬜ **Rest of Week 2** — LangGraph loop, tool registry, first real n8n tool, cost logging.
- ⬜ Weeks 3–4 — approval UI, Langfuse tracing, audit log, eval-in-CI, polish.

## 3. Architecture (6 layers)

```
[Channels]      [Ingest]      [Brain]                     [Hands]      [Safety]        [Glass]
 Web form ──┐               ┌ Router (cheap LLM) ──────┐
 Email ─────┼─ FastAPI ────►│ RAG Answerer              ├─► n8n tool  ┌ Human approval  Langfuse
 WhatsApp ──┘   endpoints   │ (pgvector + citations)    │   webhooks  │ queue (risky)   Eval harness
                            └ Action Agent ─────────────┘             └ Confidence gate Cost dashboard
```

**Week 1 built the Brain (RAG Answerer) + the web-form Ingest endpoint.** Everything else
is planned/partial.

## 4. Repo layout

```
Sentinel/
├── backend/
│   ├── app/
│   │   ├── config.py       # tiny .env loader + settings
│   │   ├── db.py           # psycopg3 + pgvector schema/connection
│   │   ├── chunking.py     # heading-aware Markdown chunking (keeps [citation-id]s)
│   │   ├── embed.py        # Ollama HTTP client (embeddings + chat), stdlib only
│   │   ├── ingest.py       # docs/ -> chunk -> embed -> upsert
│   │   ├── retrieve.py     # hybrid vector+FTS retrieval, RRF fusion
│   │   ├── answer.py       # cited answer generation, citations-or-escalate
│   │   ├── router.py       # triage router (route/intent/urgency/action_required)
│   │   ├── eval_routing.py # scores router vs golden.json
│   │   ├── cli.py          # init | ingest | search | route | ask
│   │   └── main.py         # FastAPI app: POST /ask, GET /health
│   ├── requirements.txt    # psycopg[binary], fastapi, uvicorn[standard]
│   └── .venv/              # Python 3.14 venv
├── frontend/               # placeholder (Week 3 approval UI)
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
├── docker-compose.yml      # Postgres + pgvector (container: sentinel-db)
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
| LLM calls | **stdlib `urllib`** to Ollama HTTP | No SDK needed yet. |
| Fine-tune | **PEFT LoRA** on Kaggle T4 | Local AMD GPU can't train (no CUDA). |

## 6. How to run

Prereqs: **Docker Desktop running**, **Ollama running** with models pulled
(`ollama pull nomic-embed-text` and `ollama pull llama3.2:3b`), Python 3.11+.

```bash
cp .env.example .env
docker compose up -d                       # Postgres + pgvector (sentinel-db)

cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

.venv\Scripts\python -m app.cli init       # create schema
.venv\Scripts\python -m app.cli ingest --reset   # load docs/ (175 chunks)

# CLI
.venv\Scripts\python -m app.cli ask "how do I rotate an API key?"
.venv\Scripts\python -m app.cli route "cancel my subscription"

# API
.venv\Scripts\uvicorn app.main:app --reload --port 8000   # then open /docs

# Routing eval
.venv\Scripts\python -m app.eval_routing
```

## 7. Key design decisions & gotchas (learned the hard way)

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
- **Kaggle LoRA working config** (see `finetune/kaggle_train.py`): `unsloth/Llama-3.2-1B-Instruct`
  (ungated), plain `transformers.Trainer` (not trl), pinned `transformers==4.46.3`+`peft==0.13.2`,
  `pip uninstall -y torchao`, tokenize via `apply_chat_template(tokenize=False)` then `tok(text)`.

## 8. Numbers to remember

- Ingest: **175 chunks** from 16 markdown files.
- Golden set: **35 cases** (answerable 15, action 5, unsupported 6, adversarial 8, spam 1).
- Router baseline: **routing 88.6%, urgency 82.9%, escalation recall 81.8%, over-escalation 0%.**
- LoRA router: **routing 85.7%** (−2.9 pts) — negative result, honestly reported.

## 9. Meridian (the fictional KB company) — consistency facts

API base `https://api.meridian.io/v1`; dashboard `dashboard.meridian.io`; keys `msk_live_`/
`msk_test_`/`mpk_live_`/`whsec_`/`mpat_`; plans Hobby/Pro($19)/Team($99)/Enterprise; support
Community/Standard/Priority/Premier; regions us-east/us-west/eu-central/ap-south/ap-southeast;
date-versioned API `Meridian-Version: 2025-08-01`. Every doc H2 ends with a stable
`[citation-id]` (prefix per doc, mapped in `docs/README.md`). Keep these stable if editing docs.

## 10. Next step

Week 2 proper: a **LangGraph** graph (router → answer/action/escalate), a **tool registry**,
and the **first real n8n tool** (`create_ticket` / `send_reply`) — the "n8n hands" that make
this more than a chatbot. Then cost/latency logging.
