"""WiseOLife - design system: tokens, theme CSS, HTML components and Plotly charts.

Presentation helpers only - nothing here scores, predicts or stores anything.

HTML strings are built WITHOUT leading indentation/newlines, otherwise Markdown would
treat them as code blocks.
"""
import html
import inspect
import re

import plotly.graph_objects as go
import streamlit as st

from . import config

# ---------------------------------------------------------------------------
# DESIGN TOKENS (mirrored by the CSS custom properties in inject_css)
# ---------------------------------------------------------------------------
BRAND = "#5946D8"
BRAND_INK = "#3E2EAE"
BRAND_SOFT = "#EEEAFE"
INK = "#182033"
TEXT_2 = "#3D475C"
MUTED = "#697386"
BORDER = "#E6E9F0"
GRID = "#EEF0F5"
FONT = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"

# tone -> (fill for bars/dots, ink for text on the soft background, soft background)
TONES = {
    "ok": ("#1E9A61", "#11683F", "#E7F6EE"),
    "caution": ("#CFA225", "#6E5300", "#FBF5DD"),
    "warn": ("#E48A13", "#8F4E07", "#FEF3E4"),
    "high": ("#E0661F", "#983A0A", "#FDEDE3"),
    "err": ("#D93B3B", "#A42424", "#FCECEC"),
    "brand": (BRAND, BRAND_INK, BRAND_SOFT),
    "neutral": ("#8A93A6", "#3D475C", "#F1F3F8"),
}
LEVEL_TONE = {
    "Low": "ok", "Minimal": "ok", "Normal": "ok", "Mild": "caution", "Moderate": "warn",
    "Moderately Severe": "high", "High": "err", "Severe": "err", "Extremely Severe": "err",
}
POSITIVE_TONE = {"High": "ok", "Moderate": "warn", "Low": "err"}   # MBI Personal Accomplishment
RISK_TONE = {"LOW": "ok", "MEDIUM": "warn", "HIGH": "err"}
RISK_ICON = {"LOW": "check-circle", "MEDIUM": "alert-circle", "HIGH": "alert"}
SERIES = [BRAND, "#E48A13", "#D93B3B", "#1E9A61", "#8A93A6", "#2E8FD6"]

# Back-compat names (older code paths read these).
PURPLE = BRAND
LEVEL_COLORS = {k: TONES[v][0] for k, v in LEVEL_TONE.items()}


def tone_of(level, positive=False):
    return (POSITIVE_TONE if positive else LEVEL_TONE).get(level, "neutral")


# ---------------------------------------------------------------------------
# STREAMLIT VERSION HELPERS
# ---------------------------------------------------------------------------
def _params(fn):
    try:
        return inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return {}


def wide(fn):
    """kwargs that make a Streamlit widget full width, across Streamlit versions."""
    if "width" in _params(fn):
        return {"width": "stretch"}
    return {"use_container_width": True}


def icon_kw(fn, icon):
    """{'icon': ...} when this Streamlit version supports widget icons."""
    return {"icon": icon} if icon and "icon" in _params(fn) else {}


def box(key=None, border=None):
    """st.container with an optional CSS hook (key -> .st-key-<key>) and border, when supported."""
    params, kwargs = _params(st.container), {}
    if key and "key" in params:
        kwargs["key"] = key
    if border is not None and "border" in params:
        kwargs["border"] = border
    return st.container(**kwargs)


def columns(spec, gap="small", align=None):
    kwargs = {"gap": gap}
    if align and "vertical_alignment" in _params(st.columns):
        kwargs["vertical_alignment"] = align
    return st.columns(spec, **kwargs)


# ---------------------------------------------------------------------------
# ICONS (inline SVG, 24px grid, stroke = currentColor)
# ---------------------------------------------------------------------------
_ICONS = {
    "info": "<circle cx='12' cy='12' r='9'/><path d='M12 11v5'/><path d='M12 7.8h.01'/>",
    "alert": "<path d='M10.3 4.3 2.9 17.4a2 2 0 0 0 1.7 3h14.8a2 2 0 0 0 1.7-3L13.7 4.3a2 2 0 0 0-3.4 0Z'/>"
             "<path d='M12 9.5v4'/><path d='M12 16.8h.01'/>",
    "alert-circle": "<circle cx='12' cy='12' r='9'/><path d='M12 7.5v5'/><path d='M12 16h.01'/>",
    "check-circle": "<circle cx='12' cy='12' r='9'/><path d='m8.4 12.3 2.4 2.4 4.8-5.1'/>",
    "check": "<path d='m5 12.5 4.2 4.2L19 7'/>",
    "shield": "<path d='M12 3.2 5 6v5.3c0 4.3 2.9 8 7 9.5 4.1-1.5 7-5.2 7-9.5V6Z'/>",
    "clock": "<circle cx='12' cy='12' r='9'/><path d='M12 7v5l3.2 2'/>",
    "lock": "<rect x='5' y='11' width='14' height='9.5' rx='2'/><path d='M8 11V8a4 4 0 0 1 8 0v3'/>",
    "arrow-right": "<path d='M5 12h14'/><path d='m13 6 6 6-6 6'/>",
    "list": "<path d='M9 6h11'/><path d='M9 12h11'/><path d='M9 18h11'/><path d='M4.5 6h.01'/>"
            "<path d='M4.5 12h.01'/><path d='M4.5 18h.01'/>",
    "chart": "<path d='M5 20v-8'/><path d='M12 20V5'/><path d='M19 20v-5'/>",
    "trend": "<path d='m3 17 6-6 4 4 8-8'/><path d='M15 7h6v6'/>",
    "book": "<path d='M5 4.5A1.5 1.5 0 0 1 6.5 3H19v15H6.5A1.5 1.5 0 0 0 5 19.5Z'/>"
            "<path d='M5 19.5A1.5 1.5 0 0 0 6.5 21H19'/>",
    "chat": "<path d='M20 12a8 8 0 0 1-11.6 7.1L4 20.5l1.3-4.2A8 8 0 1 1 20 12Z'/>",
    "user-check": "<circle cx='9' cy='8' r='3.5'/><path d='M3 20a6 6 0 0 1 12 0'/><path d='m16 11.5 2 2 4-4'/>",
    "sparkle": "<path d='M12 3.5l1.7 5 5 1.7-5 1.7-1.7 5-1.7-5-5-1.7 5-1.7Z'/><path d='M19 16v4'/><path d='M17 18h4'/>",
    "inbox": "<path d='M3 13h5l1.5 3h5l1.5-3h5'/><path d='M5.5 5h13L21 13v6a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-6Z'/>",
    "doc": "<path d='M6 3h8l5 5v13H6Z'/><path d='M14 3v5h5'/><path d='M9 13h7'/><path d='M9 17h5'/>",
    "target": "<circle cx='12' cy='12' r='9'/><circle cx='12' cy='12' r='5'/><circle cx='12' cy='12' r='1'/>",
    "layers": "<path d='m12 3 9 5-9 5-9-5Z'/><path d='m3 13 9 5 9-5'/>",
    "users": "<circle cx='9' cy='8' r='3.5'/><path d='M3 20a6 6 0 0 1 12 0'/><path d='M16 4.5a3.5 3.5 0 0 1 0 7'/>"
             "<path d='M18 14.5a6 6 0 0 1 3 5.5'/>",
    "sprout": "<path d='M12 20.5V12'/><path d='M12 12c0-3.6-2.5-5.8-6.5-5.8 0 3.6 2.5 5.8 6.5 5.8Z'/>"
              "<path d='M12 14.5c0-3.2 2.3-5.3 6-5.3 0 3.2-2.3 5.3-6 5.3Z'/>",
}


def icon(name, size=16, cls=""):
    body = _ICONS.get(name, _ICONS["info"])
    return (f"<svg class='wl-ico {cls}' width='{size}' height='{size}' viewBox='0 0 24 24' fill='none' "
            f"stroke='currentColor' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round' "
            f"aria-hidden='true' focusable='false'>{body}</svg>")


# ---------------------------------------------------------------------------
# THEME CSS
# ---------------------------------------------------------------------------
_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root{
--wl-font:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
--wl-mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
--wl-bg:#F8F9FC;--wl-surface:#FFFFFF;--wl-subtle:#F4F5FA;--wl-subtle-2:#EEF0F6;
--wl-text:#182033;--wl-text-2:#3D475C;--wl-muted:#697386;--wl-faint:#8A93A6;
--wl-border:#E6E9F0;--wl-border-strong:#D3D8E3;
--wl-brand:#5946D8;--wl-brand-hover:#4A38C4;--wl-brand-ink:#3E2EAE;--wl-brand-soft:#EEEAFE;--wl-brand-tint:#F7F5FF;
--wl-ok:#1E9A61;--wl-ok-ink:#11683F;--wl-ok-soft:#E7F6EE;--wl-ok-line:#BFE3CF;
--wl-caution:#CFA225;--wl-caution-ink:#6E5300;--wl-caution-soft:#FBF5DD;
--wl-warn:#E48A13;--wl-warn-ink:#8F4E07;--wl-warn-soft:#FEF3E4;--wl-warn-line:#F4D6AE;
--wl-high:#E0661F;--wl-high-ink:#983A0A;--wl-high-soft:#FDEDE3;
--wl-err:#D93B3B;--wl-err-ink:#A42424;--wl-err-soft:#FCECEC;--wl-err-line:#F2C7C7;
--wl-neutral:#8A93A6;--wl-neutral-ink:#3D475C;--wl-neutral-soft:#F1F3F8;
--wl-r-sm:6px;--wl-r:8px;--wl-r-lg:12px;--wl-r-pill:999px;
--wl-shadow-sm:0 1px 2px rgba(24,32,51,.05);
--wl-shadow:0 1px 2px rgba(24,32,51,.04),0 8px 24px -12px rgba(24,32,51,.10);
--wl-focus:0 0 0 3px rgba(89,70,216,.30);
--wl-content:1120px;
}

