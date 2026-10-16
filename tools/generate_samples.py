"""Generate the synthetic tanker recap eval set.

Each sample starts as a structured fixture (the expected answer) and is then
rendered into recap text in one of several broker styles. Because the text is
written from the answer, the expected JSON is correct by construction; the
generator is also reviewed by hand (see docs/decision-log.md).

All vessels, companies, figures and IMO numbers are invented. Nothing here is a
real commercial fixture.

Usage:  python3 tools/generate_samples.py          (writes evals/recaps + evals/expected)
"""

import datetime as dt
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from ports import canonical_port  # noqa: E402

RNG = random.Random(20261016)
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
MONTHS_LONG = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST",
               "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]

# ---------------------------------------------------------------- invented pools

VESSELS = [
    "AEGEAN CREST", "KESTREL SPIRIT", "SOLWAY TRADER", "HALCYON DAWN", "TIDEWAY PRIDE",
    "CORVINA BAY", "BRAEMOOR VOYAGER", "FJELLSTAD", "SEA WARBLER", "MARLIN HORIZON",
    "OCEAN LYRIC", "CAPE TERN", "STELLAR PIPER", "ISLA BRAVA", "NORTHERN QUILL",
    "PACIFIC WREN", "AMBER FALCON", "LOCH TORRIDON", "SILVER MAHSEER", "TORM OSPREY",
    "BLUE HERON II", "ARCTIC LARCH", "SANTA ZOE", "MINERVA GALE", "CASTLE ROCK",
    "VEGA STRAIT", "PORT ELSPETH", "LADY KORRIGAN", "SIERRA ALBA", "GANNET POINT",
    "KOTA LESTARI", "SEA OF HEBRIDES", "MORAY FIRTH", "ADRIA SKY", "DELTA KINGFISHER",
    "OCEAN TEAL", "NORDLYS", "CAPE COLVILLE", "AZURE MERLIN", "HELIX VOYAGER",
]
# "TORM" is a real tanker owner prefix; replace to keep everything invented.
VESSELS[VESSELS.index("TORM OSPREY")] = "TERN OSPREY"

OWNERS = [
    "FJELLSTAD TANKERS AS", "AEGEAN CREST SHIPPING", "KESTREL MARITIME LTD", "SOLWAY TANKER POOL",
    "HALCYON NAVIGATION SA", "TIDEWAY SHIPHOLDING", "CORVINA MARINE INC", "BRAEMOOR CRUDE CARRIERS",
]
CHARTERERS = [
    "ACME ENERGY TRADING SA", "VERIDIAN REFINING", "COASTLINE PETROLEUM", "ORIEL OIL TRADING",
    "SUNMERE ENERGY", "HARBORLINE FUELS", "PELICAN BAY REFINERY", "TERRANOVA CRUDE MARKETING",
]
CP_FORMS = ["ASBATANKVOY", "BPVOY4", "SHELLVOY 6"]

CPP_GRADES = ["CPP (ULSD)", "CPP (UNL GASOLINE)", "CPP (JET A1)", "CPP (NAPHTHA)", "CPP (GASOIL 10PPM)"]
DIRTY_GRADES = ["CRUDE OIL", "FUEL OIL 380 CST", "VGO", "FUEL OIL 180 CST", "CONDENSATE"]

