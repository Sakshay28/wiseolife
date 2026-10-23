"""WiseOLife - synthetic demo candidates, demo history, demo HR cohort, demo journal.

All values here are clearly synthetic. The displayed risk is ALWAYS the model's own
prediction - `expected_risk` is only used by the self-test to detect drift.
"""
from datetime import date, timedelta

import numpy as np

from . import config
from . import model as ml

DEFAULT_DEMO = "WL-DEMO-01"

# Feature order: config.FEATURE_NAMES
DEMO_CANDIDATES = {
    "WL-DEMO-01": {
        "title": "Moderate stress, mild anxiety, strong coping traits",
        "expected_risk": "MEDIUM",
        "features": [24, 9, 10, 14, 10, 26, 26, 7, 35, 3.8, 3.9, 3.2, 4.0, 3.2],
    },
    "WL-DEMO-02": {
        "title": "Balanced, resilient profile",
        "expected_risk": "LOW",
        "features": [9, 3, 3, 4, 3, 8, 12, 2, 42, 3.9, 4.2, 3.5, 4.1, 2.2],
    },
    "WL-DEMO-03": {
        "title": "High stress, burnout and low accomplishment",
        "expected_risk": "HIGH",
        "features": [33, 16, 19, 26, 22, 32, 40, 15, 24, 3.2, 2.6, 2.5, 3.2, 4.5],
    },
}


def demo_options():
    """[(candidate_id, label)] for the sidebar selector."""
    return [(cid, f"{cid} · {config.risk_label(c['expected_risk'])} · {c['title']}")
            for cid, c in DEMO_CANDIDATES.items()]


def get_demo_features(candidate_id):
    return [float(x) for x in DEMO_CANDIDATES[candidate_id]["features"]]


def demo_progress_series(candidate_id, n=6):
    """Six monthly synthetic records ending at the candidate's current profile."""
    target = np.array(get_demo_features(candidate_id))
    rng = np.random.RandomState(7)
    rows = []
    today = date.today()
    for k in range(n):
        weeks_ago = (n - 1 - k) * 4
        # earlier records drift away from the current profile (worse earlier, improving)
        drift = (n - 1 - k) / (n - 1)
        vec = []
        for j, name in enumerate(config.FEATURE_NAMES):
            lo, hi = config.FEATURE_RANGES[name]
            sign = -1 if name == "mbi_personal_accomplishment" else 1
            if name in ("openness", "extraversion", "agreeableness", "conscientiousness"):
                sign = 0
            span = (hi - lo) * 0.12
            val = target[j] + sign * drift * span + rng.normal(0, span * 0.1)
            val = min(max(val, lo), hi)
            vec.append(round(val, 2) if isinstance(hi, float) else int(round(val)))
        row = {"date": str(today - timedelta(weeks=weeks_ago)), "risk": "demo"}
        row.update(dict(zip(config.FEATURE_NAMES, vec)))
        rows.append(row)
    return rows


def demo_journal_entries():
    notes = ["Busy day but manageable.", "Slept badly, felt tense.", "Good walk, felt calmer.",
             "Deadlines piling up.", "Relaxed weekend.", "Mixed day, a little tired."]
    moods = [6, 4, 7, 4, 8, 6]
    stress = [5, 7, 4, 8, 3, 5]
    sleep = [7.0, 5.5, 7.5, 6.0, 8.5, 7.0]
    today = date.today()
    return [{"entry_date": str(today - timedelta(days=len(notes) - i)), "mood": moods[i],
             "stress": stress[i], "sleep_hours": sleep[i], "note": notes[i], "is_demo": True}
            for i in range(len(notes))]


def hr_cohort(bundle, n=18):
    """Anonymised cohort: synthetic profiles scored by the real model."""
    df = bundle["dataset"].sample(n=n, random_state=11).reset_index(drop=True)
    today = date.today()
    cohort = []
    for i, row in df.iterrows():
        feats = [float(row[f]) for f in config.FEATURE_NAMES]
        pred = ml.predict_risk(bundle, feats)
        risk = pred["risk"]
        if risk == "HIGH":
            status = "Pending Review" if i % 3 else "In Review"
        elif risk == "MEDIUM":
            status = "Optional Review" if i % 2 else "Not Required"
        else:
            status = "Not Required"
        cohort.append({
            "candidate_id": f"WL-{i + 1:03d}",
            "date": str(today - timedelta(days=int(i * 2 % 28))),
            "risk": risk, "confidence": pred["confidence"] * 100,
            "pss": int(row["pss_score"]), "gad7": int(row["gad7_score"]),
            "phq9": int(row["phq9_score"]), "burnout_ee": int(row["mbi_emotional_exhaustion"]),
            "review_status": status,
        })
    return cohort
