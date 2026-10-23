"""WiseOLife - scoring engine for the six instruments and the 14-feature vector.

Missing answers: an unanswered item contributes the scale default (0 for the
symptom scales, 3 = Neutral for the Big Five) and is never reversed. The result is
marked complete=False so the UI can warn the user.
"""
from . import config
from . import questions as qs

# ---------------------------------------------------------------------------
# INTERPRETATION BANDS: list of (upper_inclusive, label)
# ---------------------------------------------------------------------------
PSS_BANDS = [(13, "Low"), (26, "Moderate"), (40, "High")]
GAD7_BANDS = [(4, "Minimal"), (9, "Mild"), (14, "Moderate"), (21, "Severe")]
PHQ9_BANDS = [(4, "Minimal"), (9, "Mild"), (14, "Moderate"),
              (19, "Moderately Severe"), (27, "Severe")]
DASS_D_BANDS = [(9, "Normal"), (13, "Mild"), (20, "Moderate"), (27, "Severe"), (42, "Extremely Severe")]
DASS_A_BANDS = [(7, "Normal"), (9, "Mild"), (14, "Moderate"), (19, "Severe"), (42, "Extremely Severe")]
DASS_S_BANDS = [(14, "Normal"), (18, "Mild"), (25, "Moderate"), (33, "Severe"), (42, "Extremely Severe")]
MBI_EE_BANDS = [(18, "Low"), (26, "Moderate"), (54, "High")]
MBI_DP_BANDS = [(5, "Low"), (9, "Moderate"), (30, "High")]
# Personal Accomplishment: HIGH is POSITIVE. Labels describe the score itself.
MBI_PA_BANDS = [(31, "Low"), (38, "Moderate"), (48, "High")]
BIG5_BANDS = [(2.5, "Low"), (3.5, "Moderate"), (5.0, "High")]

DASS_MULTIPLIER = 2
PSS_REVERSE_FORMULA = "new_score = max_scale - original_score  (= 4 - original on the 0-4 scale)"
BIG5_REVERSE_FORMULA = "new_score = 6 - original_score  (= min + max - original on the 1-5 scale)"


def band(value, bands):
    """Return the label of the first band whose upper bound is >= value."""
    for upper, label in bands:
        if value <= upper:
            return label
    return bands[-1][1]


def reverse_value(x, scale_min, scale_max):
    """Reverse a response: (min + max) - x. On 0-4 this equals 4 - x."""
    return scale_min + scale_max - x


def _value(resp, inst_key, i):
    """Answer for item i, or the instrument default if unanswered."""
    v = resp[inst_key][i]
    return (qs.INSTRUMENTS[inst_key]["default"], True) if v is None else (v, False)


def _count_missing(resp, inst_key):
    return sum(1 for v in resp[inst_key] if v is None)


# ---------------------------------------------------------------------------
# INDIVIDUAL SCORERS
# ---------------------------------------------------------------------------
def _pss_result(adjusted, raw=None):
    return {
        "score": adjusted, "adjusted": adjusted, "raw": raw,
        "level": band(adjusted, PSS_BANDS),
        "reverse_items": list(qs.PSS_REVERSE_ITEMS),
        "reverse_formula": PSS_REVERSE_FORMULA,
    }


def score_pss(resp):
    inst = qs.PSS
    raw = adjusted = 0
    for i in range(len(inst["items"])):
        v, missing = _value(resp, "pss", i)
        raw += v
        if inst["items"][i]["reverse"] and not missing:
            v = reverse_value(v, inst["scale_min"], inst["scale_max"])
        adjusted += v
    return _pss_result(adjusted, raw)


def _gad_result(total):
    return {"score": total, "level": band(total, GAD7_BANDS)}


def score_gad(resp):
    total = sum(_value(resp, "gad7", i)[0] for i in range(qs.item_count("gad7")))
    return _gad_result(total)


def _phq_result(total, safety_flag):
    return {"score": total, "level": band(total, PHQ9_BANDS), "safety_flag": safety_flag}


def score_phq(resp):
    total = sum(_value(resp, "phq9", i)[0] for i in range(qs.item_count("phq9")))
    safety_answer = resp["phq9"][qs.PHQ9_SAFETY_ITEM_INDEX]
    flag = safety_answer is not None and safety_answer >= qs.PHQ9_SAFETY_THRESHOLD
    return _phq_result(total, flag)


def _dass_result(d, a, s):
    return {
        "depression": d, "anxiety": a, "stress": s,
        "depression_level": band(d, DASS_D_BANDS),
        "anxiety_level": band(a, DASS_A_BANDS),
        "stress_level": band(s, DASS_S_BANDS),
        "multiplier": DASS_MULTIPLIER,
    }


def score_dass(resp):
    sums = {"D": 0, "A": 0, "S": 0}
    for i, item in enumerate(qs.DASS["items"]):
        sums[item["dim"]] += _value(resp, "dass", i)[0]
    m = DASS_MULTIPLIER
    return _dass_result(sums["D"] * m, sums["A"] * m, sums["S"] * m)


def _mbi_result(ee, dp, pa):
    return {
        "emotional_exhaustion": ee, "depersonalization": dp, "personal_accomplishment": pa,
        "ee_level": band(ee, MBI_EE_BANDS),
        "dp_level": band(dp, MBI_DP_BANDS),
        "pa_level": band(pa, MBI_PA_BANDS),
    }


def score_mbi(resp):
    sums = {"EE": 0, "DP": 0, "PA": 0}
    for i, item in enumerate(qs.MBI["items"]):
        sums[item["dim"]] += _value(resp, "mbi", i)[0]
    return _mbi_result(sums["EE"], sums["DP"], sums["PA"])


