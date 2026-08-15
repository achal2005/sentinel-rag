<h1 align="center">🛰️ Sentinel</h1>

<p align="center">
  <b>An AI support agent that cites its sources — or honestly says it doesn't know.</b><br/>
  <i>"LLM brain, n8n hands."</i> Most demos build a chatbot that <b>talks</b>. Sentinel is built to <b>act</b>.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Postgres-pgvector-4169E1?logo=postgresql&logoColor=white" alt="pgvector"/>
  <img src="https://img.shields.io/badge/Ollama-local%20LLMs-000000?logo=ollama&logoColor=white" alt="Ollama"/>
  <img src="https://img.shields.io/badge/Docker-compose-2496ED?logo=docker&logoColor=white" alt="Docker"/>
  <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT"/>
  <img src="https://img.shields.io/badge/cost-%E2%82%B90-brightgreen" alt="Zero cost"/>
</p>

---

## The idea in one breath

Large language models are confident liars when you ask them about docs they've never seen. Sentinel fixes that the honest way: it **retrieves the relevant passages from a knowledge base, answers only from them, and cites the exact section it used** — and when the answer genuinely isn't in the docs, it **escalates to a human instead of making something up**.

That single behaviour — *grounded-with-citations, or escalate* — is the whole point, and it's what separates this from the hundredth "I wrapped an LLM" project.

```
"How do I rotate my API key?"   ->  grounded answer, cites [key-06]        ✅
"What will pricing be in 2027?" ->  "not in the docs" -> escalates          ✅  (no hallucination)
```

---

## Why it's different

- 🎯 **Citations are mandatory.** Every factual sentence points at a real doc section. Fabricated citations are stripped out.
- 🚪 **It knows when to shut up.** A confidence gate + a strict prompt mean low-evidence questions escalate instead of getting guessed at.
- 🔀 **Hybrid retrieval, done right.** Vector similarity *and* keyword search, merged with Reciprocal Rank Fusion — because meaning-search and exact-term-search each have a blind spot.
- 📏 **Measured, not vibe-checked.** A hand-labelled 35-case golden set and per-capability metrics, including a *two-sided* escalation guardrail (it also punishes over-escalation).
- 🧪 **A real fine-tuning experiment — reported honestly** (including a negative result). See below.
- 💸 **₹0 to run.** Everything is local: Dockerized Postgres + pgvector, and Ollama for embeddings and generation.

---

## How it works

```
                          WRITE PATH (once)
  docs/*.md ─► heading-aware chunker ─► embed (nomic) ─► Postgres + pgvector
              (keeps [citation-id]s)     search_document:     (chunks table)

                          READ PATH (per question)
  question ─► embed (search_query:) ─┬─► vector search (cosine, top-20) ─┐
                                     └─► full-text search (top-20) ──────┘
                                                   │
                                        Reciprocal Rank Fusion
                                                   │
                                             top-5 chunks
                                                   │
                                    cosine confidence gate (≥ 0.55?)
                                          │                    │
                                        No│                    │Yes
                                          ▼                    ▼
                                   escalate to human    LLM answers using ONLY
                                                        the sources, cites [key-06]
```

Under the hood: **heading-aware chunking** so each retrieved unit maps to exactly one citable section; **nomic-embed-text** with its required `search_document:` / `search_query:` task prefixes; **pgvector** (HNSW) for vectors and a generated **tsvector** (GIN) for keyword search; and a **citations-or-escalate** answerer on top of `llama3.2:3b`.

---

## Does it actually work?

Everything below is measured against a held-out, hand-labelled golden set of **35 cases** (`evals/golden.json`). No cherry-picking, no training on the test set.

| Capability | Result |
|---|---|
| Grounded answers cite the correct section | ✅ e.g. `ans-01` → `[key-06]` |
| Unanswerable questions escalate (no hallucination) | ✅ e.g. `uns-01` |
| **Router accuracy** (answer / action / escalate / spam) | **88.6%** (31/35) |
| Urgency accuracy | 82.9% |
| Escalation recall | 81.8% |
| **Over-escalation on answerable cases** | **0%** |

*Ingest produces 175 chunks from 16 documents.*

---

## The fine-tuning experiment (and an honest result)

I also fine-tuned a **1B model with LoRA** (on a free Kaggle T4) to try to beat the prompted router, with a clean, leakage-free setup (synthetic training data, held-out golden set, identical eval).

