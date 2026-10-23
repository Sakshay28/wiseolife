# 🧠 WiseOLife – AI-Based Mental Wellness Assessment System

*Understand. Assess. Support.*

WiseOLife is an academic **screening and decision-support prototype**. A user answers an 89-item
questionnaire drawn from six psychological instruments; a scoring engine converts the answers into a
**14-feature vector**; a **Random Forest** produces a LOW / MEDIUM / HIGH risk *indication*; and the app
explains it, builds a wellness plan, produces a PDF report and routes HIGH-risk cases to a (simulated) human reviewer.

> ⚖️ WiseOLife is an academic demonstration and decision-support prototype. It is not a medical diagnostic
> tool and should not replace assessment by a qualified mental health professional. Psychological or wellness
> screening should not be used as the sole basis for employment decisions.

## Features
Landing page · 89-question assessment with progress bar · six-instrument scoring (PSS reverse scoring, DASS ×2,
MBI dimensions, Big Five reverse items) · **🧠 14-Feature AI Input Vector** dashboard · Random Forest risk prediction with
confidence · feature-importance explainability · personalised wellness plan · WiseBot (offline rule-based chatbot) ·
wellness journal (SQLite) · progress tracking · HR dashboard (anonymised, simulated) · professional-review workflow
(simulated) · PDF + CSV reports · one-click **🎬 Load Demo Candidate** · built-in self-tests (40).

## Tech stack
Python · Streamlit · scikit-learn · pandas · numpy · Plotly · matplotlib · ReportLab · SQLite (optional, local).

## Run locally
```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
Open **http://localhost:8501**. Run the validation tests with `python -m wiseolife.selftest`.

## Deploy (Streamlit Community Cloud) – public link for your teacher
1. Create a GitHub repository and upload every file in this folder (keep the `wiseolife/` folder and `.streamlit/`).
2. Go to <https://share.streamlit.io> and sign in with GitHub.
3. Click **Create app → Deploy a public app from GitHub**.
4. Select your repository and branch `main`.
5. Set **Main file path** to `app.py`.
6. Click **Deploy** (first build takes a few minutes).
7. Copy the URL `https://your-app-name.streamlit.app` and send it over WhatsApp or email.

## Project structure
```
app.py                 Streamlit pages (presentation layer)
requirements.txt
wiseolife/
  config.py            branding, TEAM_MEMBERS (edit me), thresholds, 14 feature names
  questions.py         89 items; PSS_REVERSE_ITEMS switch; replaceable wording
  scoring.py           score_pss / gad / phq / dass / mbi / big5, build_feature_vector
  model.py             synthetic dataset, labelling rule, Random Forest, explainability
  recommendations.py   wellness plan          chatbot.py   WiseBot
  report.py            PDF + CSV             storage.py   local SQLite
  demo.py              demo candidates       ui.py        theme, components, charts
  selftest.py          40 validation tests
.streamlit/config.toml theme
```

## ML methodology
* **Features (14, in order):** pss_score, gad7_score, phq9_score, dass_depression, dass_anxiety, dass_stress,
  mbi_emotional_exhaustion, mbi_depersonalization, mbi_personal_accomplishment, openness, conscientiousness,
  extraversion, agreeableness, neuroticism. No composite features.
* **Data:** 3000 synthetic profiles (seed 42) generated from a latent-distress model, labelled by a transparent
  points rule (shown on the *AI Insights* page).
* **Model:** `RandomForestClassifier(n_estimators=200, max_depth=8, random_state=42)`, stratified 80/20 split.
* **Metrics** (accuracy ≈ 91%, macro precision/recall/F1 ≈ 0.90–0.91) are measured on the **synthetic** test set and
  show how well the model recovers the labelling rule – **not clinical accuracy**.

## Psychological instruments
PSS-10 (10) · GAD-7 (7) · PHQ-9 (9) · DASS-21 (21) · MBI structure (22: EE 9, DP 5, PA 8) · Big Five (20) = **89**.
PSS reverse-scored items follow the project specification (4, 5, 6, 7, 8) and are configurable in one constant.
Item wording is paraphrased and replaceable without touching the scoring engine.

## Screenshots
Add your own: `assets/home.png`, `assets/results.png`, `assets/insights.png`, `assets/report.png`.

## Team contributions (edit names in `wiseolife/config.py`)
| Member | Role |
|---|---|
| Member 1 | Frontend / UI-UX / Streamlit |
| Member 2 | Machine learning / scoring engine |
| Member 3 | Backend / reports / testing / documentation |

## Limitations
Synthetic training data; labels come from a rule, not clinicians; paraphrased items are not clinically validated;
local SQLite is not encrypted; the review workflow is a simulation.

## Privacy
Demo assessments are processed locally and are not automatically sent to an external server by the application.
Only a Candidate ID is requested. Delete stored data from the *About* page.