CPP_ROUTES = [  # (load ports, discharge ports)
    (["USG"], ["UKC-MED"]), (["UKC"], ["USAC"]), (["AG"], ["FAR EAST"]), (["SINGAPORE"], ["FAR EAST"]),
    (["HOUSTON", "CORPUS CHRISTI"], ["ECSA"]), (["ROTTERDAM"], ["NEW YORK"]), (["AG"], ["WAF"]),
    (["WCI"], ["UKC"]), (["USG"], ["CARIBS"]), (["AMSTERDAM", "ANTWERP"], ["WAF"]),
]
DIRTY_ROUTES = [
    (["PRIMORSK"], ["UKC"]), (["CEYHAN"], ["MED"]), (["BONNY"], ["UKC-MED"]), (["RAS TANURA"], ["FAR EAST"]),
    (["USG"], ["UKC"]), (["SIDI KERIR"], ["AUGUSTA"]), (["JUBAIL", "RAS TANURA"], ["ULSAN"]),
    (["CORPUS CHRISTI"], ["ROTTERDAM"]), (["SANTOS"], ["CHIBA"]), (["FUJAIRAH"], ["SINGAPORE"]),
]
SPECIALS_CPP = [
    "TWO GRADES WVNS", "ETS COSTS FOR CHRTS ACCT", "BIMCO SANCTIONS CLAUSE TO APPLY",
    "CHRTS TO PROVIDE LOI FOR DISCH WITHOUT BL", "WAR RISK FOR CHRTS ACCT",
]
SPECIALS_DIRTY = [
    "HEATING MAX 135F THROUGHOUT", "ICE CLAUSE AS PER CP", "COW AS PER MARPOL",
    "ETS COSTS FOR CHRTS ACCT", "BIMCO SANCTIONS CLAUSE TO APPLY", "WAR RISK FOR CHRTS ACCT",
]

PORT_PRINT = {  # how brokers write some canonical names; others print as-is
    "USG": ["USG", "US GULF"], "UKC": ["UKC", "UK CONT"], "UKC-MED": ["UKC-MED", "UKC/MED"],
    "AG": ["AG", "PG", "ARABIAN GULF"], "SINGAPORE": ["SINGAPORE", "SPORE"], "ROTTERDAM": ["ROTTERDAM", "ROTT"],
    "FAR EAST": ["FAR EAST", "FEAST"], "WAF": ["WAF", "WEST AFRICA"], "USAC": ["USAC"], "MED": ["MED"],
}


# ---------------------------------------------------------------- helpers

def imo_number(rng):
    """A random 7-digit IMO number that passes the check-digit rule."""
    digits = [9] + [rng.randint(0, 9) for _ in range(5)]
    check = sum(d * w for d, w in zip(digits, range(7, 1, -1))) % 10
    return "".join(map(str, digits)) + str(check)


def money(n):
    return f"{n:,.0f}" if float(n).is_integer() else f"{n:,.2f}"


def short_k(n):
    k = n / 1000
    return (f"{k:.0f}K" if k.is_integer() else f"{k:g}K")


def d_iso(d):
    return d.isoformat()


def d_print(d, style):
    if style == 0:
        return f"{d.day:02d} {MONTHS[d.month - 1]} {d.year}"
    if style == 1:
        return f"{d.day} {MONTHS_LONG[d.month - 1].title()} {d.year}"
    return f"{d.day:02d}-{MONTHS[d.month - 1]}-{str(d.year)[2:]}"


def laycan_print(start, end, rng, with_year):
    y = f" {end.year}" if with_year else ""
    if start.month == end.month:
        sep = rng.choice(["-", "/", " - "])
        mon = rng.choice([MONTHS[start.month - 1], MONTHS_LONG[start.month - 1]])
        return f"{start.day:02d}{sep}{end.day:02d} {mon}{y}"
    return f"{start.day:02d} {MONTHS[start.month - 1]} - {end.day:02d} {MONTHS[end.month - 1]}{y}"


def port_print(canon, rng):
    return rng.choice(PORT_PRINT.get(canon, [canon]))


def ports_print(ports, rng):
    qual = rng.choice(["1/2 SP ", "1 SP ", "1-2 SB ", ""]) if len(ports) == 1 else ""
    return qual + "+".join(port_print(p, rng) for p in ports)


# ---------------------------------------------------------------- fixture builder

