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
