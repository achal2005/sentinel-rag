"""Hybrid retrieval: pgvector cosine + Postgres full-text search, fused with
Reciprocal Rank Fusion (RRF)."""
from __future__ import annotations

from dataclasses import dataclass

from . import db
from .config import RETRIEVAL_POOL, RETRIEVAL_TOPK, RRF_K
from .embed import embed_query


@dataclass
class Hit:
    id: int
    doc: str
    citation_id: str | None
    heading: str
    content: str
    score: float          # fused RRF score (ranking)
    similarity: float     # cosine similarity to the query (confidence gate)
    vector_rank: int | None
    fts_rank: int | None


VECTOR_SQL = """
SELECT id FROM chunks
ORDER BY embedding <=> %s::vector
LIMIT %s;
"""

FTS_SQL = """
SELECT id
FROM chunks
WHERE tsv @@ plainto_tsquery('english', %s)
ORDER BY ts_rank(tsv, plainto_tsquery('english', %s)) DESC
LIMIT %s;
"""


def _ranked_ids(rows) -> dict[int, int]:
    """Map row id -> 1-based rank."""
    return {row[0]: i + 1 for i, row in enumerate(rows)}


def search(
    query: str,
    topk: int = RETRIEVAL_TOPK,
    pool: int = RETRIEVAL_POOL,
    conn=None,
) -> list[Hit]:
    own = conn is None
    conn = conn or db.connect()
    try:
        qvec = db.to_vector_literal(embed_query(query))

        vec_rows = conn.execute(VECTOR_SQL, (qvec, pool)).fetchall()
        fts_rows = conn.execute(FTS_SQL, (query, query, pool)).fetchall()

        vrank = _ranked_ids(vec_rows)
        frank = _ranked_ids(fts_rows)

        # Reciprocal Rank Fusion
        fused: dict[int, float] = {}
        for cid, r in vrank.items():
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (RRF_K + r)
        for cid, r in frank.items():
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (RRF_K + r)

        top_ids = sorted(fused, key=fused.get, reverse=True)[:topk]
        if not top_ids:
            return []

        rows = conn.execute(
            "SELECT id, doc, citation_id, heading, content, "
            "1 - (embedding <=> %s::vector) AS similarity "
            "FROM chunks WHERE id = ANY(%s);",
            (qvec, top_ids),
        ).fetchall()
        by_id = {r[0]: r for r in rows}

        hits: list[Hit] = []
        for cid in top_ids:
            r = by_id[cid]
            hits.append(
                Hit(
                    id=r[0],
                    doc=r[1],
                    citation_id=r[2],
                    heading=r[3],
                    content=r[4],
                    score=fused[cid],
                    similarity=float(r[5]),
                    vector_rank=vrank.get(cid),
                    fts_rank=frank.get(cid),
                )
            )
        return hits
    finally:
        if own:
            conn.close()
