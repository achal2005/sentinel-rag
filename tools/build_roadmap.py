"""Generate the Sentinel 4-Week Build & Learning Roadmap PDF.

A day-by-day plan for building Sentinel while learning. Each day is structured as
Learn first -> Build -> Done when. Week 1 is marked done (kept for review); Weeks
2-4 are the plan ahead.

Run:  python tools/build_roadmap.py
Out:  Sentinel_Build_Roadmap.pdf   (repo root)
"""
from __future__ import annotations

import math
from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing, Polygon, Rect, String, Line
from reportlab.platypus import (
    ListFlowable, ListItem, PageBreak, Paragraph, Preformatted,
    SimpleDocTemplate, Spacer, Table, TableStyle,
)

OUT = Path(__file__).resolve().parents[1] / "Sentinel_Build_Roadmap.pdf"

INK = HexColor("#0f172a")
MUTED = HexColor("#475569")
ACCENT = HexColor("#2563eb")
LINE = HexColor("#94a3b8")
LABELBG = HexColor("#eef2ff")
CARDBG = HexColor("#f8fafc")
DONE = HexColor("#16a34a")
NEXT = HexColor("#d97706")
SOON = HexColor("#64748b")
C_BLUE = HexColor("#dbeafe")
C_GREEN = HexColor("#dcfce7")
C_AMBER = HexColor("#fef9c3")
C_PURPLE = HexColor("#ede9fe")
C_SLATE = HexColor("#e2e8f0")
STROKE = HexColor("#334155")
CODE_BG = HexColor("#f1f5f9")

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontSize=18, leading=22, textColor=INK,
                    spaceBefore=6, spaceAfter=8)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=13.5, leading=17, textColor=ACCENT,
                    spaceBefore=12, spaceAfter=5)
H3 = ParagraphStyle("H3", parent=ss["Heading3"], fontSize=11, leading=14, textColor=INK,
                    spaceBefore=10, spaceAfter=3)
BODY = ParagraphStyle("Body", parent=ss["BodyText"], fontSize=10, leading=14.5, textColor=INK,
                      spaceAfter=6, alignment=TA_LEFT)
CELL = ParagraphStyle("Cell", parent=BODY, fontSize=9, leading=12.5, spaceAfter=0)
LABEL = ParagraphStyle("Label", parent=CELL, fontName="Helvetica-Bold", textColor=ACCENT)
SMALL = ParagraphStyle("Small", parent=BODY, fontSize=8.5, leading=11.5, textColor=MUTED)
CAPTION = ParagraphStyle("Caption", parent=SMALL, alignment=TA_CENTER, spaceBefore=3, spaceAfter=12)
COVER_T = ParagraphStyle("CoverT", parent=ss["Title"], fontSize=28, leading=32, textColor=INK,
                         alignment=TA_CENTER)
COVER_S = ParagraphStyle("CoverS", parent=ss["Title"], fontSize=13.5, leading=19, textColor=MUTED,
                         alignment=TA_CENTER, fontName="Helvetica")
CODE = ParagraphStyle("Code", parent=ss["Code"], fontName="Courier", fontSize=7.8, leading=9.8,
                      textColor=INK, backColor=CODE_BG, borderPadding=6, spaceBefore=4, spaceAfter=8)

story: list = []


def p(t, s=BODY):
    story.append(Paragraph(t, s))


def h1(t):
    story.append(Paragraph(t, H1))


def h2(t):
    story.append(Paragraph(t, H2))


def gap(h=6):
    story.append(Spacer(1, h))


def caption(t):
    story.append(Paragraph(t, CAPTION))


def bullets(items, s=BODY):
    story.append(ListFlowable([ListItem(Paragraph(t, s), leftIndent=10) for t in items],
                              bulletType="bullet", start="•", leftIndent=14))
    gap(4)


def _bul(items):
    return Paragraph("<br/>".join("• " + i for i in items), CELL)


