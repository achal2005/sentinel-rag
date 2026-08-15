"""Generate the Sentinel Week 1 Build & Study Guide PDF.

A comprehensive, diagram-rich educational walkthrough of everything built in Week 1
(the cited RAG core), written for a student learning the project and for interview prep.

Run:  python tools/build_week1_guide.py
Out:  Sentinel_Week1_Guide.pdf   (repo root)
"""
from __future__ import annotations

import math
from pathlib import Path

from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).resolve().parents[1] / "Sentinel_Week1_Guide.pdf"

# ---------------------------------------------------------------- palette
INK = HexColor("#0f172a")
MUTED = HexColor("#475569")
ACCENT = HexColor("#2563eb")
LINE = HexColor("#94a3b8")
C_BLUE = HexColor("#dbeafe")
C_GREEN = HexColor("#dcfce7")
C_AMBER = HexColor("#fef9c3")
C_PURPLE = HexColor("#ede9fe")
C_SLATE = HexColor("#e2e8f0")
C_RED = HexColor("#fee2e2")
C_TEAL = HexColor("#ccfbf1")
CODE_BG = HexColor("#f1f5f9")
STROKE = HexColor("#334155")

# ---------------------------------------------------------------- styles
ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontSize=19, leading=23,
                    textColor=INK, spaceBefore=6, spaceAfter=10)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=14, leading=18,
                    textColor=ACCENT, spaceBefore=14, spaceAfter=6)
H3 = ParagraphStyle("H3", parent=ss["Heading3"], fontSize=11.5, leading=15,
                    textColor=INK, spaceBefore=10, spaceAfter=4)
BODY = ParagraphStyle("Body", parent=ss["BodyText"], fontSize=10, leading=15,
                      textColor=INK, spaceAfter=7, alignment=TA_LEFT)
SMALL = ParagraphStyle("Small", parent=BODY, fontSize=8.5, leading=12, textColor=MUTED)
CAPTION = ParagraphStyle("Caption", parent=SMALL, alignment=TA_CENTER, spaceBefore=3,
                         spaceAfter=12)
CODE = ParagraphStyle("Code", parent=ss["Code"], fontName="Courier", fontSize=7.6,
                      leading=9.6, textColor=INK, backColor=CODE_BG, borderPadding=6,
                      leftIndent=2, spaceBefore=4, spaceAfter=10)
QLABEL = ParagraphStyle("QLabel", parent=BODY, fontName="Helvetica-Bold", textColor=ACCENT,
                        spaceAfter=2)
COVER_T = ParagraphStyle("CoverT", parent=ss["Title"], fontSize=30, leading=34,
                         textColor=INK, alignment=TA_CENTER)
COVER_S = ParagraphStyle("CoverS", parent=ss["Title"], fontSize=14, leading=20,
                         textColor=MUTED, alignment=TA_CENTER, fontName="Helvetica")

story: list = []


# ---------------------------------------------------------------- helpers
def p(text, style=BODY):
    story.append(Paragraph(text, style))


def h1(text):
    story.append(Paragraph(text, H1))


def h2(text):
    story.append(Paragraph(text, H2))


def h3(text):
    story.append(Paragraph(text, H3))


def code(text):
    story.append(Preformatted(text.strip("\n"), CODE))


def gap(h=6):
    story.append(Spacer(1, h))


def caption(text):
    story.append(Paragraph(text, CAPTION))


def bullets(items, style=BODY):
    flow = [ListItem(Paragraph(t, style), leftIndent=10) for t in items]
    story.append(ListFlowable(flow, bulletType="bullet", start="•", leftIndent=14))
    gap(4)


def table(data, col_widths, header=True, font=8.5):
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    cmds = [
        ("FONT", (0, 0), (-1, -1), "Helvetica", font),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]
    if header:
        cmds += [
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", font),
        ]
    t.setStyle(TableStyle(cmds))
    story.append(t)
    gap(10)


# ---- diagram primitives -------------------------------------------------
def rbox(d, x, y, w, h, lines, fill, fs=8.5, tc=INK, stroke=STROKE):
    d.add(Rect(x, y, w, h, rx=5, ry=5, fillColor=fill, strokeColor=stroke, strokeWidth=1))
    if isinstance(lines, str):
        lines = [lines]
    lh = fs + 2.5
    start = y + h / 2 + (len(lines) - 1) * lh / 2 - fs / 2 + 1
    for i, ln in enumerate(lines):
        bold = ln.startswith("*")
        d.add(String(x + w / 2, start - i * lh, ln.lstrip("*"), textAnchor="middle",
                     fontSize=fs, fillColor=tc,
                     fontName="Helvetica-Bold" if bold else "Helvetica"))


def diamond(d, cx, cy, w, h, lines, fill, fs=8):
    d.add(Polygon([cx, cy + h / 2, cx + w / 2, cy, cx, cy - h / 2, cx - w / 2, cy],
                  fillColor=fill, strokeColor=STROKE, strokeWidth=1))
    if isinstance(lines, str):
        lines = [lines]
    lh = fs + 2
    start = cy + (len(lines) - 1) * lh / 2 - fs / 2 + 1
    for i, ln in enumerate(lines):
        d.add(String(cx, start - i * lh, ln, textAnchor="middle", fontSize=fs, fillColor=INK))


