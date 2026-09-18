import uuid
import httpx
from pathlib import Path
from datetime import datetime
from ..core.config import settings

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, Color
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, Image as RLImage
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame


def _get_heatmap_flowable(heatmap_ref: str, width_mm: float = 160):
    """
    Safely resolves a local heatmap path or downloads remote URL into temporary file
    and returns a ReportLab Image Flowable with preserved 3:1 aspect ratio.
    """
    if not heatmap_ref:
        return None
    try:
        heatmap_str = str(heatmap_ref).strip()
        local_path = None

        # 1. Direct path check
        p = Path(heatmap_str)
        if p.exists() and p.is_file():
            local_path = p

        # 2. Check in settings.heatmap_dir by filename
        if not local_path:
            clean_name = p.name.split("?")[0]
            candidate = Path(settings.heatmap_dir) / clean_name
            if candidate.exists() and candidate.is_file():
                local_path = candidate

        # 3. Check in storage/heatmaps
        if not local_path:
            clean_name = p.name.split("?")[0]
            candidate2 = Path("storage/heatmaps") / clean_name
            if candidate2.exists() and candidate2.is_file():
                local_path = candidate2

        # 4. If remote URL (e.g. Cloudinary), download temporarily
        if not local_path and (heatmap_str.startswith("http://") or heatmap_str.startswith("https://")):
            try:
                r = httpx.get(heatmap_str, timeout=8.0, follow_redirects=True)
                if r.status_code == 200:
                    tmp_hm = Path(settings.heatmap_dir) / f"tmp_pdf_{uuid.uuid4().hex}.png"
                    tmp_hm.parent.mkdir(parents=True, exist_ok=True)
                    with open(tmp_hm, "wb") as f:
                        f.write(r.content)
                    local_path = tmp_hm
            except Exception as ex:
                print(f"Notice: Failed to fetch remote heatmap for PDF: {ex}")

        if local_path and Path(local_path).exists():
            # Grad-CAM 3-panel figure has aspect ratio 15:5 = 3:1
            return RLImage(str(local_path), width=width_mm * mm, height=(width_mm / 3.0) * mm)
    except Exception as e:
        print(f"Notice: Failed to embed heatmap in PDF: {e}")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Shared colour palette
# ─────────────────────────────────────────────────────────────────────────────
C_PRIMARY    = HexColor("#5b21b6")   # deep violet
C_PRIMARY_LT = HexColor("#7c3aed")
C_ACCENT     = HexColor("#0ea5e9")   # sky blue accent
C_DARK       = HexColor("#0f172a")
C_TEXT       = HexColor("#1e293b")
C_MUTED      = HexColor("#64748b")
C_BORDER     = HexColor("#e2e8f0")
C_ROW_ALT    = HexColor("#f8fafc")
C_WHITE      = HexColor("#ffffff")
C_DANGER     = HexColor("#dc2626")
C_WARNING    = HexColor("#d97706")
C_SUCCESS    = HexColor("#059669")
C_INFO       = HexColor("#0ea5e9")
C_HEADER_BG  = HexColor("#0f172a")

DISEASE_COLORS = {
    "Anemia":   HexColor("#ef4444"),
    "Malaria":  HexColor("#f59e0b"),
    "Leukemia": HexColor("#8b5cf6"),
}


def _risk_color(risk: str) -> HexColor:
    if "High"     in risk: return C_DANGER
    if "Moderate" in risk: return C_WARNING
    if "Review"   in risk: return C_INFO
    return C_SUCCESS


def _risk_priority(risk: str) -> int:
    return {"High Risk": 3, "Moderate Risk": 2, "Review Needed": 1}.get(risk, 0)


