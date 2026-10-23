"""WiseOLife - theme CSS, HTML components and Plotly charts (presentation helpers only).

HTML strings are built WITHOUT leading indentation/newlines, otherwise Markdown would
treat them as code blocks.
"""
import html
import inspect
import re

import plotly.graph_objects as go
import streamlit as st

from . import config

PURPLE = "#6d28d9"
INDIGO = "#4f46e5"
NAVY = "#1e1b4b"
LEVEL_COLORS = {
    "Low": "#10b981", "Minimal": "#10b981", "Normal": "#10b981",
    "Mild": "#84cc16", "Moderate": "#f59e0b", "Moderately Severe": "#f97316",
    "High": "#ef4444", "Severe": "#ef4444", "Extremely Severe": "#b91c1c",
}
LEVEL_DOT = {"Low": "🟢", "Minimal": "🟢", "Normal": "🟢", "Mild": "🟡", "Moderate": "🟡",
             "Moderately Severe": "🟠", "High": "🔴", "Severe": "🔴", "Extremely Severe": "🔴"}


def wide(fn):
    """kwargs that make a Streamlit widget full width, across Streamlit versions."""
    try:
        if "width" in inspect.signature(fn).parameters:
            return {"width": "stretch"}
    except (TypeError, ValueError):
        pass
    return {"use_container_width": True}


def inject_css():
    st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
