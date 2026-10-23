"""WiseOLife - personalised wellness plan. General wellness suggestions, not treatment."""
from . import config

_LEVEL_RANK = {"Low": 0, "Minimal": 0, "Normal": 0, "Mild": 1, "Moderate": 1,
               "Moderately Severe": 2, "Severe": 2, "High": 2, "Extremely Severe": 2}

DISCLAIMER = ("These are general wellness suggestions, not medical advice or treatment. "
              "If symptoms persist or worsen, please speak with a qualified professional.")


def _sev(level):
    return _LEVEL_RANK.get(level, 0)


def generate_recommendations(scores, prediction):
    d, m, b = scores["dass"], scores["mbi"], scores["big5"]
    blocks, strengths = [], []

    stress_sev = max(_sev(scores["pss"]["level"]), _sev(d["stress_level"]))
    anx_sev = max(_sev(scores["gad7"]["level"]), _sev(d["anxiety_level"]))
    dep_sev = max(_sev(scores["phq9"]["level"]), _sev(d["depression_level"]))
    ee_sev = _sev(m["ee_level"])
    dp_sev = _sev(m["dp_level"])

    if stress_sev >= 1:
        blocks.append({
            "icon": "😰", "title": "Stress management", "severity": stress_sev,
            "why": f"PSS is {scores['pss']['level']} and DASS stress is {d['stress_level']}.",
            "actions": [
                "Practise 4-7-8 or box breathing for 5 minutes, twice a day.",
                "Schedule short structured breaks (e.g. 5 minutes every 50 minutes of work).",
                "Keep a consistent sleep routine - same bedtime and wake time, screens off 30 minutes before.",
                "List your tasks, pick the top three, and defer or delegate the rest (workload management).",
            ]})
    if anx_sev >= 1:
        blocks.append({
            "icon": "😟", "title": "Anxiety support", "severity": anx_sev,
            "why": f"GAD-7 is {scores['gad7']['level']} and DASS anxiety is {d['anxiety_level']}.",
            "actions": [
                "Try the 5-4-3-2-1 grounding exercise when worry spikes.",
                "Use progressive muscle relaxation before sleep.",
                "Limit caffeine in the afternoon and add a daily 20-minute walk.",
                "If worry is persistent or interferes with daily life, consider talking to a professional.",
            ]})
    if dep_sev >= 1:
        blocks.append({
            "icon": "😔", "title": "Mood and energy", "severity": dep_sev,
            "why": f"PHQ-9 is {scores['phq9']['level']} and DASS depression is {d['depression_level']}.",
            "actions": [
                "Plan one small enjoyable or meaningful activity each day, even if motivation is low.",
                "Keep regular meals, daylight exposure and light physical activity.",
                "Talk to someone you trust about how you have been feeling.",
                "Persistent low mood deserves a conversation with a counsellor or doctor.",
            ]})
    if ee_sev >= 1 or dp_sev >= 1:
        blocks.append({
            "icon": "🔥", "title": "Burnout prevention", "severity": max(ee_sev, dp_sev),
            "why": f"Emotional exhaustion is {m['ee_level']} and depersonalization is {m['dp_level']}.",
            "actions": [
                "Protect recovery time: one fully work-free evening and one weekend block each week.",
                "Set boundaries on after-hours messages and review your workload with a mentor or manager.",
                "Reconnect with the purpose of your work through short reflection notes.",
                "Take real breaks - lunch away from the screen, short outdoor walks.",
            ]})
    if _sev(m["pa_level"]) == 0:  # Low personal accomplishment is the concern
        blocks.append({
            "icon": "🌱", "title": "Rebuilding a sense of accomplishment", "severity": 2,
            "why": f"Personal accomplishment is {m['pa_level']} (a low score is the concern here).",
            "actions": [
                "Set realistic short-term goals and tick them off visibly.",
                "Keep a progress journal: write three small wins every evening.",
                "Ask for specific feedback and celebrate completed milestones.",
            ]})
    elif m["pa_level"] == "High":
        strengths.append("High personal accomplishment - a positive sense of achievement at work or study.")
    if b["levels"]["N"] == "High":
        blocks.append({
            "icon": "🌊", "title": "Emotional regulation", "severity": 1,
            "why": f"Neuroticism is {b['neuroticism']}/5 (tendency to experience strong negative emotion).",
            "actions": [
                "Practise a 10-minute daily mindfulness or body-scan exercise.",
                "Name the emotion you feel (\"I notice I feel anxious\") before reacting.",
                "Build a coping routine: music, walk, journaling or talking to a friend.",
            ]})
    if b["levels"]["C"] == "High":
        strengths.append("High conscientiousness - good at planning, follow-through and routines.")
    if b["levels"]["A"] == "High":
        strengths.append("High agreeableness - supportive relationships are a strong resource.")
    if b["levels"]["O"] == "High":
        strengths.append("High openness - curiosity and flexibility help with new coping strategies.")
    if b["levels"]["N"] == "Low":
        strengths.append("Low neuroticism - generally emotionally steady under pressure.")
    if scores["pss"]["level"] == "Low":
        strengths.append("Low perceived stress over the last month.")
    if scores["gad7"]["level"] == "Minimal" and scores["phq9"]["level"] == "Minimal":
        strengths.append("Minimal anxiety and depression screening scores.")

    if not blocks:
        blocks.append({
            "icon": "✨", "title": "Maintain your wellbeing", "severity": 0,
            "why": "No scale crossed an elevated threshold.",
            "actions": ["Keep regular sleep, movement and social contact.",
                        "Use the Wellness Journal for a weekly check-in.",
                        "Re-take the assessment in a few weeks to track changes."]})
    blocks.sort(key=lambda x: -x["severity"])

    safety = bool(scores["phq9"].get("safety_flag"))
    review = prediction["risk"] == "HIGH" or safety
    risk = prediction["risk"]
    summary = (f"{config.RISK_EMOJI[risk]} Your screening indication is {risk} "
               f"({prediction['confidence'] * 100:.0f}% model confidence). "
               "The plan below focuses on the areas that scored highest.")
    return {
        "summary": summary, "strengths": strengths, "blocks": blocks,
        "safety": safety, "safety_message": config.SAFETY_MESSAGE,
        "review_recommended": review, "disclaimer": DISCLAIMER,
    }
