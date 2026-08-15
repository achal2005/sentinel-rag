"""Heading-aware Markdown chunking that preserves Meridian citation IDs.

Every H2 section in docs/ ends its heading with a stable id, e.g.

    ## Regenerating (rotating) a secret key `[key-06]`

We chunk one section per H2 (the pre-H2 intro becomes its own chunk) and carry
the `citation_id` on the chunk so retrieval can cite the exact section. Oversized
sections are split on blank lines while keeping the same heading + citation_id.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

H2_RE = re.compile(r"^##\s+(.*)$")
H1_RE = re.compile(r"^#\s+(.*)$")
CIT_RE = re.compile(r"`\[([a-z]+-\d+)\]`\s*$")

# Split a section into sub-chunks if it exceeds this many characters.
MAX_CHARS = 1800


@dataclass
class Chunk:
    doc: str
    citation_id: str | None
    heading: str
    content: str
    chunk_index: int

    @property
    def token_estimate(self) -> int:
        return max(1, len(self.content) // 4)

    @property
    def content_hash(self) -> str:
        h = hashlib.sha1()
        h.update(f"{self.doc}|{self.citation_id}|{self.chunk_index}|".encode())
        h.update(self.content.encode("utf-8"))
        return h.hexdigest()


def _clean_heading(raw: str) -> tuple[str, str | None]:
    """Return (display_heading, citation_id) from a raw H2 heading line."""
    m = CIT_RE.search(raw)
    citation_id = m.group(1) if m else None
    heading = CIT_RE.sub("", raw).strip().rstrip("`").strip()
    return heading, citation_id


def _split_body(body: str) -> list[str]:
    body = body.strip()
    if len(body) <= MAX_CHARS:
        return [body] if body else []
    parts: list[str] = []
    buf: list[str] = []
    size = 0
    for para in body.split("\n\n"):
        if size + len(para) > MAX_CHARS and buf:
            parts.append("\n\n".join(buf))
            buf, size = [], 0
        buf.append(para)
        size += len(para) + 2
    if buf:
        parts.append("\n\n".join(buf))
    return parts


def chunk_markdown(doc: str, text: str) -> list[Chunk]:
    lines = text.splitlines()

    # H1 title (used to label the intro section)
    title = doc
    for ln in lines:
        m = H1_RE.match(ln)
        if m:
            title = m.group(1).strip()
            break

    # Partition into (heading_line, body_lines) sections at each H2.
    sections: list[tuple[str | None, list[str]]] = []
    current_heading: str | None = None
    current_body: list[str] = []
    for ln in lines:
        if H2_RE.match(ln):
            sections.append((current_heading, current_body))
            current_heading = ln
            current_body = []
        else:
            current_body.append(ln)
    sections.append((current_heading, current_body))

    chunks: list[Chunk] = []
    for heading_line, body_lines in sections:
        body = "\n".join(body_lines).strip()
        if heading_line is None:
            # intro / pre-first-H2 content
            heading, citation_id = f"{title} — overview", None
            display_prefix = ""
        else:
            heading, citation_id = _clean_heading(heading_line[3:])
            display_prefix = heading_line.strip() + "\n\n"

        if not body and heading_line is not None:
            # keep heading-only sections out (e.g. "## Related documents" stubs
            # with only links still carry useful text, so only skip if truly empty)
            pass

        pieces = _split_body(body)
        if not pieces:
            continue
        for i, piece in enumerate(pieces):
            content = f"{display_prefix}{piece}".strip()
            chunks.append(
                Chunk(
                    doc=doc,
                    citation_id=citation_id,
                    heading=heading,
                    content=content,
                    chunk_index=i,
                )
            )
    return chunks