# ─────────────────────────────────────────────────────────────────────────────
# Page canvas callback — header band + footer
# ─────────────────────────────────────────────────────────────────────────────
def _make_page_decorator(report_id: str, report_type: str = "Diagnostic Report"):
    """Returns an onPage callback that draws the header and footer on every page."""

    def _on_page(cv: pdfcanvas.Canvas, doc):
        W, H = A4

        # ── Dark header band ──────────────────────────────────────────────────
        cv.saveState()
        cv.setFillColor(C_HEADER_BG)
        cv.rect(0, H - 28 * mm, W, 28 * mm, fill=1, stroke=0)

        # Brand name (left)
        cv.setFont("Helvetica-Bold", 14)
        cv.setFillColor(C_WHITE)
        cv.drawString(20 * mm, H - 14 * mm, "BioLens")

        # Subtitle (left, smaller)
        cv.setFont("Helvetica", 8)
        cv.setFillColor(HexColor("#94a3b8"))
        cv.drawString(20 * mm, H - 20 * mm, "AI-Powered Hematology Analysis Platform")

        # Report type (centre)
        cv.setFont("Helvetica-Bold", 10)
        cv.setFillColor(HexColor("#c4b5fd"))
        text_w = cv.stringWidth(report_type, "Helvetica-Bold", 10)
        cv.drawString((W - text_w) / 2, H - 16 * mm, report_type)

        # Report ID (right)
        cv.setFont("Helvetica", 7.5)
        cv.setFillColor(HexColor("#94a3b8"))
        id_text = f"Report ID: {report_id}"
        cv.drawRightString(W - 20 * mm, H - 14 * mm, id_text)

        date_text = datetime.utcnow().strftime("%d %b %Y, %H:%M UTC")
        cv.drawRightString(W - 20 * mm, H - 20 * mm, date_text)

        # Thin violet accent line below header
        cv.setStrokeColor(C_PRIMARY_LT)
        cv.setLineWidth(1.5)
        cv.line(0, H - 28 * mm, W, H - 28 * mm)

        # ── Footer ────────────────────────────────────────────────────────────
        cv.setStrokeColor(C_BORDER)
        cv.setLineWidth(0.5)
        cv.line(20 * mm, 14 * mm, W - 20 * mm, 14 * mm)

        cv.setFont("Helvetica", 7.5)
        cv.setFillColor(C_MUTED)
        cv.drawString(20 * mm, 9 * mm, "BioLens Automated Diagnostic System — Confidential Medical Report")
        cv.drawRightString(W - 20 * mm, 9 * mm, f"Page {doc.page}")

        cv.restoreState()

    return _on_page


# ─────────────────────────────────────────────────────────────────────────────
# Shared style builders
# ─────────────────────────────────────────────────────────────────────────────
def _make_styles():
    base = getSampleStyleSheet()
    return {
        "section_heading": ParagraphStyle(
            "SH", parent=base["Normal"],
            fontSize=9, fontName="Helvetica-Bold",
            textColor=C_MUTED,
            spaceBefore=6 * mm, spaceAfter=2 * mm,
            leading=12,
        ),
        "body": ParagraphStyle(
            "BD", parent=base["Normal"],
            fontSize=10, fontName="Helvetica",
            textColor=C_TEXT, leading=15,
        ),
        "body_small": ParagraphStyle(
            "BDS", parent=base["Normal"],
            fontSize=8.5, fontName="Helvetica",
            textColor=C_MUTED, leading=12,
        ),
        "label": ParagraphStyle(
            "LB", parent=base["Normal"],
            fontSize=10, fontName="Helvetica-Bold",
            textColor=C_TEXT, leading=14,
        ),
        "disclaimer": ParagraphStyle(
            "DI", parent=base["Normal"],
            fontSize=7.5, fontName="Helvetica",
            textColor=C_MUTED, leading=11,
            alignment=TA_CENTER, spaceBefore=4 * mm,
        ),
        "risk_normal": ParagraphStyle(
            "RN", parent=base["Normal"],
            fontSize=10, fontName="Helvetica-Bold",
            textColor=C_TEXT, leading=14,
        ),
    }


def _sep(color=C_BORDER, thickness=0.5, width="100%"):
    return HRFlowable(width=width, thickness=thickness,
                      color=color, spaceAfter=0, spaceBefore=0)


def _section_label(text, styles):
    return [
        Paragraph(text.upper(), styles["section_heading"]),
        _sep(C_PRIMARY, 1.5),
        Spacer(1, 3 * mm),
    ]


