"""WiseOLife - developer self-tests for the scoring engine and ML pipeline.

Run:  python -m wiseolife.selftest      (or the Developer/Validation panel on the About page)
Each test returns (name, passed, expected, actual).
"""
from . import config, demo
from . import model as ml
from . import questions as qs
from . import scoring as sc
from . import teststate as ts
from . import chatbot
import copy


def _responses(**kw):
    """Full response dict; an int fills that whole instrument, a list is used as is."""
    r = qs.empty_responses()
    for key, val in kw.items():
        if val is None:
            continue
        r[key] = [val] * qs.item_count(key) if isinstance(val, int) else list(val)
    return r


def test_question_count():
    n = qs.total_question_count()
    return ("Question bank contains 89 items", n == 89, "89", str(n))


def test_instrument_counts():
    exp = {"pss": 10, "gad7": 7, "phq9": 9, "dass": 21, "mbi": 22, "big5": 20}
    act = {k: qs.item_count(k) for k in qs.INSTRUMENT_ORDER}
    return ("Per-instrument item counts (10/7/9/21/22/20)", act == exp, str(exp), str(act))


def test_pss_all_zero():
    n_rev = len(qs.PSS_REVERSE_ITEMS)
    s = sc.score_pss(_responses(pss=0))
    return (f"PSS all-zero -> raw 0, adjusted {4 * n_rev} ({n_rev} reverse items x 4)",
            s["raw"] == 0 and s["adjusted"] == 4 * n_rev,
            f"raw=0, adjusted={4 * n_rev}", f"raw={s['raw']}, adjusted={s['adjusted']}")


def test_pss_all_max():
    n_rev = len(qs.PSS_REVERSE_ITEMS)
    s = sc.score_pss(_responses(pss=4))
    exp = 4 * (10 - n_rev)
    return (f"PSS all-max -> raw 40, adjusted {exp}", s["raw"] == 40 and s["adjusted"] == exp,
            f"raw=40, adjusted={exp}", f"raw={s['raw']}, adjusted={s['adjusted']}")


def test_pss_reverse_formula():
    a = sc.reverse_value(0, 0, 4) == 4 and sc.reverse_value(3, 0, 4) == 1
    b = sc.reverse_value(1, 1, 5) == 5 and sc.reverse_value(2, 1, 5) == 4
    return ("Reverse formula (min+max)-x on 0-4 and 1-5 scales", a and b, "4,1,5,4", str(a and b))


def test_gad_zero_and_max():
    lo, hi = sc.score_gad(_responses(gad7=0))["score"], sc.score_gad(_responses(gad7=3))["score"]
    return ("GAD-7 range 0..21", (lo, hi) == (0, 21), "0 and 21", f"{lo} and {hi}")


def test_gad_bands():
    cases = [(0, "Minimal"), (4, "Minimal"), (5, "Mild"), (9, "Mild"), (10, "Moderate"),
             (14, "Moderate"), (15, "Severe"), (21, "Severe")]
    act = [sc.band(v, sc.GAD7_BANDS) for v, _ in cases]
    return ("GAD-7 interpretation bands", act == [e for _, e in cases], "see spec", str(act))


def test_phq_zero_and_max():
    lo, hi = sc.score_phq(_responses(phq9=0))["score"], sc.score_phq(_responses(phq9=3))["score"]
    return ("PHQ-9 range 0..27", (lo, hi) == (0, 27), "0 and 27", f"{lo} and {hi}")


def test_phq_bands():
    cases = [(4, "Minimal"), (9, "Mild"), (14, "Moderate"), (19, "Moderately Severe"), (27, "Severe")]
    act = [sc.band(v, sc.PHQ9_BANDS) for v, _ in cases]
    return ("PHQ-9 interpretation bands", act == [e for _, e in cases], "see spec", str(act))