def arrow(d, x1, y1, x2, y2, color=LINE, label=None):
    d.add(Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=1.2))
    ang = math.atan2(y2 - y1, x2 - x1)
    L, w = 7, 3.4
    d.add(Polygon([
        x2, y2,
        x2 - L * math.cos(ang) + w * math.sin(ang), y2 - L * math.sin(ang) - w * math.cos(ang),
        x2 - L * math.cos(ang) - w * math.sin(ang), y2 - L * math.sin(ang) + w * math.cos(ang),
    ], fillColor=color, strokeColor=color))
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        d.add(String(mx + 4, my + 3, label, fontSize=7, fillColor=MUTED))


# ---------------------------------------------------------------- diagrams
def diagram_architecture():
    d = Drawing(500, 150)
    layers = [
        ("Channels", ["Web form", "Email", "WhatsApp"], C_SLATE),
        ("Ingest", ["FastAPI", "endpoints"], C_BLUE),
        ("Brain", ["Router", "RAG answer", "Action"], C_GREEN),
        ("Hands", ["n8n tool", "webhooks"], C_AMBER),
        ("Safety", ["Approval", "gate"], C_RED),
        ("Glass", ["Evals", "Tracing", "Cost"], C_PURPLE),
    ]
    x, w, h, y = 6, 72, 84, 40
    for i, (title, lines, fill) in enumerate(layers):
        rbox(d, x, y, w, h, ["*" + title] + lines, fill, fs=7.6)
        if i < len(layers) - 1:
            arrow(d, x + w, y + h / 2, x + w + 8, y + h / 2)
        x += w + 8
    d.add(String(250, 18, "Week 1 built: the Ingest endpoint + the RAG-answer Brain (shaded).",
                 textAnchor="middle", fontSize=8, fillColor=MUTED))
    return d


def diagram_ingest():
    d = Drawing(500, 120)
    steps = [
        (["*docs/*.md", "15 Markdown", "+ 3 PDFs"], C_SLATE),
        (["*Chunker", "heading-aware", "keeps [cit-id]"], C_BLUE),
        (["*Embedder", "Ollama nomic", "search_document:"], C_GREEN),
        (["*pgvector", "chunks table", "vector+tsvector"], C_PURPLE),
    ]
    x, w, h, y = 10, 108, 60, 45
    for i, (lines, fill) in enumerate(steps):
        rbox(d, x, y, w, h, lines, fill, fs=8)
        if i < len(steps) - 1:
            arrow(d, x + w, y + h / 2, x + w + 12, y + h / 2)
        x += w + 12
    d.add(String(250, 22, "Idempotent: each chunk keyed by content hash (re-ingest only re-embeds changes).",
                 textAnchor="middle", fontSize=8, fillColor=MUTED))
    return d


def diagram_query():
    d = Drawing(500, 430)
    cx = 250
    rbox(d, cx - 70, 388, 140, 34, ["*User query"], C_SLATE, fs=9)
    arrow(d, cx, 388, cx, 372)
    rbox(d, cx - 90, 340, 180, 32, ["*Embed query  (search_query:)"], C_GREEN, fs=8.5)
    # split
    arrow(d, cx, 340, 130, 300)
    arrow(d, cx, 340, 370, 300)
    rbox(d, 55, 268, 150, 32, ["*Vector search", "cosine, top-20"], C_BLUE, fs=8)
    rbox(d, 295, 268, 150, 32, ["*Full-text search", "tsvector, top-20"], C_BLUE, fs=8)
    arrow(d, 130, 268, cx - 20, 232)
    arrow(d, 370, 268, cx + 20, 232)
    rbox(d, cx - 90, 200, 180, 32, ["*Reciprocal Rank Fusion", "merge both rankings"], C_AMBER, fs=8.5)
    arrow(d, cx, 200, cx, 184)
    rbox(d, cx - 70, 152, 140, 32, ["*Top-5 chunks"], C_TEAL, fs=8.5)
    arrow(d, cx, 152, cx, 132)
    diamond(d, cx, 104, 150, 56, ["top-hit cosine", "sim >= 0.55 ?"], C_AMBER, fs=8)
    # No branch
    arrow(d, cx - 75, 104, 95, 104, color=HexColor("#dc2626"), label="No")
    rbox(d, 10, 88, 85, 32, ["*Escalate", "to human"], C_RED, fs=8)
    # Yes branch
    arrow(d, cx, 76, cx, 60, color=HexColor("#16a34a"), label="Yes")
    rbox(d, cx - 105, 26, 210, 34, ["*LLM answers using ONLY the sources", "cites [key-06]  ·  or replies ESCALATE"], C_GREEN, fs=8)
    return d


