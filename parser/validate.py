"""Deterministic checks on an extraction (PRD FR5, FR8 to FR12).

The model's confidence is never the last word: any rule failure adds a message
and flags the field, whatever confidence the model gave it.
"""

import datetime as dt
import re

CRITICAL = {"vessel_name", "charterer", "cargo", "load_ports", "discharge_ports", "laycan", "freight",
            "demurrage", "subjects"}


def _squash(s):
    return " ".join(str(s).upper().split())


def imo_valid(imo):
    if not re.fullmatch(r"\d{7}", str(imo)):
        return False
    d = [int(c) for c in str(imo)]
    return sum(a * w for a, w in zip(d[:6], range(7, 1, -1))) % 10 == d[6]


def _date(s):
    try:
        return dt.date.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def validate(fields, recap):
    """Add messages to fields in place and return the list of flagged field names."""
    text = _squash(recap)

    def flag(name, msg):
        fields[name].setdefault("messages", []).append(msg)

    # FR5: every value must point at words that are really in the recap
    for name, f in fields.items():
        v = f.get("value")
        if v in (None, [], ""):
            if name in CRITICAL:
                flag(name, "Not found in the recap; enter it or confirm it is not agreed.")
            continue
        src = f.get("source")
        if not src:
            f["confidence"] = "low"
            flag(name, "No source words given for this value.")
            continue
        parts = [p for p in str(src).split(" | ") if p.strip()]
        if not all(_squash(p) in text for p in parts):
            f["confidence"] = "low"
            flag(name, "Source words not found in the recap; check this value.")

    fixture = _date(fields["fixture_date"].get("value"))

    # FR8: laycan order and window
    lc = fields["laycan"].get("value")
    if isinstance(lc, dict):
        s, e = _date(lc.get("start")), _date(lc.get("end"))
        if not s or not e:
            flag("laycan", "Laycan dates are not valid ISO dates.")
        else:
            if s > e:
                flag("laycan", "Laycan end is before laycan start.")
            if fixture:
                if not (fixture - dt.timedelta(days=7) <= s <= fixture + dt.timedelta(days=120)):
                    flag("laycan", "Laycan is not within 120 days after the fixture date.")
                if s.year > fixture.year:
                    flag("laycan", f"Laycan year rolled over to {s.year}; confirm.")

    # FR9: IMO check digit
    imo = fields["imo"].get("value")
    if imo and not imo_valid(imo):
        flag("imo", "IMO number fails the check-digit rule.")

    # FR10: freight basis and value agree
    fr = fields["freight"].get("value")
    if isinstance(fr, dict):
        val = fr.get("value")
        if fr.get("basis") == "WS":
            if not isinstance(val, (int, float)) or not 1 <= val <= 500:
                flag("freight", "Worldscale rate should be between 1 and 500.")
        elif fr.get("basis") in ("LUMPSUM", "PER_MT"):
            if not fr.get("currency"):
                flag("freight", "Lump sum or per-tonne freight needs a currency.")
            if not isinstance(val, (int, float)) or val <= 0:
                flag("freight", "Freight must be a positive amount.")

    # FR11: demurrage
    dem = fields["demurrage"].get("value")
    if isinstance(dem, dict):
        r = dem.get("rate_per_day")
        if not isinstance(r, (int, float)) or r <= 0 or not dem.get("currency"):
            flag("demurrage", "Demurrage needs a positive daily rate and a currency.")
        elif r > 250_000:
            flag("demurrage", "Demurrage above USD 250,000 per day is unusual for a tanker; check.")

    # cargo sanity
    cg = fields["cargo"].get("value")
    if isinstance(cg, dict):
        q = cg.get("quantity_mt")
        if not isinstance(q, (int, float)) or not 1_000 <= q <= 350_000:
            flag("cargo", "Cargo quantity outside 1,000 to 350,000 MT; check units.")

    # FR12: any message flags the field
    flagged = []
    for name, f in fields.items():
        if f.get("messages") or f.get("confidence") != "high":
            f["flagged"] = True
            flagged.append(name)
        else:
            f["flagged"] = False
    return flagged