def build_fixture(rng, kind, idx, fixture_date=None):
    vessel = VESSELS[idx % len(VESSELS)]
    if fixture_date is None:
        fixture_date = dt.date(2026, 10, 1) + dt.timedelta(days=rng.randint(0, 80))
    lay_start = fixture_date + dt.timedelta(days=rng.randint(5, 35))
    lay_end = lay_start + dt.timedelta(days=rng.choice([1, 2, 2, 3]))

    if kind == "cpp":
        size = rng.choice(["MR", "MR", "LR1", "LR2"])
        qty = {"MR": rng.choice([30000, 35000, 37000, 38000, 40000]),
               "LR1": rng.choice([55000, 60000, 65000]),
               "LR2": rng.choice([75000, 80000, 90000])}[size]
        grade = rng.choice(CPP_GRADES)
        load, disch = rng.choice(CPP_ROUTES)
        ws = rng.choice([115, 125, 132.5, 140, 155, 170, 187.5, 210, 235])
        dem = {"MR": rng.choice([22000, 24500, 26000, 28500]), "LR1": rng.choice([30000, 32500]),
               "LR2": rng.choice([38000, 40000, 42500])}[size]
        specials = rng.sample(SPECIALS_CPP, rng.choice([0, 1, 1, 2]))
    else:
        size = rng.choice(["AFRA", "AFRA", "SUEZ", "VLCC"])
        qty = {"AFRA": rng.choice([80000, 85000, 100000]), "SUEZ": rng.choice([130000, 135000, 140000]),
               "VLCC": rng.choice([260000, 270000, 280000])}[size]
        grade = rng.choice(DIRTY_GRADES) if size == "AFRA" else rng.choice(["CRUDE OIL", "CRUDE OIL", "CONDENSATE"])
        load, disch = rng.choice(DIRTY_ROUTES)
        ws = {"AFRA": rng.choice([95, 107.5, 120, 135, 150]), "SUEZ": rng.choice([72.5, 80, 87.5, 95]),
              "VLCC": rng.choice([47.5, 52, 57.5, 63])}[size]
        dem = {"AFRA": rng.choice([35000, 38500, 42000]), "SUEZ": rng.choice([45000, 48000, 52500]),
               "VLCC": rng.choice([60000, 68000, 75000, 85000])}[size]
        specials = rng.sample(SPECIALS_DIRTY, rng.choice([0, 1, 1, 2]))

    basis_roll = rng.random()
    if basis_roll < 0.72:
        freight = {"basis": "WS", "value": ws, "currency": None}
    elif basis_roll < 0.88:
        freight = {"basis": "LUMPSUM", "value": float(rng.choice([850000, 1150000, 1400000, 1875000, 2250000])), "currency": "USD"}
    else:
        freight = {"basis": "PER_MT", "value": rng.choice([12.5, 16.75, 18.5, 23.0, 31.25]), "currency": "USD"}

    addcomm = rng.choice([1.25, 2.5, 2.5, 3.75])
    return {
        "vessel_name": vessel,
        "imo": imo_number(rng),
        "charterer": rng.choice(CHARTERERS),
        "owner": rng.choice(OWNERS),
        "cargo": {"grade": grade, "quantity_mt": qty,
                  "tolerance_pct": rng.choice([5, 10, 10, 10]),
                  "tolerance_option": rng.choice(["MOLOO", "MOLOO", "MOLOO", "MOLCHOPT"])},
        "load_ports": [canonical_port(p) for p in load],
        "discharge_ports": [canonical_port(p) for p in disch],
        "laycan": {"start": d_iso(lay_start), "end": d_iso(lay_end)},
        "freight": freight,
        "demurrage": {"rate_per_day": float(dem), "currency": "USD", "pro_rata": True},
        "laytime": {"hours": float(rng.choice([72, 72, 72, 84, 96])), "terms": "SHINC"},
        "commissions": [{"type": "ADDRESS", "pct": addcomm}, {"type": "BROKERAGE", "pct": 1.25}],
        "cp_form": rng.choice(CP_FORMS),
        "subjects": rng.choice(["FIXED_CLEAN", "FIXED_CLEAN", "ON_SUBJECTS"]),
        "fixture_date": d_iso(fixture_date),
        "special_clauses": specials,
    }


# ---------------------------------------------------------------- renderers