def test_phq_safety_flag():
    r = _responses(phq9=0)
    off = sc.score_phq(r)["safety_flag"]
    r["phq9"][qs.PHQ9_SAFETY_ITEM_INDEX] = 2
    on = sc.score_phq(r)["safety_flag"]
    return ("PHQ-9 item 9 safety flag toggles correctly", (not off) and on, "False then True", f"{off} then {on}")


def test_dass_all_zero():
    s = sc.score_dass(_responses(dass=0))
    return ("DASS all-zero -> D0 A0 S0", (s["depression"], s["anxiety"], s["stress"]) == (0, 0, 0),
            "0/0/0", f"{s['depression']}/{s['anxiety']}/{s['stress']}")


def test_dass_multiplier():
    s = sc.score_dass(_responses(dass=3))
    return ("DASS all-max -> each subscale 7x3x2 = 42",
            (s["depression"], s["anxiety"], s["stress"]) == (42, 42, 42), "42/42/42",
            f"{s['depression']}/{s['anxiety']}/{s['stress']}")


def test_dass_subscale_separation():
    r = _responses(dass=0)
    for i, item in enumerate(qs.DASS["items"]):
        if item["dim"] == "D":
            r["dass"][i] = 3
    s = sc.score_dass(r)
    return ("DASS subscales stay independent", (s["depression"], s["anxiety"], s["stress"]) == (42, 0, 0),
            "42/0/0", f"{s['depression']}/{s['anxiety']}/{s['stress']}")


def test_dass_item_split():
    dims = [i["dim"] for i in qs.DASS["items"]]
    ok = all(dims.count(d) == 7 for d in "DAS")
    return ("DASS has 7 items per subscale", ok, "7/7/7", f"{dims.count('D')}/{dims.count('A')}/{dims.count('S')}")


def test_mbi_dimensions():
    s = sc.score_mbi(_responses(mbi=6))
    ok = (s["emotional_exhaustion"], s["depersonalization"], s["personal_accomplishment"]) == (54, 30, 48)
    return ("MBI all-max -> EE 54, DP 30, PA 48", ok, "54/30/48",
            f"{s['emotional_exhaustion']}/{s['depersonalization']}/{s['personal_accomplishment']}")


def test_mbi_pa_direction():
    hi, lo = sc.band(46, sc.MBI_PA_BANDS), sc.band(10, sc.MBI_PA_BANDS)
    return ("MBI Personal Accomplishment direction (high = High)", hi == "High" and lo == "Low",
            "High and Low", f"{hi} and {lo}")


def test_big5_neutral():
    s = sc.score_big5(_responses(big5=3))
    return ("Big Five all-neutral -> every trait 3.0", all(abs(s["traits"][t] - 3.0) < 1e-9 for t in "OCEAN"),
            "all 3.0", str(s["traits"]))


def test_big5_reverse():
    s = sc.score_big5(_responses(big5=1))
    exp = {}
    for t in "OCEAN":
        items = [i for i in qs.BIG5["items"] if i["dim"] == t]
        exp[t] = round(sum(5 if i["reverse"] else 1 for i in items) / len(items), 2)
    return ("Big Five reverse scoring on all-1 responses", s["traits"] == exp, str(exp), str(s["traits"]))


def test_big5_range():
    ok = all(1.0 <= sc.score_big5(_responses(big5=v))["traits"][t] <= 5.0 for v in (1, 3, 5) for t in "OCEAN")
    return ("Big Five traits stay within 1.0-5.0", ok, "within 1-5", "ok" if ok else "out of range")


def test_feature_vector_length():
    v = sc.build_feature_vector(sc.score_all(_responses(pss=2, gad7=1, phq9=1, dass=1, mbi=3, big5=3)))
    return ("Feature vector has exactly 14 values", len(v) == 14, "14", str(len(v)))


