"""Ingest docs/*.md -> chunk -> embed -> upsert into the chunks table.

Idempotent: chunks are keyed by content_hash, so re-running only re-embeds
changed content (ON CONFLICT updates the embedding).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

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


def ingest(reset: bool = False, docs_dir: Path | None = None) -> int:
    source_dir = (docs_dir or DOCS_DIR).resolve()
    md_files = sorted(source_dir.glob("*.md"))
    if not md_files:
        print(f"No markdown files found in {source_dir}", file=sys.stderr)
        return 0

    # Build every embedding before changing the live table. Hosted providers can
    # rate-limit or lose connectivity; staging first keeps the current knowledge
    # base intact if any model request fails midway through ingestion.
    prepared: list[tuple] = []
    total = 0
    for path in md_files:
        text = path.read_text(encoding="utf-8")
        chunks = chunk_markdown(path.name, text)
        for ch in chunks:
            vec = db.to_vector_literal(embed_document(ch.content))
            prepared.append(
                (
                    ch.doc,
                    ch.citation_id,
                    ch.heading,
                    ch.content,
                    ch.token_estimate,
                    ch.chunk_index,
                    vec,
                    ch.content_hash,
                )
            )
        total += len(chunks)
        cited = sum(1 for c in chunks if c.citation_id)
        print(f"  {path.name:28s} {len(chunks):3d} chunks ({cited} with citation ids)")

    conn = db.connect()
    db.init_db(conn)
    with conn.transaction():
        if reset:
            db.reset(conn)
            print("Truncated chunks table.")
        for row in prepared:
            conn.execute(UPSERT, row)

    (count,) = conn.execute("SELECT count(*) FROM chunks;").fetchone()
    conn.close()
    print(f"\nIngested {total} chunks this run. Table now holds {count} rows.")
    return total


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest Markdown docs into pgvector.")
    ap.add_argument("--reset", action="store_true", help="truncate the table first")
    ap.add_argument(
        "--docs-dir",
        type=Path,
        default=DOCS_DIR,
        help="directory containing Markdown source files (default: docs/)",
    )
    args = ap.parse_args()
    ingest(reset=args.reset, docs_dir=args.docs_dir)


if __name__ == "__main__":
    main()
