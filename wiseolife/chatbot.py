"""WiseBot - a small rule-based wellness assistant. No API key, works offline."""
import re

from . import config
from . import questions as qs
from . import teststate as ts

SUGGESTED_QUESTIONS = [
    "Explain this question",
    "What does this section measure?",
    "What do the risk levels mean?",
    "What does my stress score mean?",
    "What is PSS?",
    "How can I manage stress?",
    "What is burnout?",
    "What does neuroticism mean?",
    "What are the 14 features?",
]

# Questions offered inside the assessment (context-aware, read-only).
IN_TEST_QUESTIONS = [
    "Explain this question",
    "What does this section measure?",
    "How many questions have I skipped?",
    "What do the risk levels mean?",
]

_SAFETY = ("I'm not a substitute for professional help. If you feel unsafe or are thinking "
           "about harming yourself, please contact local emergency services or a trusted "
           "person right now.")

# (keywords, answer). First entry whose keywords are ALL present wins; ordered specific -> general.
_KB = [
    (["14", "feature"], "The model uses **14 features**: PSS, GAD-7, PHQ-9, DASS Depression/Anxiety/Stress, "
     "MBI Emotional Exhaustion/Depersonalization/Personal Accomplishment, and the Big Five (O, C, E, A, N). "
     "They are kept separate - there is no combined 'burnout' feature."),
    (["random", "forest"], "A **Random Forest** is 200 decision trees that each vote on LOW / MEDIUM / HIGH. "
     "It suits small tabular data, resists overfitting and gives feature importances for explainability."),
    (["synthetic"], "Real mental-health data is sensitive, so the model is trained on **3000 synthetic profiles** "
     "labelled by a transparent points rule. Its metrics therefore measure the rule, not clinical accuracy."),
    (["pss"], "**PSS** is the Perceived Stress Scale: 10 questions about how unpredictable, uncontrollable and "
     "overloaded life felt in the last month. Score 0-40: 0-13 Low, 14-26 Moderate, 27-40 High."),
    (["gad"], "**GAD-7** is a 7-question anxiety screening scale scored 0-21: 0-4 Minimal, 5-9 Mild, 10-14 Moderate, 15-21 Severe."),
    (["phq"], "**PHQ-9** is a 9-question depression screening scale scored 0-27 (Minimal to Severe). Item 9 asks about "
     "self-harm thoughts, so any elevated answer triggers a safety notice."),
    (["dass"], "**DASS-21** has 7 items each for depression, anxiety and stress. Each subscale is summed and multiplied by 2."),
    (["personal", "accomplishment"], "**Personal Accomplishment** (MBI) is a *positive* dimension - high is good, low is the concern."),
    (["depersonal"], "**Depersonalization** means becoming detached or cynical toward people at work/study. Higher scores are more concerning."),
    (["exhaust"], "**Emotional exhaustion** is feeling drained and used up by work or study - the core burnout signal. Higher is more concerning."),
    (["burnout"], "**Burnout** is prolonged exhaustion from work or study, measured by MBI in three parts: Emotional Exhaustion, "
     "Depersonalization and Personal Accomplishment. It is not a medical diagnosis."),
    (["neurotic"], "**Neuroticism** is the Big Five trait describing how strongly someone tends to experience worry, "
     "stress and low mood. High scores are not a disorder - just a tendency that benefits from coping routines."),
    (["openness"], "**Openness** reflects curiosity and willingness to try new ideas and experiences."),
    (["conscientious"], "**Conscientiousness** reflects organisation, reliability and self-discipline."),
    (["extravers"], "**Extraversion** reflects sociability and energy from being around people."),
    (["agreeable"], "**Agreeableness** reflects warmth, cooperation and care for others."),
    (["big five"], "The **Big Five (OCEAN)** are Openness, Conscientiousness, Extraversion, Agreeableness and Neuroticism, each scored 1-5."),
    (["manage", "stress"], "General stress tips: slow breathing (4-7-8), short structured breaks, a steady sleep routine, "
     "movement, and prioritising your top three tasks. If stress stays high, talk to a counsellor."),
    (["anxiety"], "For everyday anxiety try grounding (5-4-3-2-1), relaxation exercises and reducing caffeine. "
     "Persistent anxiety deserves professional support."),
    (["sleep"], "Aim for a consistent sleep schedule, a dark cool room, and no screens 30 minutes before bed."),
    (["review"], "High-risk cases are routed to a **human reviewer** (Tier 2) because the AI only screens - it cannot understand context."),
    (["diagnos"], "WiseOLife is a screening and decision-support prototype. It is **not** a diagnostic tool."),
    (["privacy"], config.PRIVACY_NOTICE),
]