def freight_text(f, rng, terse=False):
    if f["basis"] == "WS":
        v = f"{f['value']:g}"
        return rng.choice([f"WS {v}", f"WS{v}", f"W{v}"]) if terse else rng.choice([f"WS {v}", f"WORLDSCALE {v}"])
    if f["basis"] == "LUMPSUM":
        v = f["value"]
        return rng.choice([f"USD {v / 1e6:g}M LS", f"LS USD {money(v)}"]) if terse else rng.choice(
            [f"LUMPSUM USD {money(v)}", f"USD {money(v)} LUMPSUM"])
    v = f["value"]
    return rng.choice([f"USD {v:g} PMT", f"USD {v:g}/MT"]) if terse else f"USD {v:.2f} PER MT"


def dem_text(d, rng, terse=False):
    r = d["rate_per_day"]
    if terse:
        return rng.choice([f"DEM {short_k(r)} PDPR", f"DEM USD {short_k(r)} PDPR"])
    return rng.choice([f"USD {money(r)} PDPR", f"USD {money(r)} PER DAY PRO RATA"])


def comm_text(cs, rng, terse=False):
    a = next(c["pct"] for c in cs if c["type"] == "ADDRESS")
    b = next(c["pct"] for c in cs if c["type"] == "BROKERAGE")
    if terse:
        return rng.choice([f"{a:g}ADC+{b:g}BRK", f"{a + b:g}PCT TTL INCL {b:g} BRKG"])
    return rng.choice([f"{a:g}% ADDCOMM + {b:g}% BROKERAGE", f"ADDRESS {a:g} PCT, BROKERAGE {b:g} PCT"])


def cargo_text(c, rng, terse=False):
    tol = f"{c['tolerance_pct']:g}% {c['tolerance_option']}"
    if terse:
        return f"{c['quantity_mt'] // 1000} {c['grade'].replace('CPP (', '').rstrip(')') if 'CPP' in c['grade'] else c['grade']} {tol}"
    return f"{c['quantity_mt']:,} MT {c['grade']} {tol}"


def subj_text(s, rng):
    if s == "FIXED_CLEAN":
        return rng.choice(["CLEAN FIXED", "SUBS LIFTED - FULLY FIXED", "FIXED CLEAN"])
    return rng.choice(["ON SUBS", "SUBJECT SHIPPER/RECEIVER APPROVAL", "ON SUBJECTS - STEM"])


