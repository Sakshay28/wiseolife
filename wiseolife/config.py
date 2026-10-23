"""WiseOLife - central configuration: branding, team, thresholds, the 14 feature names.

Everything a student might want to edit (names, roll numbers, institution) lives here.
"""

# ---------------------------------------------------------------------------
# BRANDING
# ---------------------------------------------------------------------------
APP_NAME = "WiseOLife"
APP_ICON = "🧠"
APP_SUBTITLE = "AI-Based Mental Wellness Assessment System"
TAGLINE = "Understand. Assess. Support."
SUBTAGLINE = "AI-powered wellness insights for better decisions."
VERSION = "1.0"

# ---------------------------------------------------------------------------
# EDIT ME: team + institution (placeholders - replace with real names)
# ---------------------------------------------------------------------------
INSTITUTION = "Your University / College Name"
DEPARTMENT = "Department of Computer and Communication Engineering"
DEGREE = "B.Tech (Computer and Communication Engineering)"
GUIDE_NAME = "Project Guide Name"
ACADEMIC_YEAR = "2025-26"

TEAM_MEMBERS = [
    {
        "role": "Member 1 · Frontend / UI-UX / Streamlit",
        "placeholder_name": "Member 1 Name",
        "roll_no": "Roll No. ________",
        "responsibilities": [
            "Landing page, navigation and dark-navy / purple theme",
            "Assessment flow, progress indicator and results dashboard",
            "Plotly charts, score cards and feature-vector grid",
        ],
    },
    {
        "role": "Member 2 · Machine Learning / Scoring Engine",
        "placeholder_name": "Member 2 Name",
        "roll_no": "Roll No. ________",
        "responsibilities": [
            "Scoring engine for six instruments and reverse scoring",
            "14-feature vector, synthetic dataset and labelling rule",
            "Random Forest training, metrics and explainability",
        ],
    },
    {
        "role": "Member 3 · Backend / Reports / Testing / Docs",
        "placeholder_name": "Member 3 Name",
        "roll_no": "Roll No. ________",
        "responsibilities": [
            "SQLite storage, PDF/CSV report generation",
            "Self-tests, deployment and README",
            "Project report, PPT and viva preparation",
        ],
    },
]

# ---------------------------------------------------------------------------
# ASSESSMENT SIZE
# ---------------------------------------------------------------------------
TOTAL_QUESTIONS = 89
N_INSTRUMENTS = 6
ESTIMATED_MINUTES = "15-20"

INSTRUMENTS = [
    {"icon": "😰", "name": "PSS-10", "n": 10, "full": "Perceived Stress Scale - stress over the last month"},
    {"icon": "😟", "name": "GAD-7", "n": 7, "full": "Generalized Anxiety Disorder scale - anxiety symptoms"},
    {"icon": "😔", "name": "PHQ-9", "n": 9, "full": "Patient Health Questionnaire - depression symptoms"},
    {"icon": "📉", "name": "DASS-21", "n": 21, "full": "Depression, Anxiety and Stress Scale - three subscales"},
    {"icon": "🔥", "name": "MBI", "n": 22, "full": "Maslach Burnout Inventory structure - exhaustion, depersonalization, accomplishment"},
    {"icon": "🌈", "name": "Big Five", "n": 20, "full": "OCEAN personality traits - Openness to Neuroticism"},
]

# ---------------------------------------------------------------------------
# THE 14 ML FEATURES (order matters - this is the model input order)
# ---------------------------------------------------------------------------
FEATURE_NAMES = [
    "pss_score", "gad7_score", "phq9_score",
    "dass_depression", "dass_anxiety", "dass_stress",
    "mbi_emotional_exhaustion", "mbi_depersonalization", "mbi_personal_accomplishment",
    "openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism",
]

FEATURE_SHORT = {
    "pss_score": "PSS", "gad7_score": "GAD-7", "phq9_score": "PHQ-9",
    "dass_depression": "DASS Depression", "dass_anxiety": "DASS Anxiety",
    "dass_stress": "DASS Stress",
    "mbi_emotional_exhaustion": "MBI EE", "mbi_depersonalization": "MBI DP",
    "mbi_personal_accomplishment": "MBI PA",
    "openness": "O", "conscientiousness": "C", "extraversion": "E",
    "agreeableness": "A", "neuroticism": "N",
}

