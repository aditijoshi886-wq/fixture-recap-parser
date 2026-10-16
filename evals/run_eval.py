"""Score a set of parser predictions against the expected outputs.

Usage:
    python3 evals/run_eval.py --predictions path/to/predictions [--out evals/results/report.md]

Prediction files are named <recap_id>.json and look like:
    {
      "recap_id": "cpp-01",
      "prompt_version": "v0.1",
      "fields": {
        "vessel_name": {"value": "AEGEAN CREST", "confidence": "high", "source": "VSL: MT AEGEAN CREST"},
        ...
      }
    }

A field counts as flagged for review when its confidence is not "high", when it
carries validation messages, or when it sets "flagged": true.

Metrics (targets from the PRD):
    field accuracy            >= 95%
    critical-field accuracy   >= 98%
    wrong and not flagged     <= 1%   (the "silent error" rate)
    flag recall               share of expected flags the parser raised
"""

import argparse
import datetime as dt
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from ports import canonical_port  # noqa: E402

FIELDS = ["vessel_name", "imo", "charterer", "owner", "cargo", "load_ports", "discharge_ports", "laycan",
          "freight", "demurrage", "laytime", "commissions", "cp_form", "subjects", "fixture_date",
          "special_clauses"]
CRITICAL = {"vessel_name", "charterer", "cargo", "load_ports", "discharge_ports", "laycan", "freight",
            "demurrage", "subjects"}
COMPANY_SUFFIXES = {"SA", "LTD", "INC", "AS", "LLC", "PLC", "CO", "AG", "BV", "NV", "GMBH", "LIMITED"}


# ---------------------------------------------------------------- normalizers

def _text(s):
    return " ".join(re.sub(r"[^A-Z0-9 ]", " ", str(s).upper()).split())


def _vessel(s):
    t = _text(s)
    return re.sub(r"^(MT|MV|M T|M V)\s+", "", t)


def _company(s):
    words = _text(s).split()
    while words and words[-1] in COMPANY_SUFFIXES:
        words.pop()
    return " ".join(words)


def _num_eq(a, b, tol=0.01):
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


def _grade_eq(a, b):
    ta = set(_text(a).split()) - {"CPP", "DPP"}
    tb = set(_text(b).split()) - {"CPP", "DPP"}
    return bool(ta) and bool(tb) and (ta <= tb or tb <= ta)


def _empty(v):
    return v is None or v == [] or v == ""


# ---------------------------------------------------------------- field comparison

def field_correct(name, exp, got):
    if _empty(exp) or _empty(got):
        return _empty(exp) and _empty(got)
    try:
        if name == "vessel_name":
            return _vessel(exp) == _vessel(got)
        if name in ("charterer", "owner"):
            return _company(exp) == _company(got)
        if name == "imo":
            return re.sub(r"\D", "", str(got)) == exp
        if name == "cp_form":
            return _text(exp).replace(" ", "") == _text(got).replace(" ", "")
        if name == "cargo":
            return (_num_eq(exp["quantity_mt"], got.get("quantity_mt"), 0.5)
                    and _grade_eq(exp["grade"], got.get("grade", ""))
                    and ((exp["tolerance_pct"] is None and got.get("tolerance_pct") is None)
                         or _num_eq(exp["tolerance_pct"], got.get("tolerance_pct")))
                    and exp["tolerance_option"] == got.get("tolerance_option"))
        if name in ("load_ports", "discharge_ports"):
            return {canonical_port(p) for p in exp} == {canonical_port(p) for p in got}
        if name == "laycan":
            return exp["start"] == got.get("start") and exp["end"] == got.get("end")
        if name == "freight":
            if exp["basis"] != got.get("basis") or not _num_eq(exp["value"], got.get("value")):
                return False
            return exp["basis"] == "WS" or exp["currency"] == got.get("currency")
        if name == "demurrage":
            return (_num_eq(exp["rate_per_day"], got.get("rate_per_day"), 0.5)
                    and exp["currency"] == got.get("currency") and exp["pro_rata"] == got.get("pro_rata"))
        if name == "laytime":
            return (_num_eq(exp["hours"], got.get("hours"))
                    and _text(exp["terms"] or "") == _text(got.get("terms") or ""))
        if name == "commissions":
            norm = lambda cs: sorted((c["type"], round(float(c["pct"]), 3)) for c in cs)  # noqa: E731
            return norm(exp) == norm(got)
        if name == "special_clauses":
            return {_text(s) for s in exp} == {_text(s) for s in got}
        return exp == got  # subjects, fixture_date
    except (AttributeError, KeyError, TypeError, ValueError):
        return False  # malformed prediction counts as wrong


def is_flagged(pred_field):
    if not isinstance(pred_field, dict):
        return True
    return (pred_field.get("flagged") is True or pred_field.get("confidence", "low") != "high"
            or bool(pred_field.get("messages")))


# ---------------------------------------------------------------- scoring

