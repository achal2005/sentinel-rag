"""Ingest docs/*.md -> chunk -> embed -> upsert into the chunks table.

Idempotent: chunks are keyed by content_hash, so re-running only re-embeds
changed content (ON CONFLICT updates the embedding).
"""
from __future__ import annotations

import argparse
import sys

from . import db
from .chunking import chunk_markdown
from .config import DOCS_DIR
from .embed import embed_document

UPSERT = """
INSERT INTO chunks
    (doc, citation_id, heading, content, token_estimate, chunk_index, embedding, content_hash)
VALUES
    (%s, %s, %s, %s, %s, %s, %s::vector, %s)
ON CONFLICT (content_hash) DO UPDATE
    SET embedding = EXCLUDED.embedding,
        heading   = EXCLUDED.heading,
        token_estimate = EXCLUDED.token_estimate;
"""


def ingest(reset: bool = False) -> int:
    md_files = sorted(DOCS_DIR.glob("*.md"))
    if not md_files:
        print(f"No markdown files found in {DOCS_DIR}", file=sys.stderr)
        return 0

    conn = db.connect()
    db.init_db(conn)
    if reset:
        db.reset(conn)
        print("Truncated chunks table.")

    total = 0
    for path in md_files:
        text = path.read_text(encoding="utf-8")
        chunks = chunk_markdown(path.name, text)
        for ch in chunks:
            vec = db.to_vector_literal(embed_document(ch.content))
            conn.execute(
                UPSERT,
                (
                    ch.doc,
                    ch.citation_id,
                    ch.heading,
                    ch.content,
                    ch.token_estimate,
                    ch.chunk_index,
                    vec,
                    ch.content_hash,
                ),
            )
        total += len(chunks)
        cited = sum(1 for c in chunks if c.citation_id)
        print(f"  {path.name:28s} {len(chunks):3d} chunks ({cited} with citation ids)")

    (count,) = conn.execute("SELECT count(*) FROM chunks;").fetchone()
    conn.close()
    print(f"\nIngested {total} chunks this run. Table now holds {count} rows.")
    return total


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest Meridian docs into pgvector.")
    ap.add_argument("--reset", action="store_true", help="truncate the table first")
    args = ap.parse_args()
    ingest(reset=args.reset)


if __name__ == "__main__":
    main()
