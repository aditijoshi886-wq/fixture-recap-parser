"""Run the AI parser over a folder of recaps and write one prediction per recap.

Usage:
    ANTHROPIC_API_KEY=... python3 parser/run.py evals/recaps out/ai-v1 [--model claude-sonnet-5-5] [--prompt v1]

Then score it:
    python3 evals/run_eval.py --predictions out/ai-v1
"""

import argparse
import glob
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from extract import DEFAULT_MODEL, PROMPT_VERSION, extract  # noqa: E402
from validate import validate  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--prompt", default=PROMPT_VERSION)
    args = ap.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set. Add it as a repository secret (see README) or export it locally.")
    import anthropic  # imported here so the offline tests don't need the package

    client = anthropic.Anthropic(max_retries=4)
    os.makedirs(args.dst, exist_ok=True)
    paths = sorted(glob.glob(os.path.join(args.src, "*.txt")))
    tokens_in = tokens_out = 0
    started = time.time()
    for i, path in enumerate(paths, 1):
        rid = os.path.splitext(os.path.basename(path))[0]
        recap = open(path).read()
        t0 = time.time()
        try:
            pred = extract(recap, client, model=args.model, version=args.prompt)
        except Exception as e:  # one bad call should not sink the whole run
            print(f"[{i}/{len(paths)}] {rid}: FAILED {type(e).__name__}: {e}")
            continue
        flagged = validate(pred["fields"], recap)
        pred.update({"recap_id": rid, "seconds": round(time.time() - t0, 2)})
        tokens_in += pred["usage"]["input_tokens"] or 0
        tokens_out += pred["usage"]["output_tokens"] or 0
        with open(os.path.join(args.dst, f"{rid}.json"), "w") as f:
            json.dump(pred, f, indent=2)
        print(f"[{i}/{len(paths)}] {rid}: {pred['seconds']}s, flagged {len(flagged)}: {', '.join(flagged) or '-'}")
    print(f"done in {time.time() - started:.0f}s · {tokens_in:,} input tokens · {tokens_out:,} output tokens")


if __name__ == "__main__":
    main()