html, body, [class*="css"], .stApp { font-family: 'Inter', sans-serif; }
.stApp { background: #f4f6fb; }
.block-container { padding-top: 1.6rem; max-width: 1250px; }
[data-testid="stSidebar"] { background: linear-gradient(180deg,#1e1b4b 0%,#312e81 55%,#4c1d95 100%); }
[data-testid="stSidebar"] * { color: #e0e7ff; }
[data-testid="stSidebar"] .stButton>button { background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.12);
  color: #e0e7ff; border-radius: 10px; text-align: left; justify-content: flex-start; font-weight: 600; padding: .35rem .8rem; }
[data-testid="stSidebar"] .stButton>button:hover { background: rgba(255,255,255,.16); border-color: #a5b4fc; }
[data-testid="stSidebar"] .stButton>button[kind="primary"] { background: linear-gradient(90deg,#6d28d9,#4f46e5); border: none; color: #fff; }
[data-testid="stSidebar"] [data-baseweb="select"] * { color: #0f172a !important; }
.stButton>button[kind="primary"], .stDownloadButton>button[kind="primary"] { background: linear-gradient(90deg,#6d28d9,#4f46e5);
  border: none; color: #fff; border-radius: 12px; font-weight: 700; }
.stButton>button, .stDownloadButton>button { border-radius: 12px; font-weight: 600; }
.wl-hero { background: linear-gradient(120deg,#1e1b4b 0%,#4338ca 55%,#7c3aed 100%); color: #fff; border-radius: 24px;
  padding: 2.6rem 2.4rem; box-shadow: 0 18px 40px rgba(67,56,202,.28); margin-bottom: 1.2rem; }
.wl-hero h1 { color:#fff; font-size: 3rem; font-weight: 800; margin: .3rem 0 .1rem; letter-spacing:-1px; }
.wl-hero h3 { color:#c7d2fe; font-weight: 600; margin: 0 0 .8rem; }
.wl-hero p { color:#e0e7ff; max-width: 760px; font-size: 1.05rem; line-height: 1.55; }
.wl-badge { display:inline-block; background: rgba(255,255,255,.16); border-radius: 999px; padding: .25rem .85rem;
  font-size:.8rem; font-weight:700; letter-spacing:.5px; }
.wl-card { background:#fff; border:1px solid #e2e8f0; border-radius:18px; padding:1.05rem 1.2rem;
  box-shadow: 0 6px 18px rgba(15,23,42,.06); height: 100%; }
.wl-card-title { font-size:.74rem; font-weight:700; color:#6366f1; letter-spacing:.6px; text-transform:uppercase; }
.wl-card-value { font-size:1.55rem; font-weight:800; color:#0f172a; margin:.15rem 0; }
.wl-card-sub { font-size:.84rem; color:#64748b; line-height:1.4; }
.wl-stat { background:#fff; border-radius:18px; padding:1.1rem; text-align:center; border:1px solid #e2e8f0;
  box-shadow: 0 6px 18px rgba(15,23,42,.06); }
.wl-stat-n { font-size:2rem; font-weight:800; background: linear-gradient(90deg,#6d28d9,#4f46e5);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.wl-stat-l { font-size:.82rem; color:#64748b; font-weight:600; }
.wl-section h2 { font-size:1.55rem; font-weight:800; color:#1e1b4b; margin:.2rem 0 0; }
.wl-section p { color:#64748b; margin:.1rem 0 .8rem; }
.wl-note, .wl-warn, .wl-ok, .wl-disc { border-radius:14px; padding:.85rem 1.05rem; font-size:.9rem; line-height:1.5; margin:.2rem 0; }
.wl-note { background:#eef2ff; border:1px solid #c7d2fe; color:#312e81; }
.wl-warn { background:#fffbeb; border:1px solid #fcd34d; color:#78350f; }
.wl-ok { background:#ecfdf5; border:1px solid #6ee7b7; color:#065f46; }
.wl-disc { background:#f1f5f9; border:1px solid #cbd5e1; color:#475569; font-size:.8rem; }
.wl-risk { border-radius:22px; padding:1.5rem 1.8rem; color:#fff; box-shadow:0 14px 30px rgba(15,23,42,.18); margin-bottom:.6rem; }
.wl-risk h1 { color:#fff; margin:0; font-size:2.4rem; font-weight:800; }
.wl-risk .conf { font-size:1.15rem; font-weight:700; opacity:.95; }
.wl-risk .disc { font-size:.85rem; margin-top:.5rem; opacity:.92; }
.wl-pill { display:inline-block; border-radius:999px; padding:.12rem .65rem; font-size:.76rem; font-weight:700; color:#fff; }
.wl-bar { background:#e2e8f0; border-radius:999px; height:9px; overflow:hidden; margin-top:.5rem; }
.wl-bar>div { height:100%; border-radius:999px; }
.wl-chip { background:#fff; border:1px solid #e2e8f0; border-left:5px solid #6d28d9; border-radius:12px; padding:.55rem .8rem; }
.wl-chip .l { font-size:.72rem; color:#64748b; font-weight:700; } .wl-chip .v { font-size:1.35rem; font-weight:800; color:#0f172a; }
.wl-vector { background:#0f172a; color:#a5f3fc; font-family:ui-monospace,Menlo,monospace; border-radius:14px;
  padding:1rem 1.2rem; font-size:1.05rem; overflow-x:auto; }
.wl-flow { display:flex; flex-wrap:wrap; gap:.4rem; align-items:center; }
.wl-step { background:#fff; border:1px solid #c7d2fe; border-radius:12px; padding:.5rem .8rem; font-weight:700; color:#312e81; font-size:.86rem; }
.wl-arrow { color:#6366f1; font-weight:800; }
.bubble-u, .bubble-b { border-radius:16px; padding:.7rem 1rem; max-width:78%; font-size:.93rem; line-height:1.5; }
.bubble-u { background: linear-gradient(90deg,#6d28d9,#4f46e5); color:#fff; margin-left:auto; border-bottom-right-radius:4px; }
.bubble-b { background:#fff; border:1px solid #e2e8f0; color:#0f172a; border-bottom-left-radius:4px; }
#MainMenu, footer { visibility: hidden; }
</style>""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# HTML COMPONENTS
# ---------------------------------------------------------------------------
def _h(text):
    return html.escape(str(text))


def hero(title, subtitle, text, badge=""):
    st.markdown(f"<div class='wl-hero'><span class='wl-badge'>{_h(badge)}</span><h1>{_h(title)}</h1>"
                f"<h3>{_h(subtitle)}</h3><p>{_h(text)}</p></div>", unsafe_allow_html=True)


def section(title, subtitle=""):
    sub = f"<p>{_h(subtitle)}</p>" if subtitle else ""
    st.markdown(f"<div class='wl-section'><h2>{_h(title)}</h2>{sub}</div>", unsafe_allow_html=True)


def stat(n, label):
    st.markdown(f"<div class='wl-stat'><div class='wl-stat-n'>{_h(n)}</div>"
                f"<div class='wl-stat-l'>{_h(label)}</div></div>", unsafe_allow_html=True)


def card(title, value, sub=""):
    st.markdown(f"<div class='wl-card'><div class='wl-card-title'>{_h(title)}</div>"
                f"<div class='wl-card-value'>{_h(value)}</div><div class='wl-card-sub'>{_h(sub)}</div></div>",
                unsafe_allow_html=True)


def note(text_html):
    st.markdown(f"<div class='wl-note'>{text_html}</div>", unsafe_allow_html=True)


def warn(text_html):
    st.markdown(f"<div class='wl-warn'>{text_html}</div>", unsafe_allow_html=True)


def ok(text_html):
    st.markdown(f"<div class='wl-ok'>{text_html}</div>", unsafe_allow_html=True)


def disclaimer(text):
    st.markdown(f"<div class='wl-disc'>⚖️ {_h(text)}</div>", unsafe_allow_html=True)


def workflow(steps):
    parts = []
    for i, s in enumerate(steps):
        parts.append(f"<span class='wl-step'>{_h(s)}</span>")
        if i < len(steps) - 1:
            parts.append("<span class='wl-arrow'>➜</span>")
    st.markdown(f"<div class='wl-flow'>{''.join(parts)}</div>", unsafe_allow_html=True)


def score_card(icon, title, value, level, caption, pct, positive=False):
    """Headline score card with a coloured level pill and progress bar.

    positive=True means a HIGH score is good (MBI Personal Accomplishment)."""
    color = LEVEL_COLORS.get(level, "#6366f1")
    if positive:
        color = {"High": "#10b981", "Moderate": "#f59e0b", "Low": "#ef4444"}.get(level, color)
    dot = {"High": "🟢", "Moderate": "🟡", "Low": "🔴"}.get(level, "") if positive else LEVEL_DOT.get(level, "⚪")
    pct = max(0, min(100, pct))
    st.markdown(
        f"<div class='wl-card'><div class='wl-card-title'>{_h(icon)} {_h(title)}</div>"
        f"<div class='wl-card-value'>{_h(value)}</div>"
        f"<span class='wl-pill' style='background:{color}'>{dot} {_h(level)}</span>"
        f"<div class='wl-bar'><div style='width:{pct:.0f}%;background:{color}'></div></div>"
        f"<div class='wl-card-sub' style='margin-top:.4rem'>{_h(caption)}</div></div>",
        unsafe_allow_html=True)


def risk_banner(risk, confidence, disclaimer_text):
    grad = {"LOW": "linear-gradient(120deg,#047857,#10b981)",
            "MEDIUM": "linear-gradient(120deg,#b45309,#f59e0b)",
            "HIGH": "linear-gradient(120deg,#991b1b,#ef4444)"}[risk]
    st.markdown(
        f"<div class='wl-risk' style='background:{grad}'><div style='font-size:.8rem;font-weight:700;"
        f"letter-spacing:1px;opacity:.9'>AI RISK INDICATION</div>"
        f"<h1>{config.RISK_EMOJI[risk]} {risk} RISK</h1>"
        f"<div class='conf'>Confidence: {confidence * 100:.1f}%</div>"
        f"<div class='disc'>{_h(disclaimer_text)}</div></div>", unsafe_allow_html=True)


def feature_chip(label, value, is_float=False):
    shown = f"{value:.2f}" if is_float else f"{value:g}"
    st.markdown(f"<div class='wl-chip'><div class='l'>{_h(label)}</div><div class='v'>{shown}</div></div>",
                unsafe_allow_html=True)


def feature_vector_block(features):
    vec = ", ".join(f"{v:g}" for v in features)
    st.markdown(f"<div class='wl-vector'>[ {vec} ]</div>", unsafe_allow_html=True)


def _md_to_html(text):
    out = _h(text)
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)
    return out.replace("\n", "<br/>")


def chat_bubble(text, is_user=False, render_markdown=True):
    body = _md_to_html(text) if render_markdown else text
    cls = "bubble-u" if is_user else "bubble-b"
    st.markdown(f"<div class='{cls}'>{body}</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# CHARTS
# ---------------------------------------------------------------------------
def _style(fig, height=340, title=None):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=50 if title else 20, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Inter", color="#1e293b"),
                      title=dict(text=title, font=dict(size=15)) if title else None)
    return fig


def chart_scores_bar(scores):
    d, m = scores["dass"], scores["mbi"]
    items = [("PSS", scores["pss"]["score"], 40), ("GAD-7", scores["gad7"]["score"], 21),
             ("PHQ-9", scores["phq9"]["score"], 27), ("DASS-D", d["depression"], 42),
             ("DASS-A", d["anxiety"], 42), ("DASS-S", d["stress"], 42),
             ("MBI-EE", m["emotional_exhaustion"], 54), ("MBI-DP", m["depersonalization"], 30),
             ("MBI-PA ↑good", m["personal_accomplishment"], 48)]
    pct = [round(v / mx * 100, 1) for _, v, mx in items]
    colors_ = ["#10b981" if "PA" in n else PURPLE for n, _, _ in items]
    fig = go.Figure(go.Bar(x=[n for n, _, _ in items], y=pct, marker_color=colors_,
                           text=[f"{v}/{mx}" for _, v, mx in items], textposition="outside",
                           hovertemplate="%{x}: %{text} (%{y}%)<extra></extra>"))
    fig.update_yaxes(range=[0, 115], title="% of maximum")
    return _style(fig, 340, "Instrument scores (% of each maximum)")


def chart_probabilities(probs):
    order = config.RISK_CLASSES
    fig = go.Figure(go.Bar(x=[probs[c] * 100 for c in order], y=order, orientation="h",
                           marker_color=[config.RISK_COLOR[c] for c in order],
                           text=[f"{probs[c] * 100:.1f}%" for c in order], textposition="auto"))
    fig.update_xaxes(range=[0, 100], title="Probability (%)")
    return _style(fig, 340, "Model class probabilities")


def chart_dass(d):
    names = ["Depression", "Anxiety", "Stress"]
    vals = [d["depression"], d["anxiety"], d["stress"]]
    levels = [d["depression_level"], d["anxiety_level"], d["stress_level"]]
    fig = go.Figure(go.Bar(x=vals, y=names, orientation="h",
                           marker_color=[LEVEL_COLORS.get(l, PURPLE) for l in levels],
                           text=[f"{v}/42 · {l}" for v, l in zip(vals, levels)], textposition="auto"))
    fig.update_xaxes(range=[0, 42])
    return _style(fig, 240, "DASS-21 subscales (already ×2)")


def chart_mbi(m):
    names = ["Emotional Exhaustion", "Depersonalization", "Personal Accomplishment (↑ good)"]
    maxes = [54, 30, 48]
    vals = [m["emotional_exhaustion"], m["depersonalization"], m["personal_accomplishment"]]
    pct = [v / mx * 100 for v, mx in zip(vals, maxes)]
    fig = go.Figure(go.Bar(x=pct, y=names, orientation="h", marker_color=["#ef4444", "#f59e0b", "#10b981"],
                           text=[f"{v}/{mx}" for v, mx in zip(vals, maxes)], textposition="auto"))
    fig.update_xaxes(range=[0, 100], title="% of maximum")
    return _style(fig, 250, "Burnout dimensions (kept separate)")


def chart_big5_radar(b):
    labels = ["Openness", "Conscientiousness", "Extraversion", "Agreeableness", "Neuroticism"]
    vals = [b["openness"], b["conscientiousness"], b["extraversion"], b["agreeableness"], b["neuroticism"]]
    fig = go.Figure(go.Scatterpolar(r=vals + vals[:1], theta=labels + labels[:1], fill="toself",
                                    line_color=PURPLE, fillcolor="rgba(109,40,217,.25)"))
    fig.update_layout(polar=dict(radialaxis=dict(range=[0, 5], tickvals=[1, 2, 3, 4, 5])), showlegend=False)
    return _style(fig, 360, "Big Five personality radar (1-5)")


def chart_confusion(cm, labels):
    fig = go.Figure(go.Heatmap(z=cm, x=labels, y=labels, colorscale="Purples", showscale=False,
                               text=cm, texttemplate="%{text}"))
    fig.update_xaxes(title="Predicted")
    fig.update_yaxes(title="Actual", autorange="reversed")
    return _style(fig, 330, "Confusion matrix (synthetic test set)")


def chart_dataset_distribution(df):
    counts = df["risk"].value_counts()
    order = [c for c in config.RISK_CLASSES if c in counts.index]
    fig = go.Figure(go.Bar(x=order, y=[int(counts[c]) for c in order],
                           marker_color=[config.RISK_COLOR[c] for c in order],
                           text=[int(counts[c]) for c in order], textposition="outside"))
    return _style(fig, 330, "Synthetic dataset: class distribution")


def chart_importance(importance):
    rows = list(reversed(importance))
    fig = go.Figure(go.Bar(x=[r["percent"] for r in rows], y=[r["label"] for r in rows], orientation="h",
                           marker_color=PURPLE, text=[f"{r['percent']:.1f}%" for r in rows],
                           textposition="outside"))
    fig.update_xaxes(title="Importance (%)")
    return _style(fig, 520, "Random Forest feature importance")


def chart_local_influence(local):
    rows = list(reversed(local))
    fig = go.Figure(go.Bar(
        x=[r["contribution"] for r in rows], y=[r["label"] for r in rows], orientation="h",
        marker_color=["#ef4444" if r["contribution"] > 0 else "#10b981" for r in rows]))
    fig.update_xaxes(title="← protective      raises risk indication →")
    return _style(fig, 380, "What shaped this profile (association, not causation)")


def chart_trend(rows, series, title, ytitle="Score"):
    fig = go.Figure()
    for key, label, color in series:
        fig.add_trace(go.Scatter(x=[r["date"] for r in rows], y=[r[key] for r in rows], name=label,
                                 mode="lines+markers", line=dict(color=color, width=3)))
    fig.update_yaxes(title=ytitle)
    fig.update_layout(legend=dict(orientation="h", y=-0.2))
    return _style(fig, 340, title)


def chart_journal(entries):
    x = [str(e["entry_date"]) for e in entries]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=[e["mood"] for e in entries], name="Mood", mode="lines+markers",
                             line=dict(color="#10b981", width=3)))
    fig.add_trace(go.Scatter(x=x, y=[e["stress"] for e in entries], name="Stress", mode="lines+markers",
                             line=dict(color="#ef4444", width=3)))
    fig.add_trace(go.Bar(x=x, y=[e["sleep_hours"] for e in entries], name="Sleep (h)",
                         marker_color="rgba(99,102,241,.25)"))
    fig.update_layout(legend=dict(orientation="h", y=-0.2))
    return _style(fig, 340, "Mood, stress and sleep")


def chart_risk_donut(counts):
    order = config.RISK_CLASSES
    fig = go.Figure(go.Pie(labels=order, values=[counts.get(c, 0) for c in order], hole=0.6,
                           marker_colors=[config.RISK_COLOR[c] for c in order]))
    return _style(fig, 320, "Cohort risk distribution")