/* ===== base + layout ===== */
.stApp{background:var(--wl-bg);color:var(--wl-text);font-family:var(--wl-font);
  -webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;}
[data-testid="stHeader"]{background:var(--wl-bg);height:3rem;min-height:3rem;}
[data-testid="stDecoration"],[data-testid="stAppDeployButton"],#MainMenu,footer{display:none!important;}
[data-testid="stMainBlockContainer"],.block-container{max-width:var(--wl-content);padding:3.5rem 2.5rem 5rem;}
.stApp [data-testid="stMarkdownContainer"] code{font-family:var(--wl-mono);font-size:.86em;background:var(--wl-subtle-2);
  color:var(--wl-text);padding:.1em .35em;border-radius:4px;}
.stApp a{color:var(--wl-brand-hover);}
.stApp hr{border-color:var(--wl-border);margin:.5rem 0;}
[data-testid="stElementContainer"]:has(> .stMarkdown style),.element-container:has(> .stMarkdown style){display:none;}
.stApp [data-testid="stMarkdownContainer"]:has(> [class*="wl-"]){margin-bottom:0;}

/* ===== typography ===== */
.wl-eyebrow{font-size:12px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--wl-brand);margin:0 0 8px;}
.wl-h1{font-size:30px;line-height:1.2;font-weight:700;letter-spacing:-.02em;color:var(--wl-text);margin:0;}
.wl-h2{font-size:20px;line-height:1.3;font-weight:600;letter-spacing:-.01em;color:var(--wl-text);margin:0;}
.wl-h3{font-size:16px;line-height:1.4;font-weight:600;color:var(--wl-text);margin:0;}
.wl-lead{font-size:15px;line-height:1.6;color:var(--wl-muted);margin:6px 0 0;max-width:68ch;}
.wl-sub{font-size:14px;line-height:1.55;color:var(--wl-muted);margin:4px 0 0;max-width:72ch;}
.wl-small{font-size:13px;line-height:1.5;color:var(--wl-muted);}
.wl-page-head{padding:0 0 4px;}
.wl-page-head .wl-meta{display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:10px;font-size:13px;color:var(--wl-muted);}
.wl-page-head .wl-meta span{display:inline-flex;align-items:center;gap:6px;}
.wl-section{padding-top:20px;}
.wl-section.tight{padding-top:4px;}
.wl-label{font-size:12px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--wl-muted);margin:0;}
.wl-ico{flex:none;display:inline-block;vertical-align:middle;}
.stApp [data-testid="stMarkdownContainer"] h3{font-size:18px;font-weight:600;letter-spacing:-.01em;padding:18px 0 6px;}
.stApp [data-testid="stCaptionContainer"],.stApp [data-testid="stCaptionContainer"] p{color:var(--wl-muted);font-size:13px;}

