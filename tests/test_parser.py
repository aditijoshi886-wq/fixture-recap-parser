"""Offline tests for the AI parser: a fake client stands in for the API.

Run:  python3 tests/test_parser.py
"""

import copy
import json
import os
import sys
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "parser"))
from extract import FIELDS, RecapTooLong, extract, system_prompt, tool_schema  # noqa: E402
from validate import imo_valid, validate  # noqa: E402

RECAP = open(os.path.join(ROOT, "evals", "recaps", "cpp-01.txt")).read()
EXPECTED = json.load(open(os.path.join(ROOT, "evals", "expected", "cpp-01.json")))["fields"]


def _answer(fields=None):
    """A tool call that returns the expected answer, with real source snippets."""
    src = {
        "vessel_name": EXPECTED["vessel_name"], "imo": EXPECTED["imo"], "charterer": EXPECTED["charterer"],
        "owner": EXPECTED["owner"], "cargo": "CARGO", "load_ports": "LOAD", "discharge_ports": "DISCH",
        "laycan": "LAYCAN", "freight": "FRT", "demurrage": "DEM", "laytime": "LAYTIME", "commissions": "COMMS",
        "cp_form": EXPECTED["cp_form"], "subjects": "SUBJECTS", "fixture_date": "CP DD", "special_clauses": "OTHER",
    }
    out = {}
    for name in FIELDS:
        v = copy.deepcopy(EXPECTED[name])
        out[name] = {"value": v, "confidence": "high", "source": src[name] if v not in (None, []) else None}
    if fields:
        for k, v in fields.items():
            out[k].update(v)
    return out


class FakeClient:
    def __init__(self, answer):
        self.answer = answer
        self.calls = []
        self.messages = self

    def create(self, **kw):
        self.calls.append(kw)
        block = SimpleNamespace(type="tool_use", name="record_fixture", input=self.answer)
        return SimpleNamespace(content=[block], usage=SimpleNamespace(input_tokens=1000, output_tokens=500))


def test_tool_schema_covers_every_field():
    schema = tool_schema()["input_schema"]
    assert schema["required"] == FIELDS
    for name in FIELDS:
        assert set(schema["properties"][name]["required"]) == {"value", "confidence", "source"}


def test_prompt_lists_canonical_ports():
    p = system_prompt("v1")
    assert "{canonical_ports}" not in p and "UKC-MED" in p


def test_extract_forces_the_tool_and_parses_it():
    client = FakeClient(_answer())
    pred = extract(RECAP, client, model="test-model", version="v1")
    call = client.calls[0]
    assert call["tool_choice"] == {"type": "tool", "name": "record_fixture"}
    assert call["model"] == "test-model"
    assert pred["fields"]["vessel_name"]["value"] == EXPECTED["vessel_name"]
    assert pred["prompt_version"] == "v1"


def test_clean_extraction_is_not_flagged():
    pred = extract(RECAP, FakeClient(_answer()))
    flagged = validate(pred["fields"], RECAP)
    assert flagged == [], flagged


def test_invented_source_is_flagged():
    pred = extract(RECAP, FakeClient(_answer({"demurrage": {"source": "DEM USD 99,999 PDPR"}})))
    assert "demurrage" in validate(pred["fields"], RECAP)


def test_missing_critical_field_is_flagged():
    pred = extract(RECAP, FakeClient(_answer({"laycan": {"value": None, "source": None}})))
    assert "laycan" in validate(pred["fields"], RECAP)


def test_reversed_laycan_is_flagged_even_at_high_confidence():
    lc = EXPECTED["laycan"]
    pred = extract(RECAP, FakeClient(_answer({"laycan": {"value": {"start": lc["end"], "end": lc["start"]}}})))
    validate(pred["fields"], RECAP)
    assert any("before laycan start" in m for m in pred["fields"]["laycan"]["messages"])


def test_imo_check_digit():
    assert imo_valid(EXPECTED["imo"])
    bad = EXPECTED["imo"][:6] + str((int(EXPECTED["imo"][6]) + 1) % 10)
    assert not imo_valid(bad)


def test_ws_out_of_range_is_flagged():
    pred = extract(RECAP, FakeClient(_answer({"freight": {"value": {"basis": "WS", "value": 1400, "currency": None}}})))
    assert "freight" in validate(pred["fields"], RECAP)


def test_recap_over_limit_is_refused():
    try:
        extract("X" * 10_001, FakeClient(_answer()))
    except RecapTooLong as e:
        assert "10,000" in str(e)
    else:
        raise AssertionError("expected RecapTooLong")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