def day(num, title, status, color, learn, build, done):
    chip = {"done": "&#10003; done", "next": "&#9654; do next", "soon": "&#9633; upcoming"}[status]
    story.append(Paragraph(
        f"Day {num} &mdash; {title} &nbsp;<font color='#{color.hexval()[2:]}' size=9>[{chip}]</font>",
        H3))
    rows = [
        [Paragraph("Learn first", LABEL), _bul(learn)],
        [Paragraph("Build", LABEL), _bul(build)],
        [Paragraph("Done when", LABEL), Paragraph(done, CELL)],
    ]
    t = Table(rows, colWidths=[0.95 * inch, 4.75 * inch], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LABELBG),
        ("BACKGROUND", (1, 0), (1, -1), CARDBG),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, HexColor("#e2e8f0")),
        ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(t)
    gap(8)


def table(data, cw, header=True, font=8.6):
    t = Table(data, colWidths=cw, hAlign="LEFT")
    cmds = [("FONT", (0, 0), (-1, -1), "Helvetica", font), ("TEXTCOLOR", (0, 0), (-1, -1), INK),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6)]
    if header:
        cmds += [("BACKGROUND", (0, 0), (-1, 0), HexColor("#1e293b")),
                 ("TEXTCOLOR", (0, 0), (-1, 0), white), ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", font)]
    t.setStyle(TableStyle(cmds))
    story.append(t)
    gap(10)


# ---- diagram helpers
def rbox(d, x, y, w, h, lines, fill, fs=8, tc=INK):
    d.add(Rect(x, y, w, h, rx=5, ry=5, fillColor=fill, strokeColor=STROKE, strokeWidth=1))
    if isinstance(lines, str):
        lines = [lines]
    lh = fs + 2.4
    start = y + h / 2 + (len(lines) - 1) * lh / 2 - fs / 2 + 1
    for i, ln in enumerate(lines):
        b = ln.startswith("*")
        d.add(String(x + w / 2, start - i * lh, ln.lstrip("*"), textAnchor="middle", fontSize=fs,
                     fillColor=tc, fontName="Helvetica-Bold" if b else "Helvetica"))


def arrow(d, x1, y1, x2, y2, color=LINE):
    d.add(Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=1.1))
    a = math.atan2(y2 - y1, x2 - x1)
    L, w = 6, 3
    d.add(Polygon([x2, y2, x2 - L * math.cos(a) + w * math.sin(a), y2 - L * math.sin(a) - w * math.cos(a),
                   x2 - L * math.cos(a) - w * math.sin(a), y2 - L * math.sin(a) + w * math.cos(a)],
                  fillColor=color, strokeColor=color))


def diagram_timeline():
    d = Drawing(510, 150)
    weeks = [
        ("WEEK 1", "RAG core", "cited answers", C_GREEN, "done"),
        ("WEEK 2", "Orchestration", "n8n + fallback", C_AMBER, "next"),
        ("WEEK 3", "Safety + obs", "approval + traces", C_BLUE, "soon"),
        ("WEEK 4", "Evals + polish", "CI + demo", C_PURPLE, "soon"),
    ]
    x, w, h, y = 8, 116, 66, 60
    for i, (wk, t1, t2, fill, st) in enumerate(weeks):
        rbox(d, x, y, w, h, ["*" + wk, t1, t2], fill, fs=8.5)
        tag = {"done": "✓ done", "next": "▶ next", "soon": "□ upcoming"}[st]
        tc = {"done": DONE, "next": NEXT, "soon": SOON}[st]
        d.add(String(x + w / 2, y - 12, tag, textAnchor="middle", fontSize=8, fillColor=tc))
        if i < 3:
            arrow(d, x + w, y + h / 2, x + w + 8, y + h / 2)
        x += w + 8
    d.add(String(255, 30, "Milestone chain: cited answer  ->  'cancel my order' creates a ticket  ->  "
                          "risky action waits for approval  ->  eval table in CI",
                 textAnchor="middle", fontSize=7.6, fillColor=MUTED))
    return d


def diagram_daily():
    d = Drawing(510, 70)
    steps = [("*LEARN", "the concept", C_BLUE), ("*BUILD", "the thing", C_GREEN),
             ("*CHECK", "'done when'", C_AMBER)]
    x, w, h, y = 120, 90, 40, 18
    for i, (a, b, fill) in enumerate(steps):
        rbox(d, x, y, w, h, [a, b], fill, fs=8)
        if i < 2:
            arrow(d, x + w, y + h / 2, x + w + 10, y + h / 2)
        x += w + 10
    d.add(String(255, 6, "Every day follows this loop.", textAnchor="middle", fontSize=7.6, fillColor=MUTED))
    return d