def score(expected_dir, predictions_dir):
    rows = []
    versions = set()
    for path in sorted(glob.glob(os.path.join(expected_dir, "*.json"))):
        exp = json.load(open(path))
        pred_path = os.path.join(predictions_dir, f"{exp['recap_id']}.json")
        pred = json.load(open(pred_path)) if os.path.exists(pred_path) else {"fields": {}}
        if pred.get("prompt_version"):
            versions.add(pred["prompt_version"])
        for name in FIELDS:
            pf = pred.get("fields", {}).get(name)
            got = pf.get("value") if isinstance(pf, dict) else None
            ok = field_correct(name, exp["fields"][name], got) if pf is not None else False
            rows.append({"recap": exp["recap_id"], "slice": exp["slice"], "field": name,
                         "critical": name in CRITICAL, "correct": ok, "flagged": is_flagged(pf),
                         "expect_flag": name in exp.get("expect_flagged", []),
                         "expected": exp["fields"][name], "got": got})
    return rows, sorted(versions)


def pct(n, d):
    return 100.0 * n / d if d else 0.0


def summarize(rows):
    total = len(rows)
    crit = [r for r in rows if r["critical"]]
    silent = [r for r in rows if not r["correct"] and not r["flagged"]]
    want_flag = [r for r in rows if r["expect_flag"]]
    return {
        "recaps": len({r["recap"] for r in rows}),
        "fields_scored": total,
        "field_accuracy": pct(sum(r["correct"] for r in rows), total),
        "critical_accuracy": pct(sum(r["correct"] for r in crit), len(crit)),
        "silent_error_rate": pct(len(silent), total),
        "silent_errors": len(silent),
        "flag_recall": pct(sum(r["flagged"] for r in want_flag), len(want_flag)),
        "flag_rate": pct(sum(r["flagged"] for r in rows), total),
    }


def report(rows, versions, predictions_dir):
    s = summarize(rows)
    ok = lambda v, target, higher=True: "pass" if (v >= target if higher else v <= target) else "FAIL"  # noqa: E731
    out = []
    out.append(f"# Eval report: {os.path.basename(os.path.normpath(predictions_dir))}")
    out.append("")
    out.append(f"Run {dt.date.today().isoformat()} · prompt version: {', '.join(versions) or 'n/a'} · "
               f"{s['recaps']} recaps · {s['fields_scored']} fields")
    out.append("")
    out.append("| Metric | Result | Target | |")
    out.append("| --- | --- | --- | --- |")
    out.append(f"| Field accuracy | {s['field_accuracy']:.1f}% | ≥ 95% | {ok(s['field_accuracy'], 95)} |")
    out.append(f"| Critical-field accuracy | {s['critical_accuracy']:.1f}% | ≥ 98% | {ok(s['critical_accuracy'], 98)} |")
    out.append(f"| Wrong and not flagged | {s['silent_error_rate']:.1f}% ({s['silent_errors']}) | ≤ 1% | "
               f"{ok(s['silent_error_rate'], 1, higher=False)} |")
    out.append(f"| Flag recall (expected flags raised) | {s['flag_recall']:.0f}% | 100% | {ok(s['flag_recall'], 100)} |")
    out.append(f"| Share of fields flagged for review | {s['flag_rate']:.1f}% | (lower saves review time) | |")
    out.append("")
    out.append("## Accuracy by slice")
    out.append("")
    out.append("| Slice | Recaps | Field accuracy | Critical accuracy |")
    out.append("| --- | --- | --- | --- |")
    for sl in sorted({r["slice"] for r in rows}):
        sub = [r for r in rows if r["slice"] == sl]
        ss = summarize(sub)
        out.append(f"| {sl} | {ss['recaps']} | {ss['field_accuracy']:.1f}% | {ss['critical_accuracy']:.1f}% |")
    out.append("")
    out.append("## Accuracy by field")
    out.append("")
    out.append("| Field | Critical | Accuracy | Silent errors |")
    out.append("| --- | --- | --- | --- |")
    for f in FIELDS:
        sub = [r for r in rows if r["field"] == f]
        silent = sum(1 for r in sub if not r["correct"] and not r["flagged"])
        out.append(f"| {f} | {'yes' if f in CRITICAL else ''} | {pct(sum(r['correct'] for r in sub), len(sub)):.0f}% | {silent} |")
    silent = [r for r in rows if not r["correct"] and not r["flagged"]]
    if silent:
        out.append("")
        out.append("## Silent errors (wrong and marked high confidence)")
        out.append("")
        out.append("| Recap | Field | Expected | Got |")
        out.append("| --- | --- | --- | --- |")
        for r in silent[:60]:
            out.append(f"| {r['recap']} | {r['field']} | `{json.dumps(r['expected'])}` | `{json.dumps(r['got'])}` |")
        if len(silent) > 60:
            out.append(f"| … | {len(silent) - 60} more | | |")
    return "\n".join(out) + "\n", s


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--predictions", required=True, help="folder of <recap_id>.json prediction files")
    ap.add_argument("--expected", default=os.path.join(HERE, "expected"))
    ap.add_argument("--out", help="write the markdown report here as well")
    args = ap.parse_args()
    rows, versions = score(args.expected, args.predictions)
    text, s = report(rows, versions, args.predictions)
    print(text)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w") as f:
            f.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
