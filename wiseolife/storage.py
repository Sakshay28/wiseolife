"""WiseOLife - optional local SQLite storage. Every function degrades gracefully
(returns empty / False) if the filesystem is not writable, e.g. on some cloud hosts."""
import os
import sqlite3

from . import config

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "wiseolife_data.db")
_available = None


def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables. Returns True when persistence works."""
    global _available
    try:
        feature_cols = ", ".join(f"{n} REAL" for n in config.FEATURE_NAMES)
        with _connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS assessments ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, candidate_id TEXT, created_at TEXT, "
                f"source TEXT, risk TEXT, confidence REAL, {feature_cols}, "
                "reviewer TEXT, review_status TEXT, review_notes TEXT, review_decision TEXT)")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS journal ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, entry_date TEXT, mood INTEGER, "
                "stress INTEGER, sleep_hours REAL, note TEXT)")
        _available = True
    except Exception:
        _available = False
    return _available


def db_available():
    if _available is None:
        init_db()
    return bool(_available)


def save_assessment(result):
    if not db_available():
        return None
    try:
        cols = ["candidate_id", "created_at", "source", "risk", "confidence"] + config.FEATURE_NAMES
        vals = [result["candidate_id"], result["timestamp"], result["source"],
                result["prediction"]["risk"], result["prediction"]["confidence"]] + list(result["features"])
        with _connect() as conn:
            cur = conn.execute(
                f"INSERT INTO assessments ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", vals)
            return cur.lastrowid
    except Exception:
        return None


def load_assessments(limit=50):
    """Most recent first; rows are dicts with created_at, risk and the 14 features."""
    if not db_available():
        return []
    try:
        with _connect() as conn:
            rows = conn.execute("SELECT * FROM assessments ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def update_review(row_id, reviewer, status, notes, decision):
    if not db_available() or not row_id:
        return False
    try:
        with _connect() as conn:
            conn.execute("UPDATE assessments SET reviewer=?, review_status=?, review_notes=?, "
                         "review_decision=? WHERE id=?", (reviewer, status, notes, decision, row_id))
        return True
    except Exception:
        return False


def save_journal_entry(entry_date, mood, stress, sleep_hours, note):
    if not db_available():
        return None
    try:
        with _connect() as conn:
            cur = conn.execute(
                "INSERT INTO journal (entry_date, mood, stress, sleep_hours, note) VALUES (?,?,?,?,?)",
                (str(entry_date), mood, stress, sleep_hours, note))
            return cur.lastrowid
    except Exception:
        return None


def load_journal():
    if not db_available():
        return []
    try:
        with _connect() as conn:
            rows = conn.execute("SELECT * FROM journal ORDER BY entry_date ASC, id ASC").fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def stats():
    out = {"available": db_available(), "assessments": 0, "journal": 0}
    if out["available"]:
        try:
            with _connect() as conn:
                out["assessments"] = conn.execute("SELECT COUNT(*) FROM assessments").fetchone()[0]
                out["journal"] = conn.execute("SELECT COUNT(*) FROM journal").fetchone()[0]
        except Exception:
            pass
    return out


def clear_all():
    if not db_available():
        return False
    try:
        with _connect() as conn:
            conn.execute("DELETE FROM assessments")
            conn.execute("DELETE FROM journal")
        return True
    except Exception:
        return False