# ================================================================ COVER
story.append(Spacer(1, 110))
p("SENTINEL", COVER_S)
p("The 4-Week Build &amp; Learning Roadmap", COVER_T)
gap(10)
p("A day-by-day plan to build the project <i>while learning it</i>.<br/>"
  "Each day: <b>Learn first &rarr; Build &rarr; Done when.</b>", COVER_S)
gap(36)
p("<b>Week 1</b> is marked done (kept here for review). <b>Weeks 2&ndash;4</b> are the plan ahead.<br/>"
  "Author: Achal Verma &nbsp;&middot;&nbsp; github.com/achal2005", COVER_S)
story.append(PageBreak())

# ================================================================ HOW TO USE
h1("How to use this roadmap")
story.append(diagram_daily())
gap(4)
p("This is a <b>learning</b> plan as much as a build plan. For every day you get three things: what "
  "to <b>learn first</b> (the concept, before you touch code), what to <b>build</b> (the concrete "
  "task), and how to know you're <b>done</b> (a checkpoint you can actually verify). Don't skip the "
  "'learn first' box &mdash; understanding <i>why</i> is what turns this from copying code into being "
  "able to explain it in an interview.")
bullets([
    "<b>Pace:</b> the plan assumes ~4 weeks part-time (a few focused hours per day). Go slower if you "
    "need to &mdash; depth beats speed.",
    "<b>Rhythm:</b> each week ends with a <b>milestone</b> you can demo. If you can't demo it, you're "
    "not done with the week.",
    "<b>Scope discipline:</b> the four things you must never cut are <i>citations-or-escalate RAG</i>, "
    "the <i>n8n tool registry</i>, <i>model fallback</i>, and the <i>eval harness</i>. Everything else "
    "is negotiable.",
    "<b>Reproducibility rule:</b> never claim a number you can't reproduce from the code.",
])

# ---- big picture
h2("The big picture (what you're building)")
p("Sentinel is a self-hosted AI support agent: it reads a request, answers it from a knowledge base "
  "<b>with citations</b> (or escalates honestly), and <b>resolves</b> it by calling automation "
  "workflows. Tagline: <i>\"LLM brain, n8n hands.\"</i> It is built in six layers:")
bullets([
    "<b>Channels</b> &rarr; <b>Ingest</b> &rarr; <b>Brain</b> (router + RAG) &rarr; <b>Hands</b> (n8n "
    "tools) &rarr; <b>Safety</b> (approval) &rarr; <b>Glass</b> (evals + tracing).",
])
p("<b>Current status:</b> Week 1 (RAG core) is complete and on GitHub, plus the router and a bonus "
  "LoRA fine-tuning experiment. Weeks 2&ndash;4 are ahead.")

# ---- prerequisites
h2("Prerequisites &amp; mindset (before Week 1)")
p("You don't need to know everything up front &mdash; you'll learn each tool the day you need it. But "
  "these baseline skills make the whole thing smoother:")
bullets([
    "<b>Python</b> (functions, classes, dataclasses, type hints) and running scripts/modules.",
    "<b>The terminal</b>: navigating folders, virtual environments (venv), pip.",
    "<b>Docker basics</b>: what a container is, <font face='Courier'>docker compose up</font>.",
    "<b>SQL basics</b>: SELECT / INSERT, and the idea of an index.",
    "<b>HTTP basics</b>: what a POST request and JSON body are.",
])
p("<b>How to learn a new tool fast (use this every week):</b> (1) read the tool's <i>own</i> "
  "\"quickstart\" once; (2) get the smallest possible thing working (hello-world); (3) only then wire "
  "it into Sentinel. Learn just-in-time, not just-in-case.")
story.append(PageBreak())

# ---- timeline
h1("The 4 weeks at a glance")
story.append(diagram_timeline())
caption("Figure 1 — The four weeks and their milestones. Each week produces something you can demo.")
table([
    ["Week", "Theme", "Milestone (demo this)", "Status"],
    ["1", "RAG core", "A question in -> a cited answer back (or escalate).", "Done"],
    ["2", "Orchestration + Action", "\"Cancel my order\" -> actually creates a ticket via n8n.", "Next"],
    ["3", "Safety + Observability", "A risky action waits for approval; full trace visible.", "Upcoming"],
    ["4", "Evals + Polish", "Eval score table runs in CI; a 2-min demo exists.", "Upcoming"],
], [0.5 * inch, 1.5 * inch, 2.9 * inch, 0.8 * inch])
story.append(PageBreak())

