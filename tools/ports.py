"""Canonical port and area names, plus the aliases brokers commonly write.

The export schema stores canonical names. Both the sample generator and the
eval normalizer use this one table, so they cannot drift apart.
"""

CANONICAL = {
    # areas and ranges
    "USG": ["US GULF", "USGULF"],
    "USAC": ["US ATLANTIC COAST", "US EAST COAST", "USEC"],
    "UKC": ["UK CONT", "UK CONTINENT", "UK/CONT"],
    "MED": ["MEDITERRANEAN", "MEDIT"],
    "UKC-MED": ["UKC/MED", "UK CONT-MED", "UKCONT-MED"],
    "AG": ["ARABIAN GULF", "PG", "PERSIAN GULF", "MEG"],
    "WAF": ["WEST AFRICA", "W AFRICA"],
    "WCI": ["WEST COAST INDIA"],
    "FAR EAST": ["FEAST", "F.EAST"],
    "ECSA": ["EAST COAST SOUTH AMERICA"],
    "CARIBS": ["CARIBBEAN", "CARIBS/USG"],
    "BALTIC": ["BALTIC SEA"],
    # named ports
    "HOUSTON": ["HOU"],
    "CORPUS CHRISTI": ["CORPUS", "CC"],
    "NEW YORK": ["NY", "NYH", "NEW YORK HARBOR"],
    "ROTTERDAM": ["ROTT", "RDAM"],
    "ANTWERP": ["ANTW"],
    "AMSTERDAM": ["ADAM", "AMS"],
    "LE HAVRE": ["HAVRE"],
    "AUGUSTA": [],
    "SIDI KERIR": ["SIDI KRIR"],
    "CEYHAN": [],
    "PRIMORSK": [],
    "BONNY": [],
    "RAS TANURA": ["RT"],
    "JUBAIL": [],
    "FUJAIRAH": ["FUJ"],
    "SINGAPORE": ["SPORE", "SIN"],
    "ULSAN": [],
    "CHIBA": [],
    "SANTOS": [],
    "LAGOS": [],
}

_ALIAS_TO_CANON = {}
for canon, aliases in CANONICAL.items():
    _ALIAS_TO_CANON[canon] = canon
    for a in aliases:
        _ALIAS_TO_CANON[a] = canon


def canonical_port(name):
    """Return the canonical name for a port or area, or the cleaned input if unknown."""
    if name is None:
        return None
    cleaned = " ".join(str(name).upper().replace(".", " ").split())
    # strip common qualifiers such as "1/2 SP", "1-2 SB", "1SP"
    for q in ("1/2 SPS", "1/2 SP", "1-2 SP", "1/2 SB", "1-2 SB", "1 SP", "1SP", "1 SB", "1SB", "2 SP"):
        if cleaned.startswith(q + " "):
            cleaned = cleaned[len(q) + 1:]
            break
    return _ALIAS_TO_CANON.get(cleaned, cleaned)