def _two_col_table(rows, col_w=(60, 110), alt_bg=True):
    """Two-column key-value table with alternating row backgrounds."""
    style_cmds = [
        ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",      (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 0), (-1, -1), 10),
        ("TEXTCOLOR",     (0, 0), (0, -1), C_MUTED),
        ("TEXTCOLOR",     (1, 0), (1, -1), C_TEXT),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("LINEBELOW",     (0, 0), (-1, -2), 0.4, C_BORDER),
    ]
    if alt_bg:
        for i in range(0, len(rows), 2):
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), C_ROW_ALT))
    t = Table(rows, colWidths=[w * mm for w in col_w])
    t.setStyle(TableStyle(style_cmds))
    return t


def _risk_badge_table(risk: str):
    """A full-width coloured risk-level banner."""
    rc = _risk_color(risk)
    light = HexColor(rc.hexval().replace("#", "") if hasattr(rc, "hexval") else "#dc2626")
    # Create a tinted background (10% opacity simulation via a near-white tint)
    tint_map = {
        C_DANGER:  HexColor("#fef2f2"),
        C_WARNING: HexColor("#fffbeb"),
        C_INFO:    HexColor("#f0f9ff"),
        C_SUCCESS: HexColor("#f0fdf4"),
    }
    bg = tint_map.get(rc, HexColor("#f8fafc"))
    risk_label = Paragraph(
        f'<font color="{rc.hexval() if hasattr(rc, "hexval") else "#dc2626"}">'
        f'<b>&#9632; {risk}</b></font>',
        ParagraphStyle("RB", fontSize=11, fontName="Helvetica-Bold",
                       leading=14, textColor=rc)
    )
    t = Table([[risk_label]], colWidths=[170 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), bg),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("LINEBEFORE",    (0, 0), (0, -1), 4, rc),
        ("ROUNDEDCORNERS", [4]),
    ]))
    return t


def _prob_table(probabilities: dict, accent=C_PRIMARY):
    """Probability breakdown table with a header row."""
    rows = [["Classification", "Confidence Score"]]
    sorted_probs = sorted(probabilities.items(), key=lambda x: x[1], reverse=True)
    for cls_name, prob_val in sorted_probs:
        rows.append([cls_name, f"{prob_val * 100:.2f} %"])

    style_cmds = [
        # Header
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0),  9),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  C_WHITE),
        ("BACKGROUND",    (0, 0), (-1, 0),  accent),
        ("TOPPADDING",    (0, 0), (-1, 0),  8),
        ("BOTTOMPADDING", (0, 0), (-1, 0),  8),
        ("LEFTPADDING",   (0, 0), (-1, 0),  10),
        # Data rows
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), 9.5),
        ("TEXTCOLOR",     (0, 1), (-1, -1), C_TEXT),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 7),
        ("TOPPADDING",    (0, 1), (-1, -1), 7),
        ("LEFTPADDING",   (0, 1), (-1, -1), 10),
        ("ALIGN",         (1, 0), (1, -1),  "RIGHT"),
        ("RIGHTPADDING",  (1, 0), (1, -1),  10),
        ("LINEBELOW",     (0, 0), (-1, -2), 0.4, C_BORDER),
        # Highlight top row (predicted)
        ("BACKGROUND",    (0, 1), (-1, 1),  HexColor("#f5f3ff")),
        ("FONTNAME",      (0, 1), (-1, 1),  "Helvetica-Bold"),
        ("TEXTCOLOR",     (1, 1), (1, 1),   accent),
    ]
    # Alternate bg for remaining rows
    for i in range(2, len(rows), 2):
        style_cmds.append(("BACKGROUND", (0, i), (-1, i), C_ROW_ALT))

    t = Table(rows, colWidths=[110 * mm, 60 * mm])
    t.setStyle(TableStyle(style_cmds))
    return t