# ================================================================ WEEK 1
h1("Week 1 &mdash; RAG core &nbsp;<font color='#16a34a' size=12>[DONE]</font>")
p("<b>Goal:</b> retrieve the right passages and answer with citations, or escalate. "
  "<b>Milestone:</b> a question comes in and a cited answer comes back. "
  "<b>After this week you can say:</b> \"I built hybrid RAG on pgvector with mandatory citations and "
  "an honest 'I don't know'.\"")

day(0, "Environment setup", "done", DONE,
    ["What Docker, a container, and Docker Compose are.",
     "What a Python virtual environment (venv) is and why to use one.",
     "What Ollama is (runs LLMs locally) and what an embedding model vs a chat model is."],
    ["Install Docker Desktop and Ollama; pull nomic-embed-text and llama3.2:3b.",
     "Write docker-compose.yml for Postgres+pgvector; docker compose up -d.",
     "Create backend/.venv and a .env from .env.example."],
    "docker compose ps shows the DB healthy, and 'ollama list' shows both models.")

day(1, "Knowledge base + chunking", "done", DONE,
    ["What RAG is and why it beats fine-tuning for doc Q&amp;A.",
     "Why you chunk documents, and why heading-aware chunking keeps answers citable.",
     "The citation-ID convention: each section ends with a stable [id]."],
    ["The docs/ knowledge base (a consistent fictional company, Meridian).",
     "chunking.py: split each doc at H2 headings, carry the [citation-id] onto each chunk."],
    "chunk_markdown() returns chunks, each with the right citation_id.")

day(2, "Embeddings + the database schema", "done", DONE,
    ["What an embedding is; cosine similarity; the 768-dimensional vector.",
     "pgvector: the vector column type and similarity operators.",
     "Postgres full-text search (tsvector) for keyword matching.",
     "The nomic gotcha: prefixes 'search_document:' and 'search_query:'."],
    ["db.py: the chunks table (vector(768) + a generated tsvector), HNSW + GIN indexes.",
     "embed.py: call Ollama's HTTP API for embeddings and chat (stdlib only)."],
    "cli init creates the schema; embed() returns a 768-number vector.")

day(3, "Ingestion (the write path)", "done", DONE,
    ["Idempotency: why re-running should not duplicate data.",
     "UPSERT (INSERT ... ON CONFLICT) and using a content hash as the key."],
    ["ingest.py: for each doc -> chunk -> embed (search_document:) -> upsert into pgvector."],
    "cli ingest --reset loads 175 chunks; running it twice does not duplicate them.")

day(4, "Hybrid retrieval + RRF", "done", DONE,
    ["Vector search vs keyword search &mdash; and the blind spot of each.",
     "Reciprocal Rank Fusion (RRF): merge two ranked lists with 1/(k+rank)."],
    ["retrieve.py: run vector search and full-text search, fuse with RRF, return top-5.",
     "Expose the top hit's cosine similarity (you'll gate on it next)."],
    "cli search returns the relevant section near the top for a real question.")

day(5, "Cited answers + escalation", "done", DONE,
    ["Prompting an LLM to answer only from provided context (grounding).",
     "The confidence gate: gate on cosine similarity, NOT the tiny RRF score.",
     "How to stop fabricated citations (keep only IDs that were retrieved)."],
    ["answer.py: gate -> format sources -> LLM answers with [ids] or replies ESCALATE.",
     "cli.py: init / ingest / search / ask commands."],
    "ask 'rotate my key' cites [key-06]; ask 'pricing next year' escalates.")

day(6, "Eval harness + the API", "done", DONE,
    ["What a held-out golden set is and why you never train on it.",
     "FastAPI + Pydantic + Uvicorn; why the endpoint is a sync 'def' (blocking I/O)."],
    ["evals/golden.json (35 labelled cases) + a metrics script.",
     "main.py: POST /ask (wraps answer()) and GET /health."],
    "POST /ask returns a cited answer over HTTP &mdash; the Week 1 milestone.")