def _big5_result(traits):
    """traits: dict with keys O,C,E,A,N -> float (1-5)."""
    names = {"O": "openness", "C": "conscientiousness", "E": "extraversion",
             "A": "agreeableness", "N": "neuroticism"}
    out = {
        "traits": dict(traits),
        "levels": {t: band(traits[t], BIG5_BANDS) for t in "OCEAN"},
        "reverse_items": [i + 1 for i, it in enumerate(qs.BIG5["items"]) if it["reverse"]],
        "reverse_formula": BIG5_REVERSE_FORMULA,
    }
    for letter, name in names.items():
        out[name] = traits[letter]
    return out


def score_big5(resp):
    inst = qs.BIG5
    sums = {t: 0.0 for t in "OCEAN"}
    counts = {t: 0 for t in "OCEAN"}
    for i, item in enumerate(inst["items"]):
        v, missing = _value(resp, "big5", i)
        if item["reverse"] and not missing:
            v = reverse_value(v, inst["scale_min"], inst["scale_max"])
        sums[item["dim"]] += v
        counts[item["dim"]] += 1
    traits = {t: round(sums[t] / counts[t], 2) for t in "OCEAN"}
    return _big5_result(traits)


# ---------------------------------------------------------------------------
# COMBINED SCORING + FEATURE VECTOR
# ---------------------------------------------------------------------------
def score_all(resp):
    missing = {k: _count_missing(resp, k) for k in qs.INSTRUMENT_ORDER}
    total_missing = sum(missing.values())
    return {
        "pss": score_pss(resp), "gad7": score_gad(resp), "phq9": score_phq(resp),
        "dass": score_dass(resp), "mbi": score_mbi(resp), "big5": score_big5(resp),
        "missing": missing, "missing_total": total_missing,
        "complete": total_missing == 0,
    }


def build_feature_vector(scores):
    """The exact 14 numbers fed to the model, in config.FEATURE_NAMES order."""
    d, m, b = scores["dass"], scores["mbi"], scores["big5"]
    vector = [
        scores["pss"]["score"], scores["gad7"]["score"], scores["phq9"]["score"],
        d["depression"], d["anxiety"], d["stress"],
        m["emotional_exhaustion"], m["depersonalization"], m["personal_accomplishment"],
        b["openness"], b["conscientiousness"], b["extraversion"],
        b["agreeableness"], b["neuroticism"],
    ]
    return [float(x) for x in vector]


def scores_from_feature_dict(f):
    """Rebuild the full scores structure from 14 feature values (used by demo mode)."""
    traits = {"O": f["openness"], "C": f["conscientiousness"], "E": f["extraversion"],
              "A": f["agreeableness"], "N": f["neuroticism"]}
    return {
        "pss": _pss_result(int(round(f["pss_score"]))),
        "gad7": _gad_result(int(round(f["gad7_score"]))),
        "phq9": _phq_result(int(round(f["phq9_score"])), False),
        "dass": _dass_result(int(round(f["dass_depression"])), int(round(f["dass_anxiety"])),
                             int(round(f["dass_stress"]))),
        "mbi": _mbi_result(int(round(f["mbi_emotional_exhaustion"])),
                           int(round(f["mbi_depersonalization"])),
                           int(round(f["mbi_personal_accomplishment"]))),
        "big5": _big5_result(traits),
        "missing": {k: 0 for k in qs.INSTRUMENT_ORDER}, "missing_total": 0, "complete": True,
    }


def summary_cards(scores):
    """Six headline cards for the results dashboard."""
    d, m, b = scores["dass"], scores["mbi"], scores["big5"]
    return [
        {"icon": "😰", "title": "PSS · Perceived Stress", "help": "Perceived Stress Scale (0-40): how overloaded and out of control life felt this past month. Bands: 0-13 Low, 14-26 Moderate, 27-40 High.", "value": f"{scores['pss']['score']} / 40",
         "level": scores["pss"]["level"], "caption": "Higher = more stress"},
        {"icon": "😟", "title": "GAD-7 · Anxiety", "help": "Anxiety screening (0-21). 0-4 Minimal, 5-9 Mild, 10-14 Moderate, 15-21 Severe.", "value": f"{scores['gad7']['score']} / 21",
         "level": scores["gad7"]["level"], "caption": "Higher = more anxiety symptoms"},
        {"icon": "😔", "title": "PHQ-9 · Depression", "help": "Depression screening (0-27). 0-4 Minimal up to 20-27 Severe.", "value": f"{scores['phq9']['score']} / 27",
         "level": scores["phq9"]["level"], "caption": "Higher = more depressive symptoms"},
        {"icon": "📉", "title": "DASS · Stress subscale", "help": "Stress part of DASS-21 (0-42, items summed then x2). D / A / S below show all three subscales.", "value": f"{d['stress']} / 42",
         "level": d["stress_level"],
         "caption": f"D {d['depression']} · A {d['anxiety']} · S {d['stress']}"},
        {"icon": "🔥", "title": "MBI · Emotional Exhaustion", "help": "Core burnout signal (0-54): feeling drained by work or study. DP = Depersonalization, PA = Personal Accomplishment (high PA is good).",
         "value": f"{m['emotional_exhaustion']} / 54", "level": m["ee_level"],
         "caption": f"DP {m['depersonalization']} · PA {m['personal_accomplishment']}"},
        {"icon": "🌈", "title": "Big Five · Neuroticism", "help": "Tendency toward worry and low mood (1-5). O C E A = Openness, Conscientiousness, Extraversion, Agreeableness.", "value": f"{b['neuroticism']} / 5",
         "level": b["levels"]["N"],
         "caption": f"O {b['openness']} · C {b['conscientiousness']} · "
                    f"E {b['extraversion']} · A {b['agreeableness']}"},
    ]