def diagram_api():
    d = Drawing(500, 110)
    steps = [
        (["*Client", "POST /ask", "{query}"], C_SLATE),
        (["*Validate", "AskRequest", "(Pydantic)"], C_BLUE),
        (["*answer()", "RAG core"], C_GREEN),
        (["*AskResponse", "text+citations", "+sources"], C_PURPLE),
        (["*JSON out", "200 ok", "503 if dep down"], C_TEAL),
    ]
    x, w, h, y = 6, 90, 58, 42
    for i, (lines, fill) in enumerate(steps):
        rbox(d, x, y, w, h, lines, fill, fs=7.6)
        if i < len(steps) - 1:
            arrow(d, x + w, y + h / 2, x + w + 8, y + h / 2)
        x += w + 8
    d.add(String(250, 20, "The endpoint has no business logic — it validates, delegates to answer(), and shapes the reply.",
                 textAnchor="middle", fontSize=7.6, fillColor=MUTED))
    return d


# ================================================================ CONTENT
# ---- cover
story.append(Spacer(1, 120))
p("SENTINEL", COVER_S)
p("Week 1 — Building a Cited RAG Support Agent", COVER_T)
gap(10)
p("A complete build &amp; study guide — every component explained, with diagrams,<br/>"
  "for a student learning the project and for interview preparation.", COVER_S)
gap(40)
p("<b>Project:</b> Sentinel &nbsp;·&nbsp; <b>Layer:</b> RAG core (retrieval + cited answers)<br/>"
  "<b>Stack:</b> Python · FastAPI · Postgres/pgvector · Ollama (nomic-embed-text, llama3.2)<br/>"
  "<b>Author:</b> Achal Verma &nbsp;·&nbsp; github.com/achal2005", COVER_S)
story.append(PageBreak())

# ---- TOC
h1("Contents")
toc = [
    "1. Introduction — what we built and why",
    "2. RAG in plain English (the core idea)",
    "3. System architecture (the 6 layers)",
    "4. The knowledge base: a fictional company called Meridian",
    "5. Environment &amp; tech stack (and why each piece)",
    "6. The data model: how chunks live in Postgres",
    "7. Chunking: turning docs into citable pieces",
    "8. Embeddings: turning text into vectors",
    "9. Ingestion: the write path (end to end)",
    "10. Hybrid retrieval + Reciprocal Rank Fusion",
    "11. Cited answers &amp; the citations-or-escalate rule",
    "12. The command-line interface",
    "13. The FastAPI /ask endpoint (Week 1 milestone)",
    "14. Evaluation: the golden set and the metrics",
    "15. Bonus: the router + the LoRA fine-tuning experiment",
    "16. Design decisions &amp; hard-won gotchas",
    "17. Interview questions &amp; model answers",
    "18. Run it yourself",
    "19. Glossary",
]
bullets(toc)
story.append(PageBreak())

# ---- 1 intro
h1("1. Introduction — what we built and why")
p("<b>Sentinel</b> is a self-hosted AI support-operations agent. Its tagline is "
  "<i>\"LLM brain, n8n hands\"</i>: most student projects demo a chatbot that <i>talks</i>; "
  "Sentinel is built to <i>act</i> — to read a support request, answer it from a knowledge "
  "base <b>with citations</b>, and (in later weeks) actually resolve it by calling automation "
  "workflows. This guide covers <b>Week 1</b>, which builds the reliable core everything else "
  "stands on: <b>Retrieval-Augmented Generation (RAG) with mandatory citations, or an honest "
  "escalation when the answer isn't in the docs.</b>")
p("By the end of Week 1 the system can take a real question over HTTP and return a grounded, "
  "cited answer — or, if it can't ground the answer, escalate instead of making something up. "
  "That single behaviour (grounded-or-escalate) is what separates this from a naive "
  "\"ask-the-LLM\" demo, and it is the thing to be able to explain in an interview.")
h3("What Week 1 delivers")
bullets([
    "A <b>knowledge base</b> of realistic product docs with stable citation IDs.",
    "A <b>document pipeline</b>: chunk the docs, embed them, store them in Postgres/pgvector.",
    "<b>Hybrid retrieval</b>: vector similarity + keyword search, fused with Reciprocal Rank Fusion.",
    "<b>Cited answer generation</b> with a confidence gate: answer with sources, or escalate.",
    "An <b>evaluation harness</b> (a labelled 'golden set') so quality is measured, not guessed.",
    "A <b>FastAPI endpoint</b> so a request comes in over HTTP and a cited answer comes back.",
])

# ---- 2 RAG
h1("2. RAG in plain English (the core idea)")
p("A large language model (LLM) knows a lot, but it does <b>not</b> know <i>your</i> private or "
  "product-specific documents, and when asked about things it hasn't seen it will often "
  "<b>hallucinate</b> — produce a confident, wrong answer. There are two ways to fix that: "
  "<b>fine-tuning</b> (retrain the model on your data — expensive, slow, and it still can't cite "
  "sources) or <b>RAG</b> (Retrieval-Augmented Generation).")
p("<b>RAG</b> keeps the model as-is and, at question time, <b>retrieves</b> the most relevant "
  "passages from your documents and pastes them into the prompt as context. The model then "
  "answers <i>from that context</i> and points at which passage it used. Think of it as an "
  "open-book exam: the model isn't memorising the textbook, it's looking up the right page and "
  "quoting it.")
