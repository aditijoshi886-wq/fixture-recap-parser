# Decision log

Newest first. Each entry: what was decided, why, and what it rules out.

| Date | Decision | Why | Consequence |
| --- | --- | --- | --- |
| 2026-10-16 | One-liner samples expect the charterer name **as written** (e.g. `SUNMERE`, not `SUNMERE ENERGY`). | The first draft of the generator expected the full legal name even when the text only had the short form, an answer no parser could reach. Caught in review of the generated samples. | The eval measures extraction, not guessing. Mapping short names to legal entities is a separate, later feature. |
| 2026-10-16 | Position-list noise in email samples uses dates relative to the fixture date. | The first draft had October open dates in a December email, which a domain reader would spot at once. | Samples stay plausible to a tanker operator. |
| 2026-10-16 | Conflicting terms (two demurrage rates, two quantities, a laycan "amended ??") must come back **null and flagged**. | Picking one silently is the most expensive failure: it looks correct and reaches the invoice. | Measured by flag recall and the "wrong and not flagged" rate. The rules baseline fails all three cases. |
| 2026-10-16 | Expected answers are generated from structured fixtures, then the text is rendered from them. | Correct by construction, reproducible, and easy to extend to new slices. | Template text is more regular than real broker traffic, so scores on clean slices run high. Real anonymized formats are planned for week 4. |
| 2026-10-16 | Synthetic data only. All vessels, companies and IMO numbers are invented; IMO numbers still pass the check-digit rule. | Real recaps are commercially confidential. | The repo can be public. |
| 2026-10-16 | **Scope: tanker only** for the MVP (crude, DPP, CPP). Dry bulk is a later release. | Tanker recaps share one vocabulary (WS rates, SHINC, PDPR, MOLOO), so 40 samples cover the format well. | Eval set is 20 CPP/DPP block recaps + 20 harder cases. |
| 2026-10-16 | **Export: a generic JSON schema** documented in this repo, not an IMOS-specific format. | Keeps the parser independent of any one vendor's import. A mapping layer can be added per target system. | `schema/fixture.schema.json` is the contract. |
| 2026-10-16 | **Delivery: a hosted demo page plus this public repo.** | The page lets a reviewer try it in 30 seconds. The repo shows the PRD, evals and decisions behind it. | Both are maintained from the same eval set. |
| 2026-10-15 | The model extracts; code validates. Critical fields always pass deterministic checks. | An LLM can be confidently wrong; validation rules cannot be talked out of a bad laycan. | Validation rules are specified in the PRD (FR8 to FR12). |
