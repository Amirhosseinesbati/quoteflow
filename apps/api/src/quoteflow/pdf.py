"""Proposal PDF renderer with content sourced from a frozen quote version."""

from __future__ import annotations

from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from .models import QuoteVersion

INK = colors.HexColor("#272627")
CORAL = colors.HexColor("#c56b58")
PAPER = colors.HexColor("#fbfaf8")


def _paragraph(text: object, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)


def render_proposal_pdf(version: QuoteVersion, *, client_name: str, brief_reference: str) -> bytes:
    output = BytesIO()
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="QTitle",
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            textColor=INK,
            spaceAfter=10,
            splitLongWords=1,
        )
    )
    styles.add(
        ParagraphStyle(
            name="QHeading",
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=CORAL,
            spaceBefore=18,
            spaceAfter=7,
        )
    )
    styles.add(
        ParagraphStyle(name="QHeadingNext", parent=styles["QHeading"], keepWithNext=1)
    )
    styles.add(
        ParagraphStyle(
            name="QBody", fontName="Helvetica", fontSize=9, leading=14, textColor=INK, spaceAfter=6
        )
    )
    styles.add(
        ParagraphStyle(
            name="QSmall",
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=INK,
            splitLongWords=1,
        )
    )
    styles.add(ParagraphStyle(name="QRight", parent=styles["QSmall"], alignment=TA_RIGHT))

    def page(canvas, doc):
        canvas.saveState()
        width, height = doc.pagesize
        canvas.setFillColor(PAPER)
        canvas.rect(0, 0, width, height, fill=1, stroke=0)
        canvas.setStrokeColor(CORAL)
        canvas.line(46, height - 55, width - 46, height - 55)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.setFillColor(INK)
        canvas.drawString(46, height - 43, "ARC & FIELD STUDIO  /  PROPOSAL")
        canvas.setFont("Helvetica", 8)
        canvas.drawString(
            46,
            31,
            f"Quote {version.quote_id} · Version {version.number} · Catalog {version.catalog_version_id} · {version.content_hash[:10]}",
        )
        canvas.drawRightString(width - 46, 31, f"{doc.page}")
        canvas.restoreState()

    doc = BaseDocTemplate(
        output,
        pagesize=(595.28, 841.89),
        leftMargin=46,
        rightMargin=46,
        topMargin=75,
        bottomMargin=54,
    )
    frame = Frame(
        46,
        54,
        595.28 - 92,
        841.89 - 129,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    doc.addPageTemplates(PageTemplate(id="proposal", frames=frame, onPage=page))
    story = [
        Spacer(1, 18),
        _paragraph(f"A clear path for {client_name}", styles["QTitle"]),
        _paragraph(f"{version.label} proposal · Reference {brief_reference}", styles["QBody"]),
        Spacer(1, 8),
    ]
    proposal = version.proposal
    sections = [
        ("Executive summary", "executive_summary"),
        ("Objectives", "objectives"),
        ("Scope", "scope"),
        ("Deliverables", "deliverables"),
        ("Exclusions", "exclusions"),
        ("Assumptions", "assumptions"),
        ("Schedule", "schedule"),
        ("Milestones", "milestones"),
        ("Client responsibilities", "client_responsibilities"),
        ("Acceptance steps", "acceptance_steps"),
        ("Sample terms", "terms"),
    ]
    for title, key in sections:
        value = proposal.get(key)
        if not value:
            continue
        body = "; ".join(map(str, value)) if isinstance(value, list) else str(value)
        story.append(
            KeepTogether([_paragraph(title, styles["QHeading"]), _paragraph(body, styles["QBody"])])
        )
    story.append(_paragraph("Investment", styles["QHeadingNext"]))
    rows = [["Service", "Qty", "Rate", "Amount"]]
    for line in version.lines:
        rows.append(
            [
                _paragraph(
                    line.service_name + (f"\n{line.assumption}" if line.assumption else ""),
                    styles["QSmall"],
                ),
                str(line.quantity),
                f"${line.unit_price:,.2f}",
                f"${line.line_total:,.2f}",
            ]
        )
    table = Table(
        rows,
        colWidths=[290, 45, 83, 84],
        repeatRows=1,
        splitInRow=1,
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0e9e5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), INK),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (1, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#d8d4d0")),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ]
        )
    )
    story.append(table)
    totals = [
        ("Subtotal", version.subtotal),
        (f"Discount ({version.discount_percent}%)", -version.discount_amount),
        (f"Contingency ({version.contingency_percent}%)", version.contingency_amount),
        (f"Tax ({version.tax_percent}%)", version.tax_amount),
        ("Total", version.total),
    ]
    total_block = []
    for label, amount in totals:
        style = styles["QHeading"] if label == "Total" else styles["QRight"]
        total_block.append(_paragraph(f"{label}: ${amount:,.2f}", style))
    story.append(KeepTogether(total_block))
    story.append(Spacer(1, 0.2 * inch))
    story.append(
        _paragraph(
            "Acceptance through the review page records a workflow acknowledgement, not a certified electronic signature.",
            styles["QSmall"],
        )
    )
    doc.build(story)
    return output.getvalue()