def test_feature_vector_order():
    s = sc.score_all(_responses(pss=0, gad7=3, phq9=0, dass=0, mbi=0, big5=3))
    d = dict(zip(config.FEATURE_NAMES, sc.build_feature_vector(s)))
    pss_exp = 4 * len(qs.PSS_REVERSE_ITEMS)
    ok = d["gad7_score"] == 21 and d["phq9_score"] == 0 and d["pss_score"] == pss_exp
    return ("Feature vector order matches FEATURE_NAMES", ok, f"gad7=21, phq9=0, pss={pss_exp}",
            f"gad7={d['gad7_score']:.0f}, phq9={d['phq9_score']:.0f}, pss={d['pss_score']:.0f}")


def test_no_composite_features():
    names = set(config.FEATURE_NAMES)
    req = {"mbi_emotional_exhaustion", "mbi_depersonalization", "mbi_personal_accomplishment",
           "dass_depression", "dass_anxiety", "dass_stress", "openness", "conscientiousness",
           "extraversion", "agreeableness", "neuroticism"}
    return ("No composite features - all dimensions separate", req <= names and len(names) == 14,
            "14 separate features", f"{len(names)} features")


def test_missing_values_handled():
    s = sc.score_all(qs.empty_responses())
    v = sc.build_feature_vector(s)
    return ("Unanswered assessment degrades safely", len(v) == 14 and s["missing_total"] == 89 and not s["complete"],
            "14 values, 89 missing, complete=False", f"{len(v)} values, {s['missing_total']} missing, complete={s['complete']}")


def test_round_trip_feature_dict():
    orig = demo.get_demo_features("WL-DEMO-01")
    rebuilt = sc.build_feature_vector(sc.scores_from_feature_dict(dict(zip(config.FEATURE_NAMES, orig))))
    return ("Feature dict -> scores -> feature vector round trip",
            all(abs(a - b) < 1e-6 for a, b in zip(orig, rebuilt)), str(orig), str(rebuilt))


def test_label_rule_monotonic():
    healthy = dict(zip(config.FEATURE_NAMES, [5, 1, 1, 2, 2, 4, 8, 2, 45, 3.5, 4.0, 3.5, 4.0, 2.0]))
    severe = dict(zip(config.FEATURE_NAMES, [35, 19, 24, 34, 30, 36, 46, 22, 14, 3.0, 2.0, 2.2, 2.8, 4.6]))
    a, b = ml.label_risk(healthy), ml.label_risk(severe)
    return ("Labelling rule: healthy -> LOW, severe -> HIGH", a == "LOW" and b == "HIGH", "LOW and HIGH", f"{a} and {b}")


def test_model_pipeline(bundle=None):
    b = bundle or ml.train_model()
    m = b["metrics"]
    ok = m["n_features"] == 14 and 0.5 <= m["accuracy"] <= 1.0 and \
        m["train_size"] + m["test_size"] == config.N_SYNTHETIC_RECORDS
    return ("Model trains on 14 features with sane metrics", ok, "14 features, 3000 records, accuracy>0.5",
            f"{m['n_features']} features, {m['train_size'] + m['test_size']} records, accuracy={m['accuracy']:.3f}")


def test_model_determinism(bundle=None):
    b1, b2 = bundle or ml.train_model(), ml.train_model()
    v = demo.get_demo_features("WL-DEMO-01")
    p1, p2 = ml.predict_risk(b1, v), ml.predict_risk(b2, v)
    ok = p1["risk"] == p2["risk"] and abs(p1["confidence"] - p2["confidence"]) < 1e-9
    return ("Model is deterministic (random_state=42)", ok, f"{p1['risk']} twice", f"{p1['risk']} then {p2['risk']}")


def test_demo_predictions(bundle=None):
    b = bundle or ml.train_model()
    ok, res = True, []
    for cid, c in demo.DEMO_CANDIDATES.items():
        p = ml.predict_risk(b, c["features"])
        ok = ok and p["risk"] == c["expected_risk"]
        res.append(f"{cid}={p['risk']}")
    return ("Demo candidates match their documented risk levels", ok,
            ", ".join(f"{k}={v['expected_risk']}" for k, v in demo.DEMO_CANDIDATES.items()), ", ".join(res))


