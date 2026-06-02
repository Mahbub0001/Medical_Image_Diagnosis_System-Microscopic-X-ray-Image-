from pathlib import Path
from datetime import datetime
from ..core.config import settings

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER


def generate_text_report(prediction: dict, patient_name: str = "User") -> str:
    report_dir = Path(settings.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    report_path = report_dir / f"report_{timestamp}.pdf"

    # ---- Colour Palette ----
    primary_color = HexColor("#7c3aed")
    dark_bg = HexColor("#1e293b")
    text_color = HexColor("#1e293b")
    muted_color = HexColor("#64748b")
    white = HexColor("#ffffff")
    danger_color = HexColor("#dc2626")
    success_color = HexColor("#059669")

    # ---- Styles ----
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=22,
        leading=26,
        textColor=primary_color,
        alignment=TA_CENTER,
        spaceAfter=4 * mm,
    )

    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=muted_color,
        alignment=TA_CENTER,
        spaceAfter=8 * mm,
    )

    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        textColor=primary_color,
        spaceBefore=6 * mm,
        spaceAfter=3 * mm,
    )

    body_style = ParagraphStyle(
        "BodyText2",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=text_color,
    )

    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=muted_color,
        alignment=TA_CENTER,
        spaceBefore=10 * mm,
    )

    # ---- Build PDF Elements ----
    elements = []

    # Title Block
    elements.append(Paragraph("BloodDetect AI — Diagnostic Report", title_style))
    elements.append(Paragraph(
        f"Generated on {datetime.utcnow().strftime('%B %d, %Y at %H:%M:%S')} UTC",
        subtitle_style
    ))

    # Separator line via a thin table
    sep_table = Table([[""]],  colWidths=[170 * mm])
    sep_table.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 1, primary_color),
    ]))
    elements.append(sep_table)
    elements.append(Spacer(1, 6 * mm))

    # Patient Information Section
    elements.append(Paragraph("Patient Information", heading_style))
    patient_data = [
        ["Patient Name", patient_name],
        ["Report ID", f"RPT-{timestamp}"],
        ["Analysis Date", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")],
    ]
    patient_table = Table(patient_data, colWidths=[55 * mm, 115 * mm])
    patient_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), muted_color),
        ("TEXTCOLOR", (1, 0), (1, -1), text_color),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, HexColor("#e2e8f0")),
    ]))
    elements.append(patient_table)

    # Diagnosis Result Section
    elements.append(Paragraph("Diagnosis Result", heading_style))

    risk = prediction.get("risk_level", "")
    risk_color = danger_color if "High" in risk else (
        HexColor("#d97706") if "Moderate" in risk else success_color
    )

    diagnosis_data = [
        ["Diagnostic Category", prediction.get("predicted_disease", "N/A")],
        ["Predicted Classification", prediction.get("predicted_class", "N/A")],
        ["Model Confidence", f"{prediction.get('confidence', 0):.4f}  ({prediction.get('confidence', 0) * 100:.2f}%)"],
        ["Certainty Level", prediction.get("certainty", "N/A")],
        ["Risk Assessment", risk],
    ]
    diag_table = Table(diagnosis_data, colWidths=[55 * mm, 115 * mm])
    diag_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), muted_color),
        ("TEXTCOLOR", (1, 0), (1, -1), text_color),
        ("TEXTCOLOR", (1, 4), (1, 4), risk_color),
        ("FONTNAME", (1, 4), (1, 4), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, HexColor("#e2e8f0")),
    ]))
    elements.append(diag_table)

    # Class Probability Breakdown
    probabilities = prediction.get("probabilities", {})
    if probabilities:
        elements.append(Paragraph("Class Probability Breakdown", heading_style))
        prob_rows = [["Class Label", "Probability"]]
        for cls_name, prob_val in probabilities.items():
            prob_rows.append([cls_name, f"{prob_val * 100:.2f}%"])

        prob_table = Table(prob_rows, colWidths=[85 * mm, 85 * mm])
        prob_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("BACKGROUND", (0, 0), (-1, 0), primary_color),
            ("TEXTCOLOR", (0, 1), (-1, -1), text_color),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, HexColor("#e2e8f0")),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ]))
        elements.append(prob_table)

    # Clinical Suggestion
    elements.append(Paragraph("Clinical Suggestion", heading_style))
    elements.append(Paragraph(
        prediction.get("suggestion", "No suggestion available."),
        body_style
    ))

    # Disclaimer
    elements.append(Spacer(1, 10 * mm))
    sep_table2 = Table([[""]],  colWidths=[170 * mm])
    sep_table2.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
    ]))
    elements.append(sep_table2)
    elements.append(Paragraph(
        "⚠ DISCLAIMER: This report is generated by an AI-based prototype system "
        "intended for academic and educational purposes only. It should NOT be used "
        "as a substitute for professional medical diagnosis. Please consult a qualified "
        "healthcare provider for clinical decisions.",
        disclaimer_style
    ))

    # ---- Generate the PDF ----
    doc = SimpleDocTemplate(
        str(report_path),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )
    doc.build(elements)

    return str(report_path)