def render_block(fx, rng, style=None, omit=(), overrides=None):
    """A labelled block recap, the most common broker format."""
    overrides = overrides or {}
    style = rng.choice([0, 1]) if style is None else style
    fd = dt.date.fromisoformat(fx["fixture_date"])
    ls = dt.date.fromisoformat(fx["laycan"]["start"]) if fx["laycan"] else None
    le = dt.date.fromisoformat(fx["laycan"]["end"]) if fx["laycan"] else None
    L = (lambda a, b: a) if style == 0 else (lambda a, b: b)
    lines = []
    head = rng.choice(["RECAP", "FIXTURE RECAP", "CLEAN RECAP"])
    lines.append(f"{head} - MT {fx['vessel_name']} / {fx['charterer'].split()[0]} - CP DD {d_print(fd, rng.choice([0, 1]))}")
    lines.append("")
    lines.append(rng.choice(["PLEASED TO CONFIRM THE FOLLOWING FIXTURE:", "WE ARE PLEASED TO RECAP AS FOLLOWS:",
                             "HEREWITH RECAP OF THE FIXTURE CONCLUDED TODAY:"]))
    lines.append("")
    rows = []
    if "vessel_name" not in omit:
        imo = f" (IMO {fx['imo']})" if fx["imo"] and "imo" not in omit else ""
        rows.append((L("VSL", "VESSEL"), f"MT {fx['vessel_name']}{imo}"))
    if "owner" not in omit:
        rows.append((L("OWNERS", "DISPONENT OWNERS"), fx["owner"]))
    if "charterer" not in omit:
        rows.append((L("CHRTS", "CHARTERERS"), fx["charterer"]))
    if "cargo" not in omit:
        rows.append(("CARGO", overrides.get("cargo") or cargo_text(fx["cargo"], rng)))
    if "load_ports" not in omit:
        rows.append((L("LOAD", "LOADPORT(S)"), ports_print(fx["load_ports"], rng)))
    if "discharge_ports" not in omit:
        rows.append((L("DISCH", "DISCHARGE PORT(S)"), ports_print(fx["discharge_ports"], rng)))
    if "laycan" not in omit:
        rows.append((L("LAYCAN", "LAYDAYS/CANCELLING"), overrides.get("laycan") or laycan_print(ls, le, rng, rng.random() < 0.6)))
    if "freight" not in omit:
        rows.append((L("FRT", "FREIGHT"), freight_text(fx["freight"], rng)))
    if "demurrage" not in omit:
        rows.append((L("DEM", "DEMURRAGE"), overrides.get("demurrage") or dem_text(fx["demurrage"], rng)))
    if "laytime" not in omit:
        rows.append(("LAYTIME", f"{fx['laytime']['hours']:g} HRS {fx['laytime']['terms']}"))
    if "commissions" not in omit:
        rows.append((L("COMMS", "COMMISSION"), comm_text(fx["commissions"], rng)))
    if "cp_form" not in omit:
        rows.append((L("CP", "CP FORM"), fx["cp_form"]))
    if "subjects" not in omit:
        rows.append(("SUBJECTS", subj_text(fx["subjects"], rng)))
    numbered = rng.random() < 0.4
    for i, (k, v) in enumerate(rows, 1):
        lines.append(f"{i}. {k}: {v}" if numbered else f"{k:<12}: {v}" if style == 0 else f"{k}: {v}")
    for extra in overrides.get("extra_lines", []):
        lines.append(extra)
    if fx["special_clauses"]:
        lines.append("")
        lines.append("OTHER TERMS:")
        for s in fx["special_clauses"]:
            lines.append(f"- {s}")
    lines.append("")
    lines.append(rng.choice(["OTHERWISE AS PER CHRTS PROFORMA CP LOGICALLY AMENDED.",
                             "OTHERWISE AS PER OWNERS LAST CP WITH ACME, LOGICALLY AMENDED.",
                             "ALL ELSE AS PER CP FORM, LOGICALLY AMENDED."]))
    lines.append("")
    lines.append(rng.choice(["THANKS FOR THE SUPPORT", "THANK YOU BOTH FOR A SMOOTH FIXTURE", "TKS AND BRGDS"]))
    return "\n".join(lines) + "\n"


def render_oneliner(fx, rng):
    """Shorthand one-line style used in fixture lists and chats."""
    fd = dt.date.fromisoformat(fx["fixture_date"])
    ls = dt.date.fromisoformat(fx["laycan"]["start"])
    le = dt.date.fromisoformat(fx["laycan"]["end"])
    parts = [
        f"FIXED {d_print(fd, 2)}:",
        fx["vessel_name"],
        cargo_text(fx["cargo"], rng, terse=True),
        f"{ports_print(fx['load_ports'], rng)} / {ports_print(fx['discharge_ports'], rng)}",
        laycan_print(ls, le, rng, False),
        freight_text(fx["freight"], rng, terse=True),
        dem_text(fx["demurrage"], rng, terse=True),
        fx["charterer"],
        fx["cp_form"],
        f"{fx['laytime']['hours']:g}HRS {fx['laytime']['terms']}",
        comm_text(fx["commissions"], rng, terse=True),
        "SUBS" if fx["subjects"] == "ON_SUBJECTS" else "FXD",
    ]
    return " ".join(parts) + "\n"


SIGNATURES = [
    "Best regards\nJ. Okafor\nTanker Chartering | Harbourside Shipbroking Ltd\nT: +44 20 0000 0000\n",
    "Kind regards,\nMarta Lindqvist\nClean Desk, Fairlead Brokers\nM: +45 00 00 00 00\n",
    "Rgds\nTom\nSent from my iPhone\n",
]
DISCLAIMER = ("This e-mail and any attachments are confidential and intended solely for the addressee. "
              "If you have received it in error please notify the sender and delete it.\n")