def _score_answer(result):
    if not result:
        return ("Load a demo candidate or complete the assessment first, and I can explain your own scores.")
    s = result["scores"]
    p = result["prediction"]
    return (f"Your scores: PSS **{s['pss']['score']}/40 ({s['pss']['level']})**, GAD-7 **{s['gad7']['score']}/21 "
            f"({s['gad7']['level']})**, PHQ-9 **{s['phq9']['score']}/27 ({s['phq9']['level']})**, DASS stress "
            f"**{s['dass']['stress']}/42 ({s['dass']['stress_level']})**. The model's screening indication is "
            f"**{config.risk_label(p['risk'], with_name=True)}** ({p['confidence'] * 100:.0f}% confidence) - not a diagnosis.")


_DIM_NAMES = {"D": "Depression", "A": "Anxiety", "S": "Stress", "EE": "Emotional Exhaustion",
              "DP": "Depersonalization", "PA": "Personal Accomplishment",
              "O": "Openness", "C": "Conscientiousness", "E": "Extraversion",
              "N": "Neuroticism"}


def risk_definitions_text():
    """All risk levels with number, name and definition (from config.RISK_LEVELS)."""
    lines = [f"**R{r['number']} · {r['name']}** - {r['definition']}" for r in config.RISK_LEVELS]
    return "WiseOLife uses three risk levels:\n" + "\n".join(lines) + \
        "\nThey describe a screening indication, not a diagnosis."


def explain_instrument(inst_key):
    inst = qs.get_instrument(inst_key)
    scale = ", ".join(f"{v} = {lab}" for v, lab in inst["scale"])
    extra = ""
    if inst_key == "pss":
        extra = f" Items {', '.join(map(str, qs.reverse_item_numbers('pss')))} are reverse scored (marked 🔄)."
    elif inst_key == "big5":
        extra = f" Items {', '.join(map(str, qs.reverse_item_numbers('big5')))} are reverse worded (🔄) and flipped when scoring."
    elif inst_key == "mbi":
        extra = " Emotional Exhaustion and Depersonalization: higher is more concerning. Personal Accomplishment: higher is better."
    elif inst_key == "dass":
        extra = " Each of the 3 subscales sums 7 items and is multiplied by 2."
    return (f"**{inst['name']}** - {inst['full_name']}. {inst['instructions'].replace('**', '')} "
            f"Answer scale: {scale}.{extra}")


def explain_question(number):
    """Plain-language explanation of one question. Read-only: never touches answers."""
    if not 1 <= number <= config.TOTAL_QUESTIONS:
        return f"Question numbers run from 1 to {config.TOTAL_QUESTIONS}."
    key, idx, _sec = ts.locate(number)
    inst = qs.get_instrument(key)
    item = inst["items"][idx]
    parts = [f"**Q{number}** ({inst['name']}, item {idx + 1}): \"{item['text']}\""]
    dim = item.get("dim")
    if dim:
        parts.append(f"It contributes to the **{_DIM_NAMES.get(dim, dim)}** score.")
    else:
        parts.append(f"It adds to the overall {inst['name']} total.")
    if item["reverse"]:
        parts.append("🔄 It is **reverse scored**: your answer is flipped (new = scale max - answer) so a higher final "
                     "score always means the same direction. Just answer honestly.")
    parts.append("Choose the option that best matches how you have felt over the stated period - there is no right or wrong answer.")
    return " ".join(parts)