# ---------------------------------------------------------------------------
# TEST-STATE, RISK NUMBERS, WISEBOT
# ---------------------------------------------------------------------------
def test_risk_levels_canonical():
    nums = [r["number"] for r in config.RISK_LEVELS]
    keys = [r["key"] for r in config.RISK_LEVELS]
    ok = nums == [1, 2, 3] and keys == config.RISK_CLASSES and all(r["definition"] for r in config.RISK_LEVELS)
    return ("Risk levels: numbered R1-R3 in severity order with definitions", ok, "1,2,3 / LOW,MEDIUM,HIGH", f"{nums} / {keys}")


def test_risk_number_in_exports():
    from . import report as rp
    b = demo.get_demo_features("WL-DEMO-01")
    scores = sc.scores_from_feature_dict(dict(zip(config.FEATURE_NAMES, b)))
    pred = {"risk": "MEDIUM", "confidence": 0.8, "probabilities": {"LOW": .1, "MEDIUM": .8, "HIGH": .1}}
    res = {"candidate_id": "T", "timestamp": "2026-01-01T00:00:00", "source": "demo", "scores": scores,
           "features": b, "prediction": pred}
    text = (rp.generate_csv(res) + rp.generate_feature_row_csv(res)).decode()
    ok = "R2" in text and config.risk_info("MEDIUM")["definition"] in text
    return ("CSV exports show risk number with definition", ok, "R2 + definition", "found" if ok else "missing")


def test_new_test_starts_at_question_1():
    r = qs.empty_responses()
    ok = ts.current_question(r, 0) == 1 and ts.section_range(0) == (1, 10) and ts.locate(1) == ("pss", 0, 0)
    return ("Fresh test starts at Question 1", ok, "Q1, range 1-10", f"Q{ts.current_question(r, 0)}, {ts.section_range(0)}")


def test_question_locate_round_trip():
    ok = all(ts.section_range(ts.locate(n)[2])[0] <= n <= ts.section_range(ts.locate(n)[2])[1]
             for n in range(1, 90))
    return ("Question numbers 1-89 map to the right section", ok, "all consistent", "ok" if ok else "mismatch")


def test_skipped_counting():
    r = qs.empty_responses()
    r["pss"][0] = 2
    _, s0 = ts.build_status(r, set())                       # nothing passed yet
    _, s1 = ts.build_status(r, {"pss"})                     # user moved past PSS with 9 blank
    r["pss"][1] = 3                                         # answers a skipped question
    _, s2 = ts.build_status(r, {"pss"})
    _, s3 = ts.build_status(r, {"pss", "pss"})              # passing again must not double count
    ok = (s0["skipped"] == 0 and s0["unanswered"] == 88 and s1["skipped"] == 9 and s1["unanswered"] == 79
          and s2["skipped"] == 8 and s2["answered"] == 2 and s3 == s2
          and s2["answered"] + s2["skipped"] + s2["unanswered"] == 89)
    return ("Skipped counts: derive, update on answer, never double count", ok,
            "0/9/8/8 skipped", f"{s0['skipped']}/{s1['skipped']}/{s2['skipped']}/{s3['skipped']}")


def test_changing_answer_keeps_counts():
    r = qs.empty_responses()
    r["gad7"][0] = 1
    _, a = ts.build_status(r, {"gad7"})
    r["gad7"][0] = 3
    _, b = ts.build_status(r, {"gad7"})
    return ("Changing an answer does not change skipped/answered counts", a == b, "equal", f"{a['answered']} vs {b['answered']}")


def test_responses_shape_guard():
    good = qs.empty_responses()
    bad = qs.empty_responses()
    bad["mbi"] = bad["mbi"][:-1]
    return ("Response-shape guard rejects a mismatched question bank",
            ts.responses_valid(good) and not ts.responses_valid(bad) and not ts.responses_valid({}), "True/False/False", "ok")


