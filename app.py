"""
WiseOLife - AI-Based Mental Wellness Assessment System
======================================================
Streamlit entry point.   Run locally with:   streamlit run app.py

This file is the presentation layer. All logic lives in the wiseolife/ package:
    config.py           branding, team, thresholds, the 14 feature names
    questions.py        the 89 questionnaire items (6 instruments)
    scoring.py          scoring engine + 14-feature vector builder
    model.py            synthetic dataset, Random Forest, explainability
    recommendations.py  personalised wellness plan
    chatbot.py          WiseBot (rule based, no API key needed)
    report.py           PDF (ReportLab) and CSV export
    storage.py          local SQLite history and journal
    demo.py             demo candidates and demo cohorts
    ui.py               theme CSS, HTML components and Plotly charts
    selftest.py         scoring / model validation tests
"""
import html
from datetime import date, datetime

import pandas as pd
import streamlit as st

from wiseolife import chatbot, config, demo, model as ml
from wiseolife import questions as qs
from wiseolife import recommendations as rec
from wiseolife import report as rp
from wiseolife import scoring as sc
from wiseolife import selftest, storage, ui
from wiseolife import teststate as ts

st.set_page_config(
    page_title=f"{config.APP_NAME} - {config.APP_SUBTITLE}",
    page_icon=config.APP_ICON, layout="wide", initial_sidebar_state="auto",
)
ui.inject_css()

PAGES = [
    (":material/home:", "Home"), (":material/assignment:", "Assessment"), (":material/bar_chart:", "My Results"),
    (":material/insights:", "AI Insights"), (":material/spa:", "Wellness Plan"),
    (":material/trending_up:", "Progress Tracking"), (":material/edit_note:", "Wellness Journal"),
    (":material/forum:", "WiseBot Assistant"), (":material/stethoscope:", "Professional Review"),
    (":material/groups:", "HR Dashboard"), (":material/description:", "Reports"),
    (":material/info:", "About WiseOLife"),
]
# Sidebar groups (presentation only): every page above appears exactly once, in the same order.
NAV_GROUPS = [
    (None, ["Home"]),
    ("Assessment", ["Assessment", "My Results"]),
    ("Insights", ["AI Insights", "Wellness Plan", "Progress Tracking"]),
    ("Personal wellness", ["Wellness Journal", "WiseBot Assistant"]),
    ("Care & reporting", ["Professional Review", "HR Dashboard", "Reports"]),
    ("Project", ["About WiseOLife"]),
]


# ===========================================================================
# CACHED RESOURCES
# ===========================================================================
@st.cache_resource(show_spinner="Training the Random Forest model (one time)...")
def get_model_bundle():
    """Train once per server process and reuse everywhere."""
    return ml.train_model()


@st.cache_resource(show_spinner=False)
def get_database():
    """Create SQLite tables once. Returns True when persistence works."""
    return storage.init_db()


@st.cache_data(show_spinner=False)
def get_hr_cohort_cached(_bundle, n):
    return demo.hr_cohort(_bundle, n=n)


# ===========================================================================
# SESSION STATE
# ===========================================================================
# test_stage: "overview" (not started) -> "active" (answering) -> "review" (summary)
#             -> "done" (submitted). Answers live ONLY in st.session_state.responses;
# skipped / unanswered / progress are derived from it by wiseolife.teststate.
STAGES = ("overview", "active", "review", "done")


