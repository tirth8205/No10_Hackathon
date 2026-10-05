# Results

Model `gpt-5.4`, 3 votes per element, rules `schedule1-v15-2026-06-15`. Final runs on 5 October 2026 with the cache off, so every vote is a genuine, separate model call. Every "included" result carries a quote that code verified word for word in the document.

| Set | What it is | Documents | Agreement | False approvals | False rejections | To caseworker | Element accuracy |
|---|---|---|---|---|---|---|---|
| Synthetic | Labelled by construction from the guidance, all 22 paragraphs. Used for tuning. | 146 | **100%** | **0** | **0** | 8.2% | 93.3% |
| Unseen style | 35 synthetic cases rewritten by the model in registers the rules never saw (informal email, bullets, non-native English, padding, reordered). Generated after tuning. | 35 | **100%** | **0** | **0** | 8.6% | 95.3% |
| MoJ gold | The 12 real example letters from MoJ's pack (7 accepted, 5 rejected). Held out. | 12 | **91.7%** (11/12) | **0** | **1** (the unsigned sample letter) | 0% | 96.9% |
| MoJ gold as PDFs | The same 12 letters as files: a digital PDF and a scanned (image-only) PDF of each, through the full upload path (PDF text layer or model transcription of the scan). Held out. | 24 | **100%** (24/24) | **0** | **0** | 0% | 100% |

MoJ's success criteria: agree with expert assessors in at least 90 to 95% of cases, reliably identify incomplete or unclear evidence, very low false approval and false rejection rates. Met on all three sets. A false approval would put an ineligible application through; there were none. The one false rejection is discussed below.

## How the runs were done

Tuning used the synthetic set only. The first full 3-vote synthetic run scored 98.6%; its only misses were passed letters sent to a caseworker because the model's quote stitched two non-adjacent passages (for example a header line and a finding) and the quote verifier rejected it. The verifier was changed to accept a quote fragment by fragment when every fragment is verbatim (`quote_multi_span`) and to keep header lines such as "Applicant: Jane Doe" whole. The paragraph 9 rule was clarified in the same way as paragraphs 1 to 5 (the victim's relationship with B is established by the application when the victim is the applicant). No other rule or prompt changed after the first run.

The unseen-style set was generated after tuning.

An external review then found that the three votes of an assessment shared one cache key, so a replayed run served the same recorded answer three times: earlier replayed figures were in effect single-vote figures. The cache key now includes the vote index, and the table above comes from a final run with the cache off entirely (every vote a separate live call). Over the day the gold set was run four times; the result was 11/12 every time.

## The misses

- **Synthetic and unseen style:** none in the final run.
- **Gold (1 of 12):** MoJ's accepted paragraph 11 letter. The sample text carries no signature, profession or registration number, so the author cannot be identified from the document; a real letter would be on the practice's letterhead. In earlier runs the model marked the author element *unclear* (sent to a caseworker); in the final run all three votes marked it *missing* (needs a change), which counts as a false rejection. The rule already says to use "unclear" when the author cannot be identified; the wording has not been tuned on this held-out letter. Either way the letter is not passed without a person seeing it.

## The gold letters as files

The 24 PDFs were made from the gold letters with `scripts/make_gold_pdfs.py`: 12 with a text layer (read with pypdf) and 12 rendered to images only (sent to the model to transcribe, then checked like any other text). All 24 verdicts matched the labels, including the paragraph 11 letter that misses in the text-only run: the PDF rendering puts the practice name and the signature block on the page, so the author can be identified. Median 28 seconds per PDF (transcription adds a model call for the scans).

## Where the model and the labels disagree on elements but not verdicts

When a document fails for one reason (an incident log with no caution, a conviction for a drugs offence), the synthetic labels mark the other elements "met" while the model often marks them "missing" too (no victim in a drugs caution, no perpetrator in an incident log). Both readings are defensible; the verdict is the same. This is most of the gap between 91% element accuracy and 99% agreement.

## Cost of caution

Routing to a caseworker is the engine's answer when the document does not say enough. Rates of 8 to 10% include the paragraph 21 cases (economic abuse, always a person's decision) and the cross-cutting cases built to need a human (name mismatch, unreadable scan, untranslated letter).

## Latency

Median 20 seconds per document in the final live runs (classification plus three parallel assessments). The demo runs from the recorded cache.

## Reproduce

```bash
.venv/bin/python -m eval.run_eval --set synthetic --votes 3 --cache off --name syn-v3-live
.venv/bin/python -m eval.style_shift --n 42 && .venv/bin/python -m eval.run_eval --set style --votes 3 --cache off --name style-v3-live
.venv/bin/python -m eval.run_eval --set gold --votes 3 --cache off --name gold-v3-live
.venv/bin/python -m eval.run_eval --set gold-pdf --votes 3 --cache off --name gold-pdf-v3-live
```

Per-case detail: `eval/results/<name>.json`; disagreements from the last run: `eval/results/failures.md`.
