# Backend: engine + API

Checks domestic abuse evidence for legal aid against Schedule 1 (all 22 paragraphs). Rules are YAML, the model sits behind one adapter (OpenAI `gpt-5.4` by default; Claude and an offline stub also available), every "included" carries a quote that code verifies, and a person always decides.

## Run

```bash
uv sync                                   # Python 3.12+, creates .venv
cp .env.example .env                      # add OPENAI_API_KEY (GC_LLM=openai, GC_OPENAI_MODEL=gpt-5.4) or ANTHROPIC_API_KEY (GC_LLM=anthropic)
.venv/bin/uvicorn app.main:app --reload   # API on http://localhost:8000, OpenAPI at /docs
.venv/bin/python -m demo.seed_demo --api http://localhost:8000     # demo cases
.venv/bin/python -m pytest -q
```

No key? Set `GC_LLM=offline`: a keyword stub runs so the UI still works. `GC_CACHE=on` records model answers under `demo/cache/`; `GC_CACHE=replay` serves them back so the demo never waits on the network.

CLI: `.venv/bin/python -m engine.cli check letter.pdf --applicant "Jane Doe" --other-party "John Doe" --para 17`

Eval: `.venv/bin/python -m eval.run_eval --set synthetic` (143 cases); `--set gold` is the 12 MoJ letters, run once at the end. Results land in `eval/results/latest.json` and `failures.md`; `/api/scoreboard` serves the summary.

## Vocabulary (frontend contract)

| Thing | Values |
|---|---|
| Element status | `included` · `missing` · `unclear` |
| Document verdict | `meets` · `needs_change` · `needs_caseworker` · `not_prescribed` |
| Case verdict | `meets` · `needs_change` · `needs_caseworker` · `no_evidence_yet` |
| Flags | `quote_not_found` `quote_fuzzy_match` `vote_disagreement` `hedge` `injection` `non_english` `name_mismatch` `victim_name_mismatch` `classification_low_confidence` `model_refusal` `illegible` `unfilled_placeholder` |

Suggested labels: Meets the requirements (green) · Needs a change (yellow) · Needs a caseworker check (blue) · Not an accepted evidence type (grey). Never show "rejected", "fail" or "approved" to the applicant.

## Document result (what every check returns)

```json
{
  "document_id": "…", "filename": "refuge.txt", "verdict": "needs_change",
  "rule_id": "sch1_p18_refuge_refusal", "paragraph": "18", "rule_name": "…", "legal_ref": "…",
  "claimed_rule_id": "sch1_p18_refuge_refusal", "recategorise_to": null,
  "classification": {"rule_id": "…", "confidence": "high", "document_kind": "letter", "author_name": "John Smith", "author_org": "Women's Aid", "language": "en", "rationale": "…"},
  "parties": {"victim_name": "Jane Doe", "other_party_name": null, "dates_mentioned": ["28th September 2026"]},
  "elements": [
    {"element_id": "perpetrator_named", "label": "B named", "status": "missing", "quote": null, "quote_verified": false,
     "votes": {"included": 0, "missing": 3, "unclear": 0}, "reasoning": "…", "fix": "Name the perpetrator…"}
  ],
  "flags": [], "provider_summary": "Paragraph 18, …: 4 of 5 requirements included. Missing: B named.",
  "client_message": "This document may need a little more detail. Your solicitor will help you get it.",
  "request_letter": "Dear John Smith, …", "rules_version": "schedule1-v15-2026-06-15", "model": "claude-opus-5-5", "votes": 3, "latency_ms": 9120
}
```

`recategorise_to` is set when the provider claimed a paragraph the letter does not meet but the classifier found one it does (e.g. a support-organisation letter submitted as an IDVA letter).

## Endpoints

Link 1 (applicant ↔ solicitor), all under `/api`:

| Method | Path | Notes |
|---|---|---|
| GET | `/health`, `/rules`, `/scoreboard`, `/audit` | `POST /rules/reload` hot-reloads the YAML (extensibility demo) |
| POST | `/cases` | `{applicant_name, other_party_name, case_type, work_type, safe_contact_*}` → case with neutral `ref` like `LA-7K4-29Q` |
| GET / PATCH | `/cases`, `/cases/{id}` | `{id}` accepts the id or the ref. Full case = documents + events + requests + submissions |
| GET | `/cases/{id}/status` | Small payload for 2-second polling: case verdict, per-document status/verdict/summary |
| POST | `/cases/{id}/documents` (multipart) · `/cases/{id}/documents/text` (JSON) | Fields: `file`/`text`, `claimed_para`, `uploaded_by` (`client`/`provider`), `replaces_document_id` (new version). Returns 202; check runs in the background |
| GET | `/cases/{id}/documents/{doc}?highlight=true` | Result plus `highlights: [{element_id, start, end}]` offsets into the text for `<mark>` |
| GET | `/cases/{id}/documents/{doc}/text` | Document text while still held in memory (TTL `GC_DOC_TTL_MIN`) |
| POST | `/cases/{id}/documents/{doc}/recheck?claimed_para=17` | Re-run under a different paragraph (the "switch paragraph" button) |
| GET | `/cases/{id}/documents/{doc}/request-letter` | Drafted letter to the author (text) |
| POST | `/cases/{id}/documents/{doc}/requests` → `/requests/{rid}/sent` | Record that the solicitor sent it; posts a tracker event |
| GET / POST | `/cases/{id}/events?view=applicant\|solicitor` | Tracker. Applicant view only returns `visible_to_applicant` events in applicant wording |
| POST | `/events/{eid}/release` | Solicitor releases an LAA event to the applicant, optionally with their own wording |
| POST / DELETE | `/cases/{id}/client-link` | One-time link token (7 days). `GET /client/{token}` is the applicant view: first name, plain messages, no legal reasoning. `POST /client/{token}/upload` |
| POST | `/cases/{id}/purge` | Drops document bytes/text from memory; results and audit stay |

Link 2 (solicitor ↔ LAA):

| Method | Path | Notes |
|---|---|---|
| POST | `/cases/{id}/submissions` | `{document_ids, notes, submit_anyway_reason, resubmission_of}`. Freezes the chosen document versions + checklists into `snapshot`; issues `laa_ref`. Returns 422 with a warning if nothing meets and no reason is given. Never blocks otherwise. Kicks off the LAA's independent re-check |
| GET | `/submissions?status=submitted` | Caseworker queue, sorted meets → needs_caseworker → needs_change, then age. Includes `differences` count |
| GET | `/submissions/{id}` | Snapshot, text + highlights, `laa_check`, `differences` (element-level diff provider vs LAA), drafted `return_note` |
| GET | `/submissions/{id}/return-note` | Text |
| POST | `/submissions/{id}/decision` | `{action: accept\|return\|refer, note, caseworker}`. Logs whether the caseworker agreed with the tool. Posts a hidden tracker event the solicitor can release |

## Layout

```
rules/        _gateway_da.yaml + one YAML per paragraph (ids match the test data element keys)
engine/       models · rules · ingest · prompts · llm (anthropic/offline/cache) · verify · aggregate · outputs · pipeline · cli
app/          main.py (FastAPI JSON API) · store.py (SQLite + in-memory document store)
eval/         run_eval.py; results/
data/         synthetic_cases.json (143, regenerate with scripts/generate_da_evidence.py) · moj_gold_cases.json (12, held out)
demo/         seed_demo.py · files/ · cache/
```
