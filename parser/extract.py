"""AI extraction: one recap in, one prediction out.

The model is forced to answer through a single tool whose input schema is built
from schema/fixture.schema.json, so every response parses and every field
carries a value, a confidence level and the source words it came from.
"""

import copy
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from ports import CANONICAL  # noqa: E402

FIELDS = ["vessel_name", "imo", "charterer", "owner", "cargo", "load_ports", "discharge_ports", "laycan",
          "freight", "demurrage", "laytime", "commissions", "cp_form", "subjects", "fixture_date",
          "special_clauses"]
DEFAULT_MODEL = os.environ.get("FRP_MODEL", "claude-sonnet-5-5")
PROMPT_VERSION = os.environ.get("FRP_PROMPT", "v1")
MAX_CHARS = 10_000  # FR1
TOOL_NAME = "record_fixture"


def _strip(schema):
    """Drop keywords the tool schema does not need (ids, descriptions stay)."""
    s = copy.deepcopy(schema)
    for k in ("$schema", "$id", "format"):
        s.pop(k, None)
    for v in s.get("properties", {}).values():
        if isinstance(v, dict):
            v.pop("format", None)
            for sub in v.get("properties", {}).values():
                sub.pop("format", None)
    return s


def tool_schema():
    fixture = _strip(json.load(open(os.path.join(ROOT, "schema", "fixture.schema.json"))))
    props = {}
    for name in FIELDS:
        value_schema = fixture["properties"][name]
        props[name] = {
            "type": "object",
            "additionalProperties": False,
            "required": ["value", "confidence", "source"],
            "properties": {
                "value": value_schema,
                "confidence": {"enum": ["high", "medium", "low"]},
                "source": {"type": ["string", "null"],
                           "description": "Exact words from the recap this value came from; null when value is null."},
            },
        }
    return {
        "name": TOOL_NAME,
        "description": "Record the fixture terms extracted from the recap.",
        "input_schema": {"type": "object", "additionalProperties": False, "required": FIELDS, "properties": props},
    }


def system_prompt(version=PROMPT_VERSION):
    text = open(os.path.join(ROOT, "parser", "prompts", f"{version}.md")).read()
    return text.replace("{canonical_ports}", ", ".join(CANONICAL))


class RecapTooLong(ValueError):
    pass


def extract(recap, client, model=DEFAULT_MODEL, version=PROMPT_VERSION):
    """Return {"fields": {...}, "model": ..., "prompt_version": ...} for one recap."""
    if len(recap) > MAX_CHARS:
        raise RecapTooLong(f"Recap is {len(recap):,} characters; the limit is {MAX_CHARS:,}.")
    tool = tool_schema()
    resp = client.messages.create(
        model=model,
        max_tokens=4000,
        system=system_prompt(version),
        tools=[tool],
        tool_choice={"type": "tool", "name": TOOL_NAME},
        messages=[{"role": "user", "content": f"<recap>\n{recap}\n</recap>"}],
    )
    block = next((b for b in resp.content if getattr(b, "type", None) == "tool_use"), None)
    if block is None:
        raise RuntimeError("Model did not call the record_fixture tool.")
    raw = block.input if isinstance(block.input, dict) else json.loads(block.input)
    fields = {}
    for name in FIELDS:
        f = raw.get(name) or {}
        fields[name] = {"value": f.get("value"), "confidence": f.get("confidence", "low"),
                        "source": f.get("source"), "messages": []}
    usage = getattr(resp, "usage", None)
    return {
        "fields": fields,
        "model": model,
        "prompt_version": version,
        "usage": {"input_tokens": getattr(usage, "input_tokens", None),
                  "output_tokens": getattr(usage, "output_tokens", None)},
    }