FEATURE_LABELS = {
    "pss_score": "PSS Perceived Stress",
    "gad7_score": "GAD-7 Anxiety",
    "phq9_score": "PHQ-9 Depression",
    "dass_depression": "DASS Depression",
    "dass_anxiety": "DASS Anxiety",
    "dass_stress": "DASS Stress",
    "mbi_emotional_exhaustion": "MBI Emotional Exhaustion",
    "mbi_depersonalization": "MBI Depersonalization",
    "mbi_personal_accomplishment": "MBI Personal Accomplishment",
    "openness": "Big Five Openness",
    "conscientiousness": "Big Five Conscientiousness",
    "extraversion": "Big Five Extraversion",
    "agreeableness": "Big Five Agreeableness",
    "neuroticism": "Big Five Neuroticism",
}

FEATURE_RANGES = {
    "pss_score": (0, 40), "gad7_score": (0, 21), "phq9_score": (0, 27),
    "dass_depression": (0, 42), "dass_anxiety": (0, 42), "dass_stress": (0, 42),
    "mbi_emotional_exhaustion": (0, 54), "mbi_depersonalization": (0, 30),
    "mbi_personal_accomplishment": (0, 48),
    "openness": (1.0, 5.0), "conscientiousness": (1.0, 5.0), "extraversion": (1.0, 5.0),
    "agreeableness": (1.0, 5.0), "neuroticism": (1.0, 5.0),
}

# Grouping used by the "14-Feature AI Input Vector" dashboard (each feature once).
FEATURE_GROUPS = [
    ("Stress & Anxiety", "😰", ["pss_score", "gad7_score"]),
    ("Depression", "😔", ["phq9_score"]),
    ("DASS-21 subscales", "📉", ["dass_depression", "dass_anxiety", "dass_stress"]),
    ("Burnout (MBI)", "🔥", ["mbi_emotional_exhaustion", "mbi_depersonalization",
                            "mbi_personal_accomplishment"]),
    ("Personality (Big Five)", "🌈", ["openness", "conscientiousness", "extraversion",
                                     "agreeableness", "neuroticism"]),
]

# ---------------------------------------------------------------------------
# MODEL SETTINGS
# ---------------------------------------------------------------------------
RANDOM_STATE = 42
N_SYNTHETIC_RECORDS = 3000
RF_N_ESTIMATORS = 200
RF_MAX_DEPTH = 8
RISK_CLASSES = ["LOW", "MEDIUM", "HIGH"]
RISK_EMOJI = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}
RISK_COLOR = {"LOW": "#10b981", "MEDIUM": "#f59e0b", "HIGH": "#ef4444"}

# ---------------------------------------------------------------------------
# TEXT BLOCKS
# ---------------------------------------------------------------------------
MAIN_DISCLAIMER = (
    "WiseOLife is an academic demonstration and decision-support prototype. It is not a "
    "medical diagnostic tool and should not replace assessment by a qualified mental "
    "health professional."
)
EMPLOYMENT_DISCLAIMER = (
    "Psychological or wellness screening should not be used as the sole basis for "
    "employment decisions."
)
AI_DISCLAIMER = (
    "This is an AI-generated screening indication and not a medical diagnosis."
)
PRIVACY_NOTICE = (
    "Demo assessments are processed locally and are not automatically sent to an external "
    "server by the application. If local storage is available, history and journal "
    "entries are kept in a small SQLite file (wiseolife_data.db) on the machine running "
    "the app. WiseOLife only asks for a Candidate ID - never a real name, email or phone "
    "number - and you can delete all stored data from the About page."
)
SAFETY_MESSAGE = (
    "One response relating to thoughts of self-harm was elevated. This is a screening "
    "signal, not a diagnosis. If you or someone you know may be in danger, please contact "
    "local emergency services or a trusted person right away, and consider speaking with "
    "a qualified mental health professional or a helpline in your region."
)
WORDING_NOTICE = (
    "Item wording in this prototype is paraphrased for academic use. The question bank "
    "lives in wiseolife/questions.py and can be replaced with institution-approved or "
    "licensed wording without changing the scoring engine."
)
