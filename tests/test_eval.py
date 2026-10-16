"""Self-tests for the eval harness and the sample set.

Run:  python3 -m pytest tests   (or: python3 tests/test_eval.py)
"""

import copy
import glob
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "evals"))
from run_eval import FIELDS, score, summarize  # noqa: E402

EXPECTED = os.path.join(ROOT, "evals", "expected")


def _write_perfect(dst, mutate=None):
    for path in glob.glob(os.path.join(EXPECTED, "*.json")):
        exp = json.load(open(path))
        fields = {}
        for name in FIELDS:
            flagged = name in exp["expect_flagged"]
            fields[name] = {"value": copy.deepcopy(exp["fields"][name]), "confidence": "low" if flagged else "high"}
        pred = {"recap_id": exp["recap_id"], "prompt_version": "test", "fields": fields}
        if mutate:
            mutate(pred)
        json.dump(pred, open(os.path.join(dst, f"{exp['recap_id']}.json"), "w"))


def test_sample_set_shape():
    files = glob.glob(os.path.join(EXPECTED, "*.json"))
    assert len(files) == 40
    slices = {}
    for p in files:
        s = json.load(open(p))["slice"]
        slices[s] = slices.get(s, 0) + 1
    assert slices == {"clean_cpp": 10, "dirty_crude_dpp": 10, "shorthand": 8,
                      "missing_or_conflicting": 7, "messy_email": 5}


def test_perfect_predictions_score_100():
    with tempfile.TemporaryDirectory() as d:
        _write_perfect(d)
        s = summarize(score(EXPECTED, d)[0])
        assert s["field_accuracy"] == 100 and s["critical_accuracy"] == 100
        assert s["silent_errors"] == 0 and s["flag_recall"] == 100


def test_wrong_high_confidence_value_is_a_silent_error():
    def mutate(pred):
        if pred["recap_id"] == "cpp-01":
            pred["fields"]["demurrage"]["value"]["rate_per_day"] += 1000
    with tempfile.TemporaryDirectory() as d:
        _write_perfect(d, mutate)
        rows = score(EXPECTED, d)[0]
        s = summarize(rows)
        assert s["silent_errors"] == 1
        bad = [r for r in rows if not r["correct"]]
        assert [(r["recap"], r["field"]) for r in bad] == [("cpp-01", "demurrage")]


def test_normalization_accepts_equivalent_forms():
    def mutate(pred):
        f = pred["fields"]
        f["vessel_name"]["value"] = "MT " + f["vessel_name"]["value"].lower()
        if f["load_ports"]["value"] == ["USG"]:
            f["load_ports"]["value"] = ["US Gulf"]
    with tempfile.TemporaryDirectory() as d:
        _write_perfect(d, mutate)
        assert summarize(score(EXPECTED, d)[0])["field_accuracy"] == 100


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
