"""WiseBot - a small rule-based wellness assistant. No API key, works offline."""
from . import config

SUGGESTED_QUESTIONS = [
    "What does my stress score mean?",
    "What is PSS?",
    "How can I manage stress?",
    "What is burnout?",
    "What does neuroticism mean?",
    "What is GAD-7?",
    "What are the 14 features?",
    "Why Random Forest?",
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
            f"**{p['risk']}** ({p['confidence'] * 100:.0f}% confidence) - not a diagnosis.")


def get_response(text, result=None):
    t = (text or "").lower().strip()
    if not t:
        return "Ask me about PSS, GAD-7, PHQ-9, DASS-21, burnout, the Big Five, the 14 features or your scores."
    if any(w in t for w in ["suicid", "kill myself", "self-harm", "self harm", "hurt myself", "end my life"]):
        return _SAFETY
    if any(p in t for p in ["my score", "my result", "my stress", "mean my", "my risk", "my prediction"]) \
            or ("score" in t and "mean" in t) or "my" in t.split() and "score" in t:
        return _score_answer(result)
    for keywords, answer in _KB:
        if all(k in t for k in keywords):
            return answer
    if any(g in t for g in ["hello", "hi ", "hey"]) or t in ("hi", "hey"):
        return "Hello! I'm WiseBot 🤖. Ask me about the instruments, your scores, the model or wellness tips."
    return ("I'm a small rule-based assistant, so I may not know that one. Try asking about PSS, GAD-7, PHQ-9, "
            "DASS, burnout, neuroticism, the 14 features, Random Forest, or 'what does my stress score mean?'.")
