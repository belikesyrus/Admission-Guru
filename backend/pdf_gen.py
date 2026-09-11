"""
PDF generation for college preference lists using ReportLab.
"""

import io
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT


CHANCE_COLORS = {
    "Safe":      colors.HexColor("#22c55e"),
    "Moderate":  colors.HexColor("#f59e0b"),
    "Ambitious": colors.HexColor("#ef4444"),
    "Unknown":   colors.HexColor("#94a3b8"),
}

BRAND_BLUE   = colors.HexColor("#1e40af")
BRAND_ORANGE = colors.HexColor("#f97316")
LIGHT_BLUE   = colors.HexColor("#dbeafe")
LIGHT_GRAY   = colors.HexColor("#f8fafc")
MID_GRAY     = colors.HexColor("#e2e8f0")


def generate_pdf(results, input_summary, exam_type):
    """
    Returns a BytesIO buffer with the PDF content.
    results: list of result dicts from predictor
    input_summary: dict with user inputs
    exam_type: string
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    story  = []

    # ── Header ──────────────────────────────────────────────────────────────
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=BRAND_BLUE,
        alignment=TA_CENTER,
        spaceAfter=2,
        fontName="Helvetica-Bold",
    )
    sub_style = ParagraphStyle(
        "Sub",
        parent=styles["Normal"],
        fontSize=10,
        textColor=BRAND_ORANGE,
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    info_style = ParagraphStyle(
        "Info",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#374151"),
        alignment=TA_LEFT,
        spaceAfter=4,
    )

    story.append(Paragraph("🎓 ADMISSION GURU", title_style))
    story.append(Paragraph("Your Personalized College Preference List", sub_style))
    story.append(HRFlowable(width="100%", thickness=2, color=BRAND_BLUE))
    story.append(Spacer(1, 0.3 * cm))

    # ── Input Summary ────────────────────────────────────────────────────────
    story.append(Paragraph("<b>Input Summary</b>", ParagraphStyle(
        "SectionHead", parent=styles["Normal"],
        fontSize=11, textColor=BRAND_BLUE, fontName="Helvetica-Bold", spaceAfter=4
    )))

    summary_data = [
        ["Exam Type",    exam_type],
        ["Generated On", datetime.datetime.now().strftime("%d %B %Y, %I:%M %p")],
    ]
    for k, v in input_summary.items():
        if v:
            summary_data.append([k.replace("_", " ").title(), str(v)])

    summary_table = Table(summary_data, colWidths=[5 * cm, 12 * cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (0, -1), LIGHT_BLUE),
        ("TEXTCOLOR",   (0, 0), (0, -1), BRAND_BLUE),
        ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_GRAY, colors.white]),
        ("GRID",        (0, 0), (-1, -1), 0.5, MID_GRAY),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.4 * cm))

    # ── Results count ────────────────────────────────────────────────────────
    story.append(Paragraph(
        f"<b>College Preference List</b> — {len(results)} colleges found",
        ParagraphStyle("SectionHead2", parent=styles["Normal"],
                       fontSize=11, textColor=BRAND_BLUE, fontName="Helvetica-Bold", spaceAfter=6)
    ))

    if not results:
        story.append(Paragraph(
            "No colleges found matching your criteria. Try adjusting your inputs.",
            info_style
        ))
    else:
        # Table header
        headers = ["#", "College Name", "Branch", "Category", "Cutoff %", "Cutoff Rank", "Type", "Chance"]
        col_widths = [0.7*cm, 5.5*cm, 3.5*cm, 2.5*cm, 1.5*cm, 1.8*cm, 2.3*cm, 1.8*cm]

        table_data = [headers]
        for idx, r in enumerate(results, 1):
            chance = r.get("chance", "")
            table_data.append([
                str(idx),
                r.get("college_name", ""),
                r.get("branch_name", ""),
                r.get("category", ""),
                r.get("cutoff_percentile", ""),
                r.get("cutoff_rank", ""),
                r.get("college_type", ""),
                chance,
            ])

        results_table = Table(table_data, colWidths=col_widths, repeatRows=1)

        # Base styles
        ts = [
            ("BACKGROUND",   (0, 0), (-1, 0),  BRAND_BLUE),
            ("TEXTCOLOR",    (0, 0), (-1, 0),  colors.white),
            ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, 0),  7),
            ("ALIGN",        (0, 0), (-1, 0),  "CENTER"),
            ("FONTSIZE",     (0, 1), (-1, -1), 6.5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
            ("GRID",         (0, 0), (-1, -1), 0.3, MID_GRAY),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",   (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
            ("WORDWRAP",     (0, 0), (-1, -1), True),
        ]

        # Color chance column
        chance_col = 7
        for i, r in enumerate(results, 1):
            c = r.get("chance", "Unknown")
            color = CHANCE_COLORS.get(c, colors.white)
            ts.append(("BACKGROUND", (chance_col, i), (chance_col, i), color))
            ts.append(("TEXTCOLOR",  (chance_col, i), (chance_col, i), colors.white))
            ts.append(("FONTNAME",   (chance_col, i), (chance_col, i), "Helvetica-Bold"))
            ts.append(("ALIGN",      (chance_col, i), (chance_col, i), "CENTER"))

        results_table.setStyle(TableStyle(ts))
        story.append(results_table)

    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=MID_GRAY))

    # ── Footer ───────────────────────────────────────────────────────────────
    footer_style = ParagraphStyle(
        "Footer", parent=styles["Normal"],
        fontSize=7, textColor=colors.HexColor("#94a3b8"), alignment=TA_CENTER
    )
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        "Generated by Admission Guru • Cutoff data sourced from Maharashtra State CET Cell & DTE • "
        "For reference only — verify with official sources before applying.",
        footer_style
    ))

    doc.build(story)
    buf.seek(0)
    return buf
