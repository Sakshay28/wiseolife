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
from datetime import date, datetime

import pandas as pd
import streamlit as st

from wiseolife import chatbot, config, demo, model as ml
from wiseolife import questions as qs
from wiseolife import recommendations as rec
from wiseolife import report as rp
from wiseolife import scoring as sc
from wiseolife import selftest, storage, ui

st.set_page_config(
    page_title=f"{config.APP_NAME} - {config.APP_SUBTITLE}",
    page_icon=config.APP_ICON, layout="wide", initial_sidebar_state="expanded",
)
ui.inject_css()

PAGES = [
    ("🏠", "Home"), ("🧠", "Assessment"), ("📊", "My Results"), ("🤖", "AI Insights"),
    ("🌱", "Wellness Plan"), ("📈", "Progress Tracking"), ("📔", "Wellness Journal"),
    ("💬", "WiseBot Assistant"), ("🧑‍⚕️", "Professional Review"), ("👥", "HR Dashboard"),
    ("📄", "Reports"), ("ℹ️", "About WiseOLife"),
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
def init_state():
    defaults = {
        "page": "Home", "responses": qs.empty_responses(), "section_idx": 0,
        "assessment_started": False, "result": None, "review": {}, "chat": [],
        "candidate_id": "WL-001", "session_history": [], "last_saved_id": None,
        "journal_session": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def goto(page_name):
    st.session_state.page = page_name
    st.rerun()


def reset_assessment():
    st.session_state.responses = qs.empty_responses()
    st.session_state.section_idx = 0
    st.session_state.assessment_started = False
    st.session_state.review = {}
    st.session_state.last_saved_id = None
    for key in [k for k in st.session_state.keys() if str(k).startswith("q_")]:
        del st.session_state[key]


# ===========================================================================
# RESULT BUILDERS
# ===========================================================================
def build_result(scores, features, candidate_id, source):
    """Score -> predict -> package. The prediction always comes from the model."""
    prediction = ml.predict_risk(get_model_bundle(), features)
    return {"candidate_id": candidate_id, "timestamp": datetime.now().isoformat(timespec="seconds"),
            "source": source, "scores": scores, "features": features, "prediction": prediction}


def persist_result(result):
    get_database()
    st.session_state.last_saved_id = storage.save_assessment(result)
    st.session_state.session_history.append({
        "candidate_id": result["candidate_id"], "created_at": result["timestamp"],
        "risk": result["prediction"]["risk"], "confidence": result["prediction"]["confidence"],
        **dict(zip(config.FEATURE_NAMES, result["features"])),
    })


def run_assessment():
    scores = sc.score_all(st.session_state.responses)
    features = sc.build_feature_vector(scores)
    result = build_result(scores, features, st.session_state.candidate_id, "assessment")
    st.session_state.result = result
    persist_result(result)


def load_demo_candidate(candidate_id):
    features = demo.get_demo_features(candidate_id)
    scores = sc.scores_from_feature_dict(dict(zip(config.FEATURE_NAMES, features)))
    result = build_result(scores, features, candidate_id, "demo")
    st.session_state.result = result
    st.session_state.review = {}
    persist_result(result)


def require_result():
    """Friendly prompt when a page needs an assessment but none exists."""
    if st.session_state.result:
        return True
    ui.note("No assessment loaded yet. Use <b>🎬 Load Demo Candidate</b> to see the full product "
            "instantly, or start the real 89-question assessment.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🎬 Load Demo Candidate", type="primary", key="req_demo", **ui.wide(st.button)):
            load_demo_candidate(demo.DEFAULT_DEMO)
            st.rerun()
    with c2:
        if st.button("🧠 Start New Assessment", key="req_new", **ui.wide(st.button)):
            reset_assessment()
            goto("Assessment")
    return False


def demo_banner(result):
    if result and result.get("source") == "demo":
        cand = demo.DEMO_CANDIDATES.get(result["candidate_id"], {})
        ui.note(f"🎬 <b>Demo data active</b> - {result['candidate_id']}: {cand.get('title', 'sample profile')}. "
                "These are synthetic values. The risk level shown is a genuine model prediction on those values.")


# ===========================================================================
# SIDEBAR
# ===========================================================================
def render_sidebar():
    with st.sidebar:
        st.markdown(
            f"<div style='text-align:center;padding:.3rem 0 1rem'><div style='font-size:2.6rem;line-height:1'>"
            f"{config.APP_ICON}</div><div style='font-size:1.5rem;font-weight:800'>{config.APP_NAME}</div>"
            f"<div style='font-size:.76rem;color:#a5b4fc;font-weight:600;letter-spacing:.5px'>"
            f"{config.TAGLINE}</div></div>", unsafe_allow_html=True)
        for icon, name in PAGES:
            active = st.session_state.page == name
            if st.button(f"{icon}  {name}", key=f"nav_{name}", type="primary" if active else "secondary",
                         **ui.wide(st.button)):
                goto(name)
        st.markdown("---")
        st.markdown("<div style='font-size:.75rem;font-weight:700;color:#a5b4fc;letter-spacing:.6px'>"
                    "QUICK ACTIONS</div>", unsafe_allow_html=True)
        labels = dict(demo.demo_options())
        ids = list(labels.keys())
        chosen = st.selectbox("Demo candidate", ids, format_func=lambda c: labels[c],
                              index=ids.index(demo.DEFAULT_DEMO), key="demo_choice")
        if st.button("🎬 Load Demo Candidate", key="sb_demo", type="primary", **ui.wide(st.button)):
            load_demo_candidate(chosen)
            goto("My Results")
        if st.button("🧠 Start New Assessment", key="sb_new", **ui.wide(st.button)):
            reset_assessment()
            goto("Assessment")
        st.markdown("---")
        result = st.session_state.result
        if result:
            pred = result["prediction"]
            st.markdown(
                f"<div style='background:rgba(255,255,255,.08);border-radius:12px;padding:.7rem .85rem;font-size:.8rem'>"
                f"<div style='color:#a5b4fc;font-weight:700;font-size:.7rem'>ACTIVE ASSESSMENT</div>"
                f"<div style='font-weight:700;margin-top:.2rem'>{result['candidate_id']}</div>"
                f"<div style='margin-top:.25rem'>{config.RISK_EMOJI[pred['risk']]} {pred['risk']} "
                f"({pred['confidence'] * 100:.0f}%)</div>"
                f"<div style='color:#c7d2fe;font-size:.72rem;margin-top:.2rem'>{result['source'].title()} · "
                f"{result['timestamp'][:10]}</div></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='font-size:.8rem;color:#c7d2fe'>No active assessment.</div>",
                        unsafe_allow_html=True)
        st.markdown(f"<div style='margin-top:1.2rem;font-size:.7rem;color:#a5b4fc;text-align:center'>"
                    f"v{config.VERSION} · academic prototype<br/>Not a medical device</div>",
                    unsafe_allow_html=True)


# ===========================================================================
# PAGE: HOME
# ===========================================================================
def page_home():
    ui.hero(f"{config.APP_ICON} {config.APP_NAME}", config.APP_SUBTITLE,
            "Understand your wellness profile through structured psychological assessments and explainable AI. "
            "Six instruments, an 89-item questionnaire, a 14-feature machine-learning pipeline and a "
            "human-in-the-loop review workflow.", badge=config.TAGLINE)
    c1, c2, _ = st.columns([1, 1, 2])
    with c1:
        if st.button("🚀 Start Assessment", type="primary", key="home_start", **ui.wide(st.button)):
            reset_assessment()
            goto("Assessment")
    with c2:
        if st.button("📊 View Demo", key="home_demo", **ui.wide(st.button)):
            load_demo_candidate(demo.DEFAULT_DEMO)
            goto("My Results")
    st.write("")
    stats = [(config.N_INSTRUMENTS, "Psychological Instruments"), (config.TOTAL_QUESTIONS, "Assessment Questions"),
             (len(config.FEATURE_NAMES), "Machine-Learning Features"), ("Random Forest", "Explainable AI Model")]
    for col, (n, label) in zip(st.columns(4), stats):
        with col:
            ui.stat(n, label)
    st.write("")
    ui.section("How WiseOLife works", "From questionnaire responses to a reviewed, explainable report.")
    ui.workflow(["👤 User", "📝 Questionnaire", "🧮 Scoring Engine", "🔢 14 Features", "🌳 Random Forest",
                 "⚖️ Risk Prediction", "🔍 Explainable Report", "🧑‍⚕️ Human Review"])
    st.write("")
    ui.section("The six instruments")
    cols = st.columns(3)
    for i, inst in enumerate(config.INSTRUMENTS):
        with cols[i % 3]:
            ui.card(f"{inst['icon']} {inst['name']}", f"{inst['n']} items", inst["full"])
            st.write("")
    ui.section("Three-tier decision-support architecture")
    t1, t2, t3 = st.columns(3)
    with t1:
        ui.card("Tier 1 · AI Screening", "Automated", "Questionnaire scoring plus a Random Forest risk indication over 14 features.")
    with t2:
        ui.card("Tier 2 · Professional Review", "Human", "High-risk and flagged cases are routed to a qualified reviewer who records the decision.")
    with t3:
        ui.card("Tier 3 · Reporting", "Aggregated", "Anonymised, aggregated wellness reporting for institutional / HR decision support.")
    st.write("")
    ui.disclaimer(config.MAIN_DISCLAIMER)


# ===========================================================================
# PAGE: ASSESSMENT
# ===========================================================================
def render_progress_header():
    missing = sum(1 for k in qs.INSTRUMENT_ORDER for v in st.session_state.responses[k] if v is None)
    answered = config.TOTAL_QUESTIONS - missing
    pct = answered / config.TOTAL_QUESTIONS * 100
    filled = int(round(pct / 10))
    bar = "█" * filled + "░" * (10 - filled)
    st.markdown(
        f"<div class='wl-card' style='margin-bottom:.8rem'><div style='display:flex;justify-content:space-between;"
        f"font-weight:700;color:#0f172a'><span>Assessment Progress</span>"
        f"<span>Question {min(answered + 1, config.TOTAL_QUESTIONS)} of {config.TOTAL_QUESTIONS}</span></div>"
        f"<div style='font-family:monospace;font-size:1.15rem;color:#4f46e5;letter-spacing:2px;margin-top:.3rem'>"
        f"{bar} {pct:.0f}%</div><div class='wl-card-sub'>{answered} answered · {missing} remaining</div></div>",
        unsafe_allow_html=True)
    st.progress(min(1.0, answered / config.TOTAL_QUESTIONS))


def render_section(inst_key):
    inst = qs.get_instrument(inst_key)
    offset = qs.question_offset(inst_key)
    options = [label for _v, label in inst["scale"]]
    values = [v for v, _l in inst["scale"]]
    st.markdown(
        f"<div style='background:linear-gradient(120deg,#312e81,#6d28d9);color:#fff;border-radius:16px;"
        f"padding:1.1rem 1.3rem;margin-bottom:1rem'><div style='font-size:1.35rem;font-weight:800'>"
        f"{inst['icon']} {inst['name']}</div><div style='font-size:.86rem;color:#ddd6fe'>{inst['full_name']} · "
        f"{len(inst['items'])} items · scale {inst['scale_min']}-{inst['scale_max']}</div></div>",
        unsafe_allow_html=True)
    st.markdown(inst["instructions"])
    reverse_nums = qs.reverse_item_numbers(inst_key)
    if reverse_nums:
        ui.note(f"🔄 <b>Reverse scoring applied</b> to item(s) {', '.join(map(str, reverse_nums))} of this "
                f"instrument (marked 🔄). Formula: <code>new_score = max_scale - original_score</code>. "
                "Answer normally - the scoring engine flips them for you.")
    st.write("")
    for i, item in enumerate(inst["items"]):
        qnum = offset + i + 1
        marker = " 🔄" if item["reverse"] else ""
        st.markdown(f"**Q{qnum}. {item['text']}{marker}**")
        stored = st.session_state.responses[inst_key][i]
        idx = values.index(stored) if stored in values else None
        choice = st.radio(f"Question {qnum}", options, index=idx, key=f"q_{inst_key}_{i}",
                          label_visibility="collapsed", horizontal=len(options) <= 5)
        st.session_state.responses[inst_key][i] = values[options.index(choice)] if choice is not None else None
        st.markdown("<div style='height:.3rem'></div>", unsafe_allow_html=True)


def page_assessment():
    ui.section("🧠 Wellness Assessment", "Six instruments, one section at a time. Your answers stay in this browser session.")
    if not st.session_state.assessment_started:
        overview = [(config.TOTAL_QUESTIONS, "Questions"), (config.N_INSTRUMENTS, "Instruments"),
                    (f"{config.ESTIMATED_MINUTES} min", "Estimated time"), (len(config.FEATURE_NAMES), "AI features")]
        for col, (n, label) in zip(st.columns(4), overview):
            with col:
                ui.stat(n, label)
        st.write("")
        rows = []
        for k in qs.INSTRUMENT_ORDER:
            inst = qs.get_instrument(k)
            rev = qs.reverse_item_numbers(k)
            rows.append({"Instrument": f"{inst['icon']} {inst['name']}", "Measures": inst["full_name"],
                         "Items": len(inst["items"]), "Scale": f"{inst['scale_min']} - {inst['scale_max']}",
                         "Reverse-scored items": ", ".join(map(str, rev)) if rev else "-"})
        st.dataframe(pd.DataFrame(rows), hide_index=True, **ui.wide(st.dataframe))
        st.session_state.candidate_id = st.text_input(
            "Candidate ID (no real name is required)", value=st.session_state.candidate_id,
            help="WiseOLife never asks for your name, email or phone number.")
        ui.disclaimer(config.MAIN_DISCLAIMER + " " + config.WORDING_NOTICE)
        st.write("")
        c1, c2 = st.columns([1, 3])
        with c1:
            if st.button("▶️ Begin Assessment", type="primary", **ui.wide(st.button)):
                st.session_state.assessment_started = True
                st.rerun()
        with c2:
            if st.button("🎬 Skip - load a demo candidate instead", **ui.wide(st.button)):
                load_demo_candidate(demo.DEFAULT_DEMO)
                goto("My Results")
        return

    # The progress header slot is filled AFTER the section renders, so it reflects this run's answers.
    progress_slot = st.container()
    idx = st.session_state.section_idx
    inst_key = qs.INSTRUMENT_ORDER[idx]
    st.caption(f"Section {idx + 1} of {len(qs.INSTRUMENT_ORDER)}")
    render_section(inst_key)
    with progress_slot:
        render_progress_header()
    st.markdown("---")
    unanswered = sum(1 for v in st.session_state.responses[inst_key] if v is None)
    if unanswered:
        st.warning(f"{unanswered} question(s) in this section are unanswered. You may continue - unanswered "
                   "items use the scale default and the result is marked incomplete.")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("← Back", disabled=idx == 0, **ui.wide(st.button)):
            st.session_state.section_idx = max(0, idx - 1)
            st.rerun()
    with c2:
        if idx < len(qs.INSTRUMENT_ORDER) - 1:
            if st.button("Next →", type="primary", **ui.wide(st.button)):
                st.session_state.section_idx = idx + 1
                st.rerun()
        elif st.button("✅ Submit & Analyse", type="primary", **ui.wide(st.button)):
            run_assessment()
            goto("My Results")
    with c3:
        if st.button("💾 Save & Continue", **ui.wide(st.button)):
            st.success("Progress saved in this browser session. Come back to this page any time.")
    with c4:
        if st.button("🔄 Reset", **ui.wide(st.button)):
            reset_assessment()
            st.rerun()


# ===========================================================================
# PAGE: MY RESULTS
# ===========================================================================
def page_results():
    if not require_result():
        return
    result = st.session_state.result
    scores, pred = result["scores"], result["prediction"]
    ui.section("📊 Your WiseOLife Wellness Overview",
               f"Candidate {result['candidate_id']} · {result['timestamp'][:16].replace('T', ' ')} · source: {result['source']}")
    demo_banner(result)
    if not scores.get("complete", True):
        ui.warn(f"⚠️ This assessment is <b>incomplete</b>: {scores['missing_total']} of {config.TOTAL_QUESTIONS} "
                "questions were unanswered and scored at the scale default. Interpret with caution.")
    if scores["phq9"].get("safety_flag"):
        ui.warn(f"<b>Safety notice</b> — {config.SAFETY_MESSAGE}")
    st.write("")

    cards = sc.summary_cards(scores)
    pcts = [scores["pss"]["score"] / 40 * 100, scores["gad7"]["score"] / 21 * 100,
            scores["phq9"]["score"] / 27 * 100, scores["dass"]["stress"] / 42 * 100,
            scores["mbi"]["emotional_exhaustion"] / 54 * 100, scores["big5"]["neuroticism"] / 5 * 100]
    for row in (0, 3):
        for col, card, pct in zip(st.columns(3), cards[row:row + 3], pcts[row:row + 3]):
            with col:
                ui.score_card(card["icon"], card["title"], card["value"], card["level"], card["caption"], pct)
        st.write("")

    ui.section("🤖 AI Risk Indication")
    ui.risk_banner(pred["risk"], pred["confidence"], config.AI_DISCLAIMER)
    if pred["risk"] == "HIGH":
        ui.warn("⚠️ <b>Professional Review Recommended</b> — status: Pending Review (Tier 2).")
    c1, c2 = st.columns([3, 2])
    with c1:
        st.plotly_chart(ui.chart_scores_bar(scores), **ui.wide(st.plotly_chart))
    with c2:
        st.plotly_chart(ui.chart_probabilities(pred["probabilities"]), **ui.wide(st.plotly_chart))

    st.write("")
    ui.section("🧠 14-Feature AI Input Vector", "The exact numbers passed to the Random Forest classifier.")
    fmap = dict(zip(config.FEATURE_NAMES, result["features"]))
    for group_name, icon, names in config.FEATURE_GROUPS:
        st.markdown(f"**{icon} {group_name}**")
        cols = st.columns(max(len(names), 3))
        for col, name in zip(cols, names):
            lo, hi = config.FEATURE_RANGES[name]
            with col:
                ui.feature_chip(f"{config.FEATURE_SHORT[name]} ({lo}-{hi})", fmap[name], isinstance(hi, float))
    st.markdown("**Model input vector** (in `FEATURE_NAMES` order)")
    ui.feature_vector_block(result["features"])
    st.caption("Order: " + " · ".join(f"{i}. {config.FEATURE_SHORT[n]}" for i, n in enumerate(config.FEATURE_NAMES, 1)))

    st.write("")
    ui.section("🔬 Instrument detail")
    tabs = st.tabs(["😰 PSS-10", "😟 GAD-7", "😔 PHQ-9", "📉 DASS-21", "🔥 MBI Burnout", "🌈 Big Five"])
    with tabs[0]:
        p = scores["pss"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Raw score (no reversal)", p["raw"] if p["raw"] is not None else "n/a (demo)")
        c2.metric("Adjusted score (reported)", f"{p['score']} / 40")
        c3.metric("Interpretation", p["level"])
        ui.note(f"🔄 <b>Reverse scoring applied</b> to PSS items {', '.join(map(str, p['reverse_items']))}. "
                f"Formula: <code>new_score = max_scale - original_score</code>. Bands: 0-13 Low · 14-26 Moderate · 27-40 High.")
        st.caption("This build follows the WiseOLife project specification (items 4-8 reversed). The widely "
                   "published PSS-10 reverses items 4, 5, 7, 8. The list is one constant (`PSS_REVERSE_ITEMS` in "
                   "wiseolife/questions.py). This is a configurable academic implementation, not official clinical scoring.")
    with tabs[1]:
        g = scores["gad7"]
        c1, c2 = st.columns(2)
        c1.metric("GAD-7 total", f"{g['score']} / 21")
        c2.metric("Interpretation", g["level"])
        st.progress(min(1.0, g["score"] / 21))
        st.caption("Bands: 0-4 Minimal · 5-9 Mild · 10-14 Moderate · 15-21 Severe")
    with tabs[2]:
        p = scores["phq9"]
        c1, c2 = st.columns(2)
        c1.metric("PHQ-9 total", f"{p['score']} / 27")
        c2.metric("Interpretation", p["level"])
        st.progress(min(1.0, p["score"] / 27))
        st.caption("Bands: 0-4 Minimal · 5-9 Mild · 10-14 Moderate · 15-19 Moderately Severe · 20-27 Severe")
        if p.get("safety_flag"):
            ui.warn(config.SAFETY_MESSAGE)
        else:
            st.caption("Item 9 (self-harm related) was not elevated in this response set.")
    with tabs[3]:
        d = scores["dass"]
        st.plotly_chart(ui.chart_dass(d), **ui.wide(st.plotly_chart))
        c1, c2, c3 = st.columns(3)
        c1.metric("Depression", f"{d['depression']} / 42", d["depression_level"], delta_color="off")
        c2.metric("Anxiety", f"{d['anxiety']} / 42", d["anxiety_level"], delta_color="off")
        c3.metric("Stress", f"{d['stress']} / 42", d["stress_level"], delta_color="off")
        st.caption(f"Each subscale = sum of its 7 items × {d['multiplier']} (standard DASS-21 convention).")
    with tabs[4]:
        m = scores["mbi"]
        st.plotly_chart(ui.chart_mbi(m), **ui.wide(st.plotly_chart))
        c1, c2, c3 = st.columns(3)
        with c1:
            ui.score_card("🔥", "Emotional Exhaustion", f"{m['emotional_exhaustion']} / 54", m["ee_level"],
                          "Higher = more concerning", m["emotional_exhaustion"] / 54 * 100)
        with c2:
            ui.score_card("🧊", "Depersonalization", f"{m['depersonalization']} / 30", m["dp_level"],
                          "Higher = more concerning", m["depersonalization"] / 30 * 100)
        with c3:
            ui.score_card("🌱", "Personal Accomplishment", f"{m['personal_accomplishment']} / 48", m["pa_level"],
                          "Higher = POSITIVE", m["personal_accomplishment"] / 48 * 100, positive=True)
        st.write("")
        ui.ok("The three burnout dimensions are kept separate - in interpretation and as three of the 14 model "
              "features. <b>Personal Accomplishment is positive</b>: high is good, only LOW is a concern.")
    with tabs[5]:
        b = scores["big5"]
        c1, c2 = st.columns([3, 2])
        with c1:
            st.plotly_chart(ui.chart_big5_radar(b), **ui.wide(st.plotly_chart))
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
    ui.section("🤖 AI Insights & Explainability",
               "How the model was built, how it performs on the synthetic dataset, and why it produced your result.")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ui.card("Algorithm", "Random Forest", f"{config.RF_N_ESTIMATORS} trees · max_depth={config.RF_MAX_DEPTH}")
    with c2:
        ui.card("Training records", f"{config.N_SYNTHETIC_RECORDS:,}", "Synthetic wellness profiles")
    with c3:
        ui.card("Features", str(metrics["n_features"]), "All dimensions kept separate")
    with c4:
        ui.card("Classes", "Low / Medium / High", "Screening risk indication")
    st.write("")
    ui.section("📏 Evaluation metrics")
    ui.warn("These are evaluation metrics on a held-out split of the <b>synthetic demo dataset</b>. They measure how "
            "well the model reproduces the project's rule-based labelling. They are <b>not</b> clinical accuracy.")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Accuracy", f"{metrics['accuracy'] * 100:.2f}%")
    m2.metric("Precision (macro)", f"{metrics['precision'] * 100:.2f}%")
    m3.metric("Recall (macro)", f"{metrics['recall'] * 100:.2f}%")
    m4.metric("F1 score (macro)", f"{metrics['f1'] * 100:.2f}%")
    st.caption(f"Train / test split: {metrics['train_size']} / {metrics['test_size']}, stratified, "
               f"random_state={config.RANDOM_STATE}.")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(ui.chart_confusion(bundle["confusion_matrix"], bundle["confusion_labels"]), **ui.wide(st.plotly_chart))
    with c2:
        st.plotly_chart(ui.chart_dataset_distribution(bundle["dataset"]), **ui.wide(st.plotly_chart))
    with st.expander("📄 Full classification report (scikit-learn)"):
        st.code(bundle["report_text"], language="text")

    ui.section("🔍 Why did the AI predict this?", "Random Forest feature importance across all 14 inputs.")
    st.plotly_chart(ui.chart_importance(bundle["importance"]), **ui.wide(st.plotly_chart))
    with st.expander("📋 Feature importance table"):
        st.dataframe(pd.DataFrame([{"Rank": i, "Feature": r["label"], "Importance": f"{r['percent']:.2f}%"}
                                   for i, r in enumerate(bundle["importance"], 1)]),
                     hide_index=True, **ui.wide(st.dataframe))

    ui.section("🎯 Explanation for your result")
    result = st.session_state.result
    if not result:
        ui.note("Load a demo candidate or complete an assessment to see a profile-specific explanation.")
        if st.button("🎬 Load Demo Candidate", key="ins_demo", type="primary"):
            load_demo_candidate(demo.DEFAULT_DEMO)
            st.rerun()
    else:
        pred = result["prediction"]
        ui.risk_banner(pred["risk"], pred["confidence"], config.AI_DISCLAIMER)
        ui.note("💡 " + ml.explanation_sentence(bundle, result["features"], pred["risk"]))
        st.plotly_chart(ui.chart_local_influence(ml.local_contribution(bundle, result["features"], 8)),
                        **ui.wide(st.plotly_chart))
        st.caption("Local view = each feature's global importance × how far your value sits from the training average "
                   "(direction-aware). A lightweight stand-in for SHAP: association, not causation.")

    st.write("")
    ui.section("📐 How the synthetic labels were created", "A transparent points rule - nothing about the labels is random.")
    rule_rows = [{"Indicator": r, "Threshold": f">= {t}", "Risk points": p} for _n, r, t, p in ml.RISK_RULE_TABLE] + \
                [{"Indicator": r, "Threshold": f"<= {t}", "Risk points": p} for _n, r, t, p in ml.RISK_RULE_TABLE_INVERTED]
    st.dataframe(pd.DataFrame(rule_rows), hide_index=True, **ui.wide(st.dataframe))
    ui.note(f"Total points ≥ <b>{ml.HIGH_THRESHOLD}</b> → HIGH · ≥ <b>{ml.MEDIUM_THRESHOLD}</b> → MEDIUM · otherwise LOW.")
    if result:
        fdict = dict(zip(config.FEATURE_NAMES, result["features"]))
        pts, reasons = ml.risk_points_breakdown(fdict)
        st.markdown(f"**Rule check for {result['candidate_id']}: {pts} point(s) → `{ml.label_risk(fdict)}`**")
        for reason, p in reasons:
            st.markdown(f"- {reason} → **+{p}**")
        if not reasons:
            st.markdown("- No indicator crossed an elevated threshold.")
        st.caption("The rule generated the *training labels*; the result page shows the *model's* prediction. "
                   "They usually agree; where they differ the model learned patterns across all 14 features.")
    ui.disclaimer(config.MAIN_DISCLAIMER)


# ===========================================================================
# PAGE: WELLNESS PLAN
# ===========================================================================
def page_wellness_plan():
    if not require_result():
        return
    result = st.session_state.result
    plan = rec.generate_recommendations(result["scores"], result["prediction"])
    ui.section("🌱 Your Wellness Plan", "General wellness suggestions based on your scores - not medical treatment.")
    demo_banner(result)
    if plan["safety"]:
        ui.warn(f"<b>Safety notice</b> — {plan['safety_message']}")
    ui.note(plan["summary"])
    st.write("")
    if plan["strengths"]:
        ui.section("✅ Strengths identified")
        for col_i, s in enumerate(plan["strengths"]):
            ui.ok(s)
    st.write("")
    ui.section("🎯 Focus areas")
    for block in plan["blocks"]:
        tag = "🔴 High priority" if block["severity"] == 2 else "🟡 Worth attention" if block["severity"] == 1 else "🟢 Maintenance"
        with st.expander(f"{block['icon']}  {block['title']}  ·  {tag}", expanded=block["severity"] == 2):
            st.markdown(f"*{block['why']}*")
            for action in block["actions"]:
                st.markdown(f"- {action}")
    if plan["review_recommended"]:
        ui.warn("⚠️ <b>Professional Review Recommended.</b> This profile meets the Tier-2 routing criteria.")
        if st.button("🧑‍⚕️ Go to Professional Review", type="primary"):
            goto("Professional Review")
    ui.disclaimer(plan["disclaimer"] + " " + config.MAIN_DISCLAIMER)


# ===========================================================================
# PAGE: PROGRESS TRACKING
# ===========================================================================
def _history_rows():
    """Stored history if >=2 records, else clearly-labelled demo data. Returns (rows, is_demo)."""
    get_database()
    stored = [r for r in storage.load_assessments(limit=50)]
    if len(stored) < 2:
        stored = list(reversed(st.session_state.session_history))
    if len(stored) >= 2:
        rows = []
        for r in reversed(stored):  # oldest first
            row = {"date": str(r["created_at"])[:10], "risk": r.get("risk", "")}
            row.update({n: r.get(n, 0) for n in config.FEATURE_NAMES})
            rows.append(row)
        return rows, False
    cid = (st.session_state.result or {}).get("candidate_id", demo.DEFAULT_DEMO)
    if cid not in demo.DEMO_CANDIDATES:
        cid = demo.DEFAULT_DEMO
    return demo.demo_progress_series(cid), True


def page_progress():
    ui.section("📈 Wellness Progress", "Track how your instrument scores change between assessments.")
    rows, is_demo = _history_rows()
    if is_demo:
        ui.note("📊 <b>Demo data.</b> Fewer than two saved assessments exist, so the charts use a clearly labelled "
                "synthetic history that ends at the current demo profile. Complete two or more assessments to see your own trend.")
    latest, first = rows[-1], rows[0]
    for (key, label), col in zip([("pss_score", "PSS Stress"), ("gad7_score", "GAD-7 Anxiety"),
                                  ("phq9_score", "PHQ-9 Depression"), ("mbi_emotional_exhaustion", "Burnout (EE)")],
                                 st.columns(4)):
        col.metric(label, f"{latest[key]:g}", f"{latest[key] - first[key]:+g} since first record", delta_color="inverse")
    st.plotly_chart(ui.chart_trend(rows, [("pss_score", "PSS (0-40)", "#8b5cf6"), ("gad7_score", "GAD-7 (0-21)", "#f59e0b"),
                                          ("phq9_score", "PHQ-9 (0-27)", "#ef4444")],
                                   "Stress, anxiety and depression trend"), **ui.wide(st.plotly_chart))
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(ui.chart_trend(rows, [("dass_depression", "Depression", "#ef4444"), ("dass_anxiety", "Anxiety", "#f59e0b"),
                                              ("dass_stress", "Stress", "#8b5cf6")], "DASS-21 subscale trend", "Score (0-42)"),
                        **ui.wide(st.plotly_chart))
    with c2:
        st.plotly_chart(ui.chart_trend(rows, [("mbi_emotional_exhaustion", "Emotional Exhaustion", "#ef4444"),
                                              ("mbi_depersonalization", "Depersonalization", "#f59e0b"),
                                              ("mbi_personal_accomplishment", "Personal Accomplishment ↑ good", "#10b981")],
                                   "Burnout dimension trend"), **ui.wide(st.plotly_chart))
    ui.section("🗂️ Assessment history")
    st.dataframe(pd.DataFrame([{
        "Date": r["date"], "PSS": r["pss_score"], "GAD-7": r["gad7_score"], "PHQ-9": r["phq9_score"],
        "DASS-S": r["dass_stress"], "MBI EE": r["mbi_emotional_exhaustion"],
        "MBI PA": r["mbi_personal_accomplishment"], "Neuroticism": r["neuroticism"],
        "Risk": r.get("risk") or "demo"} for r in reversed(rows)]), hide_index=True, **ui.wide(st.dataframe))
    if storage.db_available():
        s = storage.stats()
        st.caption(f"Local database: {s['assessments']} assessment(s), {s['journal']} journal entr(y/ies) in wiseolife_data.db.")
    else:
        ui.warn("Local SQLite storage is not writable here, so history is kept for this browser session only.")


# ===========================================================================
# PAGE: WELLNESS JOURNAL
# ===========================================================================
def page_journal():
    ui.section("📔 Wellness Journal", "A short daily check-in. Mood and stress are self-rated 1-10.")
    get_database()
    with st.form("journal_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        entry_date = c1.date_input("Date", value=date.today())
        mood = c2.slider("Mood (1 = very low, 10 = very good)", 1, 10, 6)
        stress = c3.slider("Stress (1 = none, 10 = extreme)", 1, 10, 5)
        sleep_hours = st.slider("Hours of sleep last night", 0.0, 12.0, 7.0, 0.5)
        note = st.text_area("How are you feeling today?", placeholder="A sentence or two is enough...")
        submitted = st.form_submit_button("💾 Save entry", type="primary")
    if submitted:
        row_id = storage.save_journal_entry(entry_date, mood, stress, sleep_hours, note)
        st.session_state.journal_session.append({"entry_date": str(entry_date), "mood": mood, "stress": stress,
                                                 "sleep_hours": sleep_hours, "note": note})
        st.success("Entry saved to the local database." if row_id else "Entry saved for this session.")
    entries = storage.load_journal() or list(st.session_state.journal_session)
    using_demo = len(entries) < 3
    if using_demo:
        entries = demo.demo_journal_entries() + entries
    entries = sorted(entries, key=lambda e: str(e["entry_date"]))
    if using_demo:
        ui.note("📊 <b>Demo entries included.</b> Fewer than three real entries exist, so sample entries are shown.")
    st.plotly_chart(ui.chart_journal(entries), **ui.wide(st.plotly_chart))
    c1, c2, c3 = st.columns(3)
    c1.metric("Average mood", f"{sum(e['mood'] for e in entries) / len(entries):.1f} / 10")
    c2.metric("Average stress", f"{sum(e['stress'] for e in entries) / len(entries):.1f} / 10")
    c3.metric("Average sleep", f"{sum(e['sleep_hours'] for e in entries) / len(entries):.1f} h")
    st.dataframe(pd.DataFrame([{"Date": e["entry_date"], "Mood": e["mood"], "Stress": e["stress"],
                                "Sleep (h)": e["sleep_hours"], "Note": e.get("note", ""),
                                "Source": "demo" if e.get("is_demo") else "you"} for e in reversed(entries)]),
                 hide_index=True, **ui.wide(st.dataframe))


# ===========================================================================
# PAGE: WISEBOT
# ===========================================================================
def _ask_bot(question):
    st.session_state.chat.append(("user", question))
    st.session_state.chat.append(("bot", chatbot.get_response(question, st.session_state.result)))


def page_chatbot():
    ui.section("💬 WiseBot - Wellness Assistant",
               "A rule-based assistant. No external API or API key is required, so the app always works offline.")
    ui.note("WiseBot answers from a fixed knowledge base. It can explain the instruments, the scoring, the model - "
            "and, once an assessment is loaded, your own scores.")
    st.markdown("**Try one of these:**")
    cols = st.columns(4)
    for i, q in enumerate(chatbot.SUGGESTED_QUESTIONS):
        with cols[i % 4]:
            if st.button(q, key=f"sugg_{i}", **ui.wide(st.button)):
                _ask_bot(q)
                st.rerun()
    st.markdown("---")
    if not st.session_state.chat:
        ui.chat_bubble("Hello! I am <b>WiseBot</b> 🤖. Ask me about PSS, GAD-7, PHQ-9, DASS-21, burnout, the Big Five, "
                       "the 14 features, Random Forest - or about your own scores.", render_markdown=False)
    for role, text in st.session_state.chat:
        ui.chat_bubble(text, is_user=(role == "user"))
        st.write("")
    prompt = st.chat_input("Ask WiseBot a question...")
    if prompt:
        _ask_bot(prompt)
        st.rerun()
    if st.session_state.chat and st.button("🗑️ Clear conversation"):
        st.session_state.chat = []
        st.rerun()


# ===========================================================================
# PAGE: PROFESSIONAL REVIEW (Tier 2)
# ===========================================================================
def page_professional_review():
    ui.section("🧑‍⚕️ Professional Review · Tier 2", "The human-in-the-loop stage. The AI never makes the final decision.")
    ui.warn("This is a <b>simulated</b> review workflow for an academic demonstration. No qualified psychologist is "
            "connected to this system and no case is transmitted anywhere.")
    c1, c2, c3 = st.columns(3)
    with c1:
        ui.card("Tier 1", "AI Screening", "Questionnaire scoring + Random Forest risk indication.")
    with c2:
        ui.card("Tier 2", "Professional Review", "A reviewer examines flagged cases and records a decision.")
    with c3:
        ui.card("Tier 3", "Final Report", "Reviewed outcome feeds the report and the aggregated HR view.")
    st.write("")
    if not require_result():
        return
    result = st.session_state.result
    pred, scores = result["prediction"], result["scores"]
    plan = rec.generate_recommendations(scores, pred)
    ui.section(f"Case {result['candidate_id']}")
    ui.risk_banner(pred["risk"], pred["confidence"], config.AI_DISCLAIMER)
    if plan["review_recommended"]:
        ui.warn("⚠️ <b>Professional Review Recommended</b> — HIGH risk indication and/or a safety flag. Status: Pending Review.")
    else:
        ui.ok("✅ This case does not meet the automatic routing criteria. A reviewer may still record an optional review.")
    d, m = scores["dass"], scores["mbi"]
    st.dataframe(pd.DataFrame([
        {"Instrument": "PSS-10", "Score": f"{scores['pss']['score']}/40", "Level": scores["pss"]["level"]},
        {"Instrument": "GAD-7", "Score": f"{scores['gad7']['score']}/21", "Level": scores["gad7"]["level"]},
        {"Instrument": "PHQ-9", "Score": f"{scores['phq9']['score']}/27", "Level": scores["phq9"]["level"]},
        {"Instrument": "DASS Depression", "Score": f"{d['depression']}/42", "Level": d["depression_level"]},
        {"Instrument": "DASS Anxiety", "Score": f"{d['anxiety']}/42", "Level": d["anxiety_level"]},
        {"Instrument": "DASS Stress", "Score": f"{d['stress']}/42", "Level": d["stress_level"]},
        {"Instrument": "MBI Emotional Exhaustion", "Score": f"{m['emotional_exhaustion']}/54", "Level": m["ee_level"]},
        {"Instrument": "MBI Depersonalization", "Score": f"{m['depersonalization']}/30", "Level": m["dp_level"]},
        {"Instrument": "MBI Personal Accomplishment (high = good)", "Score": f"{m['personal_accomplishment']}/48", "Level": m["pa_level"]},
    ]), hide_index=True, **ui.wide(st.dataframe))
    ui.section("📋 Reviewer panel")
    existing = st.session_state.review or {}
    status_options = ["Pending Review", "In Review", "Review Completed", "Not Required"]
    decision_options = ["No further action required", "Recommend a wellness / counselling conversation",
                        "Recommend follow-up assessment in 4 weeks",
                        "Escalate to a qualified mental health professional",
                        "Insufficient information - repeat assessment"]
    default_status = existing.get("status", "Pending Review" if plan["review_recommended"] else "Not Required")
    with st.form("review_form"):
        c1, c2 = st.columns(2)
        reviewer = c1.text_input("Reviewer name / ID", value=existing.get("reviewer", ""), placeholder="e.g. Reviewer-01")
        status = c2.selectbox("Review status", status_options, index=status_options.index(default_status)
                              if default_status in status_options else 0)
        decision = st.selectbox("Final review decision", decision_options,
                                index=decision_options.index(existing["decision"])
                                if existing.get("decision") in decision_options else 0)
        notes = st.text_area("Reviewer notes", value=existing.get("notes", ""), placeholder="Observations, context, next steps...")
        saved = st.form_submit_button("💾 Save review decision", type="primary")
    if saved:
        st.session_state.review = {"reviewer": reviewer, "status": status, "decision": decision, "notes": notes,
                                   "reviewed_at": datetime.now().isoformat(timespec="seconds")}
        storage.update_review(st.session_state.last_saved_id, reviewer, status, notes, decision)
        st.success("Review decision recorded. It will appear in the PDF report.")
    if st.session_state.review:
        r = st.session_state.review
        ui.ok(f"<b>Current review record</b><br/>Reviewer: {r.get('reviewer') or '-'} · Status: {r.get('status')} · "
              f"Decision: {r.get('decision')}<br/>Notes: {r.get('notes') or '-'}")
        if st.button("📄 Generate the reviewed report"):
            goto("Reports")
    ui.disclaimer(config.MAIN_DISCLAIMER + " " + config.EMPLOYMENT_DISCLAIMER)


# ===========================================================================
# PAGE: HR DASHBOARD (Tier 3)
# ===========================================================================
def page_hr_dashboard():
    bundle = get_model_bundle()
    ui.section("👥 HR / Admin Dashboard · Tier 3",
               "Anonymised, aggregated wellness reporting. No item responses or personal identifiers are exposed.")
    ui.warn("<b>Simulated cohort.</b> These candidates are synthetic profiles scored by the real model. "
            + config.EMPLOYMENT_DISCLAIMER)
    n = st.slider("Cohort size to display", 6, 40, 18, step=2)
    cohort = get_hr_cohort_cached(bundle, n)
    counts = {c: sum(1 for r in cohort if r["risk"] == c) for c in config.RISK_CLASSES}
    pending = sum(1 for r in cohort if r["review_status"] == "Pending Review")
    cols = st.columns(5)
    with cols[0]:
        ui.card("Candidates assessed", str(len(cohort)), "Anonymised IDs only")
    for col, cls, emoji in zip(cols[1:4], config.RISK_CLASSES, ["🟢", "🟡", "🔴"]):
        with col:
            ui.card(f"{emoji} {cls.title()} risk", str(counts[cls]), f"{counts[cls] / len(cohort) * 100:.0f}% of cohort")
    with cols[4]:
        ui.card("Pending human review", str(pending), "Routed to Tier 2")
    st.write("")
    c1, c2 = st.columns([2, 3])
    with c1:
        st.plotly_chart(ui.chart_risk_donut(counts), **ui.wide(st.plotly_chart))
    with c2:
        avg = pd.DataFrame(cohort).groupby("risk")[["pss", "gad7", "phq9", "burnout_ee"]].mean().round(1)
        avg = avg.reindex([c for c in config.RISK_CLASSES if c in avg.index])
        avg.columns = ["Avg PSS", "Avg GAD-7", "Avg PHQ-9", "Avg MBI EE"]
        st.markdown("**Average scores by risk band**")
        st.dataframe(avg, **ui.wide(st.dataframe))
        st.caption("Aggregated figures only - individual responses are never shown on this tier.")
    ui.section("📋 Candidate register")
    risk_filter = st.multiselect("Filter by risk level", config.RISK_CLASSES, default=config.RISK_CLASSES)
    table = pd.DataFrame([{
        "Candidate ID": r["candidate_id"], "Assessment Date": r["date"],
        "Risk Level": f"{config.RISK_EMOJI[r['risk']]} {r['risk']}", "Confidence": f"{r['confidence']:.1f}%",
        "Stress (PSS)": r["pss"], "Anxiety (GAD-7)": r["gad7"], "Burnout (MBI EE)": r["burnout_ee"],
        "Review Status": r["review_status"]} for r in cohort if r["risk"] in risk_filter])
    st.dataframe(table, hide_index=True, **ui.wide(st.dataframe))
    st.download_button("⬇️ Download cohort CSV (anonymised)", data=table.to_csv(index=False).encode("utf-8"),
                       file_name=f"WiseOLife_cohort_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")
    ui.warn("⚠️ <b>High-risk cases require human / psychologist review.</b> A risk indication is a screening signal only.")
    ui.disclaimer(config.MAIN_DISCLAIMER + " " + config.EMPLOYMENT_DISCLAIMER)


# ===========================================================================
# PAGE: REPORTS
# ===========================================================================
def page_reports():
    ui.section("📄 Generate Report", "A complete PDF report plus CSV exports of the scores and the 14-feature vector.")
    if not require_result():
        return
    result = st.session_state.result
    bundle = get_model_bundle()
    scores, pred = result["scores"], result["prediction"]
    plan = rec.generate_recommendations(scores, pred)
    explanation = ml.explanation_sentence(bundle, result["features"], pred["risk"])
    demo_banner(result)
    review_status = (st.session_state.review or {}).get("status", "Pending Review" if plan["review_recommended"] else "Not Required")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ui.card("Candidate", result["candidate_id"], result["source"].title())
    with c2:
        ui.card("Risk indication", f"{config.RISK_EMOJI[pred['risk']]} {pred['risk']}", f"{pred['confidence'] * 100:.1f}% confidence")
    with c3:
        ui.card("Instruments", f"{config.N_INSTRUMENTS} / {config.TOTAL_QUESTIONS} items", "Full battery")
    with c4:
        ui.card("Review status", review_status, "Tier 2")
    st.markdown("""
**The report contains:** title block with Candidate ID and date · AI risk classification and confidence ·
scores for PSS, GAD-7, PHQ-9, DASS, MBI and Big Five · score chart · the 14-feature vector · feature-importance chart ·
wellness recommendations · human review status · disclaimers and privacy statement.
""")
    with st.spinner("Building the PDF report..."):
        pdf_bytes = rp.generate_report(result, plan, bundle["importance"], bundle["metrics"],
                                       st.session_state.review, explanation)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("⬇️ Download PDF Report", data=pdf_bytes, file_name=rp.report_filename(result["candidate_id"]),
                           mime="application/pdf", type="primary", **ui.wide(st.download_button))
    with c2:
        st.download_button("⬇️ Download scores CSV", data=rp.generate_csv(result),
                           file_name=f"WiseOLife_scores_{result['candidate_id']}.csv", mime="text/csv",
                           **ui.wide(st.download_button))
    with c3:
        st.download_button("⬇️ Download 14-feature CSV", data=rp.generate_feature_row_csv(result),
                           file_name=f"WiseOLife_features_{result['candidate_id']}.csv", mime="text/csv",
                           **ui.wide(st.download_button))
    st.caption(f"PDF size: {len(pdf_bytes) / 1024:.0f} KB · generated in memory, nothing is uploaded anywhere.")
    with st.expander("💾 Also save a copy into generated_reports/ (local runs only)"):
        if st.button("Save a local copy"):
            path = rp.save_report_to_disk(pdf_bytes, result["candidate_id"])
            st.success(f"Saved to `{path}`") if path else st.info("Filesystem not writable here; use the download button.")
    ui.section("🔢 Feature vector included in the report")
    ui.feature_vector_block(result["features"])
    ui.disclaimer(config.MAIN_DISCLAIMER + " " + config.EMPLOYMENT_DISCLAIMER)


# ===========================================================================
# PAGE: ABOUT
# ===========================================================================
def page_about():
    ui.section(f"ℹ️ About {config.APP_NAME}", config.SUBTAGLINE)
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
    ui.section("👥 Team & Contributions")
    ui.note("Editable placeholders - set names and roll numbers in <code>wiseolife/config.py</code> → <code>TEAM_MEMBERS</code>.")
    for col, member in zip(st.columns(3), config.TEAM_MEMBERS):
        with col:
            ui.card(member["role"], member["placeholder_name"], member["roll_no"])
            for r in member["responsibilities"]:
                st.markdown(f"- {r}")
    st.markdown(f"**Institution:** {config.INSTITUTION} · {config.DEPARTMENT} · {config.DEGREE} · "
                f"Guide: {config.GUIDE_NAME} · Academic year: {config.ACADEMIC_YEAR}")

    ui.section("🔒 Data Privacy")
    ui.ok(config.PRIVACY_NOTICE)
    s = storage.stats()
    st.caption(f"Local database: {'writable' if s['available'] else 'not writable (session-only history)'} · "
               f"{s['assessments']} assessment(s), {s['journal']} journal entr(y/ies).")
    if st.button("🗑️ Delete all locally stored data"):
        if storage.clear_all():
            st.session_state.session_history = []
            st.session_state.journal_session = []
            st.success("All locally stored assessments and journal entries deleted.")
        else:
            st.info("Nothing to delete - local storage is not in use here.")

    ui.section("⚠️ Disclaimer")
    ui.disclaimer(config.MAIN_DISCLAIMER)
    ui.disclaimer(config.EMPLOYMENT_DISCLAIMER)
    ui.note(config.WORDING_NOTICE)

    ui.section("🧪 Developer / Validation")
    with st.expander("Run the scoring and model self-tests"):
        st.markdown("Verifies reverse scoring, DASS ×2, MBI dimensions, Big Five reverse items, the 14-feature vector and the "
                    "model pipeline. Also runnable with `python -m wiseolife.selftest`.")
        if st.button("▶️ Run all self-tests", type="primary"):
            with st.spinner("Running tests..."):
                rows, passed, total = selftest.run_all_tests(get_model_bundle())
            (st.success if passed == total else st.error)(
                f"✅ All {total} tests passed." if passed == total else f"❌ {total - passed} of {total} tests failed.")
            st.dataframe(pd.DataFrame([{"Result": "✅ PASS" if r["passed"] else "❌ FAIL", "Test": r["test"],
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
    render_sidebar()
    page = st.session_state.page
    if page not in PAGE_FUNCTIONS:
        page = st.session_state.page = "Home"
    PAGE_FUNCTIONS[page]()


main()
