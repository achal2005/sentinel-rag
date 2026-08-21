"""Postgres + pgvector access. Vectors are passed as pgvector literals ('[..]')
and cast with ::vector, so no extra adapter package is needed."""
from __future__ import annotations

from typing import Sequence

import psycopg

from .config import DATABASE_URL, EMBED_DIM


def connect() -> psycopg.Connection:
    return psycopg.connect(DATABASE_URL, autocommit=True)


def to_vector_literal(vec: Sequence[float]) -> str:
    """pgvector accepts a text literal like '[0.1,0.2,...]'."""
    return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"


SCHEMA = f"""
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunks (
    id             BIGSERIAL PRIMARY KEY,
    doc            TEXT NOT NULL,
    citation_id    TEXT,                 -- e.g. 'key-06'; NULL for intro chunks
    heading        TEXT,
    content        TEXT NOT NULL,
    token_estimate INT,
    chunk_index    INT NOT NULL DEFAULT 0,
    embedding      vector({EMBED_DIM}),
    content_hash   TEXT UNIQUE NOT NULL,
    tsv            tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS chunks_tsv_idx  ON chunks USING GIN (tsv);
CREATE INDEX IF NOT EXISTS chunks_hnsw_idx ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS chunks_cit_idx  ON chunks (citation_id);

-- Support tickets written by the create_ticket tool (via the n8n webhook).
-- Keep in sync with n8n/tickets.sql.
CREATE TABLE IF NOT EXISTS tickets (
    id              BIGSERIAL PRIMARY KEY,
    subject         TEXT NOT NULL,
    body            TEXT NOT NULL DEFAULT '',
    requester_email TEXT,
    route           TEXT,                 -- answer | action | escalate | spam (from the router)
    urgency         TEXT,                 -- low | normal | high (optional)
    reason          TEXT,                 -- short machine tag for tracing
    status          TEXT NOT NULL DEFAULT 'open',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS tickets_status_idx  ON tickets (status);
CREATE INDEX IF NOT EXISTS tickets_created_idx ON tickets (created_at DESC);

-- One row per graph run: cost + trace log (written by app/trace.py).
CREATE TABLE IF NOT EXISTS runs (
    id                BIGSERIAL PRIMARY KEY,
    request           TEXT NOT NULL,
    route             TEXT,                 -- answer | action | escalate | spam
    reason            TEXT,                 -- final machine tag (e.g. answered)
    escalated         BOOLEAN NOT NULL DEFAULT FALSE,
    model             TEXT,                 -- chat model that served the run
    llm_calls         INT   NOT NULL DEFAULT 0,   -- generative calls (router + answerer)
    prompt_tokens     INT   NOT NULL DEFAULT 0,
    completion_tokens INT   NOT NULL DEFAULT 0,
    total_tokens      INT   NOT NULL DEFAULT 0,
    cost_usd          NUMERIC(12, 6) NOT NULL DEFAULT 0,  -- 0 for local Ollama
    latency_ms        INT,
    citations         TEXT[],
    action_status     TEXT,                 -- created | pending_approval | invalid
    ticket_id         TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS runs_created_idx ON runs (created_at DESC);
CREATE INDEX IF NOT EXISTS runs_route_idx   ON runs (route);

-- High-risk tool calls parked here for a human to approve before they execute
-- (written by app/tools.py's enqueue()). Low/medium-risk tools skip this and
-- run directly via their n8n webhook.
CREATE TABLE IF NOT EXISTS approval_queue (
    id          BIGSERIAL PRIMARY KEY,
    tool        TEXT NOT NULL,      -- e.g. cancel_invoice
    risk_level  TEXT NOT NULL,      -- low | medium | high (high is what lands here)
    params      JSONB NOT NULL,     -- validated tool params to run on approval
    request     TEXT,               -- the originating support request
    route       TEXT,
    urgency     TEXT,
    reason      TEXT,               -- machine tag (router intent)
    run_id      BIGINT,             -- graph run (runs.id) that queued this action
    status      TEXT NOT NULL DEFAULT 'pending',  -- pending | approved | rejected | executed
    decided_by  TEXT,               -- who approved/rejected (Week 3 UI)
    decided_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Lightweight migration for DBs created before run_id existed (idempotent).
ALTER TABLE approval_queue ADD COLUMN IF NOT EXISTS run_id BIGINT;

CREATE INDEX IF NOT EXISTS approval_status_idx  ON approval_queue (status);
CREATE INDEX IF NOT EXISTS approval_created_idx ON approval_queue (created_at DESC);
CREATE INDEX IF NOT EXISTS approval_run_idx     ON approval_queue (run_id);

-- Written by the n8n 'Webhook -> cancel_invoice' workflow when a high-risk
-- invoice cancellation is APPROVED (the tool the approval queue guards).
CREATE TABLE IF NOT EXISTS invoice_cancellations (
    id              BIGSERIAL PRIMARY KEY,
    invoice_id      TEXT NOT NULL,
    requester_email TEXT,
    reason          TEXT,
    status          TEXT NOT NULL DEFAULT 'cancelled',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS invcancel_created_idx ON invoice_cancellations (created_at DESC);

-- Idempotency ledger for tool executions (written by app/tools.py's invoke()).
-- A duplicate request (same tool + normalized input) reuses the stored result
-- instead of firing a second side effect -- so a retried/duplicated action does
-- not create a second ticket. Keyed by a content hash.
CREATE TABLE IF NOT EXISTS tool_executions (
    id               BIGSERIAL PRIMARY KEY,
    idempotency_key  TEXT UNIQUE NOT NULL,
    tool             TEXT NOT NULL,
    result           JSONB,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS tool_exec_created_idx ON tool_executions (created_at DESC);

-- One row per STEP of a graph run (written by app/audit.py): the router
-- decision, the chunk ids retrieved, the tool + params selected, and the final
-- outcome. Also records out-of-run human decisions (approve/reject) so the
-- approval queue has a full paper trail. Linked to runs.id / approval_queue.id.
CREATE TABLE IF NOT EXISTS audit_log (
    id           BIGSERIAL PRIMARY KEY,
    run_id       BIGINT,             -- graph run this step belongs to (NULL for approvals)
    approval_id  BIGINT,             -- approval_queue row (NULL for run steps)
    seq          INT NOT NULL DEFAULT 0,  -- step order within a run (0,1,2,...)
    step         TEXT NOT NULL,      -- router | retrieve | tool | outcome | approval
    detail       JSONB NOT NULL DEFAULT '{{}}',  -- step-specific payload
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS audit_run_idx      ON audit_log (run_id);
CREATE INDEX IF NOT EXISTS audit_approval_idx ON audit_log (approval_id);
CREATE INDEX IF NOT EXISTS audit_created_idx  ON audit_log (created_at DESC);
"""


def init_db(conn: psycopg.Connection | None = None) -> None:
    own = conn is None
    conn = conn or connect()
    try:
        conn.execute(SCHEMA)
    finally:
        if own:
            conn.close()


def reset(conn: psycopg.Connection) -> None:
    conn.execute("TRUNCATE chunks RESTART IDENTITY;")