def _progress_text(progress):
    if not progress:
        return "Start the assessment and I can tell you how many questions you have answered or skipped."
    return (f"You have answered **{progress['answered']}** of {progress['total']}, skipped **{progress['skipped']}** "
            f"and have **{progress['unanswered']}** not yet reached. Skipped questions can be answered before you submit.")


def get_response(text, result=None, context=None):
    """Rule-based reply. `context` (optional, read-only) may hold: question (global number),
    section (instrument key) and progress (counts). Never modifies anything."""
    context = context or {}
    t = (text or "").lower().strip()
    if not t:
        return "Ask me about PSS, GAD-7, PHQ-9, DASS-21, burnout, the Big Five, the 14 features, risk levels or your scores."
    if any(w in t for w in ["suicid", "kill myself", "self-harm", "self harm", "hurt myself", "end my life"]):
        return _SAFETY

    # --- risk levels / definitions
    m = re.search(r"\br\s?([123])\b|risk (?:level|number|no\.?)\s*([123])", t)
    if m:
        n = int(m.group(1) or m.group(2))
        r = next(x for x in config.RISK_LEVELS if x["number"] == n)
        return f"**R{r['number']} · {r['name']}** - {r['definition']}"
    for r in config.RISK_LEVELS:
        if f"{r['key'].lower()} risk" in t and "my" not in t.split():
            return f"**R{r['number']} · {r['name']}** - {r['definition']}"
    if "risk" in t and any(w in t for w in ["level", "levels", "classif", "definition", "categories", "mean", "number"]) \
            and "my" not in t.split():
        return risk_definitions_text()

    # --- question explanation
    q = re.search(r"\bq(?:uestion)?\s*#?(\d{1,2})\b", t)
    if q:
        return explain_question(int(q.group(1)))
    if any(p in t for p in ["this question", "current question", "explain the question", "explain this"]):
        if context.get("question"):
            return explain_question(int(context["question"]))
        return "Open the assessment and I can explain the question you are on - or ask for a specific one, e.g. 'explain question 12'."
    if any(p in t for p in ["this section", "this scale", "this instrument", "this part"]):
        if context.get("section"):
            return explain_instrument(context["section"])
        return "Open a section of the assessment first, or ask about a specific scale such as PSS or GAD-7."

    # --- progress (read-only snapshot)
    if any(w in t for w in ["skipped", "unanswered", "left to answer", "remaining", "how many have i"]):
        return _progress_text(context.get("progress"))

    # --- personal results
    if any(p in t for p in ["my score", "my result", "my stress", "my risk", "my prediction", "mean my"]) \
            or ("score" in t and "mean" in t):
        return _score_answer(result)
    for keywords, answer in _KB:
        if all(k in t for k in keywords):
            return answer
    if any(g in t for g in ["hello", "hi ", "hey"]) or t in ("hi", "hey"):
        return "Hello! I'm WiseBot 🤖. Ask me about the instruments, a question, the risk levels, your scores or wellness tips."
    return ("I'm a small rule-based assistant, so I may not know that one. Try: 'explain question 12', 'what do the risk "
            "levels mean?', 'what is PSS?', 'how many questions have I skipped?' or 'what does my stress score mean?'.")


def safe_ask(text, result=None, context=None):
    """Wrapper used by the UI: returns {'ok': True, 'text': reply} or {'ok': False, 'error': msg}."""
    try:
        return {"ok": True, "text": get_response(text, result, context)}
    except Exception as exc:  # the UI shows a retry button instead of crashing
        return {"ok": False, "error": f"WiseBot hit a problem ({type(exc).__name__}). Please try again."}