def render_email(fx, rng, variant):
    body = render_block(fx, rng)
    fd = dt.date.fromisoformat(fx["fixture_date"])
    hdr = (f"From: Fairlead Brokers <recaps@fairlead.example>\nSent: {d_print(fd, 1)} 17:42\n"
           f"To: Ops Desk <ops@{fx['charterer'].split()[0].lower()}.example>\nSubject: RE: MT {fx['vessel_name']} - RECAP\n\n")
    if variant == 0:  # forwarded with a note on top
        return ("Ops - pls set up in VMS, recap below. Laycan tight so pls nominate agents asap.\n\n" + SIGNATURES[0] +
                "\n---------- Forwarded message ----------\n" + hdr + body + "\n" + SIGNATURES[1] + "\n" + DISCLAIMER)
    if variant == 1:  # recap followed by another vessel's position list
        o = [fd + dt.timedelta(days=k) for k in (3, 5, 6)]
        poslist = ("\n\nALSO FOR YR INFO, OPEN TONNAGE USG NEXT 10 DAYS:\n"
                   f"MT CAPE LUMEN 37K 2014 OPEN HOUSTON {o[0].day:02d}/{o[0].month:02d} LAST CPP\n"
                   f"MT ORCA GLEN 38K 2017 OPEN CORPUS {o[1].day:02d}/{o[1].month:02d} LAST UNL\n"
                   f"MT BRIGHTWATER 40K 2019 OPEN NOLA {o[2].day:02d}/{o[2].month:02d} LAST ULSD\n")
        return hdr + body + poslist + "\n" + SIGNATURES[1] + DISCLAIMER
    if variant == 2:  # quoted earlier offer below the recap
        old = fx["freight"]["value"] * 1.04 if fx["freight"]["basis"] == "WS" else fx["freight"]["value"] * 1.05
        quoted = ("\n\n> -----Original Message-----\n> OWNERS OFFER: "
                  f"{'WS ' + format(round(old * 2) / 2, 'g') if fx['freight']['basis'] == 'WS' else 'USD ' + money(round(old, -3)) + ' LUMPSUM'}"
                  " / DEM USD 99,000 PDPR / OTHERWISE AS LAST\n> PLS REVERT\n")
        return hdr + body + SIGNATURES[2] + quoted
    if variant == 3:  # chat-style paste with timestamps
        lines = body.strip().splitlines()
        stamped = "\n".join(f"[17:{40 + i // 6:02d}] Fairlead Brokers: {l}" if l else "" for i, l in enumerate(lines))
        return "[17:38] Ops Desk: any update on the recap?\n" + stamped + "\n[17:47] Ops Desk: tks, noted\n"
    # variant 4: html-ish leftovers
    html = body.replace("\n", "<br>\n")
    return hdr + "<div>" + html + "</div>\n" + SIGNATURES[0] + "&nbsp;\n" + DISCLAIMER


# ---------------------------------------------------------------- main

def write(sample_id, slice_name, text, fields, expect_flagged=None, note=None):
    with open(os.path.join(ROOT, "evals", "recaps", f"{sample_id}.txt"), "w") as f:
        f.write(text)
    exp = {"recap_id": sample_id, "slice": slice_name, "fields": fields,
           "expect_flagged": expect_flagged or []}
    if note:
        exp["note"] = note
    with open(os.path.join(ROOT, "evals", "expected", f"{sample_id}.json"), "w") as f:
        json.dump(exp, f, indent=2)
        f.write("\n")