p("<b>Bonus done this week:</b> a router (classifies answer/action/escalate/spam) with a measured "
  "88.6% baseline, plus a LoRA fine-tuning experiment (honest 85.7% result). Note your plan's scope "
  "rule says <i>don't add fine-tuning</i> &mdash; it was an intentional extra for the 'Fine-tuning' "
  "evidence row; just don't let it distract from the four core pillars.", SMALL)
story.append(PageBreak())

# ================================================================ WEEK 2
h1("Week 2 &mdash; Orchestration &amp; Action &nbsp;<font color='#d97706' size=12>[NEXT]</font>")
p("<b>Goal:</b> turn the pieces into an explainable agent graph, give it real <b>hands</b> (n8n "
  "tools), and make the model layer resilient (fallback). "
  "<b>Milestone:</b> \"cancel my order\" actually creates a ticket. "
  "<b>After this week you can say:</b> \"My agent doesn't just answer &mdash; it executes actions "
  "through a pluggable n8n tool layer, with automatic model failover and per-request cost logging.\"")

day(1, "Router agent (mostly done)", "done", DONE,
    ["Classification prompting; forcing valid JSON output; a routing taxonomy.",
     "Two-sided metrics: escalation recall AND over-escalation."],
    ["router.py (answer/action/escalate/spam + urgency) and eval_routing.py.",
     "Already built &mdash; review it and make sure you can explain every line."],
    "You can run cli route and eval_routing and explain the 88.6% number.")

day(2, "LangGraph basics + the loop", "next", NEXT,
    ["What LangGraph is: state, nodes, edges, and conditional edges.",
     "Why a graph (vs plain function calls): inspectable, resumable, explainable.",
     "Resource: the official LangGraph docs 'quickstart'."],
    ["Install langgraph. Build a 3-4 node graph: router -> {answer | action | escalate}.",
     "Define a small shared state (request, route, retrieved chunks, answer, action).",
     "Route with a conditional edge based on the router's decision."],
    "One request flows through the graph and lands in the correct node end-to-end.")

day(3, "n8n + the tool registry", "next", NEXT,
    ["What n8n is: workflows, the Webhook trigger node, and HTTP nodes.",
     "The tool-registry idea: name + JSON param schema + webhook URL + risk level.",
     "Resource: docs.n8n.io (self-hosting + webhook node)."],
    ["Add n8n to docker-compose (self-hosted, free).",
     "Build one n8n workflow: Webhook -> insert a row into a 'tickets' table.",
     "Create a tool registry (a table or a config) describing create_ticket."],
    "Hitting the n8n webhook by hand (curl) creates a ticket row.")

day(4, "Action agent + first tool (the milestone)", "next", NEXT,
    ["LLM function-calling / structured parameter extraction.",
     "Pydantic validation of tool params before doing anything real.",
     "Idempotency keys so a retry does not create two tickets."],
    ["An 'action' node: extract params -> validate with Pydantic -> POST to the n8n webhook.",
     "Wire create_ticket into the LangGraph 'action' branch."],
    "\"Cancel my order ...\" produces exactly one ticket in the DB. (Week 2 milestone.)")

day(5, "Second tool + model fallback", "next", NEXT,
    ["Provider abstraction: one interface over several LLM providers.",
     "Retries and automatic failover; reading a provider's error/rate-limit.",
     "Groq's free API (fast Llama); per-call cost + latency logging.",
     "Resource: console.groq.com/docs."],
    ["Add a send_reply tool (n8n workflow that emails / posts a message).",
     "Wrap the LLM client: Ollama primary -> Groq fallback on error/timeout.",
     "Log model, tokens, latency, and (free-tier) cost to a Postgres table per request."],
    "Stop Ollama mid-run and the request still completes via Groq; cost row is written.")

day(6, "Integrate, test, and extend the evals", "next", NEXT,
    ["Regression testing: lock in behaviour so future changes do not break it."],
    ["Wire graph + tools + fallback + logging together behind /ask (or a new endpoint).",
     "Add action + fallback cases to golden.json and check tool-selection accuracy."],
    "The action cases pass and you can show a tiny cost/latency readout.")
story.append(PageBreak())

# ================================================================ WEEK 3
h1("Week 3 &mdash; Safety &amp; Observability &nbsp;<font color='#64748b' size=12>[UPCOMING]</font>")
p("<b>Goal:</b> make it \"industrial\", not a toy &mdash; humans approve risky actions, and every "
  "decision is traceable. <b>Milestone:</b> a risky action waits for your approval, and you can see "
  "the full trace. <b>After this week you can say:</b> \"High-risk actions pause for human approval, "
  "every decision is audit-logged, and each request has an end-to-end trace.\"")

