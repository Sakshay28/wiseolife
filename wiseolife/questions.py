"""WiseOLife - the 89-item question bank (6 instruments).

The wording below is PARAPHRASED for academic use. To use institution-approved or
licensed wording, edit only the "text" fields - the scoring engine reads the
structure (scale, dimension, reverse flag), never the wording.
"""

# ---------------------------------------------------------------------------
# CONFIGURABLE SCORING SWITCHES
# ---------------------------------------------------------------------------
# 1-based PSS item numbers that are reverse scored. The WiseOLife specification uses
# 4, 5, 6, 7, 8. (The widely published PSS-10 reverse-scores 4, 5, 7, 8 only.)
# Change this ONE list to switch - nothing else needs editing.
PSS_REVERSE_ITEMS = [4, 5, 6, 7, 8]

# 0-based index of the PHQ-9 item about thoughts of self-harm (item 9).
PHQ9_SAFETY_ITEM_INDEX = 8
PHQ9_SAFETY_THRESHOLD = 1   # any answer >= 1 ("several days") raises the safety notice

BIG5_TRAIT_NAMES = {
    "O": "Openness", "C": "Conscientiousness", "E": "Extraversion",
    "A": "Agreeableness", "N": "Neuroticism",
}

INSTRUMENT_ORDER = ["pss", "gad7", "phq9", "dass", "mbi", "big5"]

_FREQ_4 = [(0, "Not at all"), (1, "Several days"),
           (2, "More than half the days"), (3, "Nearly every day")]

# ---------------------------------------------------------------------------
# PSS-10
# ---------------------------------------------------------------------------
_PSS_TEXTS = [
    "How often have you been upset because of something that happened unexpectedly?",
    "How often have you felt unable to control the important things in your life?",
    "How often have you felt nervous and stressed?",
    "How often have you felt confident about your ability to handle personal problems?",
    "How often have you felt that things were going your way?",
    "How often have you found that you could not cope with all the things you had to do?",
    "How often have you been able to control irritations in your life?",
    "How often have you felt that you were on top of things?",
    "How often have you been angered by things that were outside your control?",
    "How often have you felt that difficulties were piling up so high you could not overcome them?",
]
PSS = {
    "key": "pss", "name": "PSS-10", "icon": "😰",
    "full_name": "Perceived Stress Scale",
    "instructions": "In the **last month**, how often have you felt or thought the following?",
    "scale": [(0, "Never"), (1, "Almost Never"), (2, "Sometimes"),
              (3, "Fairly Often"), (4, "Very Often")],
    "scale_min": 0, "scale_max": 4, "default": 0,
    "items": [{"text": t, "reverse": (i + 1) in PSS_REVERSE_ITEMS}
              for i, t in enumerate(_PSS_TEXTS)],
}

# ---------------------------------------------------------------------------
# GAD-7
# ---------------------------------------------------------------------------
_GAD_TEXTS = [
    "Feeling nervous, anxious or on edge",
    "Not being able to stop or control worrying",
    "Worrying too much about different things",
    "Trouble relaxing",
    "Being so restless that it is hard to sit still",
    "Becoming easily annoyed or irritable",
    "Feeling afraid as if something awful might happen",
]
GAD7 = {
    "key": "gad7", "name": "GAD-7", "icon": "😟",
    "full_name": "Generalized Anxiety Disorder scale",
    "instructions": "Over the **last 2 weeks**, how often have you been bothered by the following?",
    "scale": _FREQ_4, "scale_min": 0, "scale_max": 3, "default": 0,
    "items": [{"text": t, "reverse": False} for t in _GAD_TEXTS],
}

# ---------------------------------------------------------------------------
# PHQ-9
# ---------------------------------------------------------------------------
_PHQ_TEXTS = [
    "Little interest or pleasure in doing things",
    "Feeling down, depressed or hopeless",
    "Trouble falling or staying asleep, or sleeping too much",
    "Feeling tired or having little energy",
    "Poor appetite or overeating",
    "Feeling bad about yourself, or that you are a failure or have let others down",
    "Trouble concentrating on things such as reading or watching television",
    "Moving or speaking so slowly that others noticed - or being unusually restless",
    "Thoughts that you would be better off not being here, or of hurting yourself in some way",
]
PHQ9 = {
    "key": "phq9", "name": "PHQ-9", "icon": "😔",
    "full_name": "Patient Health Questionnaire",
    "instructions": "Over the **last 2 weeks**, how often have you been bothered by the following?",
    "scale": _FREQ_4, "scale_min": 0, "scale_max": 3, "default": 0,
    "items": [{"text": t, "reverse": False} for t in _PHQ_TEXTS],
}

# ---------------------------------------------------------------------------
# DASS-21  (dim: D = depression, A = anxiety, S = stress, 7 items each)
# ---------------------------------------------------------------------------
_DASS = [
    ("I found it hard to wind down", "S"),
    ("I was aware of dryness in my mouth", "A"),
    ("I could not seem to experience any positive feeling at all", "D"),
    ("I had difficulty breathing without physical exertion", "A"),
    ("I found it difficult to work up the initiative to do things", "D"),
    ("I tended to over-react to situations", "S"),
    ("I experienced trembling, for example in my hands", "A"),
    ("I felt that I was using a lot of nervous energy", "S"),
    ("I was worried about situations in which I might panic or make a fool of myself", "A"),
    ("I felt that I had nothing to look forward to", "D"),
    ("I found myself getting agitated", "S"),
    ("I found it difficult to relax", "S"),
    ("I felt down-hearted and blue", "D"),
    ("I was intolerant of anything that kept me from getting on with what I was doing", "S"),
    ("I felt I was close to panic", "A"),
    ("I was unable to become enthusiastic about anything", "D"),
    ("I felt I was not worth much as a person", "D"),
    ("I felt that I was rather touchy", "S"),
    ("I was aware of my heart beating without physical exertion", "A"),
    ("I felt scared without any good reason", "A"),
    ("I felt that life was meaningless", "D"),
]
DASS = {
    "key": "dass", "name": "DASS-21", "icon": "📉",
    "full_name": "Depression Anxiety Stress Scale",
    "instructions": "Over the **past week**, how much did each statement apply to you?",
    "scale": [(0, "Did not apply to me"), (1, "Applied some of the time"),
              (2, "Applied a good part of the time"), (3, "Applied most of the time")],
    "scale_min": 0, "scale_max": 3, "default": 0,
    "items": [{"text": t, "dim": d, "reverse": False} for t, d in _DASS],
}

