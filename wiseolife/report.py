"""WiseOLife - PDF (ReportLab) and CSV report generation. Everything is built in memory."""
import csv
import io
import os
from datetime import datetime
from xml.sax.saxutils import escape

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate,  # noqa: E402
                                Spacer, Table, TableStyle)

from . import config  # noqa: E402

NAVY = colors.HexColor("#1e1b4b")
PURPLE = colors.HexColor("#6d28d9")
LIGHT = colors.HexColor("#eef2ff")
RISK_RL = {"LOW": colors.HexColor("#10b981"), "MEDIUM": colors.HexColor("#f59e0b"),
           "HIGH": colors.HexColor("#ef4444")}


def report_filename(candidate_id):
    return f"WiseOLife_Report_{candidate_id}_{datetime.now().strftime('%Y%m%d')}.pdf"


def _p(text):
    """Escape text for ReportLab Paragraph markup."""
    return escape(str(text))


def _png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _scores_chart(scores):
    d, m = scores["dass"], scores["mbi"]
    items = [
        ("PSS", scores["pss"]["score"], 40), ("GAD-7", scores["gad7"]["score"], 21),
        ("PHQ-9", scores["phq9"]["score"], 27), ("DASS-D", d["depression"], 42),
        ("DASS-A", d["anxiety"], 42), ("DASS-S", d["stress"], 42),
        ("MBI-EE", m["emotional_exhaustion"], 54), ("MBI-DP", m["depersonalization"], 30),
        ("MBI-PA*", m["personal_accomplishment"], 48),
    ]
    fig, ax = plt.subplots(figsize=(7, 3.2))
    pct = [v / mx * 100 for _, v, mx in items]
    bar_colors = ["#10b981" if n == "MBI-PA*" else "#6d28d9" for n, _, _ in items]
    ax.bar([n for n, _, _ in items], pct, color=bar_colors)
    ax.set_ylim(0, 100)
    ax.set_ylabel("% of maximum")
    ax.set_title("Instrument scores (% of each maximum)  *PA: higher = better", fontsize=9)
    ax.tick_params(axis="x", labelsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    return _png(fig)


def _importance_chart(importance):
    top = list(reversed(importance))
    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.barh([r["label"] for r in top], [r["percent"] for r in top], color="#6d28d9")
    ax.set_xlabel("Importance (%)")
    ax.set_title("Random Forest feature importance (14 features)", fontsize=9)
    ax.tick_params(axis="y", labelsize=7)
    ax.spines[["top", "right"]].set_visible(False)
    return _png(fig)


def _table(rows, col_widths, header=True):
    t = Table(rows, colWidths=col_widths, repeatRows=1 if header else 0)
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                  ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    t.setStyle(TableStyle(style))
    return t


def generate_report(result, plan, importance, metrics, review, explanation):
    """Build the full PDF and return its bytes."""
    scores, pred = result["scores"], result["prediction"]
    d, m, b = scores["dass"], scores["mbi"], scores["big5"]
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], textColor=NAVY, fontSize=22, spaceAfter=2)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=PURPLE, fontSize=13, spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("body", parent=ss["BodyText"], fontSize=9.5, leading=13)
    small = ParagraphStyle("small", parent=body, fontSize=8, textColor=colors.HexColor("#475569"))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
                            topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                            title=f"{config.APP_NAME} Report {result['candidate_id']}",
                            author=config.APP_NAME)
    W = A4[0] - 3.6 * cm
    s = []

    # --- title block
    s.append(Paragraph(f"{config.APP_NAME}", h1))
    s.append(Paragraph(_p(config.APP_SUBTITLE), body))
    s.append(Paragraph(_p(config.TAGLINE), small))
    s.append(Spacer(1, 8))
    s.append(_table([
        ["Candidate ID", result["candidate_id"], "Assessment date", result["timestamp"][:16].replace("T", " ")],
        ["Source", result["source"].title(), "Questions", f"{config.TOTAL_QUESTIONS} ({config.N_INSTRUMENTS} instruments)"],
    ], [3 * cm, 5.5 * cm, 3.4 * cm, W - 11.9 * cm], header=False))
    if result["source"] == "demo":
        s.append(Paragraph("<b>DEMO DATA</b> - synthetic values used for demonstration only.", small))

    # --- AI classification
    s.append(Paragraph("AI risk classification (screening indication)", h2))
    info = config.risk_info(pred["risk"])
    risk_tbl = Table([[f"R{info['number']} · {info['name'].upper()}", f"Model confidence: {pred['confidence'] * 100:.1f}%",
                       "  ".join(f"{k}: {v * 100:.0f}%" for k, v in pred["probabilities"].items())]],
                     colWidths=[4.6 * cm, 4.6 * cm, W - 9.2 * cm])
    risk_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), RISK_RL[pred["risk"]]), ("TEXTCOLOR", (0, 0), (0, 0), colors.white),
        ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")), ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    s.append(risk_tbl)
    s.append(Spacer(1, 4))
    s.append(Paragraph(f"<b>R{info['number']} · {_p(info['name'])}:</b> {_p(info['definition'])}", body))
    s.append(Paragraph(_p(config.AI_DISCLAIMER) + " " + _p(explanation), body))

    # --- summary
    s.append(Paragraph("Assessment summary", h2))
    s.append(_table([
        ["Instrument / dimension", "Score", "Interpretation"],
        ["PSS-10 (adjusted)", f"{scores['pss']['score']} / 40", scores["pss"]["level"]],
        ["GAD-7", f"{scores['gad7']['score']} / 21", scores["gad7"]["level"]],
        ["PHQ-9", f"{scores['phq9']['score']} / 27", scores["phq9"]["level"]],
        ["DASS Depression", f"{d['depression']} / 42", d["depression_level"]],
        ["DASS Anxiety", f"{d['anxiety']} / 42", d["anxiety_level"]],
        ["DASS Stress", f"{d['stress']} / 42", d["stress_level"]],
        ["MBI Emotional Exhaustion", f"{m['emotional_exhaustion']} / 54", m["ee_level"]],
        ["MBI Depersonalization", f"{m['depersonalization']} / 30", m["dp_level"]],
        ["MBI Personal Accomplishment (higher = better)", f"{m['personal_accomplishment']} / 48", m["pa_level"]],
        ["Big Five Openness", f"{b['openness']} / 5", b["levels"]["O"]],
        ["Big Five Conscientiousness", f"{b['conscientiousness']} / 5", b["levels"]["C"]],
        ["Big Five Extraversion", f"{b['extraversion']} / 5", b["levels"]["E"]],
        ["Big Five Agreeableness", f"{b['agreeableness']} / 5", b["levels"]["A"]],
        ["Big Five Neuroticism", f"{b['neuroticism']} / 5", b["levels"]["N"]],
    ], [8.5 * cm, 3.5 * cm, W - 12 * cm]))
    s.append(Paragraph(
        f"PSS reverse-scored items (project specification): {', '.join(map(str, scores['pss']['reverse_items']))}. "
        f"DASS subscales are multiplied by {d['multiplier']}.", small))
    s.append(Spacer(1, 6))
    s.append(Image(_scores_chart(scores), width=W, height=W * 0.45))

    # --- 14 features
    s.append(PageBreak())
    s.append(Paragraph("14-Feature AI input vector", h2))
    rows = [["#", "Feature", "Value", "Range"]]
    for i, (n, v) in enumerate(zip(config.FEATURE_NAMES, result["features"]), start=1):
        lo, hi = config.FEATURE_RANGES[n]
        rows.append([i, config.FEATURE_LABELS[n], f"{v:g}", f"{lo} - {hi}"])
    s.append(_table(rows, [1 * cm, 9 * cm, 3 * cm, W - 13 * cm]))
    s.append(Spacer(1, 4))
    s.append(Paragraph("Vector: [" + ", ".join(f"{v:g}" for v in result["features"]) + "]", body))

    # --- explainability
    s.append(Paragraph("Explainable AI - feature importance", h2))
    s.append(Image(_importance_chart(importance), width=W, height=W * 0.54))
    s.append(Paragraph(
        f"Model: Random Forest ({config.RF_N_ESTIMATORS} trees, max_depth={config.RF_MAX_DEPTH}), "
        f"trained on {config.N_SYNTHETIC_RECORDS} synthetic profiles. Metrics on the synthetic held-out set "
        f"(NOT clinical accuracy): accuracy {metrics['accuracy'] * 100:.1f}%, precision {metrics['precision'] * 100:.1f}%, "
        f"recall {metrics['recall'] * 100:.1f}%, F1 {metrics['f1'] * 100:.1f}%.", small))

    # --- recommendations
    s.append(PageBreak())
    s.append(Paragraph("Personalised wellness recommendations", h2))
    if plan["safety"]:
        s.append(Paragraph("<b>Safety notice:</b> " + _p(plan["safety_message"]), body))
    for block in plan["blocks"]:
        s.append(Paragraph(f"<b>{_p(block['title'])}</b> - {_p(block['why'])}", body))
        for a in block["actions"]:
            s.append(Paragraph("&bull; " + _p(a), body))
        s.append(Spacer(1, 3))
    if plan["strengths"]:
        s.append(Paragraph("Strengths identified", h2))
        for t in plan["strengths"]:
            s.append(Paragraph("&bull; " + _p(t), body))
    s.append(Paragraph(_p(plan["disclaimer"]), small))

    # --- human review
    s.append(Paragraph("Human review (Tier 2 - simulated workflow)", h2))
    default_status = "Pending Review" if plan["review_recommended"] else "Not Required"
    r = review or {}
    s.append(_table([
        ["Review status", r.get("status", default_status)],
        ["Reviewer", r.get("reviewer") or "-"],
        ["Final decision", r.get("decision") or "-"],
        ["Notes", r.get("notes") or "-"],
    ], [4 * cm, W - 4 * cm], header=False))
    if plan["review_recommended"]:
        s.append(Paragraph("Professional review is recommended for this case.", body))

    # --- disclaimer
    s.append(Paragraph("Disclaimer and privacy", h2))
    for t in (config.MAIN_DISCLAIMER, config.EMPLOYMENT_DISCLAIMER, config.WORDING_NOTICE, config.PRIVACY_NOTICE):
        s.append(Paragraph(_p(t), small))
        s.append(Spacer(1, 3))
    s.append(Paragraph(f"Generated by {config.APP_NAME} v{config.VERSION} on "
                       f"{datetime.now().strftime('%Y-%m-%d %H:%M')}.", small))

    doc.build(s)
    return buf.getvalue()


