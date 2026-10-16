"""Rules-only baseline: regular expressions, no AI.

This exists to give the eval a first number and to show where hand-written
rules break down (shorthand, messy emails, conflicting terms). The AI parser
has to beat it. Every value it finds is marked high confidence, which is
exactly the overconfidence the "wrong and not flagged" metric is designed to
catch.

Usage:  python3 baseline/rules_parser.py evals/recaps out/baseline
"""

import datetime as dt
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))
from ports import canonical_port  # noqa: E402

MON = {m: i + 1 for i, m in enumerate(["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                                        "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"])}


def label(text, *names):
    """Value after a 'LABEL:' line, tolerating numbering and padding."""
    for n in names:
        m = re.search(rf"^\s*(?:\d+\.\s*)?{n}\s*:\s*(.+)$", text, re.M)
        if m:
            return m.group(1).strip()
    return None


def parse_date(s):
    m = re.search(r"(\d{1,2})[ -]([A-Z]{3})[A-Z]*[ -](\d{2,4})", s.upper())
    if not m:
        return None
    y = int(m.group(3))
    y = y + 2000 if y < 100 else y
    return dt.date(y, MON[m.group(2)], int(m.group(1)))


def parse(text):
    t = text.upper()
    f = {}
    fixture = None
    m = re.search(r"CP DD (.+)", t)
    if m:
        fixture = parse_date(m.group(1))
    f["fixture_date"] = fixture.isoformat() if fixture else None

    v = label(t, "VSL", "VESSEL")
    if v:
        f["vessel_name"] = re.sub(r"^MT\s+", "", re.sub(r"\s*\(IMO.*", "", v))
    m = re.search(r"IMO\s*(\d{7})", t)
    f["imo"] = m.group(1) if m else None
    f["owner"] = label(t, "OWNERS", "DISPONENT OWNERS")
    f["charterer"] = label(t, "CHRTS", "CHARTERERS")

    c = label(t, "CARGO")
    if c:
        m = re.match(r"([\d,]+)\s*MT\s+(.+?)\s+(\d+(?:\.\d+)?)%\s*(MOLOO|MOLCHOPT)", c)
        if m:
            f["cargo"] = {"grade": m.group(2), "quantity_mt": float(m.group(1).replace(",", "")),
                          "tolerance_pct": float(m.group(3)), "tolerance_option": m.group(4)}

    for key, names in (("load_ports", ("LOAD", r"LOADPORT\(S\)")), ("discharge_ports", ("DISCH", r"DISCHARGE PORT\(S\)"))):
        p = label(t, *names)
        if p:
            f[key] = [canonical_port(x) for x in p.split("+")]

    lc = label(t, "LAYCAN", "LAYDAYS/CANCELLING")
    if lc and fixture:
        m = re.match(r"(\d{1,2})\s*[-/]\s*(\d{1,2})\s+([A-Z]{3})", lc)
        if m:
            mon = MON[m.group(3)]
            year = fixture.year + (1 if mon < fixture.month else 0)
            f["laycan"] = {"start": dt.date(year, mon, int(m.group(1))).isoformat(),
                           "end": dt.date(year, mon, int(m.group(2))).isoformat()}

    fr = label(t, "FRT", "FREIGHT")
    if fr:
        m = re.search(r"(?:WS|WORLDSCALE)\s*([\d.]+)", fr)
        if m:
            f["freight"] = {"basis": "WS", "value": float(m.group(1)), "currency": None}
        m = re.search(r"USD\s*([\d,]+)\s*LUMPSUM|LUMPSUM USD\s*([\d,]+)", fr)
        if m:
            f["freight"] = {"basis": "LUMPSUM", "value": float((m.group(1) or m.group(2)).replace(",", "")), "currency": "USD"}
        m = re.search(r"USD\s*([\d.]+)\s*PER MT", fr)
        if m:
            f["freight"] = {"basis": "PER_MT", "value": float(m.group(1)), "currency": "USD"}

    d = label(t, "DEM", "DEMURRAGE")
    if d:
        m = re.search(r"USD\s*([\d,]+)", d)
        if m:
            f["demurrage"] = {"rate_per_day": float(m.group(1).replace(",", "")), "currency": "USD",
                              "pro_rata": "PDPR" in d or "PRO RATA" in d}

    lt = label(t, "LAYTIME")
    if lt:
        m = re.match(r"([\d.]+)\s*HRS\s*(\w+)?", lt)
        if m:
            f["laytime"] = {"hours": float(m.group(1)), "terms": m.group(2)}

    cm = label(t, "COMMS", "COMMISSION")
    if cm:
        nums = re.findall(r"([\d.]+)\s*(?:%|PCT)", cm)
        if len(nums) == 2:
            f["commissions"] = [{"type": "ADDRESS", "pct": float(nums[0])}, {"type": "BROKERAGE", "pct": float(nums[1])}]

    f["cp_form"] = label(t, "CP", "CP FORM")
    s = label(t, "SUBJECTS")
    if s:
        f["subjects"] = "ON_SUBJECTS" if "SUB" in s and "LIFTED" not in s else "FIXED_CLEAN"

    m = re.search(r"OTHER TERMS:\n((?:- .+\n)+)", t)
    f["special_clauses"] = [x[2:].strip() for x in m.group(1).splitlines()] if m else []
    return f


def main(src, dst):
    os.makedirs(dst, exist_ok=True)
    for path in sorted(glob.glob(os.path.join(src, "*.txt"))):
        rid = os.path.splitext(os.path.basename(path))[0]
        found = parse(open(path).read())
        fields = {}
        for name in ["vessel_name", "imo", "charterer", "owner", "cargo", "load_ports", "discharge_ports",
                     "laycan", "freight", "demurrage", "laytime", "commissions", "cp_form", "subjects",
                     "fixture_date", "special_clauses"]:
            val = found.get(name)
            fields[name] = {"value": val, "confidence": "high" if val not in (None, []) else "low"}
        with open(os.path.join(dst, f"{rid}.json"), "w") as f:
            json.dump({"recap_id": rid, "prompt_version": "rules-baseline", "fields": fields}, f, indent=2)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