def test_scoring_ignores_skipped_flag():
    """A skipped item is never counted as answered: it scores like any blank item."""
    r = _responses(gad7=0)
    r["gad7"][0] = None
    s = sc.score_all(r)
    return ("Skipped items are not treated as answered (result marked incomplete)",
            s["missing"]["gad7"] == 1 and not s["complete"], "1 missing, incomplete", f"{s['missing']['gad7']} missing, complete={s['complete']}")


def test_wisebot_is_read_only():
    r = _responses(pss=2, gad7=1)
    snapshot = copy.deepcopy(r)
    ctx = {"question": 12, "section": "gad7", "progress": ts.build_status(r, {"pss"})[1]}
    for q in ["Explain this question", "What does this section measure?", "How many questions have I skipped?",
              "what do the risk levels mean", "explain question 5", "R3"]:
        chatbot.get_response(q, None, ctx)
    return ("WiseBot never modifies answers", r == snapshot, "unchanged", "unchanged" if r == snapshot else "CHANGED")


def test_wisebot_explains_every_question():
    ok = all("Q%d" % n in chatbot.explain_question(n) for n in range(1, 90))
    return ("WiseBot can explain all 89 questions", ok, "89 explanations", "ok" if ok else "failure")


def test_wisebot_risk_definitions():
    a = chatbot.get_response("what does r3 mean")
    ok = "R3" in a and config.risk_info("HIGH")["definition"] in a
    return ("WiseBot answers risk-number questions from the canonical source", ok, "R3 + definition", a[:60])


def test_wisebot_error_is_reported():
    orig = chatbot.get_response
    try:
        def boom(*a, **k):
            raise RuntimeError("simulated")
        chatbot.get_response = boom
        out = chatbot.safe_ask("hello")
    finally:
        chatbot.get_response = orig
    return ("WiseBot failure becomes a retryable error, not a crash", out["ok"] is False and "try again" in out["error"].lower(),
            "ok=False + message", str(out))


SCORING_TESTS = [
    test_question_count, test_instrument_counts, test_pss_all_zero, test_pss_all_max,
    test_pss_reverse_formula, test_gad_zero_and_max, test_gad_bands, test_phq_zero_and_max,
    test_phq_bands, test_phq_safety_flag, test_dass_all_zero, test_dass_multiplier,
    test_dass_subscale_separation, test_dass_item_split, test_mbi_dimensions, test_mbi_pa_direction,
    test_big5_neutral, test_big5_reverse, test_big5_range, test_feature_vector_length,
    test_feature_vector_order, test_no_composite_features, test_missing_values_handled,
    test_round_trip_feature_dict, test_label_rule_monotonic,
    test_risk_levels_canonical, test_risk_number_in_exports, test_new_test_starts_at_question_1,
    test_question_locate_round_trip, test_skipped_counting, test_changing_answer_keeps_counts,
    test_responses_shape_guard, test_scoring_ignores_skipped_flag, test_wisebot_is_read_only,
    test_wisebot_explains_every_question, test_wisebot_risk_definitions, test_wisebot_error_is_reported,
]
MODEL_TESTS = [test_model_pipeline, test_model_determinism, test_demo_predictions]


def run_all_tests(bundle=None):
    """Returns (rows, passed_count, total_count); a crash counts as a failed test."""
    rows = []
    for fn, takes_bundle in [(f, False) for f in SCORING_TESTS] + [(f, True) for f in MODEL_TESTS]:
        try:
            name, passed, expected, actual = fn(bundle) if takes_bundle else fn()
        except Exception as exc:
            name, passed, expected, actual = fn.__name__, False, "no exception", repr(exc)
        rows.append({"test": name, "passed": bool(passed), "expected": expected, "actual": actual})
    return rows, sum(r["passed"] for r in rows), len(rows)


def main():
    rows, passed, total = run_all_tests()
    print(f"WiseOLife self-tests ({total})")
    for r in rows:
        print(f"[{'PASS' if r['passed'] else 'FAIL'}] {r['test']}")
        if not r["passed"]:
            print(f"    expected: {r['expected']}\n    actual  : {r['actual']}")
    print(f"{passed}/{total} tests passed.")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