def _disclaimer_block(styles):
    return [
        Spacer(1, 6 * mm),
        _sep(C_BORDER, 0.5),
        Spacer(1, 3 * mm),
        Paragraph(
            "BioLens Automated Hematology Diagnostic System  |  Clinical Record  |  Confidential",
            ParagraphStyle("DF2", fontSize=7.5, fontName="Helvetica-Bold",
                           textColor=HexColor("#94a3b8"), alignment=TA_CENTER,
                           spaceBefore=2 * mm),
        ),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Single-disease report
# ─────────────────────────────────────────────────────────────────────────────
def generate_text_report(
    prediction: dict,
    patient_name: str = "User",
    phone_number: str = "N/A",
) -> str:
    report_dir = Path(settings.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp    = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report_id    = f"RPT-{timestamp}"
    report_path  = report_dir / f"report_{timestamp}.pdf"

    styles = _make_styles()
    on_page = _make_page_decorator(report_id, "Diagnostic Report")

    elements = []
    elements.append(Spacer(1, 2 * mm))   # breathing room below header band

    # ── Patient Information ──────────────────────────────────────────────────
    elements.extend(_section_label("Patient Information", styles))
    patient_rows = [
        ["Patient Name",   patient_name],
        ["Phone / Patient ID", phone_number or "N/A"],
        ["Report Reference",   report_id],
        ["Analysis Date",  datetime.utcnow().strftime("%d %B %Y, %H:%M UTC")],
    ]
    elements.append(_two_col_table(patient_rows))
    elements.append(Spacer(1, 5 * mm))

    # ── Diagnosis Result ─────────────────────────────────────────────────────
    elements.extend(_section_label("Diagnosis Result", styles))

    risk = prediction.get("risk_level", "")
    diag_rows = [
        ["Diagnostic Category",      prediction.get("predicted_disease", "N/A")],
        ["Predicted Classification", prediction.get("predicted_class",   "N/A")],
        ["Model Confidence",
         f"{prediction.get('confidence', 0) * 100:.2f}%  "
         f"(raw: {prediction.get('confidence', 0):.4f})"],
        ["Certainty Level",          prediction.get("certainty", "N/A")],
    ]
    elements.append(_two_col_table(diag_rows))
    elements.append(Spacer(1, 4 * mm))
    elements.append(_risk_badge_table(risk))
    elements.append(Spacer(1, 5 * mm))

    # ── Class Probability Breakdown ──────────────────────────────────────────
    probabilities = prediction.get("probabilities", {})
    if probabilities:
        elements.extend(_section_label("Class Probability Breakdown", styles))
        elements.append(_prob_table(probabilities))
        elements.append(Spacer(1, 5 * mm))

    # ── Explainable AI (Grad-CAM Neural Activation Map) ──────────────────────
    heatmap_ref = prediction.get("heatmap_path") or prediction.get("heatmap_url")
    hm_flowable = _get_heatmap_flowable(heatmap_ref, width_mm=165)
    if hm_flowable:
        elements.extend(_section_label("Explainable AI — Neural Activation Map (Grad-CAM)", styles))
        caption = Paragraph(
            "<b>Visual Heatmap Analysis:</b> Input Smear &nbsp;|&nbsp; Activation &nbsp;|&nbsp; Overlay",
            styles["body_small"]
        )
        hm_table = Table([[hm_flowable], [caption]], colWidths=[170 * mm])
        hm_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C_ROW_ALT),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
            ("LINEBELOW",     (0, 0), (-1, -1), 0.5, C_BORDER),
        ]))
        elements.append(KeepTogether([hm_table]))
        elements.append(Spacer(1, 5 * mm))

    # ── Clinical Recommendation ──────────────────────────────────────────────
    elements.extend(_section_label("Clinical Recommendation", styles))
    suggestion = prediction.get("suggestion", "No suggestion available.")
    sug_table = Table([[suggestion]], colWidths=[170 * mm])
    sug_table.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 0), (-1, -1), 10),
        ("TEXTCOLOR",     (0, 0), (-1, -1), C_TEXT),
        ("BACKGROUND",    (0, 0), (-1, -1), C_ROW_ALT),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("LINEBEFORE",    (0, 0), (0, -1), 4, C_PRIMARY_LT),
    ]))
    elements.append(sug_table)

    # ── Disclaimer ───────────────────────────────────────────────────────────
    elements.extend(_disclaimer_block(styles))

    # ── Build PDF ────────────────────────────────────────────────────────────
    doc = SimpleDocTemplate(
        str(report_path),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=34 * mm,   # leave room for header band
        bottomMargin=22 * mm,
    )
    doc.build(elements, onFirstPage=on_page, onLaterPages=on_page)
    return str(report_path)