def init_state():
    defaults = {
        "page": "Home", "responses": qs.empty_responses(), "section_idx": 0,
        "test_stage": "overview", "passed_sections": [], "attempt_id": 0,
        "submitted_attempt": None, "confirm_restart": False,
        "pending_focus": None, "focus_nonce": 0,
        "result": None, "review": {}, "chat": [],
        "candidate_id": "WL-001", "session_history": [], "last_saved_id": None,
        "journal_session": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    # Defensive: never run with a response set that does not match the question bank.
    if not ts.responses_valid(st.session_state.responses):
        reset_assessment()
    if st.session_state.test_stage not in STAGES:
        st.session_state.test_stage = "overview"
    st.session_state.section_idx = min(max(int(st.session_state.section_idx), 0),
                                       len(qs.INSTRUMENT_ORDER) - 1)


def request_focus(question=None, nav=False):
    """One-shot request: scroll to / focus a question (or to the top when None).

    Consumed by emit_focus() after the next render, so it never re-fires on later reruns.
    nav=True also closes the overlay sidebar on phone-width screens after navigating."""
    st.session_state.focus_nonce += 1
    st.session_state.pending_focus = {"q": question, "nonce": st.session_state.focus_nonce, "nav": nav}


def goto(page_name):
    """Navigate and rerun. Landing on a page always positions the view deliberately."""
    st.session_state.page = page_name
    ss = st.session_state
    if page_name == "Assessment" and ss.test_stage == "active":
        request_focus(ts.current_question(ss.responses, ss.section_idx), nav=True)
    else:
        request_focus(None, nav=True)
    st.rerun()


def reset_assessment():
    """Clean slate: no answers, no skipped markers, back to the overview screen."""
    ss = st.session_state
    ss.responses = qs.empty_responses()
    ss.section_idx = 0
    ss.test_stage = "overview"
    ss.passed_sections = []
    ss.confirm_restart = False
    ss.review = {}
    ss.last_saved_id = None
    ss.pending_focus = None
    for key in [k for k in ss.keys() if str(k).startswith("q_")]:
        del ss[key]


def begin_test():
    """Start a NEW test or RESTART one - always at Question 1 with a clean slate."""
    reset_assessment()
    ss = st.session_state
    ss.test_stage = "active"
    ss.attempt_id += 1
    ss.submitted_attempt = None
    request_focus(1)


def resume_test():
    """Continue an unfinished test exactly where the user left it."""
    ss = st.session_state
    ss.confirm_restart = False
    request_focus(ts.current_question(ss.responses, ss.section_idx) if ss.test_stage == "active" else None)


def request_new_test():
    """'Start new assessment' buttons: never silently erase an unfinished test."""
    ss = st.session_state
    if ts.has_progress(ss.test_stage, ss.responses):
        ss.confirm_restart = True          # the Assessment page asks: Resume or Restart
    else:
        reset_assessment()
    goto("Assessment")


def jump_to_question(number):
    """Open the section containing a global question number and focus that question."""
    _key, _idx, section = ts.locate(number)
    ss = st.session_state
    ss.section_idx = section
    ss.test_stage = "active"
    ss.confirm_restart = False
    request_focus(number)
    st.rerun()


def _run_script(doc):
    """Run a tiny one-shot browser script. Uses st.iframe on current Streamlit, the older
    components API otherwise, and never lets a failure break the page."""
    try:
        if hasattr(st, "iframe"):
            st.iframe(doc, height=1)
        else:
            import streamlit.components.v1 as components
            components.html(doc, height=0)
    except Exception:
        pass


def emit_focus():
    """Run the pending one-shot scroll/focus request (if any) in the browser."""
    ss = st.session_state
    pf = ss.pending_focus
    if not pf:
        return
    ss.pending_focus = None
    q = pf["q"]
    first = "true" if q and ts.section_range(ts.locate(q)[2])[0] == q else "false"
    nav = "true" if pf.get("nav") else "false"
    _run_script(f"""<script>/* focus request {pf['nonce']} */
(function () {{
  var Q = {q if q else 'null'}, FIRST = {first}, NAV = {nav}, tries = 0;
  function closeSidebar(d) {{
    try {{
      if (!NAV || window.parent.innerWidth >= 768) return;
      var sb = d.querySelector('[data-testid="stSidebar"]');
      if (!sb || sb.getAttribute('aria-expanded') !== 'true') return;
      var b = sb.querySelector('[data-testid="stSidebarCollapseButton"] button');
      if (b) b.click();
    }} catch (e) {{}}
  }}
  function run() {{
    var d; try {{ d = window.parent.document; }} catch (e) {{ return; }}
    if (tries === 0) closeSidebar(d);
    var main = d.querySelector('[data-testid="stMain"]') || d.querySelector('section.main');
    var target = Q ? d.querySelector('[data-q="' + Q + '"]') : null;
    if (Q && !target && tries++ < 30) {{ return setTimeout(run, 80); }}
    if (!target || FIRST) {{ if (main) main.scrollTo({{top: 0}}); window.parent.scrollTo(0, 0); }}
    else {{ target.scrollIntoView({{block: 'start'}}); }}
    if (target) {{ target.setAttribute('tabindex', '-1'); target.focus({{preventScroll: true}}); }}
  }}
  run();
}})();
</script>""")


# ===========================================================================
# RESULT BUILDERS
# ===========================================================================
def build_result(scores, features, candidate_id, source):
    """Score -> predict -> package. The prediction always comes from the model."""
    prediction = ml.predict_risk(get_model_bundle(), features)
    return {"candidate_id": candidate_id, "timestamp": datetime.now().isoformat(timespec="seconds"),
            "source": source, "scores": scores, "features": features, "prediction": prediction}


def persist_result(result):
    """Save to history. Demo loads are kept in-session only and never duplicated."""
    ss = st.session_state
    if result["source"] == "demo":
        if any(h.get("source") == "demo" and h["candidate_id"] == result["candidate_id"]
               for h in ss.session_history):
            return
    else:
        get_database()
        ss.last_saved_id = storage.save_assessment(result)
    ss.session_history.append({
        "candidate_id": result["candidate_id"], "created_at": result["timestamp"],
        "source": result["source"], "risk": result["prediction"]["risk"],
        "confidence": result["prediction"]["confidence"],
        **dict(zip(config.FEATURE_NAMES, result["features"])),
    })


def run_assessment():
    scores = sc.score_all(st.session_state.responses)
    features = sc.build_feature_vector(scores)
    result = build_result(scores, features, st.session_state.candidate_id, "assessment")
    st.session_state.result = result
    persist_result(result)


def submit_assessment():
    """Score once per attempt. A second click / replay cannot create a duplicate record."""
    ss = st.session_state
    if ss.submitted_attempt != ss.attempt_id:
        run_assessment()
        ss.submitted_attempt = ss.attempt_id
    ss.test_stage = "done"
    goto("My Results")


def load_demo_candidate(candidate_id):
    features = demo.get_demo_features(candidate_id)
    scores = sc.scores_from_feature_dict(dict(zip(config.FEATURE_NAMES, features)))
    result = build_result(scores, features, candidate_id, "demo")
    st.session_state.result = result
    st.session_state.review = {}
    st.session_state.last_saved_id = None
    persist_result(result)


def require_result():
    """Friendly prompt when a page needs an assessment but none exists."""
    if st.session_state.result:
        return True
    with ui.box("wl_card_empty", border=True):
        ui.empty_state("inbox", "No assessment yet",
                       f"Complete the {config.TOTAL_QUESTIONS}-question assessment to see this page with your own "
                       "results, or load a demo profile to explore it with synthetic data.")
        _l, c1, c2, _r = st.columns([1, 2, 2, 1])
        with c1:
            if st.button("Start assessment", type="primary", key="req_new", **ui.wide(st.button),
                         help="Begins the 89-question assessment at Question 1."):
                request_new_test()
        with c2:
            if st.button("Load demo profile", key="req_demo", **ui.wide(st.button),
                         help="Loads a synthetic example profile so every page has data. Does not touch a test in progress."):
                load_demo_candidate(demo.DEFAULT_DEMO)
                st.rerun()
        st.write("")
    return False


def demo_banner(result):
    if result and result.get("source") == "demo":
        cand = demo.DEMO_CANDIDATES.get(result["candidate_id"], {})
        ui.note(f"<b>Demo profile active</b> — {html.escape(result['candidate_id'])}: "
                f"{html.escape(cand.get('title', 'sample profile'))}. These are synthetic values; the risk level shown "
                "is a genuine model prediction on those values.")


# ===========================================================================
# WISEBOT HELPERS (shared by the chat page and the in-test panel)
# ===========================================================================
def chat_context():
    """Read-only snapshot of where the user is. WiseBot can explain it but never change it."""
    ss = st.session_state
    ctx = {"page": ss.page}
    if ss.test_stage in ("active", "review"):
        _rows, summary = ts.build_status(ss.responses, set(ss.passed_sections))
        ctx["progress"] = summary
        if ss.test_stage == "active":
            ctx["section"] = qs.INSTRUMENT_ORDER[ss.section_idx]
            ctx["question"] = ts.current_question(ss.responses, ss.section_idx)
    return ctx


def ask_wisebot(question, context=None, replace_index=None):
    """Ask WiseBot. On failure store an error entry that the UI can retry."""
    context = context if context is not None else chat_context()
    with st.spinner("WiseBot is thinking..."):
        out = chatbot.safe_ask(question, st.session_state.result, context)
    entry = ({"role": "bot", "text": out["text"]} if out["ok"] else
             {"role": "error", "text": out["error"], "retry": question, "context": context})
    if replace_index is None:
        st.session_state.chat.append({"role": "user", "text": question})
        st.session_state.chat.append(entry)
    else:
        st.session_state.chat[replace_index] = entry


def render_chat_messages(prefix, limit=None):
    chat = st.session_state.chat
    start = max(0, len(chat) - limit) if limit else 0
    for i in range(start, len(chat)):
        m = chat[i]
        if m["role"] == "error":
            ui.danger(html.escape(m["text"]))
            if st.button("Retry", key=f"{prefix}_retry_{i}", **ui.icon_kw(st.button, ":material/refresh:")):
                ask_wisebot(m["retry"], m.get("context"), replace_index=i)
                st.rerun()
        else:
            ui.chat_bubble(m["text"], is_user=(m["role"] == "user"))


# ===========================================================================
# SIDEBAR
# ===========================================================================
def render_sidebar():
    ss = st.session_state
    icons = dict((name, icon) for icon, name in PAGES)
    with st.sidebar:
        ui.brand_block()
        with ui.box("wl_nav"):
            for group, names in NAV_GROUPS:
                if group:
                    ui.nav_label(group)
                for name in names:
                    active = ss.page == name
                    if st.button(name, key=f"nav_{name}", type="primary" if active else "secondary",
                                 **ui.icon_kw(st.button, icons[name]), **ui.wide(st.button)):
                        goto(name)

        with ui.box("wl_quick"):
            ui.nav_label("Quick actions")
            progress_slot = st.empty()       # filled after the page renders, so counts include this run's answers
            if st.button("Start new assessment", key="sb_new", type="primary", **ui.wide(st.button),
                         **ui.icon_kw(st.button, ":material/add:"),
                         help="Begins the 89-question assessment at Question 1. If one is unfinished you can resume or restart."):
                request_new_test()
            labels = dict(demo.demo_options())
            ids = list(labels.keys())
            chosen = st.selectbox("Demo candidate", ids, format_func=lambda c: labels[c],
                                  index=ids.index(demo.DEFAULT_DEMO), key="demo_choice",
                                  help="Synthetic example profiles for exploring the product.")
            if st.button("Load demo candidate", key="sb_demo", **ui.wide(st.button),
                         **ui.icon_kw(st.button, ":material/play_circle:")):
                load_demo_candidate(chosen)
                goto("My Results")

            result = ss.result
            if result:
                pred = result["prediction"]
                st.markdown(
                    f"<div class='wl-side-card'><div class='wl-label'>Active result</div>"
                    f"<div class='wl-side-row'><span class='wl-side-id'>{html.escape(result['candidate_id'])}</span></div>"
                    f"<div style='margin-top:8px'>{ui.risk_badge(pred['risk'], pred['confidence'], small=True)}</div>"
                    f"<div class='wl-side-meta'>{html.escape(result['source'].title())} · {result['timestamp'][:10]}</div></div>",
                    unsafe_allow_html=True)
            else:
                st.markdown("<div class='wl-side-foot'>No active result yet.</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='wl-side-foot'>v{config.VERSION} · Academic prototype · Not a medical device</div>",
                        unsafe_allow_html=True)
    return progress_slot


def render_sidebar_progress(slot):
    """Unfinished-test card in the sidebar, drawn after the page so it matches the page's own counts."""
    ss = st.session_state
    if not ts.has_progress(ss.test_stage, ss.responses):
        return
    _r, _s = ts.build_status(ss.responses, set(ss.passed_sections))
    slot.markdown(
        f"<div class='wl-side-card'><div class='wl-label'>Assessment in progress</div>"
        f"<div class='wl-side-meta' style='margin:6px 0 8px'>{_s['answered']} of {_s['total']} answered"
        f" · {_s['skipped']} skipped</div>{ui.meter(_s['percent'], 'brand', 'Assessment progress')}</div>",
        unsafe_allow_html=True)


# ===========================================================================
# PAGE: HOME
# ===========================================================================
def render_home_status():
    """Right-hand status panel: an unfinished test, the latest real result, or an honest empty state."""
    ss = st.session_state
    if ts.has_progress(ss.test_stage, ss.responses):
        _rows, summ = ts.build_status(ss.responses, set(ss.passed_sections))
        resume_q = ts.current_question(ss.responses, ss.section_idx) if ss.test_stage == "active" else None
        st.markdown(
            f"<div class='wl-label'>Assessment in progress</div>"
            f"<div class='wl-h2' style='margin-top:8px'>{summ['answered']} of {summ['total']} answered</div>"
            f"<div class='wl-small' style='margin:4px 0 12px'>{summ['skipped']} skipped · kept in this browser session"
            f"</div>{ui.meter(summ['percent'], 'brand', 'Assessment progress')}", unsafe_allow_html=True)
        label = f"Resume at question {resume_q}" if resume_q else "Resume (review screen)"
        if st.button(label, type="primary", key="home_resume", **ui.wide(st.button),
                     **ui.icon_kw(st.button, ":material/play_arrow:")):
            resume_test()
            goto("Assessment")
    elif ss.result:
        result, pred = ss.result, ss.result["prediction"]
        src = "Demo profile" if result["source"] == "demo" else "Your assessment"
        st.markdown(
            f"<div class='wl-label'>Latest result</div>"
            f"<div class='wl-h2' style='margin-top:8px'>{html.escape(result['candidate_id'])}</div>"
            f"<div class='wl-small' style='margin:2px 0 12px'>{src} · {result['timestamp'][:16].replace('T', ' ')}</div>"
            f"{ui.risk_badge(pred['risk'], pred['confidence'])}"
            f"<div class='wl-small' style='margin-top:10px'>{html.escape(config.risk_info(pred['risk'])['definition'])}</div>",
            unsafe_allow_html=True)
        if st.button("View results", key="home_view", **ui.wide(st.button),
                     **ui.icon_kw(st.button, ":material/arrow_forward:")):
            goto("My Results")
    else:
        st.markdown(
            f"<div class='wl-empty' style='padding:8px 0 4px'><div class='wl-empty-ico'>{ui.icon('clock', 22)}</div>"
            f"<div class='wl-empty-title'>No assessment yet</div><div class='wl-empty-body'>Your latest result will "
            f"appear here once you finish the assessment. It takes about {config.ESTIMATED_MINUTES} minutes and "
            f"you can pause at any point in this session.</div></div>", unsafe_allow_html=True)


def page_home():
    left, right = ui.columns([7, 4], gap="medium", align="top")
    with left:
        with ui.box("wl_welcome"):
            st.markdown(
                "<div class='wl-welcome'><div class='wl-eyebrow'>Your wellness space</div>"
                "<div class='wl-h1' role='heading' aria-level='1'>Understand your mental well-being.</div>"
                f"<p class='wl-lead'>Answer {config.TOTAL_QUESTIONS} questions from {config.N_INSTRUMENTS} established "
                "psychological instruments. WiseOLife scores them transparently, explains what stands out and "
                "suggests a wellness plan — a screening aid, not a diagnosis.</p></div>"
                "<div class='wl-welcome-actions'></div>", unsafe_allow_html=True)
            c1, c2, _ = ui.columns([1.45, 1.1, 0.45])
            with c1:
                if st.button("Start assessment", type="primary", key="home_start", **ui.wide(st.button),
                             **ui.icon_kw(st.button, ":material/arrow_forward:"),
                             help="Begin the 89-question assessment at Question 1."):
                    request_new_test()
            with c2:
                if st.button("Explore demo", key="home_demo", **ui.wide(st.button),
                             help="Load a synthetic example profile and open its results."):
                    load_demo_candidate(demo.DEFAULT_DEMO)
                    goto("My Results")
    with right:
        with ui.box("wl_status"):
            render_home_status()

    ui.stat_strip([(config.N_INSTRUMENTS, "Psychological instruments", "PSS, GAD-7, PHQ-9, DASS, MBI, Big Five"),
                   (config.TOTAL_QUESTIONS, "Assessment questions", f"About {config.ESTIMATED_MINUTES} minutes"),
                   (len(config.FEATURE_NAMES), "Model features", "Scores passed to the model"),
                   ("Random Forest", "Explainable model", f"{config.RF_N_ESTIMATORS} trees · synthetic training data")])

    ui.section("How WiseOLife works", "From questionnaire responses to a reviewed, explainable report.")
    ui.process([
        ("Answer the questionnaire", f"{config.TOTAL_QUESTIONS} items, one instrument at a time. Change any answer before you submit.",
         ["Questionnaire"]),
        ("Score each instrument", "A transparent scoring engine applies each instrument's rules and builds the feature vector.",
         ["Scoring engine", f"{len(config.FEATURE_NAMES)} features"]),
        ("Get an explained indication", "A Random Forest estimates Low, Medium or High risk and shows what shaped it.",
         ["Random Forest", "Risk prediction", "Explainable report"]),
        ("Human review and plan", "Flagged cases are routed to a reviewer; everyone gets a wellness plan and report.",
         ["Human review"]),
    ])

    ui.section("The six instruments", "Each one measures a separate dimension; none is merged into a composite.")
    ui.instrument_grid(config.INSTRUMENTS)

    ui.section("Three-tier decision support")
    ui.rows([
        ("Tier 1 · AI screening", "Questionnaire scoring plus a Random Forest risk indication over 14 features.",
         ui.badge("Automated", "brand", dot=False, small=True)),
        ("Tier 2 · Professional review", "High-risk and flagged cases are routed to a qualified reviewer who records the decision.",
         ui.badge("Human", "ok", dot=False, small=True)),
        ("Tier 3 · Reporting", "Anonymised, aggregated wellness reporting for institutional / HR decision support.",
         ui.badge("Aggregated", "neutral", dot=False, small=True)),
    ])
    st.write("")
    ui.disclaimer(config.MAIN_DISCLAIMER)


# ===========================================================================
# PAGE: ASSESSMENT
# ===========================================================================
def render_progress_header(section_idx):
    """Progress card. Counts are DERIVED from the responses, so they are always in sync."""
    ss = st.session_state
    rows, summ = ts.build_status(ss.responses, set(ss.passed_sections))
    current = ts.current_question(ss.responses, section_idx)
    inst = qs.get_instrument(qs.INSTRUMENT_ORDER[section_idx])
    steps = []
    for s, key in enumerate(qs.INSTRUMENT_ORDER):
        sec = [r for r in rows if r["key"] == key]
        answered = sum(r["answered"] for r in sec)
        done, skipped = answered == len(sec), any(r["skipped"] for r in sec)
        cls = " ".join(filter(None, ["cur" if s == section_idx else "", "done" if done else "skip" if skipped else ""]))
        mark = ui.icon("check", 12) if done else (ui.icon("alert-circle", 12) if skipped else "")
        state = "complete" if done else "has skipped questions" if skipped else f"{answered} of {len(sec)} answered"
        steps.append(f"<li class='{cls}' title='{html.escape(qs.get_instrument(key)['name'])}: {state}'>"
                     f"<div class='bar'><span style='width:{answered / len(sec) * 100:.0f}%'></span></div>"
                     f"<div class='lbl'>{mark}<span>{s + 1}</span><span class='t'>{html.escape(qs.get_instrument(key)['name'])}</span></div></li>")
    tone_sq = lambda t: f"<i style='background:{ui.TONES[t][0]}'></i>"
    st.markdown(
        f"<div class='wl-progress' aria-live='polite'>"
        f"<div class='wl-prog-top'><span class='wl-prog-t'>Section {section_idx + 1} of {len(qs.INSTRUMENT_ORDER)} · "
        f"{html.escape(inst['name'])}{ui.tip('Progress counts answered questions only. Skipped = left blank when you moved to the next section; you can return to them before submitting.')}</span>"
        f"<span class='wl-prog-q'>Question <b>{current}</b> of {config.TOTAL_QUESTIONS}</span></div>"
        f"<ol class='wl-stepper' style='--n:{len(qs.INSTRUMENT_ORDER)}' aria-label='Sections'>{''.join(steps)}</ol>"
        f"{ui.meter(summ['percent'], 'brand', 'Overall progress: answered questions')}"
        f"<div class='wl-counts' style='margin-top:10px'>"
        f"<span>{tone_sq('ok')}{summ['answered']} answered</span>"
        f"<span>{tone_sq('warn')}{summ['skipped']} skipped</span>"
        f"<span>{tone_sq('neutral')}{summ['unanswered']} not answered</span>"
        f"<span style='margin-left:auto;color:var(--wl-text-2);font-weight:600'>{summ['percent']:.0f}% complete</span></div></div>",
        unsafe_allow_html=True)


def render_section(inst_key):
    """One instrument's questions. Each question shows a live Answered/Skipped/Not answered chip."""
    ss = st.session_state
    inst = qs.get_instrument(inst_key)
    offset = qs.question_offset(inst_key)
    options = [label for _v, label in inst["scale"]]
    values = [v for v, _l in inst["scale"]]
    section_passed = inst_key in ss.passed_sections
    first, last = ts.section_range(qs.INSTRUMENT_ORDER.index(inst_key))
    st.markdown(
        f"<div class='wl-section-intro'><div><div class='wl-h2' role='heading' aria-level='2'>"
        f"{html.escape(inst['name'])} <span style='color:var(--wl-muted);font-weight:500'>· {html.escape(inst['full_name'])}</span></div>"
        f"<div class='wl-meta'>Questions {first}–{last} · {len(inst['items'])} items · answer scale "
        f"{inst['scale_min']}–{inst['scale_max']}</div></div></div>"
        f"<div class='wl-instr'>{ui.md_inline(inst['instructions'])}</div>", unsafe_allow_html=True)
    with st.expander("How to answer · answer scale", expanded=False):
        st.markdown("Pick **one** option per question - the one that fits best. There are no right or wrong answers, "
                    "and you can change an answer at any time.")
        st.markdown("**Scale:** " + " · ".join(f"`{v}` {lab}" for v, lab in inst["scale"]))
        reverse_nums = qs.reverse_item_numbers(inst_key)
        if reverse_nums:
            st.markdown(f"**Reverse scoring** applies to item(s) {', '.join(map(str, reverse_nums))} "
                        "(marked *Reverse-scored*): the engine flips them (`new_score = max_scale - original_score`) "
                        "so a higher final score always points the same way. Answer normally.")
    for i, item in enumerate(inst["items"]):
        qnum = offset + i + 1
        with ui.box(f"wlq_{qnum}"):
            head = st.empty()                      # filled AFTER the radio so the chip is never one rerun stale
            stored = ss.responses[inst_key][i]
            idx = values.index(stored) if stored in values else None
            choice = st.radio(f"Question {qnum}: {item['text']}", options, index=idx, key=f"q_{inst_key}_{i}",
                              label_visibility="collapsed", horizontal=len(options) <= 5)
            value = values[options.index(choice)] if choice is not None else None
            ss.responses[inst_key][i] = value
            state = "answered" if value is not None else ("skipped" if section_passed else "unanswered")
            marker = ui.badge("Reverse-scored", "neutral", dot=False, small=True) if item["reverse"] else ""
            head.markdown(
                f"<div class='wl-qhead' data-q='{qnum}' tabindex='-1' role='heading' aria-level='3'>"
                f"<div class='wl-qmeta'><span class='wl-qnum'>Question {qnum} of {config.TOTAL_QUESTIONS}</span>"
                f"{ui.status_chip(state)}{marker}</div>"
                f"<div class='wl-qtext'>{html.escape(item['text'])}</div></div>",
                unsafe_allow_html=True)


def _go_section(new_idx):
    ss = st.session_state
    ss.section_idx = new_idx
    request_focus(ts.section_range(new_idx)[0])
    st.rerun()


def _pass_section(key):
    """Moving past a section turns its blank questions into 'skipped' (derived, never double counted)."""
    if key not in st.session_state.passed_sections:
        st.session_state.passed_sections.append(key)


def render_chat_popover(prefix):
    """WiseBot inside the test: explains the current question/section/risk levels, read-only."""
    with st.popover("Ask WiseBot", help="Ask about this question, section or the risk levels. "
                                        "Chatting never changes your answers or progress.",
                    **ui.icon_kw(st.popover, ":material/forum:"), **ui.wide(st.popover)):
        st.caption("Read-only helper - your answers and progress are not affected.")
        ctx = chat_context()
        cols = st.columns(2)
        for i, q in enumerate(chatbot.IN_TEST_QUESTIONS):
            with cols[i % 2]:
                if st.button(q, key=f"{prefix}_q{i}", **ui.wide(st.button)):
                    ask_wisebot(q, ctx)
        with st.form(f"{prefix}_form", clear_on_submit=True):
            text = st.text_input("Your question", placeholder="e.g. explain question 5",
                                 label_visibility="collapsed")
            sent = st.form_submit_button("Send", **ui.wide(st.form_submit_button))
        if sent and text.strip():
            ask_wisebot(text.strip(), ctx)
        render_chat_messages(prefix, limit=6)


def render_overview():
    ss = st.session_state
    main, side = ui.columns([7, 4], gap="large")
    with main:
        ui.stat_strip([(config.TOTAL_QUESTIONS, "Questions"), (config.N_INSTRUMENTS, "Instruments"),
                       (config.ESTIMATED_MINUTES.replace("-", "–"), "Estimated minutes"), (len(config.FEATURE_NAMES), "Model features")])
        ui.section("What the assessment covers", "One instrument per section, always starting at Question 1.")
        body = []
        for k in qs.INSTRUMENT_ORDER:
            inst = qs.get_instrument(k)
            rev = qs.reverse_item_numbers(k)
            body.append([html.escape(inst["name"]), html.escape(inst["full_name"]), str(len(inst["items"])),
                         f"{inst['scale_min']}–{inst['scale_max']}", ", ".join(map(str, rev)) if rev else "–"])
        ui.table(["Instrument", "Measures", "Items", "Scale", "Reverse-scored items"], body, num_cols=(2, 3))
        st.write("")
        ss.candidate_id = st.text_input(
            "Candidate ID (no real name is required)", value=ss.candidate_id,
            help="Any label you like, e.g. WL-001. WiseOLife never asks for your name, email or phone number.")
        c1, c2 = ui.columns([1, 1.35])
        with c1:
            if st.button("Begin assessment", type="primary", **ui.wide(st.button),
                         **ui.icon_kw(st.button, ":material/arrow_forward:"),
                         help="Start the 89-question assessment at Question 1."):
                begin_test()
                st.rerun()
        with c2:
            if st.button("Load a demo candidate instead", **ui.wide(st.button),
                         help="See the full product with a synthetic profile instead of answering 89 questions."):
                load_demo_candidate(demo.DEFAULT_DEMO)
                goto("My Results")
    with side:
        ui.notice("<ul><li>The assessment always starts at <b>Question 1</b>.</li>"
                  "<li>Your answers are kept in this browser session until you submit.</li>"
                  "<li>You can go back, change answers and review skipped questions before submitting.</li></ul>",
                  "info", title="Before you begin")
        ui.notice(html.escape(config.MAIN_DISCLAIMER), "neutral", title="Not a diagnosis", ico="shield")
        ui.notice(html.escape(config.WORDING_NOTICE), "neutral", title="About the wording", ico="doc")


def render_restart_choice():
    """Start-new vs restart vs resume: asked explicitly, never decided silently."""
    ss = st.session_state
    _rows, summ = ts.build_status(ss.responses, set(ss.passed_sections))
    resume_q = ts.current_question(ss.responses, ss.section_idx) if ss.test_stage == "active" else None
    ui.warn(f"{summ['answered']} of {summ['total']} answered, {summ['skipped']} skipped. Resume it, or restart from "
            "Question 1 (this erases your current answers).", title="You have an unfinished assessment")
    c1, c2, _ = ui.columns([1, 1, 1])
    with c1:
        label = f"Resume at question {resume_q}" if resume_q else "Resume (review screen)"
        if st.button(label, type="primary", key="choice_resume", **ui.wide(st.button),
                     **ui.icon_kw(st.button, ":material/play_arrow:"),
                     help="Keep every saved answer and continue where you stopped."):
            resume_test()
            st.rerun()
    with c2:
        if st.button("Restart from question 1", key="choice_restart", **ui.wide(st.button),
                     **ui.icon_kw(st.button, ":material/restart_alt:"),
                     help="Erase the current answers and start a fresh attempt at Question 1."):
            begin_test()
            st.rerun()


def _saved_feedback():
    msg = "Progress saved in this browser session. Come back to this page any time to resume."
    if hasattr(st, "toast"):
        st.toast(msg, **ui.icon_kw(st.toast, ":material/check_circle:"))
    else:
        st.success(msg)


def render_active():
    ss = st.session_state
    idx = ss.section_idx
    inst_key = qs.INSTRUMENT_ORDER[idx]
    progress_slot = st.container()          # filled after the section renders (reflects this run's answers)
    top = ui.columns([3, 1], align="center")
    top[0].caption(f"Section {idx + 1} of {len(qs.INSTRUMENT_ORDER)} · answers are kept in this browser session "
                   "as you select them")
    with top[1]:
        render_chat_popover("chat_test")
    render_section(inst_key)
    with progress_slot:
        render_progress_header(idx)
    blank = sum(1 for v in ss.responses[inst_key] if v is None)
    if blank:
        ui.warn(f"{blank} question(s) in this section are blank. If you continue they are counted as "
                "<b>skipped</b> — you can come back to them from the review screen before submitting.")
    is_last = idx == len(qs.INSTRUMENT_ORDER) - 1
    with ui.box("wl_qnav"):
        c1, c2, c3, c4 = ui.columns([1, 1, 1.25, 1.35])
        with c1:
            if st.button("Back", disabled=idx == 0, **ui.wide(st.button), **ui.icon_kw(st.button, ":material/arrow_back:"),
                         help="Previous section. Your answers are kept."):
                _go_section(idx - 1)
        with c2:
            if st.button("Restart", **ui.wide(st.button), **ui.icon_kw(st.button, ":material/restart_alt:"),
                         help="Asks for confirmation, then restarts at Question 1."):
                ss.confirm_restart = True
                st.rerun()
        with c3:
            if st.button("Save & continue", **ui.wide(st.button), **ui.icon_kw(st.button, ":material/check:"),
                         help="Answers are already saved in this browser session as you select them."):
                _saved_feedback()
        with c4:
            if not is_last:
                if st.button("Next section", type="primary", **ui.wide(st.button),
                             **ui.icon_kw(st.button, ":material/arrow_forward:"),
                             help="Next section. Blank questions here will be marked as skipped."):
                    _pass_section(inst_key)
                    _go_section(idx + 1)
            elif st.button("Review & submit", type="primary", **ui.wide(st.button),
                           **ui.icon_kw(st.button, ":material/fact_check:"),
                           help="See answered / skipped counts and submit."):
                _pass_section(inst_key)
                ss.test_stage = "review"
                request_focus(None)
                st.rerun()


def render_review():
    ss = st.session_state
    rows, summ = ts.build_status(ss.responses, set(ss.passed_sections))
    ui.section("Review before submitting", "Check what is answered, skipped or not answered. You can still go back.",
               help="Skipped = left blank when you moved on. Skipped and unanswered questions are scored at the scale "
                    "default and the result is marked incomplete.", tight=True)
    ui.stat_strip([(f"{summ['answered']} / {summ['total']}", "Answered", f"{summ['percent']:.0f}% complete"),
                   (summ["skipped"], "Skipped", "Left blank when moving on"),
                   (summ["unanswered"], "Not answered", "Not reached yet")])
    st.markdown(ui.meter(summ["percent"], "brand", "Answered questions"), unsafe_allow_html=True)
    blank_rows = [r for r in rows if not r["answered"]]
    if not blank_rows:
        ui.ok(f"All {summ['total']} questions are answered. You are ready to submit.")
    else:
        ui.warn(f"<b>{len(blank_rows)} question(s) are blank.</b> They will not be treated as answered; they are scored "
                "at the scale default and the result will be marked <b>incomplete</b>.")
        first_skipped = next((r for r in blank_rows if r["skipped"]), blank_rows[0])
        if st.button(f"Go to first {'skipped' if first_skipped['skipped'] else 'unanswered'} question "
                     f"(Q{first_skipped['number']})", type="primary", key="rev_first",
                     **ui.icon_kw(st.button, ":material/undo:")):
            jump_to_question(first_skipped["number"])
        with ui.box("wl_card_review", border=True):
            for key in qs.INSTRUMENT_ORDER:
                inst_rows = [r for r in blank_rows if r["key"] == key]
                if not inst_rows:
                    continue
                sk = [f"Q{r['number']}" for r in inst_rows if r["skipped"]]
                un = [f"Q{r['number']}" for r in inst_rows if r["unanswered"]]
                text = " · ".join(filter(None, [("Skipped: " + ", ".join(sk)) if sk else "",
                                                ("Not answered: " + ", ".join(un)) if un else ""]))
                cols = ui.columns([5, 1], align="center")
                cols[0].markdown(f"<div class='wl-row-t'>{html.escape(qs.get_instrument(key)['name'])}</div>"
                                 f"<div class='wl-row-d'>{html.escape(text)}</div>", unsafe_allow_html=True)
                if cols[1].button("Go", key=f"rev_go_{key}", help=f"Open the first blank {qs.get_instrument(key)['name']} question",
                                  **ui.wide(st.button)):
                    jump_to_question(inst_rows[0]["number"])
    confirmed = True
    if blank_rows:
        confirmed = st.checkbox(f"I understand {len(blank_rows)} blank question(s) will be left unscored and the result "
                                "marked incomplete.", key="rev_confirm")
    c1, c2, _ = ui.columns([1, 1, 1.4])
    with c1:
        if st.button("Back to questions", **ui.wide(st.button), **ui.icon_kw(st.button, ":material/arrow_back:")):
            ss.test_stage = "active"
            request_focus(ts.current_question(ss.responses, ss.section_idx))
            st.rerun()
    with c2:
        if st.button("Submit & analyse", type="primary", disabled=not confirmed, **ui.wide(st.button),
                     **ui.icon_kw(st.button, ":material/check:"),
                     help="Scores your answers, builds the 14-feature vector and runs the model."):
            submit_assessment()


def render_done():
    ui.ok("Your results are ready.", title="Your assessment has been submitted")
    c1, c2, _ = ui.columns([1, 1, 1])
    with c1:
        if st.button("View my results", type="primary", key="done_results", **ui.wide(st.button),
                     **ui.icon_kw(st.button, ":material/arrow_forward:")):
            goto("My Results")
    with c2:
        if st.button("Start a new assessment", key="done_new", **ui.wide(st.button),
                     help="Begins a fresh test at Question 1. Your submitted results stay available."):
            reset_assessment()
            goto("Assessment")


def page_assessment():
    ss = st.session_state
    ui.page_header("Wellness assessment",
                   "Six instruments, one section at a time. Your answers stay in this browser session.",
                   eyebrow="Assessment")
    if ss.confirm_restart and ts.has_progress(ss.test_stage, ss.responses):
        render_restart_choice()
    elif ss.test_stage == "active":
        render_active()
    elif ss.test_stage == "review":
        render_review()
    elif ss.test_stage == "done":
        render_done()
    else:
        ss.confirm_restart = False
        render_overview()


# ===========================================================================
# PAGE: MY RESULTS
# ===========================================================================
def _result_meta(result):
    src = ui.badge("Demo profile", "brand", dot=False, small=True) if result["source"] == "demo" else \
        ui.badge("Submitted assessment", "neutral", dot=False, small=True)
    return [f"Candidate <b style='color:var(--wl-text)'>{html.escape(result['candidate_id'])}</b>",
            f"{ui.icon('clock', 14)} {result['timestamp'][:16].replace('T', ' ')}", src]


def _toggle(label, value, key, help=None):
    widget = st.toggle if hasattr(st, "toggle") else st.checkbox
    return widget(label, value=value, key=key, help=help)


def page_results():
    result = st.session_state.result
    if not result:
        ui.page_header("My results", "Your measured scores, the model's screening estimate and each instrument in detail.",
                       eyebrow="Assessment")
        require_result()
        return
    scores, pred = result["scores"], result["prediction"]
    ui.page_header("Your wellness overview",
                   "Measured scores from your answers first, then the model's screening estimate.",
                   eyebrow="My results", meta=_result_meta(result))
    demo_banner(result)
    if not scores.get("complete", True):
        ui.warn(f"{scores['missing_total']} of {config.TOTAL_QUESTIONS} questions were unanswered and scored at the "
                "scale default. Interpret with caution.", title="This assessment is incomplete")
    if scores["phq9"].get("safety_flag"):
        ui.warn(html.escape(config.SAFETY_MESSAGE), title="Safety notice")

    ui.section("Measured scores", "Computed directly from your answers using each instrument's own scoring rules.")
    cards = sc.summary_cards(scores)
    pcts = [scores["pss"]["score"] / 40 * 100, scores["gad7"]["score"] / 21 * 100,
            scores["phq9"]["score"] / 27 * 100, scores["dass"]["stress"] / 42 * 100,
            scores["mbi"]["emotional_exhaustion"] / 54 * 100, scores["big5"]["neuroticism"] / 5 * 100]
    ui.score_grid([dict(card, pct=pct) for card, pct in zip(cards, pcts)])

    ui.section("Model estimate", "A Random Forest screening indication computed from the 14 scores below. "
                                 "It is an estimate, not a diagnosis.")
    c1, c2 = ui.columns([5, 6], gap="medium")
    with c1:
        ui.risk_card(pred["risk"], pred["confidence"], config.AI_DISCLAIMER)
    with c2:
        probs = pred["probabilities"]
        ui.plot(ui.chart_probabilities(probs),
                "Probabilities: " + " · ".join(f"{config.risk_label(c)} {probs[c] * 100:.1f}%" for c in config.RISK_CLASSES))
        with st.expander("What do the risk levels R1–R3 mean?"):
            ui.risk_legend()
    if pred["risk"] == "HIGH":
        ui.warn("Status: Pending Review (Tier 2).", title="Professional review recommended")

    ui.section("Score overview", "Every scale as a share of its maximum, so different ranges can be compared.")
    d, m = scores["dass"], scores["mbi"]
    ui.plot(ui.chart_scores_bar(scores),
            f"PSS-10 {scores['pss']['score']}/40 · GAD-7 {scores['gad7']['score']}/21 · PHQ-9 {scores['phq9']['score']}/27 · "
            f"DASS depression {d['depression']}/42, anxiety {d['anxiety']}/42, stress {d['stress']}/42 · "
            f"MBI exhaustion {m['emotional_exhaustion']}/54, depersonalization {m['depersonalization']}/30, "
            f"accomplishment {m['personal_accomplishment']}/48 (higher is better).")

    ui.section("Model input: 14 features", "The exact numbers passed to the Random Forest classifier.",
               help="A feature is one number the model uses. WiseOLife turns 89 answers into these 14 scores; "
                    "the model sees only these.")
    fmap = dict(zip(config.FEATURE_NAMES, result["features"]))
    groups = []
    for group_name, _icon, names in config.FEATURE_GROUPS:
        items = []
        for name in names:
            lo, hi = config.FEATURE_RANGES[name]
            items.append((config.FEATURE_LABELS[name].replace("Big Five ", "").replace("MBI ", ""), f"{lo}–{hi}", fmap[name], isinstance(hi, float),
                          config.FEATURE_HELP[name]))
        groups.append((group_name, items))
    ui.feature_groups(groups)
    ui.label("Model input vector (FEATURE_NAMES order)")
    ui.feature_vector_block(result["features"])
    st.caption("Order: " + " · ".join(f"{i}. {config.FEATURE_SHORT[n]}" for i, n in enumerate(config.FEATURE_NAMES, 1)))

    ui.section("Instrument detail", "Raw and adjusted scores, interpretation bands and scoring notes.")
    tabs = st.tabs(["PSS-10", "GAD-7", "PHQ-9", "DASS-21", "MBI burnout", "Big Five"])
    with tabs[0]:
        p = scores["pss"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Raw score (no reversal)", p["raw"] if p["raw"] is not None else "n/a (demo)",
                  help="Simple sum of your 10 answers before any items are flipped.")
        c2.metric("Adjusted score (reported)", f"{p['score']} / 40",
                  help="Score after reverse scoring - this is the number used by the model.")
        c3.metric("Interpretation", p["level"], help="Low 0-13 · Moderate 14-26 · High 27-40.")
        ui.note(f"<b>Reverse scoring applied</b> to PSS items {', '.join(map(str, p['reverse_items']))}. "
                f"Formula: <code>new_score = max_scale - original_score</code>. Bands: 0-13 Low · 14-26 Moderate · 27-40 High.")
        st.caption("This build follows the WiseOLife project specification (items 4-8 reversed). The widely "
                   "published PSS-10 reverses items 4, 5, 7, 8. The list is one constant (`PSS_REVERSE_ITEMS` in "
                   "wiseolife/questions.py). This is a configurable academic implementation, not official clinical scoring.")
    with tabs[1]:
        g = scores["gad7"]
        c1, c2 = st.columns(2)
        c1.metric("GAD-7 total", f"{g['score']} / 21", help="Sum of 7 items, each scored 0-3.")
        c2.metric("Interpretation", g["level"], help="0-4 Minimal · 5-9 Mild · 10-14 Moderate · 15-21 Severe.")
        st.markdown(ui.meter(g["score"] / 21 * 100, ui.tone_of(g["level"]), "GAD-7 score"), unsafe_allow_html=True)
        st.caption("Bands: 0-4 Minimal · 5-9 Mild · 10-14 Moderate · 15-21 Severe")
    with tabs[2]:
        p = scores["phq9"]
        c1, c2 = st.columns(2)
        c1.metric("PHQ-9 total", f"{p['score']} / 27", help="Sum of 9 items, each scored 0-3.")
        c2.metric("Interpretation", p["level"], help="0-4 Minimal · 5-9 Mild · 10-14 Moderate · 15-19 Moderately Severe · 20-27 Severe.")
        st.markdown(ui.meter(p["score"] / 27 * 100, ui.tone_of(p["level"]), "PHQ-9 score"), unsafe_allow_html=True)
        st.caption("Bands: 0-4 Minimal · 5-9 Mild · 10-14 Moderate · 15-19 Moderately Severe · 20-27 Severe")
        if p.get("safety_flag"):
            ui.warn(html.escape(config.SAFETY_MESSAGE), title="Safety notice")
        else:
            st.caption("Item 9 (self-harm related) was not elevated in this response set.")
    with tabs[3]:
        d = scores["dass"]
        ui.plot(ui.chart_dass(d), f"Depression {d['depression']}/42 ({d['depression_level']}) · Anxiety {d['anxiety']}/42 "
                                  f"({d['anxiety_level']}) · Stress {d['stress']}/42 ({d['stress_level']}).")
        c1, c2, c3 = st.columns(3)
        c1.metric("Depression", f"{d['depression']} / 42", d["depression_level"], delta_color="off")
        c2.metric("Anxiety", f"{d['anxiety']} / 42", d["anxiety_level"], delta_color="off")
        c3.metric("Stress", f"{d['stress']} / 42", d["stress_level"], delta_color="off")
        st.caption(f"Each subscale = sum of its 7 items × {d['multiplier']} (standard DASS-21 convention).")
    with tabs[4]:
        m = scores["mbi"]
        ui.plot(ui.chart_mbi(m), f"Emotional exhaustion {m['emotional_exhaustion']}/54 ({m['ee_level']}) · "
                                 f"Depersonalization {m['depersonalization']}/30 ({m['dp_level']}) · Personal accomplishment "
                                 f"{m['personal_accomplishment']}/48 ({m['pa_level']}, higher is better).")
        ui.score_grid([
            dict(title="Emotional Exhaustion", value=f"{m['emotional_exhaustion']} / 54", level=m["ee_level"],
                 caption="Higher = more concerning", pct=m["emotional_exhaustion"] / 54 * 100),
            dict(title="Depersonalization", value=f"{m['depersonalization']} / 30", level=m["dp_level"],
                 caption="Higher = more concerning", pct=m["depersonalization"] / 30 * 100),
            dict(title="Personal Accomplishment", value=f"{m['personal_accomplishment']} / 48", level=m["pa_level"],
                 caption="Higher = POSITIVE", pct=m["personal_accomplishment"] / 48 * 100, positive=True),
        ])
        ui.ok("The three burnout dimensions are kept separate - in interpretation and as three of the 14 model "
              "features. <b>Personal Accomplishment is positive</b>: high is good, only LOW is a concern.")
    with tabs[5]:
        b = scores["big5"]
        c1, c2 = ui.columns([3, 2], gap="medium")
        with c1:
            ui.plot(ui.chart_big5_radar(b), "Openness {openness}, Conscientiousness {conscientiousness}, Extraversion "
                                            "{extraversion}, Agreeableness {agreeableness}, Neuroticism {neuroticism} "
                                            "(each 1-5).".format(**b))
        with c2:
            for t, letter in [("openness", "O"), ("conscientiousness", "C"), ("extraversion", "E"),
                              ("agreeableness", "A"), ("neuroticism", "N")]:
                st.metric(f"{letter} - {qs.BIG5_TRAIT_NAMES[letter]}", f"{b[t]} / 5.0", b["levels"][letter],
                          delta_color="off")
        st.caption(f"Each trait = mean of 4 items on a 1-5 scale. Reverse-scored items: "
                   f"{', '.join(map(str, b['reverse_items']))} (new = 6 - original).")
    st.write("")
    ui.disclaimer(config.MAIN_DISCLAIMER)


# ===========================================================================
# PAGE: AI INSIGHTS
# ===========================================================================
def page_ai_insights():
    bundle = get_model_bundle()
    metrics = bundle["metrics"]
    ui.page_header("AI insights & explainability",
                   "Why the model produced your result, how it was built, and how it performs on the synthetic dataset.",
                   eyebrow="Insights")
    ui.stat_strip([("Random Forest", "Algorithm", f"{config.RF_N_ESTIMATORS} trees · max_depth={config.RF_MAX_DEPTH}"),
                   (f"{config.N_SYNTHETIC_RECORDS:,}", "Training records", "Synthetic wellness profiles"),
                   (str(metrics["n_features"]), "Features", "All dimensions kept separate"),
                   ("Low / Medium / High", "Classes", "Screening risk indication")])

    ui.section("Your result, explained", "The main finding first, then what shaped it.")
    result = st.session_state.result
    if not result:
        with ui.box("wl_card_ins", border=True):
            ui.empty_state("sparkle", "No result to explain yet",
                           "Load a demo candidate or complete an assessment to see a profile-specific explanation.")
            _l, c, _r = st.columns([1.3, 1, 1.3])
            with c:
                if st.button("Load demo candidate", key="ins_demo", type="primary", **ui.wide(st.button)):
                    load_demo_candidate(demo.DEFAULT_DEMO)
                    st.rerun()
            st.write("")
    else:
        pred = result["prediction"]
        info = config.risk_info(pred["risk"])
        local = ml.local_contribution(bundle, result["features"], 8)
        c1, c2 = ui.columns([5, 6], gap="medium")
        with c1:
            ui.insight(f"{ui.risk_badge(pred['risk'])}<div style='margin-top:10px'>The model returned a "
                       f"<b>{html.escape(info['name'].lower())}</b> indication with {pred['confidence'] * 100:.1f}% "
                       f"model confidence for {html.escape(result['candidate_id'])}.</div>",
                       ml.explanation_sentence(bundle, result["features"], pred["risk"]),
                       "Random Forest prediction on this profile's 14 feature values. The chart weighs each feature's "
                       "global importance by how far the value sits from the training average (direction-aware).")
            ui.disclaimer(config.AI_DISCLAIMER)
        with c2:
            raising = [r["label"] for r in local if r["contribution"] > 0][:3]
            protect = [r["label"] for r in local if r["contribution"] < 0][:2]
            ui.plot(ui.chart_local_influence(local),
                    "Raising the indication most: " + (", ".join(raising) or "none") +
                    ". Most protective: " + (", ".join(protect) or "none") + ".")
        st.caption("Local view = each feature's global importance × how far your value sits from the training average "
                   "(direction-aware). A lightweight stand-in for SHAP: association, not causation.")

    ui.section("Evaluation metrics", "How well the model reproduces the project's labelling rule on held-out data.")
    ui.warn("These are evaluation metrics on a held-out split of the <b>synthetic demo dataset</b>. They measure how "
            "well the model reproduces the project's rule-based labelling. They are <b>not</b> clinical accuracy.")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Accuracy", f"{metrics['accuracy'] * 100:.2f}%",
              help="Share of test profiles given the same label as the labelling rule. Synthetic data only.")
    m2.metric("Precision (macro)", f"{metrics['precision'] * 100:.2f}%",
              help="When the model says a class, how often it is right - averaged over LOW/MEDIUM/HIGH.")
    m3.metric("Recall (macro)", f"{metrics['recall'] * 100:.2f}%",
              help="Of all profiles truly in a class, how many the model finds - averaged over classes.")
    m4.metric("F1 score (macro)", f"{metrics['f1'] * 100:.2f}%",
              help="Balance of precision and recall (their harmonic mean), averaged over classes.")
    st.caption(f"Train / test split: {metrics['train_size']} / {metrics['test_size']}, stratified, "
               f"random_state={config.RANDOM_STATE}.")
    c1, c2 = st.columns(2)
    with c1:
        ui.plot(ui.chart_confusion(bundle["confusion_matrix"], bundle["confusion_labels"]),
                "Rows are the rule's label, columns the model's prediction; the diagonal counts agreements.")
    with c2:
        counts = bundle["dataset"]["risk"].value_counts()
        ui.plot(ui.chart_dataset_distribution(bundle["dataset"]),
                "Profiles per class: " + " · ".join(f"{config.risk_label(c)} {int(counts[c])}"
                                                    for c in config.RISK_CLASSES if c in counts.index) + ".")
    with st.expander("Full classification report (scikit-learn)"):
        st.code(bundle["report_text"], language="text")

    ui.section("What drives the model overall", "Random Forest feature importance across all 14 inputs.",
               help="Feature importance shows how much each input helped the forest separate the classes overall. "
                    "It shows association, not cause.")
    top3 = bundle["importance"][:3]
    ui.plot(ui.chart_importance(bundle["importance"]),
            "Most important: " + ", ".join(f"{r['label']} ({r['percent']:.1f}%)" for r in top3) + ".")
    with st.expander("Feature importance table"):
        st.dataframe(pd.DataFrame([{"Rank": i, "Feature": r["label"], "Importance": f"{r['percent']:.2f}%"}
                                   for i, r in enumerate(bundle["importance"], 1)]),
                     hide_index=True, **ui.wide(st.dataframe))

    ui.section("Risk levels", "Number, name and definition of each risk class the model predicts.")
    ui.risk_legend()

    ui.section("How the synthetic labels were created", "A transparent points rule - nothing about the labels is random.")
    rule_rows = [[html.escape(r), f"≥ {t}", f"+{p}"] for _n, r, t, p in ml.RISK_RULE_TABLE] + \
                [[html.escape(r), f"≤ {t}", f"+{p}"] for _n, r, t, p in ml.RISK_RULE_TABLE_INVERTED]
    ui.table(["Indicator", "Threshold", "Risk points"], rule_rows, num_cols=(1, 2))
    ui.note(f"Total points ≥ <b>{ml.HIGH_THRESHOLD}</b> → HIGH · ≥ <b>{ml.MEDIUM_THRESHOLD}</b> → MEDIUM · otherwise LOW.")
    if result:
        fdict = dict(zip(config.FEATURE_NAMES, result["features"]))
        pts, reasons = ml.risk_points_breakdown(fdict)
        with ui.box("wl_card_rule", border=True):
            st.markdown(f"<div class='wl-label'>Rule check · {html.escape(result['candidate_id'])}</div>"
                        f"<div class='wl-h3' style='margin-top:6px'>{pts} point(s) → "
                        f"<code>{ml.label_risk(fdict)}</code></div>", unsafe_allow_html=True)
            if reasons:
                ui.checklist([f"{html.escape(reason)} → <b>+{p}</b>" for reason, p in reasons], escape=False)
            else:
                st.markdown("<div class='wl-small'>No indicator crossed an elevated threshold.</div>", unsafe_allow_html=True)
        st.caption("The rule generated the *training labels*; the result page shows the *model's* prediction. "
                   "They usually agree; where they differ the model learned patterns across all 14 features.")
    st.write("")
    ui.disclaimer(config.MAIN_DISCLAIMER)