day(1, "Risk levels + the approval queue", "soon", SOON,
    ["Human-in-the-loop; risk levels (low auto-runs, high needs approval).",
     "Idempotency and 'exactly-once' side effects."],
    ["Add risk_level to each tool. High-risk actions write to an approval_queue table",
     "instead of executing, and pause the graph."],
    "A high-risk action stops and waits instead of running immediately.")

day(2, "The approval UI", "soon", SOON,
    ["A minimal review UI: list pending actions, Approve / Reject.",
     "Option A: a tiny Next.js page (your niche). Option B: a small FastAPI + HTML page."],
    ["Build the Approve/Reject page reading the approval_queue.",
     "Approving triggers the n8n tool; rejecting closes the item."],
    "Click Approve in the UI and the action executes via n8n.")

day(3, "Audit log", "soon", SOON,
    ["Structured decision records: what the agent decided and why."],
    ["Write an audit row for every step: router decision, retrieved IDs, tool + params, outcome."],
    "You can reconstruct any request's full decision trail from the DB.")

day(4, "Tracing with Langfuse", "soon", SOON,
    ["Observability: traces and spans; why you trace an LLM pipeline.",
     "Resource: langfuse.com/docs (self-hosting)."],
    ["Add Langfuse (Docker) to the stack and instrument the graph.",
     "Trace: router -> chunks -> prompt -> tool call -> cost, per request."],
    "One request shows a complete, readable trace in the Langfuse UI.")

day(5, "Guardrails + adversarial hardening", "soon", SOON,
    ["Prompt injection, credential-exfil, unsafe/destructive actions.",
     "A verification/critic step; rate limiting with jitter."],
    ["Add a critic/verification check before high-risk execution.",
     "Make the adversarial golden cases pass."],
    "Injection and credential-request cases are refused or escalated, not obeyed.")

day(6, "Buffer &amp; integration", "soon", SOON,
    ["Nothing new &mdash; consolidate and fix rough edges."],
    ["Make the whole Week 1-3 pipeline run cleanly end to end."],
    "A full demo path works without manual babysitting.")
story.append(PageBreak())

# ================================================================ WEEK 4
h1("Week 4 &mdash; Evals &amp; Polish &nbsp;<font color='#64748b' size=12>[UPCOMING]</font>")
p("<b>Goal:</b> prove it works with numbers, and make it presentable. <b>Milestone:</b> an eval score "
  "table runs automatically in CI, and a 2-minute demo exists. <b>After this week you can say:</b> "
  "\"I measure my LLM system &mdash; correctness and citation faithfulness &mdash; and the score table "
  "runs on every change.\"")

day(1, "LLM-as-judge evaluation", "soon", SOON,
    ["Using an LLM to score answers; correctness vs citation faithfulness.",
     "Why a rubric + a strong judge model reduces noise."],
    ["A judge that scores each golden answer for correctness and whether its citations",
     "are actually supported by the retrieved text."],
    "You get a per-metric score table across the whole golden set.")

day(2, "Evals in CI (GitHub Actions)", "soon", SOON,
    ["What CI is; GitHub Actions workflows; running tests on a push/PR.",
     "Resource: docs.github.com/actions."],
    ["A workflow that runs the eval suite and prints the score table on every PR."],
    "A pull request shows the eval table automatically.")

day(3, "Reliability / fault injection", "soon", SOON,
    ["Fault injection: deliberately break a dependency to prove resilience."],
    ["Tests that kill Ollama / the DB and assert the fallback or escalation fires."],
    "You have a short 'reliability' results section backed by tests.")

day(4, "README, diagram, and a demo GIF", "soon", SOON,
    ["What makes a repo credible at a glance: diagram, quickstart, score table."],
    ["Polish the README (already strong); record a short GIF of the agent resolving a ticket."],
    "A newcomer understands and runs the project from the README alone.")

day(5, "Deploy a demo", "soon", SOON,
    ["Free deploy options: local + ngrok, or an Oracle Cloud Always-Free VM.",
     "Exposing a local webhook to the internet for n8n."],
    ["Deploy the stack (or record a solid local demo) and get a shareable link/video."],
    "There is a link or a 2-minute video showing it actually working.")

