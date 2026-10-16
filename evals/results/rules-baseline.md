# Eval report: baseline

Run 2026-10-16 · prompt version: rules-baseline · 40 recaps · 640 fields

| Metric | Result | Target | |
| --- | --- | --- | --- |
| Field accuracy | 79.7% | ≥ 95% | FAIL |
| Critical-field accuracy | 75.0% | ≥ 98% | FAIL |
| Wrong and not flagged | 1.2% (8) | ≤ 1% | FAIL |
| Flag recall (expected flags raised) | 40% | 100% | FAIL |
| Share of fields flagged for review | 25.3% | (lower saves review time) | |

## Accuracy by slice

| Slice | Recaps | Field accuracy | Critical accuracy |
| --- | --- | --- | --- |
| clean_cpp | 10 | 98.8% | 97.8% |
| dirty_crude_dpp | 10 | 99.4% | 98.9% |
| messy_email | 5 | 75.0% | 73.3% |
| missing_or_conflicting | 7 | 97.3% | 95.2% |
| shorthand | 8 | 18.8% | 0.0% |

## Accuracy by field

| Field | Critical | Accuracy | Silent errors |
| --- | --- | --- | --- |
| vessel_name | yes | 78% | 0 |
| imo |  | 100% | 0 |
| charterer | yes | 75% | 1 |
| owner |  | 95% | 1 |
| cargo | yes | 75% | 1 |
| load_ports | yes | 75% | 1 |
| discharge_ports | yes | 75% | 1 |
| laycan | yes | 68% | 1 |
| freight | yes | 78% | 0 |
| demurrage | yes | 75% | 1 |
| laytime |  | 78% | 0 |
| commissions |  | 78% | 0 |
| cp_form |  | 75% | 1 |
| subjects | yes | 78% | 0 |
| fixture_date |  | 80% | 0 |
| special_clauses |  | 95% | 0 |

## Silent errors (wrong and marked high confidence)

| Recap | Field | Expected | Got |
| --- | --- | --- | --- |
| email-05 | charterer | `"VERIDIAN REFINING"` | `"VERIDIAN REFINING<BR>"` |
| email-05 | owner | `"AEGEAN CREST SHIPPING"` | `"AEGEAN CREST SHIPPING<BR>"` |
| email-05 | load_ports | `["UKC"]` | `["UK CONT<BR>"]` |
| email-05 | discharge_ports | `["USAC"]` | `["USAC<BR>"]` |
| email-05 | cp_form | `"BPVOY4"` | `"BPVOY4<BR>"` |
| gap-05 | demurrage | `null` | `{"rate_per_day": 32500.0, "currency": "USD", "pro_rata": true}` |
| gap-06 | laycan | `null` | `{"start": "2026-10-26", "end": "2026-10-28"}` |
| gap-07 | cargo | `null` | `{"grade": "CPP (UNL GASOLINE)", "quantity_mt": 30000.0, "tolerance_pct": 10.0, "tolerance_option": "MOLOO"}` |