# ===========================================================================
# PAGE: WELLNESS PLAN
# ===========================================================================
PRIORITY = {2: ("High priority", "err"), 1: ("Worth attention", "warn"), 0: ("Maintenance", "ok")}


def page_wellness_plan():
    ui.page_header("Your wellness plan", "General wellness suggestions based on your scores - not medical treatment.",
                   eyebrow="Insights")
    if not require_result():
        return
    result = st.session_state.result
    pred = result["prediction"]
    plan = rec.generate_recommendations(result["scores"], pred)
    demo_banner(result)
    if plan["safety"]:
        ui.warn(html.escape(plan["safety_message"]), title="Safety notice")
    summary = plan["summary"].replace(config.RISK_EMOJI[pred["risk"]] + " ", "", 1)
    st.markdown(f"<div class='wl-card'><div class='wl-card-title'>Overview</div>"
                f"<div style='margin:10px 0 8px'>{ui.risk_badge(pred['risk'], pred['confidence'])}</div>"
                f"<div class='wl-card-sub' style='font-size:14.5px;color:var(--wl-text-2)'>{html.escape(summary)}</div></div>",
                unsafe_allow_html=True)

    main, side = ui.columns([7, 4], gap="large")
    with main:
        ui.section("Focus areas", "Ordered by priority. Each area explains why it was suggested.")
        for block in plan["blocks"]:
            text, tone = PRIORITY.get(block["severity"], PRIORITY[0])
            ui.plan_block(block["title"], block["why"], block["actions"], ui.badge(text, tone, small=True))
    with side:
        if plan["strengths"]:
            ui.section("Strengths identified", "Resources you can lean on.")
            with ui.box("wl_card_strengths", border=True):
                ui.checklist(plan["strengths"], tone="ok", ico="check-circle")
        if plan["review_recommended"]:
            ui.section("Next step")
            ui.warn("This profile meets the Tier-2 routing criteria.", title="Professional review recommended")
            if st.button("Go to professional review", type="primary", **ui.wide(st.button),
                         **ui.icon_kw(st.button, ":material/arrow_forward:")):
                goto("Professional Review")
    st.write("")
    ui.disclaimer(plan["disclaimer"] + " " + config.MAIN_DISCLAIMER)