def save_report_to_disk(pdf_bytes, candidate_id):
    """Optional local copy in generated_reports/. Returns the path, or None if not writable."""
    try:
        folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "generated_reports")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, report_filename(candidate_id))
        with open(path, "wb") as fh:
            fh.write(pdf_bytes)
        return path
    except Exception:
        return None


def generate_csv(result):
    """Scores CSV: one row per reported score."""
    scores = result["scores"]
    d, m, b = scores["dass"], scores["mbi"], scores["big5"]
    rows = [
        ("PSS (adjusted)", scores["pss"]["score"], scores["pss"]["level"]),
        ("GAD-7", scores["gad7"]["score"], scores["gad7"]["level"]),
        ("PHQ-9", scores["phq9"]["score"], scores["phq9"]["level"]),
        ("DASS Depression", d["depression"], d["depression_level"]),
        ("DASS Anxiety", d["anxiety"], d["anxiety_level"]),
        ("DASS Stress", d["stress"], d["stress_level"]),
        ("MBI Emotional Exhaustion", m["emotional_exhaustion"], m["ee_level"]),
        ("MBI Depersonalization", m["depersonalization"], m["dp_level"]),
        ("MBI Personal Accomplishment", m["personal_accomplishment"], m["pa_level"]),
    ] + [(f"Big Five {config.FEATURE_LABELS[n].split()[-1]}", b[n], b["levels"][n[0].upper()])
         for n in ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism")]
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["candidate_id", "date", "measure", "score", "interpretation"])
    risk = result["prediction"]["risk"]
    for name, val, lvl in rows:
        w.writerow([result["candidate_id"], result["timestamp"][:10], name, val, lvl])
    w.writerow([result["candidate_id"], result["timestamp"][:10], "AI risk indication",
                f"{result['prediction']['confidence'] * 100:.1f}%", config.risk_full(risk)])
    return out.getvalue().encode("utf-8")


def generate_feature_row_csv(result):
    """One-row CSV of the 14 model inputs plus the prediction."""
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["candidate_id"] + config.FEATURE_NAMES + ["risk_number", "predicted_risk", "risk_definition", "confidence"])
    w.writerow([result["candidate_id"]] + list(result["features"]) +
               [config.risk_info(result["prediction"]["risk"])["number"], result["prediction"]["risk"],
                config.risk_info(result["prediction"]["risk"])["definition"],
                round(result["prediction"]["confidence"], 4)])
    return out.getvalue().encode("utf-8")