# ---------------------------------------------------------------------------
# MBI structure (22 items: EE 9, DP 5, PA 8)
# ---------------------------------------------------------------------------
_MBI = [
    ("I feel emotionally drained from my work or studies", "EE"),
    ("I feel used up at the end of the working day", "EE"),
    ("I feel tired when I get up and face another day of work or study", "EE"),
    ("I can easily understand how the people around me feel", "PA"),
    ("I feel I treat some people as if they were impersonal objects", "DP"),
    ("Working with people all day is really a strain for me", "EE"),
    ("I deal very effectively with the problems of others", "PA"),
    ("I feel burned out from my work or studies", "EE"),
    ("I feel I am positively influencing other people's lives through my work", "PA"),
    ("I have become more callous towards people since I took this role", "DP"),
    ("I worry that this work is hardening me emotionally", "DP"),
    ("I feel very energetic", "PA"),
    ("I feel frustrated by my work or studies", "EE"),
    ("I feel I am working too hard", "EE"),
    ("I do not really care what happens to some of the people I deal with", "DP"),
    ("Working directly with people puts too much stress on me", "EE"),
    ("I can easily create a relaxed atmosphere with others", "PA"),
    ("I feel exhilarated after working closely with others", "PA"),
    ("I have accomplished many worthwhile things in this role", "PA"),
    ("I feel I am at the end of my rope", "EE"),
    ("In my work I deal with emotional problems very calmly", "PA"),
    ("I feel others blame me for some of their problems", "DP"),
]
MBI = {
    "key": "mbi", "name": "MBI", "icon": "🔥",
    "full_name": "Maslach Burnout Inventory (22-item structure)",
    "instructions": "How **often** do you have each of these feelings about your work or studies?",
    "scale": [(0, "Never"), (1, "A few times a year"), (2, "Once a month"),
              (3, "A few times a month"), (4, "Once a week"),
              (5, "A few times a week"), (6, "Every day")],
    "scale_min": 0, "scale_max": 6, "default": 0,
    "items": [{"text": t, "dim": d, "reverse": False} for t, d in _MBI],
}

# ---------------------------------------------------------------------------
# BIG FIVE (20 items, 4 per trait, some reverse worded)
# ---------------------------------------------------------------------------
_BIG5 = [
    ("I have a vivid imagination", "O", False),
    ("I enjoy trying new ideas and experiences", "O", False),
    ("I am not interested in abstract ideas", "O", True),
    ("I prefer routine to variety", "O", True),
    ("I am always prepared", "C", False),
    ("I pay attention to details", "C", False),
    ("I leave my belongings around", "C", True),
    ("I often forget to put things back in their proper place", "C", True),
    ("I am the life of the party", "E", False),
    ("I feel comfortable around people", "E", False),
    ("I keep in the background", "E", True),
    ("I find it hard to start conversations", "E", True),
    ("I am interested in other people's problems", "A", False),
    ("I take time out for others", "A", False),
    ("I am not really interested in others", "A", True),
    ("I insult people", "A", True),
    ("I get stressed out easily", "N", False),
    ("I worry about things", "N", False),
    ("I am relaxed most of the time", "N", True),
    ("I seldom feel blue", "N", True),
]
BIG5 = {
    "key": "big5", "name": "Big Five", "icon": "🌈",
    "full_name": "Big Five personality (OCEAN)",
    "instructions": "How much do you **agree** that each statement describes you?",
    "scale": [(1, "Strongly Disagree"), (2, "Disagree"), (3, "Neutral"),
              (4, "Agree"), (5, "Strongly Agree")],
    "scale_min": 1, "scale_max": 5, "default": 3,
    "items": [{"text": t, "dim": d, "reverse": r} for t, d, r in _BIG5],
}

INSTRUMENTS = {"pss": PSS, "gad7": GAD7, "phq9": PHQ9, "dass": DASS, "mbi": MBI, "big5": BIG5}


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def get_instrument(key):
    return INSTRUMENTS[key]


def item_count(key):
    return len(INSTRUMENTS[key]["items"])


def total_question_count():
    return sum(item_count(k) for k in INSTRUMENT_ORDER)


def question_offset(key):
    """Number of questions that come before this instrument (for 'Q42' numbering)."""
    offset = 0
    for k in INSTRUMENT_ORDER:
        if k == key:
            return offset
        offset += item_count(k)
    return offset


def reverse_item_numbers(key):
    """1-based numbers of reverse-scored items in an instrument."""
    return [i + 1 for i, item in enumerate(INSTRUMENTS[key]["items"]) if item["reverse"]]


def empty_responses():
    """A fresh response dict: every answer None (unanswered)."""
    return {k: [None] * item_count(k) for k in INSTRUMENT_ORDER}
