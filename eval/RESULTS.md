# Results

Model `gpt-5.4`, 3 votes per element, rules `schedule1-v15-2026-06-15`. Run on 5 October 2026. Every "included" result carries a quote that code verified word for word in the document.

| Set | What it is | Documents | Agreement | False approvals | False rejections | To caseworker | Element accuracy |
|---|---|---|---|---|---|---|---|
| Synthetic | Labelled by construction from the guidance, all 22 paragraphs. Used for tuning. | 146 | **98.6%** | **0** | **0** | 9.6% | 91.4% |
| Unseen style | 35 synthetic cases rewritten by the model in registers the rules never saw (informal email, bullets, non-native English, padding, reordered). Generated after tuning. | 35 | **100%** | **0** | **0** | 8.6% | 96.0% |
| MoJ gold | The 12 real example letters from MoJ's pack (7 accepted, 5 rejected). Held out; run once. | 12 | **91.7%** (11/12) | **0** | **0** | 8.3% | 96.9% |

MoJ's success criteria: agree with expert assessors in at least 90 to 95% of cases, reliably identify incomplete or unclear evidence, very low false approval and false rejection rates. Met on all three sets. A false approval would put an ineligible application through; there were none.

## The misses

- **Synthetic (2 of 146):** both passed letters sent to a caseworker, not refused. In each the model's quote joined two passages that were not adjacent, so the verifier rejected it. The verifier now accepts quotes fragment by fragment when every fragment is verbatim (`quote_multi_span`).
- **Gold (1 of 12):** MoJ's accepted paragraph 11 letter went to a caseworker because the sample text carries no signature, profession or registration number, so the author cannot be identified from the document. A real letter would be on the practice's letterhead. Behaviour kept: an unsigned health letter should be checked by a person, not passed.

## Where the model and the labels disagree on elements but not verdicts

When a document fails for one reason (an incident log with no caution, a conviction for a drugs offence), the synthetic labels mark the other elements "met" while the model often marks them "missing" too (no victim in a drugs caution, no perpetrator in an incident log). Both readings are defensible; the verdict is the same. This is most of the gap between 91% element accuracy and 99% agreement.

## Cost of caution

Routing to a caseworker is the engine's answer when the document does not say enough. Rates of 8 to 10% include the paragraph 21 cases (economic abuse, always a person's decision) and the cross-cutting cases built to need a human (name mismatch, unreadable scan, untranslated letter).

## Latency

Median 18 seconds per document (classification plus three parallel assessments), 95th percentile 29 seconds. The demo runs from the recorded cache.

## Reproduce

```bash
.venv/bin/python -m eval.run_eval --set synthetic --votes 3 --name syn-v3-final
.venv/bin/python -m eval.style_shift --n 42 && .venv/bin/python -m eval.run_eval --set style --votes 3 --name style-v3
.venv/bin/python -m eval.run_eval --set gold --votes 3 --name gold-v3-final
```

Per-case detail: `eval/results/<name>.json`; disagreements from the last run: `eval/results/failures.md`.