# ===========================================================================
# PAGE: PROGRESS TRACKING
# ===========================================================================
def _stored_history():
    """Real saved records: stored history if >=2 records, else this session's history."""
    get_database()
    stored = [r for r in storage.load_assessments(limit=50)]
    if len(stored) < 2:
        stored = list(reversed(st.session_state.session_history))
    return stored


def _history_rows(include_sample=False):
    """Real history (oldest first) when >=2 records exist. Otherwise a clearly-labelled sample series,
    only when asked for. Returns (rows or None, is_sample)."""
    stored = _stored_history()
    if len(stored) >= 2:
        rows = []
        for r in reversed(stored):  # oldest first
            row = {"date": str(r["created_at"])[:10], "risk": r.get("risk", "")}
            row.update({n: r.get(n, 0) for n in config.FEATURE_NAMES})
            rows.append(row)
        return rows, False
    if not include_sample:
        return None, False
    cid = (st.session_state.result or {}).get("candidate_id", demo.DEFAULT_DEMO)
    if cid not in demo.DEMO_CANDIDATES:
        cid = demo.DEFAULT_DEMO
    return demo.demo_progress_series(cid), True


def _demo_active():
    return (st.session_state.result or {}).get("source") == "demo"


def page_progress():
    ui.page_header("Progress tracking", "Track how your instrument scores change between assessments.",
                   eyebrow="Insights")
    rows, is_demo = _history_rows()
    if rows is None:
        n = len(_stored_history())
        with ui.box("wl_card_prog", border=True):
            ui.empty_state("trend", "Not enough history yet",
                           f"Trends appear once two or more assessments have been completed. "
                           f"{n} record{'s' if n != 1 else ''} saved so far.")
            _l, c, _r = st.columns([1.2, 1, 1.2])
            with c:
                show = _toggle("Preview with sample data", _demo_active(), "prog_sample",
                               help="Shows a clearly labelled synthetic history. Your own records are never mixed in.")
            st.write("")
        if not show:
            return
        rows, is_demo = _history_rows(include_sample=True)
        ui.note("<b>Sample data.</b> These charts use a clearly labelled synthetic history that ends at the current "
                "demo profile. Complete two or more assessments to see your own trend.")
    latest, first = rows[-1], rows[0]
    ui.section("Latest vs first record", tight=True)
    for (key, label), col in zip([("pss_score", "PSS Stress"), ("gad7_score", "GAD-7 Anxiety"),
                                  ("phq9_score", "PHQ-9 Depression"), ("mbi_emotional_exhaustion", "Burnout (EE)")],
                                 st.columns(4)):
        col.metric(label, f"{latest[key]:g}", f"{latest[key] - first[key]:+g} since first record", delta_color="inverse")
    ui.plot(ui.chart_trend(rows, [("pss_score", "PSS (0-40)", ui.SERIES[0]), ("gad7_score", "GAD-7 (0-21)", ui.SERIES[1]),
                                  ("phq9_score", "PHQ-9 (0-27)", ui.SERIES[2])],
                           "Stress, anxiety and depression trend"),
            f"{len(rows)} records from {first['date']} to {latest['date']}. Latest: PSS {latest['pss_score']:g}, "
            f"GAD-7 {latest['gad7_score']:g}, PHQ-9 {latest['phq9_score']:g}.")
    c1, c2 = st.columns(2)
    with c1:
        ui.plot(ui.chart_trend(rows, [("dass_depression", "Depression", ui.SERIES[2]), ("dass_anxiety", "Anxiety", ui.SERIES[1]),
                                      ("dass_stress", "Stress", ui.SERIES[0])], "DASS-21 subscale trend", "Score (0-42)"))
    with c2:
        ui.plot(ui.chart_trend(rows, [("mbi_emotional_exhaustion", "Emotional Exhaustion", ui.SERIES[2]),
                                      ("mbi_depersonalization", "Depersonalization", ui.SERIES[1]),
                                      ("mbi_personal_accomplishment", "Personal Accomplishment ↑ good", ui.SERIES[3])],
                               "Burnout dimension trend"))
    ui.section("Assessment history")
    st.dataframe(pd.DataFrame([{
        "Date": r["date"], "PSS": r["pss_score"], "GAD-7": r["gad7_score"], "PHQ-9": r["phq9_score"],
        "DASS-S": r["dass_stress"], "MBI EE": r["mbi_emotional_exhaustion"],
        "MBI PA": r["mbi_personal_accomplishment"], "Neuroticism": r["neuroticism"],
        "Risk": config.risk_label(r["risk"]) if r.get("risk") in config.RISK_CLASSES else "demo"} for r in reversed(rows)]), hide_index=True, **ui.wide(st.dataframe))
    if storage.db_available():
        s = storage.stats()
        st.caption(f"Local database: {s['assessments']} assessment(s), {s['journal']} journal entr(y/ies) in wiseolife_data.db.")
    else:
        ui.warn("Local SQLite storage is not writable here, so history is kept for this browser session only.")