/* ===== sidebar ===== */
[data-testid="stSidebar"]{background:var(--wl-surface);border-right:1px solid var(--wl-border);}
.stApp [data-testid="stSidebarHeader"]{height:2.75rem;min-height:2.75rem;padding:0 .75rem;margin-bottom:0;}
.stApp [data-testid="stSidebarUserContent"]{padding:0 10px 28px!important;}
.stApp [data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"]{gap:12px;}
.wl-brand{display:flex;align-items:center;gap:9px;padding:0 6px 8px;}
.wl-brand-mark{width:30px;height:30px;border-radius:8px;background:var(--wl-brand);color:#fff;display:grid;place-items:center;flex:none;}
.wl-brand-name{font-size:16px;font-weight:700;letter-spacing:-.01em;color:var(--wl-text);line-height:1.2;}
.wl-brand-tag{font-size:11px;color:var(--wl-muted);line-height:1.35;}
.wl-brand > div{min-width:0;}
.stApp .st-key-wl_nav{gap:1px!important;}
.wl-nav-label{font-size:11px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;color:var(--wl-faint);
  padding:14px 10px 6px;margin:0;}
.stApp [data-testid="stSidebar"] .st-key-wl_nav .stButton button{justify-content:flex-start;gap:10px;min-height:34px;height:34px;
  padding:0 10px;background:transparent;border:1px solid transparent;box-shadow:none;color:var(--wl-text-2);border-radius:var(--wl-r);}
.stApp [data-testid="stSidebar"] .st-key-wl_nav .stButton button > div{justify-content:flex-start;width:100%;}
.stApp [data-testid="stSidebar"] .st-key-wl_nav .stButton button > div > span{justify-content:flex-start;}
.stApp [data-testid="stSidebar"] .st-key-wl_nav .stButton button:hover{background:var(--wl-subtle);color:var(--wl-text);}
.stApp [data-testid="stSidebar"] .st-key-wl_nav .stButton button p{font-size:14px;font-weight:500;text-align:left;white-space:nowrap;}
.stApp [data-testid="stSidebar"] .st-key-wl_nav .stButton button [data-testid="stIconMaterial"]{font-size:19px;color:var(--wl-faint);}
.stApp [data-testid="stSidebar"] .st-key-wl_nav .stButton button[kind="primary"]{background:var(--wl-brand-soft);color:var(--wl-brand-ink);}
.stApp [data-testid="stSidebar"] .st-key-wl_nav .stButton button[kind="primary"] p{font-weight:600;color:var(--wl-brand-ink);}
.stApp [data-testid="stSidebar"] .st-key-wl_nav .stButton button[kind="primary"] [data-testid="stIconMaterial"]{color:var(--wl-brand);}
.stApp [data-testid="stSidebar"] .st-key-wl_nav .stButton button:focus-visible{box-shadow:var(--wl-focus)!important;}
.stApp .st-key-wl_quick{gap:8px!important;border-top:1px solid var(--wl-border);padding-top:6px;margin-top:6px;}
.stApp .st-key-wl_quick .wl-nav-label{padding-top:10px;}
.stApp [data-testid="stSidebar"] .st-key-wl_quick .stButton button{min-height:38px;padding:4px 12px;}
.stApp [data-testid="stSidebar"] .st-key-wl_quick .stButton button p{white-space:nowrap;}
.wl-side-card{border:1px solid var(--wl-border);border-radius:var(--wl-r-lg);padding:12px;background:var(--wl-surface);}
.wl-side-card .wl-label{font-size:11px;}
.wl-side-row{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:6px;}
.wl-side-id{font-size:14px;font-weight:600;color:var(--wl-text);}
.wl-side-meta{font-size:12px;color:var(--wl-muted);margin-top:6px;}
.wl-side-foot{font-size:11.5px;color:var(--wl-faint);padding:4px 8px 0;line-height:1.5;}

/* ===== buttons ===== */
.stApp .stButton button,.stApp .stDownloadButton button,.stApp [data-testid="stFormSubmitButton"] button,
.stApp [data-testid="stPopover"] button{min-height:40px;padding:6px 16px;border-radius:var(--wl-r);font-weight:600;
  transition:background-color .12s ease,border-color .12s ease,box-shadow .12s ease,color .12s ease;}
.stApp .stButton button p,.stApp .stDownloadButton button p,.stApp [data-testid="stFormSubmitButton"] button p,
.stApp [data-testid="stPopover"] button p{font-size:14px;font-weight:600;}
.stApp button[kind^="primary"]{background:var(--wl-brand);border:1px solid var(--wl-brand);color:#fff;box-shadow:0 1px 2px rgba(24,32,51,.12);}
.stApp button[kind^="primary"]:hover{background:var(--wl-brand-hover);border-color:var(--wl-brand-hover);color:#fff;}
.stApp button[kind^="primary"]:active{background:var(--wl-brand-ink);}
.stApp button[kind^="secondary"]{background:var(--wl-surface);border:1px solid var(--wl-border-strong);color:var(--wl-text);box-shadow:var(--wl-shadow-sm);}
.stApp button[kind^="secondary"]:hover{background:var(--wl-subtle);border-color:#C3C9D6;color:var(--wl-text);}
.stApp button[kind^="secondary"]:active{background:var(--wl-subtle-2);}
.stApp button:focus-visible{outline:none;box-shadow:var(--wl-focus)!important;}
.stApp button:disabled,.stApp button[disabled]{background:var(--wl-subtle)!important;border-color:var(--wl-border)!important;
  color:var(--wl-faint)!important;box-shadow:none!important;cursor:not-allowed;}
.stApp button [data-testid="stIconMaterial"]{font-size:18px;}

/* ===== form controls ===== */
.stApp [data-testid="stWidgetLabel"] p,.stApp [data-testid="stWidgetLabel"] label{font-size:14px;font-weight:500;color:var(--wl-text);}
.stApp [data-baseweb="input"],.stApp [data-baseweb="textarea"],.stApp [data-baseweb="select"] > div{background:var(--wl-surface);}
.stApp [data-baseweb="input"] input,.stApp [data-baseweb="textarea"] textarea{background:var(--wl-surface);font-size:14px;}
.stApp [data-testid="stForm"]{background:var(--wl-surface);border:1px solid var(--wl-border);border-radius:var(--wl-r-lg);padding:20px 20px 16px;}
.stApp [data-testid="stCheckbox"] label p{font-size:14px;}

/* ===== native containers ===== */
.stApp [data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]),
.stApp [data-testid="stVerticalBlock"][class*="st-key-wl_card"]{background:var(--wl-surface);border-color:var(--wl-border);border-radius:var(--wl-r-lg);}
.stApp [data-testid="stExpander"] details{background:var(--wl-surface);border:1px solid var(--wl-border);border-radius:var(--wl-r-lg);}
.stApp [data-testid="stExpander"] summary p{font-size:14px;font-weight:600;color:var(--wl-text);}
.stApp [data-testid="stExpander"] summary:hover p{color:var(--wl-brand-ink);}
.stApp [data-testid="stMetric"]{background:var(--wl-surface);border:1px solid var(--wl-border);border-radius:var(--wl-r-lg);padding:14px 16px;height:100%;}
.stApp [data-testid="stMetricLabel"] p{font-size:13px;font-weight:500;color:var(--wl-muted);}
.stApp [data-testid="stMetricValue"]{font-size:26px;font-weight:650;letter-spacing:-.02em;color:var(--wl-text);}
.stApp [data-testid="stMetricValue"] > div{white-space:normal;}
.stApp [data-testid="stMetricDelta"]{font-size:12.5px;font-weight:500;}
.stApp [data-testid="stTabs"] [role="tablist"]{gap:22px;}
.stApp [data-testid="stTabs"] button[role="tab"] p{font-size:14px;font-weight:500;}
.stApp [data-testid="stTabs"] button[role="tab"][aria-selected="true"] p{font-weight:600;color:var(--wl-brand-ink);}
.stApp [data-testid="stAlert"] > div{border-radius:var(--wl-r-lg);}
.stApp [data-testid="stAlert"] p{font-size:14px;}
.stApp [data-testid="stDataFrame"]{border-radius:var(--wl-r);}
.stApp [data-testid="stPlotlyChart"]{border:1px solid var(--wl-border);border-radius:var(--wl-r-lg);background:var(--wl-surface);padding:8px 8px 4px;}
.stApp [data-testid="stPopoverBody"]{border-radius:var(--wl-r-lg);}
.stApp [data-testid="stChatInput"]{border-radius:var(--wl-r-lg);}
.stApp [data-testid="stCode"] pre,.stApp pre{border-radius:var(--wl-r);}

/* ===== cards + surfaces ===== */
.wl-card{background:var(--wl-surface);border:1px solid var(--wl-border);border-radius:var(--wl-r-lg);padding:18px 20px;height:100%;}
.wl-card-title{display:flex;align-items:center;gap:6px;font-size:13px;font-weight:600;color:var(--wl-muted);}
.wl-card-value{font-size:18px;font-weight:600;color:var(--wl-text);margin:6px 0 2px;letter-spacing:-.01em;}
.wl-card-sub{font-size:13.5px;color:var(--wl-muted);line-height:1.5;}
.wl-grid{display:grid;gap:12px;grid-template-columns:repeat(var(--cols,3),minmax(0,1fr));}

/* stat strip: one surface, internal dividers */
.wl-stats{display:grid;grid-template-columns:repeat(var(--cols,4),minmax(0,1fr));background:var(--wl-surface);
  border:1px solid var(--wl-border);border-radius:var(--wl-r-lg);}
.wl-stat{padding:16px 20px;border-left:1px solid var(--wl-border);min-width:0;}
.wl-stat:first-child{border-left:0;}
.wl-stat-l{font-size:12.5px;font-weight:500;color:var(--wl-muted);margin:0;display:flex;align-items:center;gap:6px;}
.wl-stat-v{font-size:28px;line-height:36px;font-weight:650;letter-spacing:-.02em;color:var(--wl-text);margin-top:2px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.wl-stat-v.text{font-size:19px;letter-spacing:-.01em;white-space:normal;line-height:1.3;min-height:36px;display:flex;align-items:center;}
.wl-stat-s{font-size:12.5px;color:var(--wl-muted);margin-top:2px;}

/* notices */
.wl-notice{display:flex;gap:12px;align-items:flex-start;border:1px solid var(--wl-border);border-radius:var(--wl-r-lg);
  padding:12px 16px;font-size:14px;line-height:1.55;color:var(--wl-text-2);background:var(--wl-surface);}
.wl-notice > .wl-ico{margin-top:2px;}
.wl-notice b{color:var(--wl-text);font-weight:600;}
.wl-notice-title{font-weight:600;color:var(--wl-text);margin-bottom:2px;}
.wl-notice--info{background:var(--wl-brand-tint);border-color:#DDD6FB;}
.wl-notice--info > .wl-ico{color:var(--wl-brand);}
.wl-notice--warn{background:var(--wl-warn-soft);border-color:var(--wl-warn-line);}
.wl-notice--warn > .wl-ico{color:var(--wl-warn);}
.wl-notice--warn,.wl-notice--warn b{color:var(--wl-warn-ink);}
.wl-notice--err{background:var(--wl-err-soft);border-color:var(--wl-err-line);}
.wl-notice--err > .wl-ico{color:var(--wl-err);}
.wl-notice--err,.wl-notice--err b{color:var(--wl-err-ink);}
.wl-notice--ok{background:var(--wl-ok-soft);border-color:var(--wl-ok-line);}
.wl-notice--ok > .wl-ico{color:var(--wl-ok);}
.wl-notice--ok,.wl-notice--ok b{color:var(--wl-ok-ink);}
.wl-notice--neutral{background:var(--wl-subtle);border-color:var(--wl-border);color:var(--wl-muted);font-size:13px;}
.wl-notice--neutral > .wl-ico{color:var(--wl-faint);}
.wl-notice ul{margin:4px 0 0;padding-left:18px;}
.wl-notice li{margin:2px 0;}

/* badges */
.wl-badge{display:inline-flex;align-items:center;gap:6px;border-radius:var(--wl-r-pill);padding:2px 10px;font-size:12.5px;
  font-weight:600;line-height:20px;white-space:nowrap;vertical-align:middle;}
.wl-badge .wl-dot{width:7px;height:7px;border-radius:50%;background:currentColor;flex:none;}
.wl-badge--sm{font-size:11.5px;padding:1px 8px;line-height:18px;}
.wl-badge--outline{background:var(--wl-surface)!important;border:1px solid var(--wl-border);color:var(--wl-text-2)!important;}

/* meter */
.wl-meter{height:6px;border-radius:var(--wl-r-pill);background:var(--wl-subtle-2);overflow:hidden;}
.wl-meter > span{display:block;height:100%;border-radius:var(--wl-r-pill);}

/* empty state */
.wl-empty{text-align:center;padding:28px 20px 8px;}
.wl-empty-ico{width:44px;height:44px;border-radius:12px;background:var(--wl-brand-soft);color:var(--wl-brand);display:grid;
  place-items:center;margin:0 auto 12px;}
.wl-empty-title{font-size:16px;font-weight:600;color:var(--wl-text);}
.wl-empty-body{font-size:14px;line-height:1.55;color:var(--wl-muted);max-width:46ch;margin:6px auto 0;}

/* home: welcome + process */
.st-key-wl_welcome{background:var(--wl-surface);border:1px solid var(--wl-border);border-radius:16px;padding:32px 32px 28px;
  gap:0!important;position:relative;overflow:hidden;}
.st-key-wl_welcome::after{content:"";position:absolute;right:-60px;top:-60px;width:220px;height:220px;border-radius:50%;
  background:radial-gradient(circle at center,rgba(89,70,216,.10),rgba(89,70,216,0) 70%);pointer-events:none;}
.wl-welcome .wl-h1{font-size:34px;max-width:18ch;}
.wl-welcome .wl-lead{font-size:16px;margin-top:10px;max-width:58ch;}
.wl-welcome-actions{height:20px;}
.st-key-wl_status{background:var(--wl-surface);border:1px solid var(--wl-border);border-radius:16px;padding:22px;gap:12px!important;justify-content:center;}
.stApp [data-testid="stLayoutWrapper"]:has(> .st-key-wl_status),.stApp [data-testid="stLayoutWrapper"]:has(> .st-key-wl_welcome){flex-grow:1;}
.wl-process{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;counter-reset:wl;}
.wl-pstep{background:var(--wl-surface);border:1px solid var(--wl-border);border-radius:var(--wl-r-lg);padding:16px 18px;}
.wl-pstep-n{width:24px;height:24px;border-radius:7px;background:var(--wl-brand-soft);color:var(--wl-brand-ink);font-size:12.5px;
  font-weight:700;display:grid;place-items:center;}
.wl-pstep-t{font-size:15px;font-weight:600;color:var(--wl-text);margin-top:12px;}
.wl-pstep-d{font-size:13.5px;line-height:1.5;color:var(--wl-muted);margin-top:4px;}
.wl-pstep-k{display:flex;flex-wrap:wrap;gap:4px;margin-top:10px;}
.wl-tag{font-size:11.5px;font-weight:500;color:var(--wl-text-2);background:var(--wl-subtle);border:1px solid var(--wl-border);
  border-radius:var(--wl-r-sm);padding:1px 7px;}

/* list rows (instruments, tiers, history) */
.wl-rows{background:var(--wl-surface);border:1px solid var(--wl-border);border-radius:var(--wl-r-lg);overflow:hidden;}
.wl-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px;align-items:center;padding:12px 18px;border-top:1px solid var(--wl-border);}
.wl-row:first-child{border-top:0;}
.wl-row-t{font-size:14.5px;font-weight:600;color:var(--wl-text);}
.wl-row-d{font-size:13.5px;color:var(--wl-muted);margin-top:1px;line-height:1.45;}
.wl-row-r{font-size:13px;color:var(--wl-muted);text-align:right;white-space:nowrap;}
.wl-inst{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));background:var(--wl-surface);border:1px solid var(--wl-border);
  border-radius:var(--wl-r-lg);overflow:hidden;}
.wl-inst > div{padding:16px 18px;border-left:1px solid var(--wl-border);border-top:1px solid var(--wl-border);margin:-1px 0 0 -1px;}
.wl-inst-h{display:flex;align-items:center;justify-content:space-between;gap:8px;}

/* tiers */
.wl-tiers{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;}
.wl-tier{background:var(--wl-surface);border:1px solid var(--wl-border);border-radius:var(--wl-r-lg);padding:14px 16px;}
.wl-tier.cur{border-color:#C9C0F6;background:var(--wl-brand-tint);}
.wl-tier-h{display:flex;align-items:center;justify-content:space-between;gap:8px;min-height:20px;}

/* tables */
.wl-table-wrap{background:var(--wl-surface);border:1px solid var(--wl-border);border-radius:var(--wl-r-lg);overflow-x:auto;}
.wl-table{width:100%;border-collapse:collapse;font-size:14px;margin:0!important;}
.wl-table th{text-align:left;font-size:12px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:var(--wl-muted);
  background:#FAFBFD;padding:10px 16px;border-bottom:1px solid var(--wl-border);white-space:nowrap;}
.wl-table td{padding:11px 16px;border-top:1px solid var(--wl-border);color:var(--wl-text-2);vertical-align:top;line-height:1.5;}
.wl-table tr:first-child td{border-top:0;}
.wl-table td.strong{color:var(--wl-text);font-weight:600;}
.wl-table td.num{font-variant-numeric:tabular-nums;white-space:nowrap;}
.stApp [data-testid="stMarkdownContainer"] table{border-collapse:collapse;font-size:14px;background:var(--wl-surface);}
.stApp [data-testid="stMarkdownContainer"] th{background:#FAFBFD;font-weight:600;color:var(--wl-muted);font-size:12.5px;}
.stApp [data-testid="stMarkdownContainer"] th,.stApp [data-testid="stMarkdownContainer"] td{border:1px solid var(--wl-border);padding:8px 12px;}

/* risk card */
.wl-risk{background:var(--wl-surface);border:1px solid var(--wl-border);border-radius:var(--wl-r-lg);padding:20px 22px;
  position:relative;overflow:visible;height:100%;}
.wl-risk::before{content:"";position:absolute;left:-1px;top:16px;bottom:16px;width:3px;border-radius:0 3px 3px 0;background:var(--tone);}
.wl-risk-top{display:flex;align-items:center;gap:6px;}
.wl-risk-main{display:flex;align-items:center;gap:12px;margin-top:12px;}
.wl-risk-ico{width:40px;height:40px;border-radius:10px;display:grid;place-items:center;flex:none;}
.wl-risk-name{font-size:24px;font-weight:700;letter-spacing:-.02em;color:var(--wl-text);line-height:1.2;}
.wl-risk-num{font-size:13px;font-weight:600;color:var(--wl-muted);}
.wl-risk-def{font-size:14px;line-height:1.55;color:var(--wl-text-2);margin-top:12px;}
.wl-risk-conf{margin-top:16px;}
.wl-risk-conf-row{display:flex;align-items:center;justify-content:space-between;font-size:13px;color:var(--wl-muted);margin-bottom:6px;}
.wl-risk-conf-row b{color:var(--wl-text);font-weight:600;font-variant-numeric:tabular-nums;}
.wl-risk-disc{display:flex;gap:8px;align-items:flex-start;font-size:12.5px;line-height:1.5;color:var(--wl-muted);
  margin-top:16px;padding-top:12px;border-top:1px solid var(--wl-border);}

/* score cards */
.wl-scores{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;}
.wl-score{background:var(--wl-surface);border:1px solid var(--wl-border);border-radius:var(--wl-r-lg);padding:16px 18px;
  display:flex;flex-direction:column;gap:10px;height:100%;}
.wl-score-h{display:flex;align-items:center;gap:6px;font-size:13px;font-weight:600;color:var(--wl-muted);}
.wl-score-v{display:flex;align-items:baseline;justify-content:space-between;gap:10px;flex-wrap:wrap;}
.wl-score-n{font-size:28px;font-weight:650;letter-spacing:-.02em;color:var(--wl-text);font-variant-numeric:tabular-nums;line-height:1.1;}
.wl-score-n small{font-size:15px;font-weight:500;color:var(--wl-faint);margin-left:2px;}
.wl-score-c{font-size:12.5px;color:var(--wl-muted);line-height:1.45;}

/* feature vector */
.wl-fgroup{margin-top:4px;}
.wl-fgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;margin-top:8px;}
.wl-chip{background:var(--wl-surface);border:1px solid var(--wl-border);border-radius:var(--wl-r);padding:10px 12px;}
.wl-chip .l{display:flex;align-items:center;font-size:12px;color:var(--wl-muted);font-weight:500;}
.wl-chip .v{font-size:19px;font-weight:650;color:var(--wl-text);font-variant-numeric:tabular-nums;margin-top:2px;}
.wl-chip .r{font-size:11.5px;color:var(--wl-faint);}
.wl-vector{background:var(--wl-subtle);border:1px solid var(--wl-border);color:var(--wl-text);font-family:var(--wl-mono);
  border-radius:var(--wl-r);padding:12px 14px;font-size:13.5px;line-height:1.6;word-break:break-word;}

.wl-fgroups{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;}
.wl-fcard{background:var(--wl-surface);border:1px solid var(--wl-border);border-radius:var(--wl-r-lg);padding:14px 16px 8px;}
.wl-frow{display:grid;grid-template-columns:minmax(0,1fr) auto 64px;gap:12px;align-items:baseline;padding:8px 0;
  border-top:1px solid var(--wl-border);}
.wl-fcard .wl-label + .wl-frow{border-top:0;margin-top:4px;}
.wl-frow .n{font-size:13.5px;color:var(--wl-text-2);display:flex;align-items:center;min-width:0;}
.wl-frow .v{font-size:15px;font-weight:650;color:var(--wl-text);font-variant-numeric:tabular-nums;text-align:right;}
.wl-frow .r{font-size:12px;color:var(--wl-faint);text-align:right;font-variant-numeric:tabular-nums;}

/* insight */
.wl-insight{background:var(--wl-surface);border:1px solid var(--wl-border);border-radius:var(--wl-r-lg);padding:18px 20px;}
.wl-insight-finding{font-size:17px;font-weight:600;color:var(--wl-text);line-height:1.45;margin-top:6px;}
.wl-insight-body{font-size:14.5px;line-height:1.6;color:var(--wl-text-2);margin-top:10px;}
.wl-insight-basis{display:flex;gap:8px;font-size:12.5px;line-height:1.5;color:var(--wl-muted);margin-top:14px;padding-top:12px;
  border-top:1px solid var(--wl-border);}

/* plan */
.wl-plan{background:var(--wl-surface);border:1px solid var(--wl-border);border-radius:var(--wl-r-lg);padding:16px 20px;}
.wl-plan-h{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;}
.wl-plan-why{font-size:14px;color:var(--wl-muted);line-height:1.55;margin-top:6px;}
.wl-checks{list-style:none;margin:12px 0 0;padding:0;display:grid;gap:8px;}
.wl-checks li{display:flex;gap:10px;align-items:flex-start;font-size:14px;line-height:1.55;color:var(--wl-text-2);margin:0;}
.wl-checks li .wl-ico{margin-top:3px;color:var(--wl-brand);}
.wl-checks.ok li .wl-ico{color:var(--wl-ok);}

/* assessment */
.wl-progress{background:var(--wl-surface);border:1px solid var(--wl-border);border-radius:var(--wl-r-lg);padding:16px 20px;}
.wl-prog-top{display:flex;align-items:baseline;justify-content:space-between;gap:12px;flex-wrap:wrap;}
.wl-prog-t{font-size:15px;font-weight:600;color:var(--wl-text);}
.wl-prog-q{font-size:13px;color:var(--wl-muted);font-variant-numeric:tabular-nums;}
.wl-prog-q b{color:var(--wl-text);font-weight:600;}
.wl-stepper{display:grid;grid-template-columns:repeat(var(--n,6),minmax(0,1fr));gap:6px;margin:14px 0 12px;list-style:none;padding:0;}
.wl-stepper li{margin:0;min-width:0;}
.wl-stepper .bar{height:4px;border-radius:4px;background:var(--wl-subtle-2);overflow:hidden;}
.wl-stepper .bar > span{display:block;height:100%;background:var(--wl-brand);}
.wl-stepper .lbl{display:flex;align-items:center;gap:4px;font-size:12px;color:var(--wl-faint);margin-top:6px;white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis;}
.wl-stepper li.cur .lbl{color:var(--wl-brand-ink);font-weight:600;}
.wl-stepper li.done .lbl{color:var(--wl-text-2);}
.wl-stepper li.skip .lbl{color:var(--wl-warn-ink);}
.wl-stepper li.done .bar > span{background:var(--wl-ok);}
.wl-stepper li.skip .bar > span{background:var(--wl-warn);}
.wl-counts{display:flex;flex-wrap:wrap;align-items:center;gap:6px 16px;font-size:13px;color:var(--wl-muted);}
.wl-counts span{display:inline-flex;align-items:center;gap:6px;}
.wl-counts i{width:8px;height:8px;border-radius:2px;display:inline-block;}
.wl-section-intro{display:flex;justify-content:space-between;gap:16px;align-items:flex-end;flex-wrap:wrap;padding-top:8px;}
.wl-section-intro .wl-meta{font-size:13px;color:var(--wl-muted);margin-top:4px;}
.wl-instr{font-size:15px;color:var(--wl-text-2);line-height:1.6;}
.wl-instr strong,.wl-instr b{color:var(--wl-text);}
[class*="st-key-wlq_"]{background:var(--wl-surface);border:1px solid var(--wl-border);border-radius:var(--wl-r-lg);
  padding:16px 18px 14px;gap:10px!important;scroll-margin-top:4.5rem;transition:border-color .15s ease;}
[class*="st-key-wlq_"]:has(input:checked){border-color:#DCD6F7;}
.wl-qhead{outline:none;border-radius:6px;scroll-margin-top:5rem;}
.wl-qhead:focus-visible{box-shadow:var(--wl-focus);}
.wl-qmeta{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
.wl-qnum{font-size:12.5px;font-weight:600;color:var(--wl-brand-ink);letter-spacing:.01em;font-variant-numeric:tabular-nums;}
.wl-qtext{font-size:16px;line-height:1.5;font-weight:500;color:var(--wl-text);margin-top:6px;max-width:70ch;}
[class*="st-key-wlq_"] [data-testid="stElementContainer"],[class*="st-key-wlq_"] [data-testid="stRadio"]{width:100%!important;max-width:100%;}
[class*="st-key-wlq_"] [role="radiogroup"]{display:grid!important;grid-template-columns:repeat(auto-fit,minmax(132px,1fr));gap:8px;width:100%;}
[class*="st-key-wlq_"] [role="radiogroup"] > label{margin:0!important;padding:10px 12px;min-height:44px;border:1px solid var(--wl-border-strong);
  border-radius:var(--wl-r);background:var(--wl-surface);align-items:center;cursor:pointer;width:auto;
  transition:border-color .12s ease,background-color .12s ease;}
[class*="st-key-wlq_"] [role="radiogroup"] > label:hover{border-color:#B9B0F0;background:var(--wl-brand-tint);}
[class*="st-key-wlq_"] [role="radiogroup"] > label:has(input:checked){border-color:var(--wl-brand);background:var(--wl-brand-soft);
  box-shadow:inset 0 0 0 1px var(--wl-brand);}
[class*="st-key-wlq_"] [role="radiogroup"] > label:has(input:checked) p{color:var(--wl-brand-ink);font-weight:600;}
[class*="st-key-wlq_"] [role="radiogroup"] > label:has(input:focus-visible){box-shadow:var(--wl-focus);}
[class*="st-key-wlq_"] [role="radiogroup"] > label p{font-size:14px;line-height:1.35;color:var(--wl-text-2);}
.st-key-wl_qnav{border-top:1px solid var(--wl-border);padding-top:16px;margin-top:4px;}

/* status chips */
.wl-st{display:inline-flex;align-items:center;gap:4px;border-radius:var(--wl-r-pill);padding:1px 8px;font-size:11.5px;font-weight:600;line-height:18px;}
.wl-st-ok{background:var(--wl-ok-soft);color:var(--wl-ok-ink);}
.wl-st-skip{background:var(--wl-warn-soft);color:var(--wl-warn-ink);}
.wl-st-open{background:var(--wl-neutral-soft);color:var(--wl-muted);}

/* chat */
.wl-msg{display:flex;gap:10px;align-items:flex-start;max-width:760px;}
.wl-msg-av{width:28px;height:28px;border-radius:8px;background:var(--wl-brand);color:#fff;display:grid;place-items:center;flex:none;margin-top:2px;}
.wl-msg-b{background:var(--wl-surface);border:1px solid var(--wl-border);border-radius:4px 12px 12px 12px;padding:10px 14px;
  font-size:14.5px;line-height:1.6;color:var(--wl-text-2);min-width:0;overflow-wrap:anywhere;}
.wl-msg-b b{color:var(--wl-text);}
.wl-msg.user{margin-left:auto;justify-content:flex-end;}
.wl-msg.user .wl-msg-b{background:var(--wl-brand-soft);border-color:#DED8FB;color:var(--wl-text);border-radius:12px 4px 12px 12px;max-width:80%;}
.wl-sr{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0;}
.st-key-wl_suggest .stButton button{min-height:32px;height:auto;padding:5px 12px;border-radius:var(--wl-r-pill);font-weight:500;
  background:var(--wl-surface);border:1px solid var(--wl-border-strong);box-shadow:none;}
.st-key-wl_suggest .stButton button p{font-size:13px;font-weight:500;}
.st-key-wl_suggest .stButton button:hover{border-color:#B9B0F0;background:var(--wl-brand-tint);color:var(--wl-brand-ink);}

/* tooltips: native <details>, works with touch + keyboard */
.wl-tipd{display:inline-block;position:relative;vertical-align:middle;margin-left:4px;}
.wl-tipd > summary{list-style:none;cursor:help;width:16px;height:16px;line-height:16px;text-align:center;border-radius:50%;
  background:var(--wl-subtle-2);color:var(--wl-muted);font-size:10.5px;font-weight:700;user-select:none;font-style:normal;}
.wl-tipd > summary::-webkit-details-marker{display:none;}
.wl-tipd > summary:hover{background:var(--wl-brand-soft);color:var(--wl-brand-ink);}
.wl-tipd > summary:focus-visible{outline:none;box-shadow:var(--wl-focus);}
.wl-tipd[open] > summary{background:var(--wl-brand);color:#fff;}
.wl-tipbody{position:absolute;z-index:60;left:-8px;top:24px;width:min(280px,72vw);background:var(--wl-text);color:#E9ECF3;
  font-size:12.5px;font-weight:400;line-height:1.5;text-transform:none;letter-spacing:0;border-radius:var(--wl-r);
  padding:10px 12px;box-shadow:0 12px 28px -8px rgba(24,32,51,.35);white-space:normal;text-align:left;}

/* ===== responsive ===== */
@media (max-width:1024px){
  [data-testid="stMainBlockContainer"],.block-container{padding:3.5rem 1.5rem 4rem;}
  .wl-process{grid-template-columns:repeat(2,minmax(0,1fr));}
  .wl-inst{grid-template-columns:repeat(2,minmax(0,1fr));}
}
@media (max-width:768px){
  [data-testid="stMainBlockContainer"],.block-container{padding:4rem 1rem 4rem;}
  .wl-h1{font-size:25px;} .wl-welcome .wl-h1{font-size:27px;} .wl-h2{font-size:18px;}
  .st-key-wl_welcome{padding:22px 20px 20px;}
  .wl-stats{grid-template-columns:repeat(2,minmax(0,1fr));}
  .wl-stat{border-left:0;border-top:1px solid var(--wl-border);}
  .wl-stat:nth-child(-n+2){border-top:0;}
  .wl-stat:nth-child(2n){border-left:1px solid var(--wl-border);}
  .wl-scores{grid-template-columns:repeat(2,minmax(0,1fr));}
  .wl-grid{grid-template-columns:repeat(min(var(--cols,3),2),minmax(0,1fr));}
  .wl-stepper .lbl{font-size:11px;}
  .wl-risk-name{font-size:21px;}
}
@media (max-width:640px){
  .wl-process,.wl-inst,.wl-scores,.wl-grid,.wl-tiers{grid-template-columns:minmax(0,1fr);}
  .wl-stat{padding:14px 16px;} .wl-stat-v{font-size:24px;line-height:32px;} .wl-stat-v.text{font-size:17px;}
  .wl-stepper{grid-template-columns:repeat(var(--n,6),minmax(0,1fr));gap:4px;}
  .wl-stepper .lbl span.t{display:none;}
  .wl-row{grid-template-columns:minmax(0,1fr);gap:4px;} .wl-row-r{text-align:left;}
  .wl-msg.user .wl-msg-b{max-width:92%;}
  .wl-tipbody{left:auto;right:-8px;}
  [class*="st-key-wlq_"] [role="radiogroup"]{grid-template-columns:minmax(0,1fr);}
  .stApp .stButton button,.stApp .stDownloadButton button{min-height:44px;}
}
@media (prefers-reduced-motion:reduce){
  .stApp *{transition:none!important;animation-duration:.01ms!important;scroll-behavior:auto!important;}
}
"""


def inject_css():
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# HTML COMPONENTS
# ---------------------------------------------------------------------------
def _h(text):
    return html.escape(str(text))


def _md(text_html):
    st.markdown(text_html, unsafe_allow_html=True)


def tip(text, label="What does this mean?"):
    """Inline (i) help bubble (native <details>: tap, click or Enter/Space to open)."""
    return (f"<details class='wl-tipd'><summary aria-label='{_h(label)}' title='{_h(label)}'>i</summary>"
            f"<div class='wl-tipbody' role='note'>{_h(text)}</div></details>")


def badge(text, tone="neutral", dot=True, small=False, ico=None):
    fill, ink, soft = TONES.get(tone, TONES["neutral"])
    mark = icon(ico, 13) if ico else ("<span class='wl-dot'></span>" if dot else "")
    size = " wl-badge--sm" if small else ""
    return f"<span class='wl-badge{size}' style='background:{soft};color:{ink}'>{mark}{_h(text)}</span>"


def level_badge(level, positive=False, small=False):
    return badge(level, tone_of(level, positive), small=small)


def risk_badge(risk, with_conf=None, small=False):
    info = config.risk_info(risk)
    text = f"R{info['number']} · {info['name']}" + (f" · {with_conf * 100:.0f}%" if with_conf is not None else "")
    return badge(text, RISK_TONE[risk], dot=False, small=small, ico=RISK_ICON[risk])


def meter(pct, tone="brand", label=None):
    pct = max(0.0, min(100.0, float(pct)))
    aria = f" aria-label='{_h(label)}'" if label else ""
    return (f"<div class='wl-meter' role='progressbar' aria-valuemin='0' aria-valuemax='100' "
            f"aria-valuenow='{pct:.0f}'{aria}><span style='width:{pct:.1f}%;background:{TONES[tone][0]}'></span></div>")


def status_chip(state):
    """state: 'answered' | 'skipped' | 'unanswered'."""
    cls, ico, label = {"answered": ("wl-st-ok", icon("check", 12), "Answered"),
                       "skipped": ("wl-st-skip", icon("alert-circle", 12), "Skipped"),
                       "unanswered": ("wl-st-open", "", "Not answered")}[state]
    return f"<span class='wl-st {cls}'>{ico}{label}</span>"


def brand_block():
    _md(f"<div class='wl-brand'><span class='wl-brand-mark'>{icon('sprout', 19)}</span><div>"
        f"<div class='wl-brand-name'>{_h(config.APP_NAME)}</div>"
        f"<div class='wl-brand-tag'>{_h(config.TAGLINE)}</div></div></div>")


def nav_label(text):
    _md(f"<div class='wl-nav-label'>{_h(text)}</div>")


def page_header(title, subtitle="", eyebrow="", help=None, meta=None):
    """Page title block (h1). meta: list of small inline facts (already-safe HTML)."""
    eb = f"<div class='wl-eyebrow'>{_h(eyebrow)}</div>" if eyebrow else ""
    sub = f"<p class='wl-lead'>{_h(subtitle)}</p>" if subtitle else ""
    meta_html = ("<div class='wl-meta'>" + "".join(f"<span>{m}</span>" for m in meta) + "</div>") if meta else ""
    _md(f"<div class='wl-page-head'>{eb}<div class='wl-h1' role='heading' aria-level='1'>{_h(title)}"
        f"{tip(help) if help else ''}</div>{sub}{meta_html}</div>")


def section(title, subtitle="", help=None, tight=False):
    """Section heading (h2) with optional supporting line."""
    sub = f"<p class='wl-sub'>{_h(subtitle)}</p>" if subtitle else ""
    cls = "wl-section tight" if tight else "wl-section"
    _md(f"<div class='{cls}'><div class='wl-h2' role='heading' aria-level='2'>{_h(title)}"
        f"{tip(help) if help else ''}</div>{sub}</div>")


def label(text):
    _md(f"<div class='wl-label'>{_h(text)}</div>")


def stat_strip(items):
    """Compact metric strip. items: (value, label) or (value, label, sub). Text values render smaller."""
    cells = []
    for item in items:
        value, lab = item[0], item[1]
        sub = item[2] if len(item) > 2 else ""
        hlp = tip(item[3]) if len(item) > 3 and item[3] else ""
        is_text = isinstance(value, str) and not re.fullmatch(r"[\d.,/%\s\u2013-]+(min|h)?", value)
        cells.append(f"<div class='wl-stat'><div class='wl-stat-l'>{_h(lab)}{hlp}</div>"
                     f"<div class='wl-stat-v{' text' if is_text else ''}' title='{_h(value)}'>{_h(value)}</div>"
                     + (f"<div class='wl-stat-s'>{_h(sub)}</div>" if sub else "") + "</div>")
    _md(f"<div class='wl-stats' style='--cols:{len(items)}'>{''.join(cells)}</div>")


def tier_strip(tiers, current):
    """The three decision-support tiers; `current` (1-3) is highlighted. tiers: [(title, description)]."""
    cells = "".join(
        f"<div class='wl-tier{' cur' if i == current else ''}'><div class='wl-tier-h'><span class='wl-label'>Tier {i}</span>"
        + (badge("This page", "brand", dot=False, small=True) if i == current else "") +
        f"</div><div class='wl-row-t' style='margin-top:6px'>{_h(t)}</div><div class='wl-row-d'>{_h(d)}</div></div>"
        for i, (t, d) in enumerate(tiers, 1))
    _md(f"<div class='wl-tiers'>{cells}</div>")


stat_grid = stat_strip


def card(title, value, sub="", help=None):
    _md(f"<div class='wl-card'><div class='wl-card-title'>{_h(title)}{tip(help) if help else ''}</div>"
        f"<div class='wl-card-value'>{_h(value)}</div><div class='wl-card-sub'>{_h(sub)}</div></div>")


def notice(body_html, tone="info", title=None, ico=None):
    ico = ico or {"info": "info", "warn": "alert", "err": "alert", "ok": "check-circle", "neutral": "shield"}[tone]
    head = f"<div class='wl-notice-title'>{_h(title)}</div>" if title else ""
    role = " role='alert'" if tone == "err" else ""
    _md(f"<div class='wl-notice wl-notice--{tone}'{role}>{icon(ico, 18)}<div>{head}{body_html}</div></div>")


def note(text_html, title=None):
    notice(text_html, "info", title)


def warn(text_html, title=None):
    notice(text_html, "warn", title)


def ok(text_html, title=None):
    notice(text_html, "ok", title)


def danger(text_html, title=None):
    notice(text_html, "err", title)


def disclaimer(text):
    notice(_h(text), "neutral")


def empty_state(ico, title, body):
    _md(f"<div class='wl-empty'><div class='wl-empty-ico'>{icon(ico, 22)}</div>"
        f"<div class='wl-empty-title'>{_h(title)}</div><div class='wl-empty-body'>{_h(body)}</div></div>")


def process(steps):
    """Numbered process. steps: [(title, description, [tags])]."""
    cells = "".join(
        f"<div class='wl-pstep'><div class='wl-pstep-n'>{i}</div><div class='wl-pstep-t'>{_h(t)}</div>"
        f"<div class='wl-pstep-d'>{_h(d)}</div>"
        + (("<div class='wl-pstep-k'>" + "".join(f"<span class='wl-tag'>{_h(k)}</span>" for k in tags) + "</div>")
           if tags else "") + "</div>"
        for i, (t, d, tags) in enumerate(steps, 1))
    _md(f"<div class='wl-process'>{cells}</div>")


def workflow(steps):
    """Back-compat: a plain list of step names rendered as a numbered process."""
    process([(s, "", []) for s in steps])


def instrument_grid(instruments):
    cells = "".join(
        f"<div><div class='wl-inst-h'><span class='wl-row-t'>{_h(i['name'])}</span>"
        f"{badge(str(i['n']) + ' items', 'neutral', dot=False, small=True)}</div>"
        f"<div class='wl-row-d' style='margin-top:4px'>{_h(i['full'])}</div></div>" for i in instruments)
    _md(f"<div class='wl-inst'>{cells}</div>")


def rows(items):
    """Simple list rows. items: [(title, description, right_html)]."""
    body = "".join(f"<div class='wl-row'><div><div class='wl-row-t'>{_h(t)}</div>"
                   + (f"<div class='wl-row-d'>{_h(d)}</div>" if d else "") + f"</div>"
                   f"<div class='wl-row-r'>{r}</div></div>" for t, d, r in items)
    _md(f"<div class='wl-rows'>{body}</div>")


def table(headers, body_rows, strong_first=True, num_cols=()):
    """Static HTML table. Cells in body_rows are already-safe HTML strings."""
    head = "".join(f"<th scope='col'>{_h(h)}</th>" for h in headers)
    trs = []
    for r in body_rows:
        tds = []
        for j, c in enumerate(r):
            cls = " class='strong'" if (j == 0 and strong_first) else (" class='num'" if j in num_cols else "")
            tds.append(f"<td{cls}>{c}</td>")
        trs.append("<tr>" + "".join(tds) + "</tr>")
    _md(f"<div class='wl-table-wrap'><table class='wl-table'><thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(trs)}</tbody></table></div>")


def checklist(items, tone="brand", ico="arrow-right", escape=True):
    lis = "".join(f"<li>{icon(ico, 15)}<span>{_h(i) if escape else i}</span></li>" for i in items)
    _md(f"<ul class='wl-checks{' ok' if tone == 'ok' else ''}'>{lis}</ul>")


def _score_html(title, value, level, caption, pct, positive=False, help=None):
    tone = tone_of(level, positive)
    num, _, mx = str(value).partition(" / ")
    shown = f"{_h(num)}<small>/ {_h(mx)}</small>" if mx else _h(value)
    return (f"<div class='wl-score'><div class='wl-score-h'>{_h(title)}{tip(help) if help else ''}</div>"
            f"<div class='wl-score-v'><span class='wl-score-n'>{shown}</span>{level_badge(level, positive)}</div>"
            f"{meter(pct, tone, f'{title}: {pct:.0f}% of maximum')}"
            f"<div class='wl-score-c'>{_h(caption)}</div></div>")


def score_card(icon_, title, value, level, caption, pct, positive=False, help=None):
    """Headline score card: value, level badge (text + colour), meter and caption.

    positive=True means a HIGH score is good (MBI Personal Accomplishment)."""
    _md(_score_html(title, value, level, caption, pct, positive, help))


def score_grid(cards):
    """cards: dicts with title, value, level, caption, pct, optional positive/help."""
    body = "".join(_score_html(c["title"], c["value"], c["level"], c["caption"], c["pct"],
                               c.get("positive", False), c.get("help")) for c in cards)
    _md(f"<div class='wl-scores'>{body}</div>")


def risk_card(risk, confidence, disclaimer_text, eyebrow="Model estimate · AI risk indication"):
    """Risk card: number, name and definition together (from config.RISK_LEVELS), plus confidence."""
    info = config.risk_info(risk)
    tone = RISK_TONE[risk]
    fill, ink, soft = TONES[tone]
    _md(f"<div class='wl-risk' style='--tone:{fill}'>"
        f"<div class='wl-risk-top'><span class='wl-label'>{_h(eyebrow)}</span>"
        f"{tip('A screening indication from a Random Forest trained on synthetic data. R1-R3 rank severity; it is not a diagnosis.')}</div>"
        f"<div class='wl-risk-main'><span class='wl-risk-ico' style='background:{soft};color:{ink}'>{icon(RISK_ICON[risk], 22)}</span>"
        f"<div><div class='wl-risk-num'>Level R{info['number']} of 3</div>"
        f"<div class='wl-risk-name'>{_h(info['name'])}</div></div></div>"
        f"<div class='wl-risk-def'>{_h(info['definition'])}</div>"
        f"<div class='wl-risk-conf'><div class='wl-risk-conf-row'><span>Model confidence"
        f"{tip('Share of the forest trees that voted for this class. It reflects agreement among trees, not clinical certainty.')}"
        f"</span><b>{confidence * 100:.1f}%</b></div>{meter(confidence * 100, 'brand', 'Model confidence')}</div>"
        f"<div class='wl-risk-disc'>{icon('shield', 15)}<span>{_h(disclaimer_text)}</span></div></div>")


risk_banner = risk_card


def risk_legend():
    """The three risk levels with numbers and definitions, as a compact table."""
    table(["Level", "Risk", "Definition"],
          [[f"R{r['number']}", risk_badge(r["key"], small=True), _h(r["definition"])] for r in config.RISK_LEVELS])


def feature_group(title, items):
    """items: [(label, range_text, value, is_float, help)]"""
    chips = "".join(
        f"<div class='wl-chip'><div class='l'>{_h(lab)}{tip(hlp) if hlp else ''}</div>"
        f"<div class='v'>{(f'{v:.2f}' if is_f else f'{v:g}')}</div><div class='r'>range {_h(rng)}</div></div>"
        for lab, rng, v, is_f, hlp in items)
    _md(f"<div class='wl-fgroup'><div class='wl-label'>{_h(title)}</div><div class='wl-fgrid'>{chips}</div></div>")


def feature_groups(groups):
    """Grouped feature cards. groups: [(title, [(label, range_text, value, is_float, help)])]"""
    cards = []
    for title, items in groups:
        rows_ = "".join(
            f"<div class='wl-frow'><span class='n'>{_h(lab)}{tip(hlp) if hlp else ''}</span>"
            f"<span class='v'>{(f'{v:.2f}' if is_f else f'{v:g}')}</span><span class='r'>{_h(rng)}</span></div>"
            for lab, rng, v, is_f, hlp in items)
        cards.append(f"<div class='wl-fcard'><div class='wl-label'>{_h(title)}</div>{rows_}</div>")
    _md(f"<div class='wl-fgroups'>{''.join(cards)}</div>")


def feature_chip(label_, value, is_float=False, help=None):
    shown = f"{value:.2f}" if is_float else f"{value:g}"
    _md(f"<div class='wl-chip'><div class='l'>{_h(label_)}{tip(help) if help else ''}</div><div class='v'>{shown}</div></div>")


def feature_vector_block(features):
    vec = ", ".join(f"{v:g}" for v in features)
    _md(f"<div class='wl-vector' aria-label='Model input vector'>[ {vec} ]</div>")


def insight(finding_html, body, basis, eyebrow="Main finding"):
    _md(f"<div class='wl-insight'><div class='wl-label'>{_h(eyebrow)}</div>"
        f"<div class='wl-insight-finding'>{finding_html}</div>"
        f"<div class='wl-insight-body'>{_h(body)}</div>"
        f"<div class='wl-insight-basis'>{icon('info', 15)}<span><b>Basis:</b> {_h(basis)}</span></div></div>")


def plan_block(title, why, actions, priority_html):
    lis = "".join(f"<li>{icon('arrow-right', 15)}<span>{_h(a)}</span></li>" for a in actions)
    _md(f"<div class='wl-plan'><div class='wl-plan-h'><span class='wl-h3'>{_h(title)}</span>{priority_html}</div>"
        f"<div class='wl-plan-why'>{_h(why)}</div><ul class='wl-checks'>{lis}</ul></div>")


def _md_to_html(text):
    out = _h(text)
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)
    return out.replace("\n", "<br/>")


md_inline = _md_to_html


def chat_bubble(text, is_user=False, render_markdown=True):
    body = _md_to_html(text) if render_markdown else text
    if is_user:
        _md(f"<div class='wl-msg user'><div class='wl-msg-b'><span class='wl-sr'>You said: </span>{body}</div></div>")
    else:
        _md(f"<div class='wl-msg'><span class='wl-msg-av' aria-hidden='true'>{icon('sprout', 16)}</span>"
            f"<div class='wl-msg-b'><span class='wl-sr'>WiseBot said: </span>{body}</div></div>")


def chart_note(text):
    """Plain-language summary under a chart (also serves screen-reader users)."""
    st.caption(text)


# ---------------------------------------------------------------------------
# CHARTS
# ---------------------------------------------------------------------------
def plot(fig, summary=None):
    st.plotly_chart(fig, config={"displayModeBar": False, "responsive": True}, **wide(st.plotly_chart))
    if summary:
        chart_note(summary)


def _style(fig, height=340, title=None):
    fig.update_layout(
        height=height, margin=dict(l=8, r=16, t=48 if title else 16, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=TEXT_2, size=12),
        title=dict(text=title, font=dict(size=14, color=INK, family=FONT), x=0.01, xanchor="left", y=0.97) if title else None,
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=BORDER, font=dict(family=FONT, color=INK, size=12)),
        legend=dict(font=dict(size=12)), bargap=0.35)
    fig.update_xaxes(gridcolor=GRID, zeroline=False, linecolor=BORDER, tickfont=dict(size=11.5, color=MUTED),
                     title_font=dict(size=12, color=MUTED), automargin=True)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=BORDER, tickfont=dict(size=11.5, color=TEXT_2),
                     title_font=dict(size=12, color=MUTED), automargin=True)
    return fig


def chart_scores_bar(scores):
    d, m = scores["dass"], scores["mbi"]
    items = [("PSS-10", scores["pss"]["score"], 40), ("GAD-7", scores["gad7"]["score"], 21),
             ("PHQ-9", scores["phq9"]["score"], 27), ("DASS Depression", d["depression"], 42),
             ("DASS Anxiety", d["anxiety"], 42), ("DASS Stress", d["stress"], 42),
             ("MBI Exhaustion", m["emotional_exhaustion"], 54), ("MBI Depersonalization", m["depersonalization"], 30),
             ("MBI Accomplishment (higher = good)", m["personal_accomplishment"], 48)]
    rows_ = list(reversed(items))
    pct = [round(v / mx * 100, 1) for _, v, mx in rows_]
    colors_ = [TONES["ok"][0] if "Accomplishment" in n else BRAND for n, _, _ in rows_]
    fig = go.Figure(go.Bar(x=pct, y=[n for n, _, _ in rows_], orientation="h", marker_color=colors_,
                           marker_line_width=0, text=[f"{v:g}/{mx}" for _, v, mx in rows_], textposition="outside",
                           textfont=dict(size=11.5, color=TEXT_2), cliponaxis=False,
                           hovertemplate="%{y}: %{text} (%{x}% of max)<extra></extra>"))
    fig.update_xaxes(range=[0, 112], title="% of maximum", ticksuffix="%")
    return _style(fig, 380, "Instrument scores (% of each maximum)")


def chart_probabilities(probs):
    order = config.RISK_CLASSES
    fig = go.Figure(go.Bar(x=[probs[c] * 100 for c in order], y=[config.risk_label(c) for c in order], orientation="h",
                           marker_color=[TONES[RISK_TONE[c]][0] for c in order], marker_line_width=0,
                           text=[f"{probs[c] * 100:.1f}%" for c in order], textposition="outside", cliponaxis=False,
                           textfont=dict(size=12, color=INK),
                           hovertemplate="%{y}: %{x:.1f}%<extra></extra>"))
    fig.update_xaxes(range=[0, 112], title="Probability (%)", ticksuffix="%")
    fig.update_yaxes(autorange="reversed")
    return _style(fig, 260, "Model class probabilities")


def chart_dass(d):
    names = ["Depression", "Anxiety", "Stress"]
    vals = [d["depression"], d["anxiety"], d["stress"]]
    levels = [d["depression_level"], d["anxiety_level"], d["stress_level"]]
    fig = go.Figure(go.Bar(x=vals, y=names, orientation="h", marker_line_width=0,
                           marker_color=[TONES[tone_of(l)][0] for l in levels],
                           text=[f"{v}/42 · {l}" for v, l in zip(vals, levels)], textposition="outside",
                           cliponaxis=False, textfont=dict(size=12, color=INK)))
    fig.update_xaxes(range=[0, 52], title="Score (0-42)")
    fig.update_yaxes(autorange="reversed")
    return _style(fig, 250, "DASS-21 subscales (already ×2)")


def chart_mbi(m):
    names = ["Emotional Exhaustion", "Depersonalization", "Personal Accomplishment (higher = good)"]
    maxes = [54, 30, 48]
    vals = [m["emotional_exhaustion"], m["depersonalization"], m["personal_accomplishment"]]
    tones = [tone_of(m["ee_level"]), tone_of(m["dp_level"]), tone_of(m["pa_level"], positive=True)]
    pct = [v / mx * 100 for v, mx in zip(vals, maxes)]
    fig = go.Figure(go.Bar(x=pct, y=names, orientation="h", marker_color=[TONES[t][0] for t in tones],
                           marker_line_width=0, text=[f"{v}/{mx}" for v, mx in zip(vals, maxes)],
                           textposition="outside", cliponaxis=False, textfont=dict(size=12, color=INK)))
    fig.update_xaxes(range=[0, 112], title="% of maximum", ticksuffix="%")
    fig.update_yaxes(autorange="reversed")
    return _style(fig, 250, "Burnout dimensions (kept separate)")


def chart_big5_radar(b):
    labels = ["Openness", "Conscientiousness", "Extraversion", "Agreeableness", "Neuroticism"]
    vals = [b["openness"], b["conscientiousness"], b["extraversion"], b["agreeableness"], b["neuroticism"]]
    fig = go.Figure(go.Scatterpolar(r=vals + vals[:1], theta=labels + labels[:1], fill="toself",
                                    line=dict(color=BRAND, width=2), fillcolor="rgba(89,70,216,.14)",
                                    marker=dict(size=6, color=BRAND),
                                    hovertemplate="%{theta}: %{r}<extra></extra>"))
    fig.update_layout(polar=dict(bgcolor="rgba(0,0,0,0)",
                                 radialaxis=dict(range=[0, 5], tickvals=[1, 2, 3, 4, 5], gridcolor=GRID, linecolor=GRID,
                                                 tickfont=dict(size=10, color=MUTED)),
                                 angularaxis=dict(gridcolor=GRID, linecolor=BORDER, tickfont=dict(size=12, color=TEXT_2))),
                      showlegend=False)
    return _style(fig, 360, "Big Five personality profile (1-5)")


def chart_confusion(cm, labels):
    names = [config.risk_label(c) for c in labels]
    fig = go.Figure(go.Heatmap(z=cm, x=names, y=names, colorscale=[[0, "#F7F5FF"], [0.5, "#B3A8F0"], [1, BRAND]],
                               showscale=False, text=cm, texttemplate="%{text}", textfont=dict(size=13),
                               xgap=2, ygap=2, hovertemplate="Actual %{y} · Predicted %{x}: %{z}<extra></extra>"))
    fig.update_xaxes(title="Predicted", showgrid=False)
    fig.update_yaxes(title="Actual", autorange="reversed", showgrid=False)
    return _style(fig, 330, "Confusion matrix (synthetic test set)")


def chart_dataset_distribution(df):
    counts = df["risk"].value_counts()
    order = [c for c in config.RISK_CLASSES if c in counts.index]
    fig = go.Figure(go.Bar(x=[config.risk_label(c) for c in order], y=[int(counts[c]) for c in order],
                           marker_color=[TONES[RISK_TONE[c]][0] for c in order], marker_line_width=0,
                           text=[int(counts[c]) for c in order], textposition="outside", cliponaxis=False,
                           textfont=dict(size=12, color=INK)))
    fig.update_yaxes(title="Profiles")
    return _style(fig, 330, "Synthetic dataset: class distribution")


def chart_importance(importance):
    rows_ = list(reversed(importance))
    fig = go.Figure(go.Bar(x=[r["percent"] for r in rows_], y=[r["label"] for r in rows_], orientation="h",
                           marker_color=BRAND, marker_line_width=0, text=[f"{r['percent']:.1f}%" for r in rows_],
                           textposition="outside", cliponaxis=False, textfont=dict(size=11.5, color=TEXT_2)))
    fig.update_xaxes(title="Importance (%)", ticksuffix="%")
    return _style(fig, 480, "Random Forest feature importance")


def chart_local_influence(local):
    rows_ = list(reversed(local))
    fig = go.Figure(go.Bar(
        x=[r["contribution"] for r in rows_], y=[r["label"] for r in rows_], orientation="h", marker_line_width=0,
        marker_color=[TONES["err"][0] if r["contribution"] > 0 else TONES["ok"][0] for r in rows_],
        hovertemplate="%{y}: %{x:.3f}<extra></extra>"))
    fig.update_xaxes(title="← protective      raises risk indication →", zeroline=True, zerolinecolor="#C3C9D6")
    return _style(fig, 380, "What shaped this profile (association, not causation)")


_SYMBOLS = ["circle", "square", "diamond", "triangle-up", "x"]


def _x_axis(dates):
    """Dates as-is when unique; otherwise one category per record so same-day records don't stack."""
    dates = [str(d) for d in dates]
    if len(set(dates)) == len(dates):
        return dates, None
    return [f"#{i} · {d}" for i, d in enumerate(dates, 1)], "category"


def chart_trend(rows_, series, title, ytitle="Score"):
    fig = go.Figure()
    x, xtype = _x_axis([r["date"] for r in rows_])
    for i, (key, lab, color) in enumerate(series):
        fig.add_trace(go.Scatter(x=x, y=[r[key] for r in rows_], name=lab,
                                 mode="lines+markers", line=dict(color=color, width=2.5),
                                 marker=dict(size=7, symbol=_SYMBOLS[i % len(_SYMBOLS)], color=color)))
    fig.update_yaxes(title=ytitle)
    if xtype:
        fig.update_xaxes(type=xtype, title="Record (oldest → newest)")
    fig.update_layout(legend=dict(orientation="h", y=-0.3 if xtype else -0.22, x=0, xanchor="left"))
    return _style(fig, 360 if xtype else 340, title)


def chart_journal(entries):
    x, xtype = _x_axis([e["entry_date"] for e in entries])
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=[e["sleep_hours"] for e in entries], name="Sleep (h)",
                         marker_color="rgba(89,70,216,.16)", marker_line_width=0))
    fig.add_trace(go.Scatter(x=x, y=[e["mood"] for e in entries], name="Mood", mode="lines+markers",
                             line=dict(color=TONES["ok"][0], width=2.5), marker=dict(size=7, symbol="circle")))
    fig.add_trace(go.Scatter(x=x, y=[e["stress"] for e in entries], name="Stress", mode="lines+markers",
                             line=dict(color=TONES["err"][0], width=2.5), marker=dict(size=7, symbol="square")))
    fig.update_yaxes(title="Rating (1-10) · hours")
    if xtype:
        fig.update_xaxes(type=xtype)
    fig.update_layout(legend=dict(orientation="h", y=-0.3 if xtype else -0.22, x=0, xanchor="left"), bargap=0.5)
    return _style(fig, 330, "Mood, stress and sleep")


def chart_risk_donut(counts):
    order = config.RISK_CLASSES
    fig = go.Figure(go.Pie(labels=[config.risk_label(c) for c in order], values=[counts.get(c, 0) for c in order], hole=0.62,
                           marker=dict(colors=[TONES[RISK_TONE[c]][0] for c in order], line=dict(color="#FFFFFF", width=2)),
                           textinfo="value", textfont=dict(size=13), sort=False,
                           hovertemplate="%{label}: %{value} (%{percent})<extra></extra>"))
    fig.update_layout(legend=dict(orientation="h", y=-0.08, x=0.5, xanchor="center"))
    return _style(fig, 320, "Cohort risk distribution")
