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
