from __future__ import annotations

from html import escape
from io import BytesIO

def report_pdf(result: dict) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:
        raise ValueError("PDF reports require ReportLab. Install with: pip install 'datasheetdelta[reports]'.") from exc

    output = BytesIO()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=22, leading=26, textColor=colors.HexColor("#202927"), alignment=TA_LEFT, spaceAfter=5))
    styles.add(ParagraphStyle(name="Subtle", parent=styles["Normal"], fontSize=8, leading=11,
        textColor=colors.HexColor("#68716b")))
    styles.add(ParagraphStyle(name="FindingTitle", parent=styles["Heading2"], fontSize=12, leading=15,
        textColor=colors.HexColor("#202927"), spaceBefore=10, spaceAfter=5))
    styles.add(ParagraphStyle(name="BodySmall", parent=styles["BodyText"], fontSize=8, leading=11,
        textColor=colors.HexColor("#303936"), wordWrap="CJK"))
    styles.add(ParagraphStyle(name="Label", parent=styles["BodyText"], fontName="Helvetica-Bold",
        fontSize=7, leading=9, textColor=colors.HexColor("#a9825b")))
    styles.add(ParagraphStyle(name="Warning", parent=styles["BodyText"], fontSize=8, leading=11,
        textColor=colors.HexColor("#79572e"), backColor=colors.HexColor("#f3e9db"), borderPadding=6))

    def para(value, style="BodySmall"):
        return Paragraph(escape(str(value if value is not None else "—")).replace("\n", "<br/>"), styles[style])

    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#d8d3c6"))
        canvas.line(16 * mm, 13 * mm, A4[0] - 16 * mm, 13 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#68716b"))
        canvas.drawString(16 * mm, 8 * mm, "DATASHEETDELTA · HUMAN ENGINEERING REVIEW REQUIRED")
        canvas.drawRightString(A4[0] - 16 * mm, 8 * mm, f"Page {document.page}")
        canvas.restoreState()

    story = [
        para("DATASHEETDELTA", "Label"),
        para("Engineering change report", "ReportTitle"),
        para(f"Reference: {result.get('reference_file', '—')}"),
        para(f"Revised: {result.get('revised_file', '—')}"),
        Spacer(1, 5 * mm),
    ]
    findings = result.get("findings", [])
    counts = {}
    for item in findings:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    summary = " · ".join(f"{key.replace('_', ' ').title()}: {value}" for key, value in sorted(counts.items())) or "No fields extracted"
    story.extend([para("FINDINGS SUMMARY", "Label"), para(summary), Spacer(1, 3 * mm)])
    story.append(para("Review every extracted field against the source documents. A difference is not automatically a defect or safety issue.", "Warning"))

    for index, item in enumerate(findings, 1):
        story.append(para(f"{index:03d} · {item.get('parameter', 'Unnamed parameter')} · {item.get('status', 'unknown').replace('_', ' ').upper()}", "FindingTitle"))
        comparison = [
            [para("REFERENCE VALUE", "Label"), para("REVISED VALUE", "Label")],
            [para(item.get("reference")), para(item.get("revised"))],
            [para("SOURCE LOCATION", "Label"), para("SOURCE LOCATION", "Label")],
            [para(item.get("reference_source")), para(item.get("revised_source"))],
            [para("SOURCE EXCERPT", "Label"), para("SOURCE EXCERPT", "Label")],
            [para(item.get("reference_excerpt")), para(item.get("revised_excerpt"))],
        ]
        table = Table(comparison, colWidths=[(A4[0] - 38 * mm) / 2] * 2, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f0e7")),
            ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#f3f0e7")),
            ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#f3f0e7")),
            ("BOX", (0, 0), (-1, -1), .4, colors.HexColor("#d8d3c6")),
            ("INNERGRID", (0, 0), (-1, -1), .3, colors.HexColor("#d8d3c6")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.extend([table, Spacer(1, 2 * mm), para("INTERPRETATION", "Label"), para(item.get("explanation")), Spacer(1, 2 * mm)])

    warnings = result.get("warnings", [])
    if warnings:
        story.extend([para("EXTRACTION WARNINGS", "FindingTitle")])
        for warning in warnings:
            story.append(para("• " + warning, "Warning"))
    story.extend([
        Spacer(1, 5 * mm),
        para("METHOD AND LIMITATIONS", "FindingTitle"),
        para(result.get("method", "Deterministic extraction and comparison")),
    ])
    for limitation in result.get("limitations", []):
        story.append(para("• " + limitation))
    story.append(Spacer(1, 3 * mm))
    story.append(para("This report is an aid to document review. It does not establish extraction completeness, engineering suitability, safety, regulatory compliance or approval. A qualified engineer must determine materiality and authorize any change.", "Warning"))

    document = SimpleDocTemplate(output, pagesize=A4, rightMargin=19 * mm, leftMargin=19 * mm,
        topMargin=17 * mm, bottomMargin=19 * mm, title="DatasheetDelta Engineering Change Report",
        author="DatasheetDelta")
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