# ─────────────────────────────────────────────────────────────────────────────
# Combined multi-disease report (Comprehensive Blood Panel)
# ─────────────────────────────────────────────────────────────────────────────
def generate_combined_report(
    findings: list,
    patient_name: str = "User",
    phone_number: str = "N/A",
) -> str:
    report_dir = Path(settings.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp   = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report_id   = f"COMB-{timestamp}"
    report_path = report_dir / f"combined_report_{timestamp}.pdf"

    styles  = _make_styles()
    on_page = _make_page_decorator(report_id, "Comprehensive Hematology Report")

    # ── Overall metrics ───────────────────────────────────────────────────────
    positive_labels = {"Parasitized", "Anemic", "Early", "Pre", "Pro"}
    positive_count  = sum(
        1 for f in findings if f.get("predicted_class", "") in positive_labels
    )
    overall_risk = max(
        (f.get("risk_level", "Low Risk") for f in findings),
        key=_risk_priority, default="Low Risk",
    )
    overall_risk_color = _risk_color(overall_risk)

    elements = []
    elements.append(Spacer(1, 2 * mm))

    # ── Patient Information ───────────────────────────────────────────────────
    elements.extend(_section_label("Patient Information", styles))
    patient_rows = [
        ["Patient Name",       patient_name],
        ["Phone / Patient ID", phone_number or "N/A"],
        ["Report Reference",   report_id],
        ["Analysis Date",      datetime.utcnow().strftime("%d %B %Y, %H:%M UTC")],
    ]
    elements.append(_two_col_table(patient_rows))
    elements.append(Spacer(1, 5 * mm))

    # ── Executive Summary ─────────────────────────────────────────────────────
    elements.extend(_section_label("Executive Summary", styles))

    # Build a 4-cell summary card row
    def _summary_cell(label, value, value_color=C_TEXT):
        return (
            Paragraph(f'<font color="#64748b"><b>{label}</b></font>',
                      ParagraphStyle("SC_L", fontSize=8, leading=10,
                                     fontName="Helvetica-Bold")),
            Paragraph(f'<font color="{value_color.hexval() if hasattr(value_color,"hexval") else "#1e293b"}">'
                      f'<b>{value}</b></font>',
                      ParagraphStyle("SC_V", fontSize=14, leading=17,
                                     fontName="Helvetica-Bold")),
        )

    def _clean_label(f, idx=0):
        lbl = f.get("test_label") or f.get("predicted_disease") or f"Test {idx+1}"
        if "[" in lbl or "]" in lbl or "Comprehensive" in lbl:
            lbl = f.get("predicted_disease") or lbl.replace("[", "").replace("]", "").replace("Comprehensive Panel", "").replace("|", "").strip()
        return lbl or f"Test {idx+1}"

    screened   = " | ".join(
        _clean_label(f, i) for i, f in enumerate(findings)
    )
    pos_str    = f"{positive_count} / {len(findings)}"
    pos_color  = C_DANGER if positive_count > 0 else C_SUCCESS

    summary_inner = [
        [
            _make_stat_cell("Tests Conducted", str(len(findings)), C_PRIMARY_LT),
            _make_stat_cell("Positive Findings", pos_str, pos_color),
            _make_stat_cell("Overall Risk", overall_risk, overall_risk_color),
        ]
    ]
    summary_t = Table(summary_inner, colWidths=[56 * mm, 57 * mm, 57 * mm])
    summary_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_ROW_ALT),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("LINEAFTER",     (0, 0), (1, -1),  0.5, C_BORDER),
        ("ROUNDEDCORNERS", [6]),
    ]))
    elements.append(summary_t)
    elements.append(Spacer(1, 3 * mm))

    # Screened diseases sub-row
    screened_t = Table(
        [[Paragraph(f"Diseases screened: <b>{screened}</b>",
                    ParagraphStyle("SC", fontSize=9, fontName="Helvetica",
                                   textColor=C_MUTED, leading=12))]],
        colWidths=[170 * mm]
    )
    screened_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), HexColor("#f1f5f9")),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
    ]))
    elements.append(screened_t)
    elements.append(Spacer(1, 6 * mm))

    # ── Per-Disease Panels ────────────────────────────────────────────────────
    elements.extend(_section_label("Detailed Diagnostic Findings", styles))

    for idx, finding in enumerate(findings):
        label   = _clean_label(finding, idx)
        d_color = DISEASE_COLORS.get(label, C_PRIMARY)
        risk    = finding.get("risk_level", "N/A")
        rc      = _risk_color(risk)
        pred_cls= finding.get("predicted_class", "N/A")
        conf    = finding.get("confidence", 0)

        # Panel title bar
        panel_title = Table(
            [[Paragraph(
                f'<font color="white"><b>Panel {idx+1} — {label} Screening</b></font>',
                ParagraphStyle("PT", fontSize=11, fontName="Helvetica-Bold",
                               leading=14, textColor=C_WHITE)
            )]],
            colWidths=[170 * mm]
        )
        panel_title.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), d_color),
            ("TOPPADDING",    (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ]))

        # Key result row (3 cards: class | confidence | risk)
        result_row = Table(
            [[
                _make_stat_cell("Classification", pred_cls, d_color),
                _make_stat_cell("Confidence",     f"{conf*100:.1f}%", C_TEXT),
                _make_stat_cell("Risk Level",     risk, rc),
            ]],
            colWidths=[56 * mm, 57 * mm, 57 * mm]
        )
        result_row.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C_ROW_ALT),
            ("TOPPADDING",    (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING",   (0, 0), (-1, -1), 14),
            ("LINEAFTER",     (0, 0), (1, -1),  0.5, C_BORDER),
        ]))

        panel_block = [
            panel_title,
            Spacer(1, 2 * mm),
            result_row,
        ]

        # Full detail sub-table
        detail_rows = [
            ["Disease Category",     finding.get("predicted_disease", "N/A")],
            ["Model Confidence",
             f"{conf*100:.2f}%  (raw: {conf:.4f})"],
            ["Certainty Level",      finding.get("certainty", "N/A")],
        ]
        panel_block.append(Spacer(1, 2 * mm))
        panel_block.append(_two_col_table(detail_rows))

        # Probability breakdown
        probs = finding.get("probabilities", {})
        if probs:
            panel_block.append(Spacer(1, 3 * mm))
            panel_block.append(Paragraph(
                "CLASS PROBABILITY BREAKDOWN",
                ParagraphStyle("PBL", fontSize=8, fontName="Helvetica-Bold",
                               textColor=C_MUTED, leading=11, spaceBefore=2 * mm)
            ))
            panel_block.append(Spacer(1, 1 * mm))
            panel_block.append(_prob_table(probs, accent=d_color))

        # Embedded Grad-CAM Heatmap
        hm_ref = finding.get("heatmap_path") or finding.get("heatmap_url")
        hm_img = _get_heatmap_flowable(hm_ref, width_mm=155)
        if hm_img:
            panel_block.append(Spacer(1, 3 * mm))
            panel_block.append(Paragraph(
                "EXPLAINABLE AI — GRAD-CAM ACTIVATION MAP",
                ParagraphStyle("GH", fontSize=8, fontName="Helvetica-Bold",
                               textColor=C_MUTED, leading=11, spaceBefore=2 * mm)
            ))
            panel_block.append(Spacer(1, 1 * mm))
            hm_wrap = Table([[hm_img]], colWidths=[170 * mm])
            hm_wrap.setStyle(TableStyle([
                ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
                ("BACKGROUND",    (0, 0), (-1, -1), C_ROW_ALT),
                ("TOPPADDING",    (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING",   (0, 0), (-1, -1), 6),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
                ("LINEBELOW",     (0, 0), (-1, -1), 0.5, C_BORDER),
            ]))
            panel_block.append(hm_wrap)

        # Clinical suggestion
        sug = finding.get("suggestion", "")
        if sug:
            panel_block.append(Spacer(1, 3 * mm))
            sug_t = Table([[sug]], colWidths=[170 * mm])
            sug_t.setStyle(TableStyle([
                ("FONTNAME",      (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE",      (0, 0), (-1, -1), 9.5),
                ("TEXTCOLOR",     (0, 0), (-1, -1), C_TEXT),
                ("BACKGROUND",    (0, 0), (-1, -1), C_ROW_ALT),
                ("TOPPADDING",    (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("LEFTPADDING",   (0, 0), (-1, -1), 12),
                ("LINEBEFORE",    (0, 0), (0, -1), 3, d_color),
            ]))
            panel_block.append(sug_t)

        panel_block.append(Spacer(1, 6 * mm))
        elements.append(KeepTogether(panel_block))

    # ── Combined Clinical Recommendation ─────────────────────────────────────
    elements.extend(_section_label("Combined Clinical Recommendation", styles))
    elements.append(_risk_badge_table(overall_risk))
    elements.append(Spacer(1, 3 * mm))

    if "High Risk" in overall_risk:
        overall_note = (
            "One or more findings indicate HIGH RISK status. Immediate consultation "
            "with a qualified hematologist or physician is strongly advised. Do not "
            "delay seeking professional medical evaluation."
        )
    elif "Moderate" in overall_risk or "Review" in overall_risk:
        overall_note = (
            "The panel results include findings that require further clinical evaluation. "
            "Please schedule a follow-up appointment with a healthcare professional at "
            "the earliest opportunity."
        )
    else:
        overall_note = (
            "All screened panels returned low-risk findings. The results appear within "
            "normal ranges for the tested parameters. Routine follow-up with a clinician "
            "is still recommended for comprehensive clinical confirmation."
        )

    note_t = Table([[overall_note]], colWidths=[170 * mm])
    note_t.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 0), (-1, -1), 10),
        ("TEXTCOLOR",     (0, 0), (-1, -1), C_TEXT),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("LINEBEFORE",    (0, 0), (0, -1), 4, C_PRIMARY_LT),
    ]))
    elements.append(note_t)

    # Individual per-test suggestions
    elements.append(Spacer(1, 3 * mm))
    for idx, f in enumerate(findings):
        label = _clean_label(f, idx)
        sug   = f.get("suggestion", "")
        if sug and label:
            elements.append(Paragraph(
                f"<b>{label}:</b>  {sug}",
                ParagraphStyle("IS", fontSize=9, fontName="Helvetica",
                               textColor=C_TEXT, leading=13, spaceBefore=2 * mm,
                               leftIndent=8 * mm),
            ))

    # ── Disclaimer ────────────────────────────────────────────────────────────
    elements.extend(_disclaimer_block(styles))

    # ── Build PDF ─────────────────────────────────────────────────────────────
    doc = SimpleDocTemplate(
        str(report_path),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=34 * mm,
        bottomMargin=22 * mm,
    )
    doc.build(elements, onFirstPage=on_page, onLaterPages=on_page)
    return str(report_path)


# ─────────────────────────────────────────────────────────────────────────────
# Helper — stat cell for summary / result cards
# ─────────────────────────────────────────────────────────────────────────────
def _make_stat_cell(label: str, value: str, value_color: HexColor = C_TEXT):
    """Returns a (label on top, big value below) pair of Paragraphs in a list."""
    return [
        Paragraph(
            label.upper(),
            ParagraphStyle("SCL", fontSize=7.5, fontName="Helvetica-Bold",
                           textColor=C_MUTED, leading=10, spaceAfter=3),
        ),
        Paragraph(
            value,
            ParagraphStyle("SCV", fontSize=13, fontName="Helvetica-Bold",
                           textColor=value_color, leading=16),
        ),
    ]