def main():
    n = 0
    # 1. clean product tankers: 10
    for i in range(10):
        fx = build_fixture(RNG, "cpp", n)
        write(f"cpp-{i + 1:02d}", "clean_cpp", render_block(fx, RNG), fx)
        n += 1
    # 2. dirty tankers: 10
    for i in range(10):
        fx = build_fixture(RNG, "dirty", n)
        write(f"dpp-{i + 1:02d}", "dirty_crude_dpp", render_block(fx, RNG), fx)
        n += 1
    # 3. shorthand one-liners: 8 (no IMO or owner in this style; one crosses the year end)
    for i in range(8):
        fd = dt.date(2026, 12, 21) if i == 7 else None
        fx = build_fixture(RNG, "cpp" if i % 2 == 0 else "dirty", n, fixture_date=fd)
        fx["special_clauses"] = []
        if RNG.random() < 0.5:  # one-liners often use a short charterer name; expect what is written
            fx["charterer"] = fx["charterer"].split()[0]
        if i == 7:
            fx["laycan"] = {"start": "2027-01-03", "end": "2027-01-05"}
        fx_expected = dict(fx, imo=None, owner=None)
        note = "Laycan year must roll to 2027 (fixed 21 Dec 2026, laycan 03-05 JAN)." if i == 7 else None
        write(f"short-{i + 1:02d}", "shorthand", render_oneliner(fx, RNG), fx_expected, note=note)
        n += 1
    # 4. missing or conflicting terms: 7
    missing_cases = [
        (["imo", "owner"], "IMO and owner not stated; both null, nothing flagged as both are non-critical."),
        (["demurrage"], "No demurrage stated; must be null and flagged."),
        (["laycan"], "No laycan stated; must be null and flagged."),
        (["cp_form", "commissions"], "CP form and commissions missing; null, non-critical."),
    ]
    critical = {"vessel_name", "charterer", "cargo", "load_ports", "discharge_ports", "laycan", "freight",
                "demurrage", "subjects"}
    for i, (omit, note) in enumerate(missing_cases):
        fx = build_fixture(RNG, "cpp" if i % 2 == 0 else "dirty", n)
        text = render_block(fx, RNG, omit=omit)
        exp = dict(fx)
        for f in omit:
            exp[f] = None
        write(f"gap-{i + 1:02d}", "missing_or_conflicting", text, exp,
              expect_flagged=[f for f in omit if f in critical], note=note)
        n += 1
    # conflicts: the same term stated twice with different values
    fx = build_fixture(RNG, "cpp", n)
    alt = fx["demurrage"]["rate_per_day"] + 2500
    text = render_block(fx, RNG, overrides={"extra_lines": [f"NB DEMURRAGE USD {money(alt)} PDPR AS PER OWNERS LAST"]})
    write("gap-05", "missing_or_conflicting", text, dict(fx, demurrage=None), expect_flagged=["demurrage"],
          note="Two different demurrage rates in one recap; must be null and flagged, never one picked silently.")
    n += 1
    fx = build_fixture(RNG, "dirty", n)
    ls = dt.date.fromisoformat(fx["laycan"]["start"]) + dt.timedelta(days=4)
    text = render_block(fx, RNG, overrides={"extra_lines": [f"LAYCAN AMENDED TO {ls.day:02d}-{ls.day + 1 if ls.day < 28 else ls.day:02d} {MONTHS[ls.month - 1]} ??"]})
    write("gap-06", "missing_or_conflicting", text, dict(fx, laycan=None), expect_flagged=["laycan"],
          note="Laycan stated, then 'amended' with a query mark; ambiguous, must be null and flagged.")
    n += 1
    fx = build_fixture(RNG, "cpp", n)
    q2 = fx["cargo"]["quantity_mt"] + 3000
    text = render_block(fx, RNG, overrides={"extra_lines": [f"CARGO QTY: {q2:,} MT (CHRTS OPTION)"]})
    write("gap-07", "missing_or_conflicting", text, dict(fx, cargo=None), expect_flagged=["cargo"],
          note="Two different cargo quantities; must be null and flagged.")
    n += 1
    # 5. messy email: 5
    for i in range(5):
        fx = build_fixture(RNG, "cpp" if i % 2 == 0 else "dirty", n)
        write(f"email-{i + 1:02d}", "messy_email", render_email(fx, RNG, i), fx)
        n += 1
    print(f"wrote {n} samples")


if __name__ == "__main__":
    main()