> **Result: the LoRA router scored 85.7% — it did *not* beat the 88.6% prompted baseline (−2.9 pts).**

That's a *feature of the writeup*, not a failure. With a strong baseline, a tiny model, and ~340 synthetic examples, prompting winning is the expected outcome — and reporting a negative result honestly is far more credible than a suspiciously perfect one. The value is the reproducible methodology and the demonstrated PEFT/LoRA skill. Details in [`finetune/README.md`](./finetune/README.md).

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Vector store | **Postgres + pgvector** | One service, transactional consistency, trivial backups. |
| Embeddings | **Ollama `nomic-embed-text`** (768-d) | Local, free, no rate limits. |
| Generation | **Ollama `llama3.2:3b`** | Local, free, laptop-friendly. |
| API | **FastAPI + Uvicorn** | Typed, auto-docs, production-shaped. |
| DB driver | **psycopg 3** | Bundled libpq, no system Postgres needed. |
| Fine-tuning | **PEFT LoRA** on Kaggle T4 | Genuinely free GPU. |
| Orchestration | **Docker Compose** | `docker compose up` and you're running. |

---

## Quickstart

**Prerequisites:** Docker Desktop, [Ollama](https://ollama.com), and Python 3.11+.

```bash
# 1) pull the local models
ollama pull nomic-embed-text
ollama pull llama3.2:3b

# 2) start Postgres + pgvector
cp .env.example .env
docker compose up -d

# 3) set up the backend
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt      # (.venv/bin on macOS/Linux)

# 4) build the index and ask a question
.venv/Scripts/python -m app.cli init
.venv/Scripts/python -m app.cli ingest --reset      # -> 175 chunks
.venv/Scripts/python -m app.cli ask "how do I rotate an API key?"

# 5) or run it as an API
.venv/Scripts/uvicorn app.main:app --reload --port 8000
#   then open http://localhost:8000/docs  and POST to /ask
```

```jsonc
// POST /ask
{ "query": "how do I rotate an API key?" }
// -> { "text": "... under Settings → API Keys [key-06] ...",
//      "escalated": false, "citations": ["key-06"], "sources": [ ... ] }
```

---

## Project structure

```
sentinel-rag/
├── backend/app/         # the RAG core
│   ├── chunking.py      #   heading-aware Markdown chunking (keeps citation IDs)
│   ├── embed.py         #   Ollama embeddings + chat (stdlib HTTP)
│   ├── ingest.py        #   docs -> chunk -> embed -> pgvector (idempotent)
│   ├── retrieve.py      #   hybrid vector + full-text search, RRF fusion
│   ├── answer.py        #   cited answers, citations-or-escalate
│   ├── router.py        #   triage: answer / action / escalate / spam
│   ├── eval_routing.py  #   scores the router vs. the golden set
│   ├── cli.py           #   init | ingest | search | route | ask
│   └── main.py          #   FastAPI: POST /ask, GET /health
├── docs/                # Meridian — a coherent fictional SaaS KB (the corpus)
├── evals/               # golden.json (35 labelled cases) + metrics
├── finetune/            # the LoRA router experiment (dataset gen + Kaggle notebook)
├── docker-compose.yml   # Postgres + pgvector
└── context.md           # project orientation (status, decisions, gotchas)
```

---

## Roadmap

- [x] **Week 1 — RAG core:** hybrid retrieval, cited answers, eval harness, HTTP endpoint.
- [x] Router + baseline (88.6%) and a LoRA fine-tuning experiment.
- [ ] **Week 2 — Action:** a LangGraph loop + a tool registry, with the first real **n8n** tool (`create_ticket` / `send_reply`) — the "hands".
- [ ] **Week 3 — Safety & observability:** human-approval queue, audit log, Langfuse tracing.
- [ ] **Week 4 — Polish:** evals in CI, cost dashboard, a live demo.

---

## A note on the knowledge base

The corpus is **Meridian**, a fictional cloud platform invented so the docs are fully consistent and the eval set is deterministic. Every section heading carries a stable `[citation-id]` (e.g. `[key-06]`), which is exactly what retrieval cites and what the golden set checks against. Point the ingest pipeline at any real docs and the same pipeline works.

---

## License

[MIT](./LICENSE) © 2026 Achal Verma

<p align="center"><sub>Built as a portfolio project — every number in this README is reproducible from the code.</sub></p>
