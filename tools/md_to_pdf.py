"""
Minimal Markdown -> PDF renderer for the Meridian docs, using reportlab.

Supports: ATX headings (#..####), GFM pipe tables, fenced code blocks,
blockquotes, bullet lists, horizontal rules, and inline **bold**, *italic*,
`code`, and [links](url). Good enough to produce realistic, parser-testable
PDFs from the docs in /docs.

Usage:
    python tools/md_to_pdf.py docs/authentication.md docs/billing.md docs/security.md
"""

import re
import sys
import html
from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Preformatted, Table, TableStyle, HRFlowable,
)

# ---------- styles ----------
styles = getSampleStyleSheet()
BODY = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14, spaceAfter=6)
H1 = ParagraphStyle("H1", parent=styles["Title"], fontSize=22, leading=26, spaceAfter=12, textColor=colors.HexColor("#1a2b4a"))
H2 = ParagraphStyle("H2", parent=styles["Heading1"], fontSize=15, leading=19, spaceBefore=12, spaceAfter=6, textColor=colors.HexColor("#1a2b4a"))
H3 = ParagraphStyle("H3", parent=styles["Heading2"], fontSize=12.5, leading=16, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#33456b"))
H4 = ParagraphStyle("H4", parent=styles["Heading3"], fontSize=11, leading=14, spaceBefore=8, spaceAfter=3, textColor=colors.HexColor("#33456b"))
BULLET = ParagraphStyle("Bullet", parent=BODY, leftIndent=16, bulletIndent=4, spaceAfter=3)
QUOTE = ParagraphStyle("Quote", parent=BODY, leftIndent=14, textColor=colors.HexColor("#444444"), fontName="Helvetica-Oblique", borderPadding=(2, 2, 2, 8))
CODE = ParagraphStyle("Code", parent=styles["Code"], fontSize=8.5, leading=11, backColor=colors.HexColor("#f4f5f7"),
                      borderColor=colors.HexColor("#dddddd"), borderWidth=0.5, borderPadding=6, spaceAfter=8, spaceBefore=2)
CELL = ParagraphStyle("Cell", parent=BODY, fontSize=8.5, leading=11, spaceAfter=0)
CELL_H = ParagraphStyle("CellH", parent=CELL, fontName="Helvetica-Bold", textColor=colors.white)

HEADING_STYLES = {1: H1, 2: H2, 3: H3, 4: H4}


def inline(text: str) -> str:
    """Convert inline markdown to reportlab mini-markup, code-span safe."""
    spans = {}

    def stash(m):
        key = f"\x00{len(spans)}\x00"
        spans[key] = m.group(1)
        return key

    # pull out `code` spans first so we don't format inside them
    text = re.sub(r"`([^`]+)`", stash, text)
    text = html.escape(text, quote=False)
    # bold, then italic
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"(?<!_)_([^_]+)_(?!_)", r"<i>\1</i>", text)
    # links [text](url) -> underlined text (drop bare-file links cleanly)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<u>\1</u>', text)
    # reinsert code spans, escaped, in a mono font with a subtle tint
    for key, raw in spans.items():
        safe = html.escape(raw, quote=False)
        text = text.replace(key, f'<font face="Courier" size="9" backColor="#eef0f3"> {safe} </font>')
    return text


def build_story(md: str):
    story = []
    lines = md.split("\n")
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]

        # fenced code block
        if line.lstrip().startswith("```"):
            i += 1
            buf = []
            while i < n and not lines[i].lstrip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            story.append(Preformatted("\n".join(buf) if buf else " ", CODE))
            continue

        # table: header row followed by a |---| separator
        if line.strip().startswith("|") and i + 1 < n and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[i + 1]) and "-" in lines[i + 1]:
            rows = []
            header = [c.strip() for c in line.strip().strip("|").split("|")]
            rows.append(header)
            i += 2  # skip header + separator
            while i < n and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            story.append(make_table(rows))
            story.append(Spacer(1, 6))
            continue

        # horizontal rule
        if re.match(r"^\s*---+\s*$", line):
            story.append(Spacer(1, 4))
            story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#cccccc")))
            story.append(Spacer(1, 6))
            i += 1
            continue

        # headings
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            level = len(m.group(1))
            story.append(Paragraph(inline(m.group(2)), HEADING_STYLES[level]))
            i += 1
            continue

        # blockquote
        if line.startswith(">"):
            buf = []
            while i < n and lines[i].startswith(">"):
                buf.append(lines[i].lstrip(">").strip())
                i += 1
            story.append(Paragraph(inline(" ".join(buf)), QUOTE))
            story.append(Spacer(1, 4))
            continue

        # bullet list
        if re.match(r"^\s*[-*]\s+", line):
            while i < n and re.match(r"^\s*[-*]\s+", lines[i]):
                item = re.sub(r"^\s*[-*]\s+", "", lines[i])
                story.append(Paragraph(inline(item), BULLET, bulletText="•"))
                i += 1
            story.append(Spacer(1, 4))
            continue

        # blank
        if not line.strip():
            i += 1
            continue

        # paragraph (gather until blank / block start)
        buf = [line]
        i += 1
        while i < n and lines[i].strip() and not re.match(r"^(#{1,4}\s|\s*[-*]\s|>|\|)", lines[i]) and not lines[i].lstrip().startswith("```") and not re.match(r"^\s*---+\s*$", lines[i]):
            buf.append(lines[i])
            i += 1
        story.append(Paragraph(inline(" ".join(buf)), BODY))
    return story


def make_table(rows):
    header, *body = rows
    ncols = len(header)
    data = [[Paragraph(inline(c), CELL_H) for c in header]]
    for r in body:
        r = (r + [""] * ncols)[:ncols]
        data.append([Paragraph(inline(c), CELL) for c in r])
    avail = LETTER[0] - 1.5 * inch
    col_w = avail / ncols
    t = Table(data, colWidths=[col_w] * ncols, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#33456b")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f5f7")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def convert(path: Path):
    md = path.read_text(encoding="utf-8")
    out = path.with_suffix(".pdf")
    doc = SimpleDocTemplate(
        str(out), pagesize=LETTER,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        title=path.stem.replace("-", " ").title() + " — Meridian Docs",
        author="Meridian",
    )
    doc.build(build_story(md))
    print(f"wrote {out}")


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        convert(Path(arg))