# ===========================================================================
# PAGE: WELLNESS JOURNAL
# ===========================================================================
def page_journal():
    ui.page_header("Wellness journal", "A short daily check-in. Mood and stress are self-rated 1-10.",
                   eyebrow="Personal wellness")
    get_database()
    left, right = ui.columns([5, 7], gap="large")
    with left:
        ui.section("New entry", "A sentence or two is enough.", tight=True)
        with st.form("journal_form", clear_on_submit=True):
            entry_date = st.date_input("Date", value=date.today())
            mood = st.slider("Mood (1 = very low, 10 = very good)", 1, 10, 6, help="Your overall mood today.")
            stress = st.slider("Stress (1 = none, 10 = extreme)", 1, 10, 5, help="How stressed you felt today.")
            sleep_hours = st.slider("Hours of sleep last night", 0.0, 12.0, 7.0, 0.5, help="Hours slept, in half-hour steps.")
            note = st.text_area("How are you feeling today?", placeholder="A sentence or two is enough...")
            submitted = st.form_submit_button("Save entry", type="primary", **ui.wide(st.form_submit_button),
                                              **ui.icon_kw(st.form_submit_button, ":material/check:"))
        if submitted:
            row_id = storage.save_journal_entry(entry_date, mood, stress, sleep_hours, note)
            st.session_state.journal_session.append({"entry_date": str(entry_date), "mood": mood, "stress": stress,
                                                     "sleep_hours": sleep_hours, "note": note})
            st.success("Entry saved to the local database." if row_id else "Entry saved for this session.")
        st.caption("Entries go to the local SQLite file (wiseolife_data.db) on the machine running the app when it is "
                   "writable, otherwise they are kept for this session only. The file is not encrypted.")
    entries = storage.load_journal() or list(st.session_state.journal_session)
    with right:
        ui.section("Your check-ins", "Averages and trends from your entries.", tight=True)
        using_demo = False
        if len(entries) < 3:
            using_demo = _toggle("Include sample entries", _demo_active(), "journal_sample",
                                 help="Adds clearly labelled synthetic entries so the chart has something to show.")
        if using_demo:
            entries = demo.demo_journal_entries() + entries
        entries = sorted(entries, key=lambda e: str(e["entry_date"]))
        if not entries:
            with ui.box("wl_card_journal", border=True):
                ui.empty_state("book", "No entries yet",
                               "Your mood, stress and sleep trends appear here after your first check-in.")
                st.write("")
        else:
            if using_demo:
                ui.note("<b>Sample entries included.</b> Rows marked “demo” are synthetic; rows marked “you” are yours.")
            c1, c2, c3 = st.columns(3)
            c1.metric("Average mood", f"{sum(e['mood'] for e in entries) / len(entries):.1f} / 10")
            c2.metric("Average stress", f"{sum(e['stress'] for e in entries) / len(entries):.1f} / 10")
            c3.metric("Average sleep", f"{sum(e['sleep_hours'] for e in entries) / len(entries):.1f} h")
            ui.plot(ui.chart_journal(entries),
                    f"{len(entries)} entries from {entries[0]['entry_date']} to {entries[-1]['entry_date']}.")
    if entries:
        ui.section("Entries")
        st.dataframe(pd.DataFrame([{"Date": e["entry_date"], "Mood": e["mood"], "Stress": e["stress"],
                                    "Sleep (h)": e["sleep_hours"], "Note": e.get("note", ""),
                                    "Source": "demo" if e.get("is_demo") else "you"} for e in reversed(entries)]),
                     hide_index=True, **ui.wide(st.dataframe))


