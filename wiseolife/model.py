"""WiseOLife - synthetic dataset, transparent labelling rule, Random Forest, explainability.

IMPORTANT: the dataset is synthetic and the labels come from an explicit points rule,
so the evaluation metrics measure how well the forest recovers THAT rule. They are not
clinical accuracy.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                             f1_score, precision_score, recall_score)
from sklearn.model_selection import train_test_split

from . import config

# ---------------------------------------------------------------------------
# TRANSPARENT LABELLING RULE
# (feature, reason, threshold, risk points). "Elevated" = value >= threshold.
# ---------------------------------------------------------------------------
RISK_RULE_TABLE = [
    ("pss_score", "High perceived stress (PSS)", 27, 2),
    ("gad7_score", "Moderate-to-severe anxiety (GAD-7)", 10, 2),
    ("phq9_score", "Moderate-to-severe depressive symptoms (PHQ-9)", 10, 2),
    ("dass_depression", "DASS depression in the severe range", 21, 1),
    ("dass_anxiety", "DASS anxiety in the severe range", 15, 1),
    ("dass_stress", "DASS stress in the severe range", 26, 1),
    ("mbi_emotional_exhaustion", "High emotional exhaustion (MBI)", 27, 2),
    ("mbi_depersonalization", "High depersonalization (MBI)", 10, 1),
    ("neuroticism", "High neuroticism (Big Five)", 4.0, 1),
]
# Protective features: risk when value is LOW (value <= threshold).
RISK_RULE_TABLE_INVERTED = [
    ("mbi_personal_accomplishment", "Low personal accomplishment (MBI)", 31, 1),
    ("conscientiousness", "Low conscientiousness (Big Five)", 2.5, 1),
]
HIGH_THRESHOLD = 7
MEDIUM_THRESHOLD = 3

# Features where a HIGHER value is protective (used to set the sign in explanations).
PROTECTIVE_FEATURES = {"mbi_personal_accomplishment", "conscientiousness"}
NEUTRAL_FEATURES = {"openness", "extraversion", "agreeableness"}


def risk_points_breakdown(f):
    """f: dict feature->value. Returns (total_points, [(reason, points), ...])."""
    total, reasons = 0, []
    for name, reason, thr, pts in RISK_RULE_TABLE:
        if f[name] >= thr:
            total += pts
            reasons.append((reason, pts))
    for name, reason, thr, pts in RISK_RULE_TABLE_INVERTED:
        if f[name] <= thr:
            total += pts
            reasons.append((reason, pts))
    return total, reasons


def label_risk(f):
    """The rule that creates the training labels."""
    pts, _ = risk_points_breakdown(f)
    if pts >= HIGH_THRESHOLD:
        return "HIGH"
    if pts >= MEDIUM_THRESHOLD:
        return "MEDIUM"
    return "LOW"


# ---------------------------------------------------------------------------
# SYNTHETIC DATASET
# (mean, std, loading on the latent "distress" factor)
# ---------------------------------------------------------------------------
_DISTRIBUTION = {
    "pss_score": (18.0, 8.0, 0.80),
    "gad7_score": (6.0, 5.0, 0.80),
    "phq9_score": (7.0, 5.5, 0.80),
    "dass_depression": (12.0, 9.0, 0.78),
    "dass_anxiety": (10.0, 8.0, 0.78),
    "dass_stress": (17.0, 10.0, 0.80),
    "mbi_emotional_exhaustion": (22.0, 11.0, 0.75),
    "mbi_depersonalization": (8.0, 6.0, 0.60),
    "mbi_personal_accomplishment": (36.0, 8.0, -0.50),
    "openness": (3.5, 0.6, 0.0),
    "conscientiousness": (3.5, 0.6, -0.30),
    "extraversion": (3.2, 0.7, -0.20),
    "agreeableness": (3.6, 0.6, -0.10),
    "neuroticism": (2.9, 0.7, 0.65),
}


def generate_synthetic_dataset(n=config.N_SYNTHETIC_RECORDS, seed=config.RANDOM_STATE):
    """Reproducible synthetic profiles: a latent distress factor drives all scales."""
    rng = np.random.RandomState(seed)
    z = rng.normal(0.0, 1.0, n)
    cols = {}
    for name in config.FEATURE_NAMES:
        mean, std, loading = _DISTRIBUTION[name]
        noise = rng.normal(0.0, 1.0, n)
        value = mean + std * (loading * z + np.sqrt(1 - loading ** 2) * noise)
        lo, hi = config.FEATURE_RANGES[name]
        value = np.clip(value, lo, hi)
        cols[name] = np.round(value, 2) if isinstance(hi, float) else np.round(value)
    df = pd.DataFrame(cols)
    df["risk"] = [label_risk(row) for row in df[config.FEATURE_NAMES].to_dict("records")]
    return df


# ---------------------------------------------------------------------------
# TRAINING
# ---------------------------------------------------------------------------
def train_model():
    """Train the Random Forest on all 14 features. Deterministic (random_state=42)."""
    df = generate_synthetic_dataset()
    X = df[config.FEATURE_NAMES].values
    y = df["risk"].values
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=config.RANDOM_STATE, stratify=y)
    clf = RandomForestClassifier(
        n_estimators=config.RF_N_ESTIMATORS, random_state=config.RANDOM_STATE,
        max_depth=config.RF_MAX_DEPTH)
    clf.fit(X_tr, y_tr)
    y_pred = clf.predict(X_te)

    metrics = {
        "accuracy": accuracy_score(y_te, y_pred),
        "precision": precision_score(y_te, y_pred, average="macro", zero_division=0),
        "recall": recall_score(y_te, y_pred, average="macro", zero_division=0),
        "f1": f1_score(y_te, y_pred, average="macro", zero_division=0),
        "n_features": X.shape[1],
        "train_size": len(y_tr), "test_size": len(y_te),
    }
    labels = [c for c in config.RISK_CLASSES if c in set(y)]
    importance = sorted(
        ({"name": n, "label": config.FEATURE_LABELS[n], "percent": float(imp) * 100}
         for n, imp in zip(config.FEATURE_NAMES, clf.feature_importances_)),
        key=lambda r: r["percent"], reverse=True)

    return {
        "model": clf,
        "metrics": metrics,
        "importance": importance,
        "confusion_matrix": confusion_matrix(y_te, y_pred, labels=labels),
        "confusion_labels": labels,
        "report_text": classification_report(y_te, y_pred, labels=labels, zero_division=0),
        "dataset": df,
        "means": df[config.FEATURE_NAMES].mean().to_dict(),
        "stds": df[config.FEATURE_NAMES].std().to_dict(),
    }


# ---------------------------------------------------------------------------
# PREDICTION + EXPLANATION
# ---------------------------------------------------------------------------
def predict_risk(bundle, features):
    """features: list of 14 numbers. Returns risk, confidence (0-1) and probabilities."""
    clf = bundle["model"]
    x = np.array(features, dtype=float).reshape(1, -1)
    proba = clf.predict_proba(x)[0]
    probs = {c: float(p) for c, p in zip(clf.classes_, proba)}
    for c in config.RISK_CLASSES:
        probs.setdefault(c, 0.0)
    risk = max(probs, key=probs.get)
    return {"risk": risk, "confidence": probs[risk], "probabilities": probs}


def local_contribution(bundle, features, top_n=8):
    """Lightweight per-profile view: global importance x standardised deviation.

    Positive = pushes towards higher risk, negative = protective. Association only.
    """
    rows = []
    imp = {r["name"]: r["percent"] / 100 for r in bundle["importance"]}
    for name, value in zip(config.FEATURE_NAMES, features):
        std = bundle["stds"][name] or 1.0
        z = (value - bundle["means"][name]) / std
        if name in PROTECTIVE_FEATURES:
            z = -z
        elif name in NEUTRAL_FEATURES:
            z = 0.0
        rows.append({"name": name, "label": config.FEATURE_LABELS[name],
                     "contribution": float(imp[name] * z)})
    rows.sort(key=lambda r: abs(r["contribution"]), reverse=True)
    return rows[:top_n]


def explanation_sentence(bundle, features, risk):
    """Plain-language sentence naming the top influences. No causal claims."""
    local = local_contribution(bundle, features, top_n=14)
    up = [r["label"] for r in local if r["contribution"] > 0.01][:2]
    down = [r["label"] for r in local if r["contribution"] < -0.01][:1]
    if risk == "LOW" or not up:
        text = "No indicator stood out as strongly elevated, so the model returned a lower-risk indication."
        if down:
            text += f" {down[0]} was one of the more favourable signals."
        return text
    text = (f"The {risk} indication was influenced most by elevated "
            f"{' and '.join(up)} (association, not causation).")
    if down:
        text += f" {down[0]} was a relatively protective signal."
    return text