p("The RAG loop has two halves. The <b>write path</b> (done once, ahead of time): split docs into "
  "chunks, convert each chunk to a vector, and store them. The <b>read path</b> (per question): "
  "convert the question to a vector, find the closest chunks, and hand them to the LLM to answer "
  "with citations. Week 1 builds both halves.")
h3("Why citations-or-escalate matters")
p("A grounded answer is only trustworthy if the model actually used the retrieved sources. So "
  "Sentinel enforces two rules: (1) every factual sentence must cite a section ID that appears "
  "in the retrieved context, and (2) if retrieval confidence is too low, or the model can't "
  "ground its answer, the system <b>escalates to a human</b> instead of guessing. This is the "
  "reliability behaviour recruiters actually care about.")

# ---- 3 architecture
h1("3. System architecture (the 6 layers)")
p("The full Sentinel design is six layers. Week 1 implements the shaded parts: the ingest "
  "endpoint and the RAG-answer brain. The rest (tools, safety, observability) come in later weeks.")
story.append(diagram_architecture())
caption("Figure 1 — The six layers. A request flows left to right: it arrives on a channel, is "
        "ingested, understood by the brain, optionally acted on by 'hands', checked by safety, "
        "and observed through the 'glass'.")
bullets([
    "<b>Channels</b> — where requests originate (Week 1 uses a web-form-style JSON request).",
    "<b>Ingest</b> — a FastAPI endpoint that receives the request.",
    "<b>Brain</b> — routing + RAG answering (Week 1) and, later, an action agent.",
    "<b>Hands</b> — n8n workflows the agent calls to actually do things (later weeks).",
    "<b>Safety</b> — human approval for risky actions, confidence gates (later weeks).",
    "<b>Glass</b> — evaluation, tracing, and cost dashboards (the eval harness is in Week 1).",
])

# ---- 4 KB
h1("4. The knowledge base: a fictional company called Meridian")
p("RAG needs documents. Rather than scrape a real company (messy, and you can't control the "
  "test set), we invented one coherent fictional SaaS company: <b>Meridian</b>, a cloud "
  "application platform. It has 15 Markdown documents (authentication, API keys, billing, "
  "deployments, webhooks, rate limits, and so on) plus three PDF versions for mixed-format "
  "testing. Every fact is internally consistent (the same API base URL, the same plan names, the "
  "same key formats) so answers can be checked deterministically.")
h3("The citation ID convention (this is the clever part)")
p("Every section heading ends with a <b>stable citation ID</b> in square brackets, for example "
  "<font face='Courier'>## Regenerating a secret key `[key-06]`</font>. These IDs never change, "
  "so an automated system can cite an exact section. They are also what the evaluation set checks "
  "against: a correct answer to \"how do I rotate my key?\" must cite <font face='Courier'>[key-06]</font>. "
  "Each document has its own prefix (<font face='Courier'>auth-</font>, <font face='Courier'>key-</font>, "
  "<font face='Courier'>bill-</font>, ...), documented in <font face='Courier'>docs/README.md</font>.")

# ---- 5 stack
h1("5. Environment &amp; tech stack (and why each piece)")
table([
    ["Concern", "Choice", "Why this choice"],
    ["Vector store", "Postgres + pgvector (Docker)", "One less service; transactional; a strong interview line."],
    ["Embeddings", "Ollama nomic-embed-text (768-d)", "Local, free, no API limits."],
    ["Generation", "Ollama llama3.2:3b", "Local, free; small enough for a laptop."],
    ["DB driver", "psycopg 3 (binary)", "Bundles libpq; no system Postgres needed."],
    ["HTTP API", "FastAPI + uvicorn", "Typed, auto-generated docs, production-shaped."],
    ["LLM calls", "stdlib urllib -> Ollama", "No heavy SDK; Ollama speaks plain HTTP/JSON."],
], [1.2 * inch, 2.1 * inch, 3.0 * inch])
p("Two ideas worth internalising. First, <b>pgvector over a dedicated vector database</b>: "
  "storing vectors <i>inside</i> Postgres means one database to run and back up, and your chunks "
  "and their embeddings stay transactionally consistent. Second, <b>local models via Ollama</b>: "
  "everything runs on your machine at zero cost, which is perfect for a portfolio project and "
  "forces you to understand the pipeline rather than lean on a paid API.")

# ---- 6 data model
h1("6. The data model: how chunks live in Postgres")
p("Everything retrieval needs lives in one table, <font face='Courier'>chunks</font>. Each row is "
  "one citable piece of a document, with both its embedding (for vector search) and an "
  "auto-maintained text-search column (for keyword search).")
