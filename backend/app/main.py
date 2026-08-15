"""FastAPI HTTP entry point for Sentinel RAG API."""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .answer import answer

app = FastAPI(
    title="Sentinel RAG API",
    description="Agentic support-operations API with grounded citations and escalation.",
    version="0.1.0",
)


# 1) Request model: what the caller sends
class AskRequest(BaseModel):
    query: str = Field(..., description="The user question or support request")
    channel: str = Field("web_form", description="Channel origin (web_form, email, whatsapp)")


# 2) Source model: clean metadata from retrieved chunks
class Source(BaseModel):
    citation_id: str | None = None
    doc: str
    heading: str
    similarity: float


# 3) Response model: what the API returns to the caller
class AskResponse(BaseModel):
    query: str
    text: str
    escalated: bool
    citations: list[str]
    reason: str
    sources: list[Source]


@app.get("/health")
def health() -> dict[str, str]:
    """Simple health check endpoint."""
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def handle_ask(req: AskRequest) -> AskResponse:
    """Run RAG retrieval and cited answer generation."""
    ans = answer(req.query)

    # Convert Hit dataclasses into clean Source Pydantic models
    sources = [
        Source(
            citation_id=h.citation_id,
            doc=h.doc,
            heading=h.heading,
            similarity=round(h.similarity, 3),
        )
        for h in ans.hits
    ]

    return AskResponse(
        query=ans.query,
        text=ans.text,
        escalated=ans.escalated,
        citations=ans.citations,
        reason=ans.reason,
        sources=sources,
    )