# ===========================================================================
# PAGE: WISEBOT
# ===========================================================================
def page_chatbot():
    ui.page_header("WiseBot assistant",
                   "A rule-based assistant. No external API or API key is required, so the app always works offline.",
                   eyebrow="Personal wellness",
                   help="WiseBot answers from a fixed knowledge base and from read-only context (your current question, "
                        "section, progress and loaded results). It cannot change answers or scores.")
    ui.notice("WiseBot can explain the instruments, individual questions (try <i>“explain question 12”</i>), the "
              "<b>risk levels R1–R3</b>, the model and, once an assessment is loaded, your own scores. It does not "
              "diagnose and is not a substitute for a qualified professional. If you or someone you know may be in "
              "danger, contact local emergency services or a trusted person right away.", "neutral", ico="shield")
    ctx = chat_context()
    ui.label("Try asking")
    with ui.box("wl_suggest"):
        cols = st.columns(4)
        for i, q in enumerate(chatbot.SUGGESTED_QUESTIONS):
            with cols[i % 4]:
                if st.button(q, key=f"sugg_{i}", **ui.wide(st.button)):
                    ask_wisebot(q, ctx)
                    st.rerun()
    st.markdown("<hr/>", unsafe_allow_html=True)
    if not st.session_state.chat:
        ui.chat_bubble("Hello! I am <b>WiseBot</b>. Ask me about PSS, GAD-7, PHQ-9, DASS-21, burnout, the Big Five, "
                       "the 14 features, the risk levels - or about your own scores.", render_markdown=False)
    render_chat_messages("chat_page")
    prompt = st.chat_input("Ask WiseBot a question...")
    if prompt:
        ask_wisebot(prompt, ctx)
        st.rerun()
    if st.session_state.chat and st.button("Clear conversation", **ui.icon_kw(st.button, ":material/delete_sweep:"),
                                           help="Clears the chat only - your test, answers and results are untouched."):
        st.session_state.chat = []
        st.rerun()