code(
"CREATE EXTENSION IF NOT EXISTS vector;\n\n"
"CREATE TABLE chunks (\n"
"    id             BIGSERIAL PRIMARY KEY,\n"
"    doc            TEXT NOT NULL,        -- source file, e.g. api-keys.md\n"
"    citation_id    TEXT,                 -- e.g. 'key-06' (NULL for intro chunks)\n"
"    heading        TEXT,\n"
"    content        TEXT NOT NULL,\n"
"    token_estimate INT,\n"
"    chunk_index    INT NOT NULL DEFAULT 0,\n"
"    embedding      vector(768),          -- the nomic-embed-text vector\n"
"    content_hash   TEXT UNIQUE NOT NULL, -- makes re-ingest idempotent\n"
"    tsv            tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,\n"
"    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()\n"
");\n\n"
"CREATE INDEX chunks_hnsw_idx ON chunks USING hnsw (embedding vector_cosine_ops);\n"
"CREATE INDEX chunks_tsv_idx  ON chunks USING GIN (tsv);"
)
bullets([
    "<b>embedding vector(768)</b> — pgvector's column type; 768 is nomic-embed-text's dimension.",
    "<b>tsv ... GENERATED ALWAYS</b> — Postgres builds the full-text index automatically from "
    "<font face='Courier'>content</font>; you never maintain it by hand.",
    "<b>content_hash UNIQUE</b> — re-running ingestion updates changed chunks instead of "
    "duplicating them (idempotency).",
    "<b>HNSW index</b> — makes nearest-neighbour vector search fast; <b>GIN index</b> — makes "
    "keyword search fast.",
])

# ---- 7 chunking
h1("7. Chunking: turning docs into citable pieces")
p("You cannot embed a whole 2,000-word document as one vector — it blurs many topics together "
  "and retrieval gets vague. So we split each doc into <b>chunks</b>. The key design choice: "
  "<b>chunk on headings</b>, one chunk per <font face='Courier'>##</font> section, and carry that "
  "section's citation ID onto the chunk. That way retrieval returns a unit that maps exactly to a "
  "citable section — retrieval and citation become the same thing.")
code(
"H2_RE  = re.compile(r'^##\\s+(.*)$')\n"
"CIT_RE = re.compile(r'`\\[([a-z]+-\\d+)\\]`\\s*$')   # the [key-06] tag at a heading's end\n\n"
"def chunk_markdown(doc, text):\n"
"    # 1) split the file into sections at every '## ' heading\n"
"    # 2) for each section: pull the citation_id from the heading via CIT_RE\n"
"    # 3) if a section is very long, split it on blank lines but keep the same id\n"
"    # 4) emit Chunk(doc, citation_id, heading, content, chunk_index)\n"
"    ..."
)
p("Two details that matter. The text before the first heading becomes its own \"overview\" chunk "
  "(citation_id = None). And each chunk's <font face='Courier'>content</font> keeps its heading "
  "line, so the embedding and the LLM both see the section title as context. A rough size target "
  "of ~500 tokens keeps chunks focused without cutting mid-thought.")

# ---- 8 embeddings
h1("8. Embeddings: turning text into vectors")
p("An <b>embedding</b> is a list of numbers (here, 768 of them) that captures the <i>meaning</i> "
  "of a piece of text. Texts with similar meaning get vectors that point in similar directions, "
  "so we can measure similarity with the <b>cosine</b> of the angle between two vectors (1.0 = "
  "identical direction, 0 = unrelated). We call a local model, <font face='Courier'>nomic-embed-text</font>, "
  "through Ollama's HTTP API using nothing but the Python standard library.")
code(
"def embed(text):\n"
"    data = _post('/api/embeddings', {'model': EMBED_MODEL, 'prompt': text})\n"
"    return data['embedding']              # a list of 768 floats\n\n"
"# nomic is trained for ASYMMETRIC retrieval and expects task prefixes:\n"
"def embed_document(text): return embed(f'search_document: {text}')\n"
"def embed_query(text):    return embed(f'search_query: {text}')"
)
p("<b>The single most important gotcha in Week 1 lives here.</b> nomic-embed-text was trained "
  "with task prefixes: documents must be embedded with <font face='Courier'>search_document:</font> "
  "and queries with <font face='Courier'>search_query:</font>. Forget the prefixes and retrieval "
  "quality collapses — in our own testing, top-hit similarity for a correct match jumped from "
  "noise to ~0.75 once we added them. Small detail, huge effect. This is a great thing to mention "
  "in an interview because it shows you actually read the model card.")

# ---- 9 ingestion
h1("9. Ingestion: the write path (end to end)")
p("Ingestion ties chunking and embedding together and writes to Postgres. It reads every "
  "<font face='Courier'>docs/*.md</font>, chunks it, embeds each chunk with the "
  "<font face='Courier'>search_document:</font> prefix, and upserts by content hash.")
story.append(diagram_ingest())
caption("Figure 2 — The ingestion (write) path. Runs once up front; re-running only re-embeds "
        "chunks whose content changed.")
code(
"UPSERT = '''\n"
"INSERT INTO chunks (doc, citation_id, heading, content, token_estimate,\n"
"                    chunk_index, embedding, content_hash)\n"
"VALUES (%s,%s,%s,%s,%s,%s, %s::vector, %s)\n"
"ON CONFLICT (content_hash) DO UPDATE SET embedding = EXCLUDED.embedding;\n"
"'''\n\n"
"for path in docs.glob('*.md'):\n"
"    for ch in chunk_markdown(path.name, path.read_text()):\n"
"        vec = to_vector_literal(embed_document(ch.content))   # '[0.1,0.2,...]'\n"
"        conn.execute(UPSERT, (ch.doc, ch.citation_id, ch.heading, ch.content,\n"
"                              ch.token_estimate, ch.chunk_index, vec, ch.content_hash))"
)
p("The vector is passed as a text literal like <font face='Courier'>'[0.1,0.2,...]'</font> and "
  "cast with <font face='Courier'>::vector</font>, so no special adapter is needed. Running this "
  "on the Meridian docs produces <b>175 chunks</b> from 16 files.")