day(6, "Write-up + the 'killer demo move'", "soon", SOON,
    ["Turning a project into outreach: evidence-backed claims only.",
     "Map each resume bullet to concrete evidence (traces, tests, the score table)."],
    ["Point the ingest pipeline at a target company's real public docs and resolve 5 sample tickets.",
     "Write a short blog post and finalise the evidence-mapped resume bullets."],
    "You can send a founder \"here's my agent resolving 5 tickets against your docs\".")
story.append(PageBreak())

# ================================================================ RESOURCES
h1("Learning resources by topic")
p("Prefer each tool's <i>official</i> docs &mdash; they're the most accurate and teach the mental "
  "model, not just snippets. Learn just-in-time, on the day you need it.")
table([
    ["Topic", "Where to learn it (official)"],
    ["RAG concept", "Search 'retrieval augmented generation' + read one primer; then build."],
    ["pgvector", "github.com/pgvector/pgvector (README = the whole tutorial)."],
    ["Postgres full-text", "postgresql.org/docs -> 'Full Text Search' chapter."],
    ["Reciprocal Rank Fusion", "Search 'Reciprocal Rank Fusion' (Cormack et al., 2009)."],
    ["FastAPI / Pydantic", "fastapi.tiangolo.com (the tutorial is excellent)."],
    ["Ollama", "github.com/ollama/ollama (API + model library)."],
    ["LangGraph", "langchain-ai.github.io/langgraph (quickstart + concepts)."],
    ["n8n (self-host)", "docs.n8n.io (hosting, Webhook node, HTTP node)."],
    ["Groq API", "console.groq.com/docs (OpenAI-compatible, free tier)."],
    ["Langfuse", "langfuse.com/docs (self-hosting + tracing SDK)."],
    ["LoRA / PEFT", "huggingface.co/docs/peft (LoRA config + SFT)."],
    ["GitHub Actions", "docs.github.com/actions (workflow syntax)."],
], [1.6 * inch, 4.0 * inch])

# ---- evidence map
h2("The evidence map (claim -> proof)")
p("Only claim what you can reproduce. Every headline maps to a concrete artifact:")
table([
    ["Claim", "Evidence you must be able to show"],
    ["Multi-step agent", "A working LangGraph graph (router + specialist + a check)."],
    ["RAG with citations", "Retrieval traces + citation tests on the golden set."],
    ["Tool execution", "An n8n execution record creating a real ticket."],
    ["Safe execution", "Approval queue + idempotency + verification tests."],
    ["Model orchestration", "Fallback firing on failure + per-request cost/latency logs."],
    ["Reliability", "Fault-injection / adversarial results."],
    ["Fine-tuning", "The LoRA adapter + the benchmark table (done: 85.7% vs 88.6%)."],
    ["Improvement", "Baseline vs final comparison numbers."],
], [1.7 * inch, 3.9 * inch])

h2("Scope discipline (read twice)")
bullets([
    "<b>Never cut:</b> citations-or-escalate RAG, the n8n tool registry, model fallback, the eval harness. "
    "<i>These four are the pitch.</i>",
    "<b>Cut first if time-pressed:</b> fancy approval UI -> a simple table + CLI; Langfuse -> structured "
    "JSON logs; 5 tools -> 3; local Ollama -> a single cloud model.",
    "<b>Don't add:</b> multi-tenancy, heavy auth, a fancy frontend. Depth over surface area.",
])
gap(8)
p("&mdash; Build one week at a time. Demo the milestone before moving on. Keep every claim "
  "reproducible. &mdash;", SMALL)


def footer(c, d):
    c.saveState()
    c.setFont("Helvetica", 8)
    c.setFillColor(LINE)
    c.drawString(54, 30, "Sentinel — 4-Week Build & Learning Roadmap")
    c.drawRightString(letter[0] - 54, 30, f"Page {d.page}")
    c.restoreState()


doc = SimpleDocTemplate(str(OUT), pagesize=letter, leftMargin=54, rightMargin=54,
                        topMargin=50, bottomMargin=46,
                        title="Sentinel — 4-Week Build & Learning Roadmap", author="Achal Verma")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(f"Wrote {OUT}  ({OUT.stat().st_size // 1024} KB)")