# ===========================================================================
# PAGE: PROFESSIONAL REVIEW (Tier 2)
# ===========================================================================
def page_professional_review():
    ui.page_header("Professional review", "Tier 2 — the human-in-the-loop stage. The AI never makes the final decision.",
                   eyebrow="Care & reporting")
    ui.warn("No qualified psychologist is connected to this system and no case is transmitted anywhere.",
            title="Simulated review workflow for an academic demonstration")
    ui.tier_strip([("AI screening", "Questionnaire scoring + Random Forest risk indication."),
                   ("Professional review", "A reviewer examines flagged cases and records a decision."),
                   ("Final report", "Reviewed outcome feeds the report and the aggregated HR view.")], current=2)
    if not require_result():
        return
    result = st.session_state.result
    pred, scores = result["prediction"], result["scores"]
    plan = rec.generate_recommendations(scores, pred)
    ui.section(f"Case {result['candidate_id']}",
               f"{'Demo profile' if result['source'] == 'demo' else 'Submitted assessment'} · "
               f"{result['timestamp'][:16].replace('T', ' ')}")
    if plan["review_recommended"]:
        ui.warn("HIGH risk indication and/or a safety flag. Status: Pending Review.",
                title="Professional review recommended")
    else:
        ui.ok("This case does not meet the automatic routing criteria. A reviewer may still record an optional review.")
    left, right = ui.columns([6, 5], gap="large")
    with left:
        ui.risk_card(pred["risk"], pred["confidence"], config.AI_DISCLAIMER)
        st.write("")
        d, m = scores["dass"], scores["mbi"]
        lines = [
            ("PSS-10", f"{scores['pss']['score']}/40", scores["pss"]["level"], False),
            ("GAD-7", f"{scores['gad7']['score']}/21", scores["gad7"]["level"], False),
            ("PHQ-9", f"{scores['phq9']['score']}/27", scores["phq9"]["level"], False),
            ("DASS Depression", f"{d['depression']}/42", d["depression_level"], False),
            ("DASS Anxiety", f"{d['anxiety']}/42", d["anxiety_level"], False),
            ("DASS Stress", f"{d['stress']}/42", d["stress_level"], False),
            ("MBI Emotional Exhaustion", f"{m['emotional_exhaustion']}/54", m["ee_level"], False),
            ("MBI Depersonalization", f"{m['depersonalization']}/30", m["dp_level"], False),
            ("MBI Personal Accomplishment (high = good)", f"{m['personal_accomplishment']}/48", m["pa_level"], True),
        ]
        ui.table(["Instrument", "Score", "Level"],
                 [[html.escape(n), s, ui.level_badge(lvl, positive=pos, small=True)] for n, s, lvl, pos in lines],
                 num_cols=(1,))
    with right:
        ui.section("Reviewer panel", "Record the Tier-2 decision. It is included in the PDF report.", tight=True)
        existing = st.session_state.review or {}
        status_options = ["Pending Review", "In Review", "Review Completed", "Not Required"]
        decision_options = ["No further action required", "Recommend a wellness / counselling conversation",
                            "Recommend follow-up assessment in 4 weeks",
                            "Escalate to a qualified mental health professional",
                            "Insufficient information - repeat assessment"]
        default_status = existing.get("status", "Pending Review" if plan["review_recommended"] else "Not Required")
        with st.form("review_form"):
            reviewer = st.text_input("Reviewer name / ID", value=existing.get("reviewer", ""), placeholder="e.g. Reviewer-01",
                                     help="Simulated reviewer label. Use any ID - no real clinician is connected.")
            status = st.selectbox("Review status", status_options, index=status_options.index(default_status)
                                  if default_status in status_options else 0,
                                  help="Where this case is in Tier 2. HIGH-risk cases default to Pending Review.")
            decision = st.selectbox("Final review decision", decision_options,
                                    index=decision_options.index(existing["decision"])
                                    if existing.get("decision") in decision_options else 0)
            notes = st.text_area("Reviewer notes", value=existing.get("notes", ""), placeholder="Observations, context, next steps...",
                                 help="Free-text notes. They are included in the PDF report.")
            saved = st.form_submit_button("Save review decision", type="primary", **ui.wide(st.form_submit_button))
        if saved:
            st.session_state.review = {"reviewer": reviewer, "status": status, "decision": decision, "notes": notes,
                                       "reviewed_at": datetime.now().isoformat(timespec="seconds")}
            storage.update_review(st.session_state.last_saved_id, reviewer, status, notes, decision)
            st.success("Review decision recorded. It will appear in the PDF report.")
        if st.session_state.review:
            r = st.session_state.review
            ui.ok(f"Reviewer: {html.escape(r.get('reviewer') or '-')} · Status: {html.escape(str(r.get('status')))}<br/>"
                  f"Decision: {html.escape(str(r.get('decision')))}<br/>Notes: {html.escape(r.get('notes') or '-')}",
                  title="Current review record")
            if st.button("Generate the reviewed report", **ui.wide(st.button), **ui.icon_kw(st.button, ":material/description:")):
                goto("Reports")
    st.write("")
    ui.disclaimer(config.MAIN_DISCLAIMER + " " + config.EMPLOYMENT_DISCLAIMER)


# ===========================================================================
# PAGE: HR DASHBOARD (Tier 3)
# ===========================================================================
def page_hr_dashboard():
    bundle = get_model_bundle()
    ui.page_header("HR / admin dashboard",
                   "Tier 3 — anonymised, aggregated wellness reporting. No item responses or personal identifiers are exposed.",
                   eyebrow="Care & reporting")
    ui.warn("These candidates are synthetic profiles scored by the real model. " + html.escape(config.EMPLOYMENT_DISCLAIMER),
            title="Simulated cohort")
    with st.expander("Risk level definitions"):
        ui.risk_legend()
    n = st.slider("Cohort size to display", 6, 40, 18, step=2,
                  help="How many synthetic candidates to include in the simulated cohort.")
    cohort = get_hr_cohort_cached(bundle, n)
    counts = {c: sum(1 for r in cohort if r["risk"] == c) for c in config.RISK_CLASSES}
    pending = sum(1 for r in cohort if r["review_status"] == "Pending Review")
    strip = [(len(cohort), "Candidates assessed", "Anonymised IDs only")]
    for cls in config.RISK_CLASSES:
        info = config.risk_info(cls)
        strip.append((counts[cls], f"R{info['number']} · {info['name']}", f"{counts[cls] / len(cohort) * 100:.0f}% of cohort",
                      info["definition"]))
    strip.append((pending, "Pending human review", "Routed to Tier 2",
                  "HIGH-risk cases waiting for a reviewer (Tier 2). A simulated workflow."))
    ui.stat_strip(strip)
    c1, c2 = ui.columns([2, 3], gap="medium")
    with c1:
        ui.plot(ui.chart_risk_donut(counts),
                " · ".join(f"{config.risk_label(c)}: {counts[c]}" for c in config.RISK_CLASSES))
    with c2:
        avg = pd.DataFrame(cohort).groupby("risk")[["pss", "gad7", "phq9", "burnout_ee"]].mean().round(1)
        avg = avg.reindex([c for c in config.RISK_CLASSES if c in avg.index])
        avg.columns = ["Avg PSS", "Avg GAD-7", "Avg PHQ-9", "Avg MBI EE"]
        with ui.box("wl_card_hr_avg", border=True):
            st.markdown("<div class='wl-h3'>Average scores by risk band</div>", unsafe_allow_html=True)
            st.dataframe(avg, **ui.wide(st.dataframe))
            st.caption("Aggregated figures only - individual responses are never shown on this tier.")
    ui.section("Candidate register")
    risk_filter = st.multiselect("Filter by risk level", config.RISK_CLASSES, default=config.RISK_CLASSES,
                                 format_func=lambda c: config.risk_label(c, with_name=True),
                                 help="Show only the selected risk levels (R1 Low, R2 Medium, R3 High).")
    table = pd.DataFrame([{
        "Candidate ID": r["candidate_id"], "Assessment Date": r["date"],
        "Risk Level": f"{config.RISK_EMOJI[r['risk']]} {config.risk_label(r['risk'], with_name=True)}", "Confidence": f"{r['confidence']:.1f}%",
        "Stress (PSS)": r["pss"], "Anxiety (GAD-7)": r["gad7"], "Burnout (MBI EE)": r["burnout_ee"],
        "Review Status": r["review_status"]} for r in cohort if r["risk"] in risk_filter])
    st.dataframe(table, hide_index=True, **ui.wide(st.dataframe))
    st.download_button("Download cohort CSV (anonymised)", data=table.to_csv(index=False).encode("utf-8"),
                       file_name=f"WiseOLife_cohort_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv",
                       **ui.icon_kw(st.download_button, ":material/download:"))
    ui.warn("A risk indication is a screening signal only.", title="High-risk cases require human / psychologist review")
    ui.disclaimer(config.MAIN_DISCLAIMER + " " + config.EMPLOYMENT_DISCLAIMER)