# ---- 10 retrieval
h1("10. Hybrid retrieval + Reciprocal Rank Fusion")
p("Given a question, how do we find the right chunks? Two methods, each with a blind spot. "
  "<b>Vector search</b> understands meaning but can miss exact terms (a specific error code, a "
  "product name). <b>Full-text (keyword) search</b> nails exact terms but misses paraphrases. So "
  "we run <b>both</b> and merge the results — this is <b>hybrid retrieval</b>.")
code(
"# vector side: nearest neighbours by cosine distance (<=> is pgvector's operator)\n"
"SELECT id FROM chunks ORDER BY embedding <=> %s::vector LIMIT 20;\n\n"
"# keyword side: Postgres full-text ranking\n"
"SELECT id FROM chunks\n"
"WHERE tsv @@ plainto_tsquery('english', %s)\n"
"ORDER BY ts_rank(tsv, plainto_tsquery('english', %s)) DESC LIMIT 20;"
)
h3("Merging with Reciprocal Rank Fusion (RRF)")
p("Now we have two ranked lists. RRF is a simple, robust way to combine them <i>without</i> "
  "needing the two scoring systems to be on the same scale. Each list contributes "
  "<font face='Courier'>1 / (k + rank)</font> to a chunk's fused score (we use "
  "<font face='Courier'>k = 60</font>). A chunk that ranks high in <i>both</i> lists rises to the "
  "top. Here is a worked example:")
table([
    ["Chunk", "Vector rank", "FTS rank", "RRF score = 1/(60+rv) + 1/(60+rf)"],
    ["key-06", "2", "1", "1/62 + 1/61 = 0.0325  (top)"],
    ["key-07", "1", "—", "1/61 + 0      = 0.0164"],
    ["key-03", "5", "3", "1/65 + 1/63  = 0.0313"],
], [0.9 * inch, 1.0 * inch, 0.9 * inch, 2.6 * inch])
p("A chunk only needs to appear in one list to score, but appearing high in both wins. RRF has no "
  "tunable weights to overfit and works even when one retriever returns nothing — which is exactly "
  "why it's a favourite in production search.")

# ---- 11 answering
h1("11. Cited answers &amp; the citations-or-escalate rule")
p("Retrieval hands the top-5 chunks to the answerer. Before calling the LLM at all, we apply a "
  "<b>confidence gate</b>. This is the second big gotcha: we gate on the top hit's <b>cosine "
  "similarity</b> (~0.7 for a good match), <b>not</b> on the RRF score. RRF scores are tiny by "
  "construction (~0.03 even for a perfect hit), so thresholding on them would escalate almost "
  "everything. We escalate when the top similarity is below "
  "<font face='Courier'>CONFIDENCE_MIN = 0.55</font>.")
story.append(diagram_query())
caption("Figure 3 — The query (read) path: embed the question, search two ways, fuse with RRF, "
        "gate on confidence, then either answer with citations or escalate.")
p("If the gate passes, we format the chunks as labelled sources and instruct the model to answer "
  "using only those sources and to cite the section IDs. If the sources don't contain the answer, "
  "the model must reply with the literal word <font face='Courier'>ESCALATE</font>. Finally we "
  "keep only citations that were actually in the retrieved set, so the model cannot fabricate an "
  "ID.")
code(
"SYSTEM = ('Answer ONLY using the SOURCES. After every factual sentence cite the id(s) '\n"
"          'in brackets like [key-06]. Use only ids that appear in the SOURCES. If the '\n"
"          'SOURCES do not contain the answer, reply with exactly ESCALATE.')\n\n"
"hits = search(query)\n"
"if not hits or hits[0].similarity < CONFIDENCE_MIN:\n"
"    return escalate('low_retrieval_confidence')      # never fabricate\n"
"raw = chat(SYSTEM, format_sources(hits))\n"
"if raw.startswith('ESCALATE'):\n"
"    return escalate('model_declined')\n"
"citations = [c for c in find_ids(raw) if c in {h.citation_id for h in hits}]"
)

# ---- 12 CLI
h1("12. The command-line interface")
p("A tiny CLI ties the pieces together so you can drive the system without a server — perfect for "
  "development and for the eval harness.")
code(
"python -m app.cli init                 # create the schema\n"
"python -m app.cli ingest --reset       # load docs/ into pgvector (175 chunks)\n"
"python -m app.cli search \"rotate api key\"   # inspect raw retrieval hits\n"
"python -m app.cli ask    \"rotate api key\"   # full cited answer or escalation"
)
p("Verified behaviour: <font face='Courier'>ask \"how do I regenerate my API key?\"</font> returns "
  "a grounded answer citing <font face='Courier'>[key-06]</font>; "
  "<font face='Courier'>ask \"what will pricing be next year?\"</font> escalates, because that "
  "fact is not in the docs.")

