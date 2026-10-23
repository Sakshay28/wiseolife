"""WiseOLife - assessment-progress bookkeeping (pure functions, no Streamlit).

There is ONE source of truth for answers: the `responses` dict (None = unanswered).
Everything else here is DERIVED from it, so counts can never drift or double-count.

Definitions
-----------
answered    the item has a stored answer
skipped     the item is blank AND the user has moved past its section (Next / Review)
unanswered  the item is blank and the user has not moved past its section yet
"""
from . import config
from . import questions as qs


def responses_valid(responses):
    """True when `responses` matches the question bank exactly (right keys and lengths)."""
    try:
        return all(len(responses[k]) == qs.item_count(k) for k in qs.INSTRUMENT_ORDER) \
            and set(responses) == set(qs.INSTRUMENT_ORDER)
    except (KeyError, TypeError):
        return False


def build_status(responses, passed_sections):
    """Per-question status rows (global question numbers 1..89) and summary counts."""
    passed = set(passed_sections)
    rows, n = [], 0
    for key in qs.INSTRUMENT_ORDER:
        inst = qs.get_instrument(key)
        for i, value in enumerate(responses[key]):
            n += 1
            answered = value is not None
            skipped = (not answered) and key in passed
            rows.append({
                "number": n, "key": key, "index": i, "instrument": inst["name"],
                "text": inst["items"][i]["text"], "answered": answered, "skipped": skipped,
                "unanswered": (not answered) and not skipped,
                "section": qs.INSTRUMENT_ORDER.index(key),
            })
    summary = {
        "total": len(rows),
        "answered": sum(r["answered"] for r in rows),
        "skipped": sum(r["skipped"] for r in rows),
        "unanswered": sum(r["unanswered"] for r in rows),
    }
    summary["blank"] = summary["skipped"] + summary["unanswered"]
    summary["percent"] = summary["answered"] / summary["total"] * 100 if summary["total"] else 0.0
    return rows, summary


def section_range(section_idx):
    """(first, last) global question numbers shown on a section page."""
    key = qs.INSTRUMENT_ORDER[section_idx]
    first = qs.question_offset(key) + 1
    return first, first + qs.item_count(key) - 1


def current_question(responses, section_idx):
    """The question the user should answer next on this section page.

    First blank question of the section, else the section's last question.
    On a brand-new test this is always Question 1."""
    key = qs.INSTRUMENT_ORDER[section_idx]
    first, last = section_range(section_idx)
    for i, v in enumerate(responses[key]):
        if v is None:
            return first + i
    return last


def locate(question_number):
    """(instrument_key, item_index, section_idx) for a global question number."""
    n = 0
    for s, key in enumerate(qs.INSTRUMENT_ORDER):
        count = qs.item_count(key)
        if question_number <= n + count:
            return key, question_number - n - 1, s
        n += count
    raise ValueError(f"question number out of range: {question_number}")


def has_progress(stage, responses):
    """True when an unfinished test exists (so 'start new' must not silently erase it)."""
    return stage in ("active", "review") and any(
        v is not None for k in qs.INSTRUMENT_ORDER for v in responses[k])