# ===========================================================================
# PAGE: REPORTS
# ===========================================================================
REPORT_CONTENTS = [
    "Title block with Candidate ID and date", "AI risk classification and confidence",
    "Scores for PSS, GAD-7, PHQ-9, DASS, MBI and Big Five", "Score chart", "The 14-feature vector",
    "Feature-importance chart", "Wellness recommendations", "Human review status",
    "Disclaimers and privacy statement",
]


def page_reports():
    ui.page_header("Reports", "A complete PDF report plus CSV exports of the scores and the 14-feature vector.",
                   eyebrow="Care & reporting")
    if not require_result():
        return
    result = st.session_state.result
    bundle = get_model_bundle()
    scores, pred = result["scores"], result["prediction"]
    plan = rec.generate_recommendations(scores, pred)
    explanation = ml.explanation_sentence(bundle, result["features"], pred["risk"])
    demo_banner(result)
    review_status = (st.session_state.review or {}).get("status", "Pending Review" if plan["review_recommended"] else "Not Required")
    ui.stat_strip([(result["candidate_id"], "Candidate", result["source"].title()),
                   (config.risk_label(pred["risk"]), "Risk indication", f"{pred['confidence'] * 100:.1f}% confidence",
                    config.risk_info(pred["risk"])["definition"]),
                   (f"{config.N_INSTRUMENTS} / {config.TOTAL_QUESTIONS} items", "Instruments", "Full battery"),
                   (review_status, "Review status", "Tier 2")])
    left, right = ui.columns([6, 5], gap="large")
    with left:
        ui.section("What the report contains", tight=True)
        with ui.box("wl_card_contents", border=True):
            ui.checklist(REPORT_CONTENTS, tone="ok", ico="check")
    with right:
        ui.section("Download", "PDF report and CSV exports for this result.", tight=True)
        with st.spinner("Building the PDF report..."):
            pdf_bytes = rp.generate_report(result, plan, bundle["importance"], bundle["metrics"],
                                           st.session_state.review, explanation)
        st.download_button("Download PDF report", data=pdf_bytes, file_name=rp.report_filename(result["candidate_id"]),
                           mime="application/pdf", type="primary", **ui.wide(st.download_button),
                           **ui.icon_kw(st.download_button, ":material/picture_as_pdf:"))
        st.download_button("Download scores CSV", data=rp.generate_csv(result),
                           file_name=f"WiseOLife_scores_{result['candidate_id']}.csv", mime="text/csv",
                           **ui.wide(st.download_button), **ui.icon_kw(st.download_button, ":material/download:"))
        st.download_button("Download 14-feature CSV", data=rp.generate_feature_row_csv(result),
                           file_name=f"WiseOLife_features_{result['candidate_id']}.csv", mime="text/csv",
                           **ui.wide(st.download_button), **ui.icon_kw(st.download_button, ":material/download:"))
        st.caption(f"PDF size: {len(pdf_bytes) / 1024:.0f} KB · generated in memory, nothing is uploaded anywhere.")
        with st.expander("Also save a copy into generated_reports/ (local runs only)"):
            if st.button("Save a local copy"):
                path = rp.save_report_to_disk(pdf_bytes, result["candidate_id"])
                st.success(f"Saved to `{path}`") if path else st.info("Filesystem not writable here; use the download button.")
    ui.section("Feature vector included in the report")
    ui.feature_vector_block(result["features"])
    st.write("")
    ui.disclaimer(config.MAIN_DISCLAIMER + " " + config.EMPLOYMENT_DISCLAIMER)


# ===========================================================================
# PAGE: ABOUT
# ===========================================================================
def page_about():
    ui.page_header(f"About {config.APP_NAME}", config.SUBTAGLINE, eyebrow="Project")
    st.markdown(f"""
### What is WiseOLife?
**{config.APP_NAME}** is an academic prototype of an AI-assisted mental-wellness **screening and decision-support**
platform. A person completes a {config.TOTAL_QUESTIONS}-item battery from {config.N_INSTRUMENTS} psychological instruments;
a scoring engine converts the answers into {len(config.FEATURE_NAMES)} numeric features; a Random Forest produces a
LOW / MEDIUM / HIGH **risk indication**; the system explains it, builds a wellness plan, and routes flagged cases to a human reviewer.

### Why psychological wellness assessment?
Stress, anxiety, low mood and burnout are common among students and professionals and usually occur together.
Structured questionnaires make them measurable and comparable over time - the first step towards support.

### Why six instruments?
| Instrument | Measures | Items |
|---|---|---|
| PSS-10 | Perceived stress, last month | 10 |
| GAD-7 | Generalised anxiety symptoms | 7 |
| PHQ-9 | Depression-related symptoms | 9 |
| DASS-21 | Depression, anxiety, stress as three subscales | 21 |
| MBI (22-item structure) | Exhaustion, depersonalization, accomplishment | 22 |
| Big Five (OCEAN) | Stable personality traits that shape coping | 20 |
| **Total** | | **{config.TOTAL_QUESTIONS}** |

### How does the AI work?
1. **Scoring engine** - each instrument has its own rules, incl. reverse scoring and the DASS ×2 convention.
2. **Feature engineering** - scores become a fixed 14-number vector.
3. **Synthetic training data** - {config.N_SYNTHETIC_RECORDS:,} profiles from a documented statistical model, labelled by a transparent points rule.
4. **Random Forest** - {config.RF_N_ESTIMATORS} decision trees vote on the class.
5. **Explainability** - global feature importance plus a per-profile influence view.
6. **Human review** - HIGH-risk or flagged cases go to Tier 2.

### What are the 14 features?
""")
    st.dataframe(pd.DataFrame([{"#": i, "Feature name": n, "Description": config.FEATURE_LABELS[n],
                                "Range": f"{config.FEATURE_RANGES[n][0]} - {config.FEATURE_RANGES[n][1]}"}
                               for i, n in enumerate(config.FEATURE_NAMES, 1)]), hide_index=True, **ui.wide(st.dataframe))
    st.markdown("""
The DASS subscales, MBI dimensions and Big Five traits stay **separate**. There is deliberately no "burnout composite",
because merging would hide that a *high* Personal Accomplishment is a **positive** sign.

### Why Random Forest?
Works well on small tabular data, needs no feature scaling, resists overfitting (bagging + random features), and gives
feature importances for free - which powers the explainability page. A neural network would need far more data and be harder to justify.

### Why synthetic data?
Real psychological data is sensitive and cannot be collected or published by students. So training data is generated from a
documented model and labelled by a visible rule. **Consequence:** the accuracy measures how well the model recovers *our own rule* -
it is **not** evidence of clinical validity.

### Why human review?
An algorithm trained on synthetic data cannot understand a person's context. Tier 1 screens, Tier 2 is a qualified human, Tier 3 reports only aggregates.

### Future scope
Real, ethically-approved data · SHAP explanations · multi-language item banks · longitudinal modelling ·
authentication and encryption · a formal validation study before any non-academic use.
""")
    ui.section("Risk levels", "Every risk shown in WiseOLife uses these numbers, names and definitions.")
    ui.risk_legend()
    ui.section("Team & contributions")
    ui.note("Editable placeholders - set names and roll numbers in <code>wiseolife/config.py</code> → <code>TEAM_MEMBERS</code>.")
    for i, (col, member) in enumerate(zip(st.columns(3), config.TEAM_MEMBERS)):
        with col:
            with ui.box(f"wl_card_member_{i}", border=True):
                st.markdown(f"<div class='wl-label'>{html.escape(member['role'])}</div>"
                            f"<div class='wl-h3' style='margin-top:8px'>{html.escape(member['placeholder_name'])}</div>"
                            f"<div class='wl-small'>{html.escape(member['roll_no'])}</div>", unsafe_allow_html=True)
                ui.checklist(member["responsibilities"], ico="check")
    st.caption(f"Institution: {config.INSTITUTION} · {config.DEPARTMENT} · {config.DEGREE} · "
               f"Guide: {config.GUIDE_NAME} · Academic year: {config.ACADEMIC_YEAR}")

    ui.section("Data privacy")
    ui.notice(html.escape(config.PRIVACY_NOTICE), "neutral", ico="lock")
    s = storage.stats()
    st.caption(f"Local database: {'writable' if s['available'] else 'not writable (session-only history)'} · "
               f"{s['assessments']} assessment(s), {s['journal']} journal entr(y/ies).")
    if st.button("Delete all locally stored data", **ui.icon_kw(st.button, ":material/delete:")):
        if storage.clear_all():
            st.session_state.session_history = []
            st.session_state.journal_session = []
            st.success("All locally stored assessments and journal entries deleted.")
        else:
            st.info("Nothing to delete - local storage is not in use here.")

    ui.section("Disclaimer")
    ui.disclaimer(config.MAIN_DISCLAIMER)
    ui.disclaimer(config.EMPLOYMENT_DISCLAIMER)
    ui.note(html.escape(config.WORDING_NOTICE))

    ui.section("Developer / validation")
    with st.expander("Run the scoring and model self-tests"):
        st.markdown("Verifies reverse scoring, DASS ×2, MBI dimensions, Big Five reverse items, the 14-feature vector and the "
                    "model pipeline. Also runnable with `python -m wiseolife.selftest`.")
        if st.button("Run all self-tests", type="primary", **ui.icon_kw(st.button, ":material/play_arrow:")):
            with st.spinner("Running tests..."):
                rows, passed, total = selftest.run_all_tests(get_model_bundle())
            (st.success if passed == total else st.error)(
                f"All {total} tests passed." if passed == total else f"{total - passed} of {total} tests failed.")
            st.dataframe(pd.DataFrame([{"Result": "PASS" if r["passed"] else "FAIL", "Test": r["test"],
                                        "Expected": r["expected"], "Actual": r["actual"]} for r in rows]),
                         hide_index=True, **ui.wide(st.dataframe))
    st.caption(f"{config.APP_NAME} v{config.VERSION} · academic prototype · built with Streamlit, scikit-learn, Plotly and ReportLab.")


# ===========================================================================
# ROUTER
# ===========================================================================
PAGE_FUNCTIONS = {
    "Home": page_home, "Assessment": page_assessment, "My Results": page_results,
    "AI Insights": page_ai_insights, "Wellness Plan": page_wellness_plan,
    "Progress Tracking": page_progress, "Wellness Journal": page_journal,
    "WiseBot Assistant": page_chatbot, "Professional Review": page_professional_review,
    "HR Dashboard": page_hr_dashboard, "Reports": page_reports, "About WiseOLife": page_about,
}


def main():
    init_state()
    get_database()
    progress_slot = render_sidebar()
    page = st.session_state.page
    if page not in PAGE_FUNCTIONS:
        page = st.session_state.page = "Home"
    PAGE_FUNCTIONS[page]()
    render_sidebar_progress(progress_slot)
    emit_focus()


main()