# ---- 13 API
h1("13. The FastAPI /ask endpoint (the Week 1 milestone)")
p("The milestone is: a request comes in <i>over HTTP</i> and a cited answer goes back. A thin "
  "FastAPI layer wraps the existing <font face='Courier'>answer()</font> function. It has no "
  "business logic of its own — it validates input, delegates, and shapes the reply.")
story.append(diagram_api())
caption("Figure 4 — The request lifecycle for POST /ask.")
code(
"class AskRequest(BaseModel):\n"
"    query: str\n"
"    channel: str = 'web_form'\n\n"
"@app.post('/ask', response_model=AskResponse)\n"
"def handle_ask(req: AskRequest) -> AskResponse:\n"
"    ans = answer(req.query)                      # delegate to the RAG core\n"
"    sources = [Source(citation_id=h.citation_id, doc=h.doc,\n"
"                      heading=h.heading, similarity=round(h.similarity, 3))\n"
"               for h in ans.hits]\n"
"    return AskResponse(text=ans.text, escalated=ans.escalated,\n"
"                       citations=ans.citations, reason=ans.reason, sources=sources)"
)
p("<b>Why a plain <font face='Courier'>def</font> and not <font face='Courier'>async def</font>?</b> "
  "Because <font face='Courier'>answer()</font> does blocking I/O (it calls Ollama and Postgres). "
  "With a normal <font face='Courier'>def</font>, FastAPI runs it in a worker thread so the event "
  "loop stays free. If you wrote <font face='Courier'>async def</font> and then made a blocking "
  "call, you would freeze the whole server. Also note the endpoint returns HTTP 200 even when it "
  "escalates — escalation is a valid outcome, not an error; a genuine dependency failure returns "
  "503. Test it live at <font face='Courier'>http://localhost:8000/docs</font>.")

# ---- 14 evals
h1("14. Evaluation: the golden set and the metrics")
p("The differentiator of this project is that quality is <b>measured</b>, not vibe-checked. We "
  "hand-wrote a <b>golden set</b> of 35 labelled cases in <font face='Courier'>evals/golden.json</font>, "
  "each with the expected routing decision and, where relevant, the citation IDs a correct answer "
  "must reference. Crucially, this set is <b>held out</b> — it is a test set, never used for "
  "training.")
table([
    ["Category", "Count", "What it proves"],
    ["answerable", "15", "Grounded RAG with correct citations across doc areas."],
    ["action", "5", "Requests that need a real side effect (later weeks)."],
    ["unsupported", "6", "'No evidence -> escalate', never fabricate."],
    ["adversarial", "8", "Prompt injection, credential exfil, unsafe actions."],
    ["spam", "1", "Spam classification."],
], [1.1 * inch, 0.6 * inch, 3.6 * inch])
p("We report each metric separately (never one vague number): retrieval hit-rate, citation "
  "correctness, and — for the router — routing accuracy, urgency accuracy, and a <b>two-sided</b> "
  "escalation guardrail. \"Two-sided\" means we check both that must-escalate cases <i>do</i> "
  "escalate <b>and</b> that answerable cases are <i>not</i> over-escalated. A model that escalates "
  "everything would score 100% on the first and fail the second — measuring both directions is a "
  "senior instinct.")

# ---- 15 bonus
h1("15. Bonus: the router + the LoRA fine-tuning experiment")
p("Slightly ahead of schedule, we also built the <b>router</b> (it classifies each request into "
  "answer / action / escalate / spam, plus urgency) and ran a <b>fine-tuning experiment</b> on "
  "it. The prompted router (llama3.2:3b) scores <b>88.6%</b> routing accuracy on the golden set. "
  "We then fine-tuned a small 1B model with <b>LoRA</b> on a free Kaggle T4 GPU to try to beat it.")
p("<b>The honest result: the fine-tune scored 85.7% — it did NOT beat the prompt (-2.9 points).</b> "
  "That is a legitimate, valuable outcome, not a failure. With a strong baseline, a tiny model, "
  "and a few hundred synthetic training examples, prompting winning is expected. The value is the "
  "clean methodology (no train/test leakage, identical evaluation) and the demonstrated skill — "
  "and reporting a negative result honestly is far more credible than a suspicious clean win. "
  "That framing is itself an interview asset.")

# ---- 16 gotchas
h1("16. Design decisions &amp; hard-won gotchas")
bullets([
    "<b>Embed with task prefixes</b> (search_document: / search_query:) or nomic retrieval is weak.",
    "<b>Gate confidence on cosine similarity, not the RRF score</b> — RRF scores are tiny (~0.03).",
    "<b>Citations-or-escalate</b>: below-threshold or ungroundable questions escalate, never fabricate.",
    "<b>Keep only citations present in the retrieved set</b> so the model can't invent an ID.",
    "<b>The golden set is a held-out TEST set</b> — training on it would be data leakage.",
    "<b>Chunk on headings</b> so a retrieved unit maps exactly to a citable section.",
    "<b>Idempotent ingestion</b> via a content-hash unique key; re-runs only re-embed changes.",
    "<b>pgvector inside Postgres</b> = one service, transactional consistency, easy backups.",
    "<b>Sync def for the endpoint</b> because the work is blocking I/O (runs in a threadpool).",
])

# ---- 17 interview
h1("17. Interview questions &amp; model answers")
qa = [
    ("What is RAG and why use it over fine-tuning here?",
     "RAG retrieves relevant document passages at question time and gives them to the LLM as "
     "context, so it answers from your data and can cite sources. Versus fine-tuning it's cheaper, "
     "updates instantly when docs change, and — critically — supports citations and "
     "'I-don't-know'. Fine-tuning bakes knowledge in but can't cite and is costly to refresh."),
    ("Why hybrid retrieval instead of just vector search?",
     "Vector search captures meaning but misses exact tokens (error codes, product names); keyword "
     "search nails exact tokens but misses paraphrases. Running both and fusing them covers each "
     "one's blind spot."),
    ("What is Reciprocal Rank Fusion and why use it?",
     "RRF merges ranked lists by summing 1/(k+rank) across lists. It needs no shared score scale, "
     "has no weights to overfit, and is robust when a retriever returns nothing — a chunk ranked "
     "high in both lists rises to the top."),
    ("Why gate confidence on cosine similarity and not the fused score?",
     "RRF scores are tiny by construction (~0.03 even for a perfect hit), so a threshold on them "
     "would escalate almost everything. Cosine similarity (~0.7 for a good match) is a meaningful, "
     "stable signal to gate on."),
    ("How do you stop the model hallucinating or citing fake sources?",
     "Three layers: a confidence gate escalates weak retrievals before calling the LLM; the prompt "
     "forces answers to use only the provided sources and to reply ESCALATE otherwise; and we keep "
     "only citations that actually appear in the retrieved set."),
    ("Why pgvector instead of a dedicated vector database?",
     "Storing vectors in Postgres means one service to run and back up, and the chunks and their "
     "embeddings stay transactionally consistent. For this scale it's simpler with no real "
     "downside."),
    ("How do you know the system is any good?",
     "A held-out golden set of 35 labelled cases and per-capability metrics — retrieval hit-rate, "
     "citation correctness, routing accuracy, and a two-sided escalation guardrail that also "
     "penalises over-escalation."),
    ("Why is the API endpoint a sync def?",
     "answer() does blocking I/O (Ollama + Postgres). A sync def runs in FastAPI's threadpool and "
     "keeps the event loop free; an async def making a blocking call would stall the server."),
]
for q, a in qa:
    p("Q: " + q, QLABEL)
    p("A: " + a)
    gap(2)

# ---- 18 run
h1("18. Run it yourself")
code(
"# prereqs: Docker Desktop running; Ollama running with models pulled\n"
"ollama pull nomic-embed-text && ollama pull llama3.2:3b\n\n"
"cp .env.example .env\n"
"docker compose up -d                 # Postgres + pgvector\n\n"
"cd backend && python -m venv .venv\n"
".venv\\Scripts\\pip install -r requirements.txt\n"
".venv\\Scripts\\python -m app.cli init\n"
".venv\\Scripts\\python -m app.cli ingest --reset      # 175 chunks\n"
".venv\\Scripts\\python -m app.cli ask \"how do I rotate an API key?\"\n"
".venv\\Scripts\\uvicorn app.main:app --reload --port 8000   # then open /docs"
)

# ---- 19 glossary
h1("19. Glossary")
gl = [
    ("Embedding", "A vector of numbers representing the meaning of a piece of text."),
    ("Cosine similarity", "Similarity of two vectors' directions (1 = identical, 0 = unrelated)."),
    ("Chunk", "A small, self-contained slice of a document that gets embedded and retrieved."),
    ("pgvector", "A Postgres extension adding a vector column type and similarity search."),
    ("tsvector / FTS", "Postgres full-text search — keyword matching with ranking."),
    ("HNSW", "A graph index that makes nearest-neighbour vector search fast."),
    ("RRF", "Reciprocal Rank Fusion — merges ranked lists via 1/(k+rank)."),
    ("Grounding", "Making the model answer from provided sources rather than memory."),
    ("Escalation", "Handing a request to a human when the agent can't answer safely."),
    ("LoRA", "Low-Rank Adaptation — cheap fine-tuning that trains tiny adapter matrices."),
    ("Golden set", "A held-out, labelled test set used to measure quality objectively."),
]
for term, d in gl:
    p(f"<b>{term}</b> — {d}")
gap(10)
p("— End of Week 1 guide. Build the endpoint's error handling next, then Week 2: LangGraph + the "
  "first n8n tool. —", SMALL)


# ---------------------------------------------------------------- footer + build
def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(LINE)
    canvas.drawString(54, 30, "Sentinel — Week 1 Build & Study Guide")
    canvas.drawRightString(letter[0] - 54, 30, f"Page {doc.page}")
    canvas.restoreState()


doc = SimpleDocTemplate(
    str(OUT), pagesize=letter,
    leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=48,
    title="Sentinel — Week 1 Build & Study Guide", author="Achal Verma",
)
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(f"Wrote {OUT}  ({OUT.stat().st_size // 1024} KB)")
