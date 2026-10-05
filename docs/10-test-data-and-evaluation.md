# 10. Test data and evaluation

## 10.1 Data sets

| File | Cases | Purpose |
|---|---|---|
| `data/synthetic_cases.json` | 143 | Development and testing across all 22 evidence types |
| `data/moj_gold_cases.json` | 12 | MoJ's own examples, held back as the final test |

### Synthetic cases by outcome

| Expected outcome | Cases |
|---|---|
| pass | 67 |
| fail | 64 |
| refer | 12 |

### Synthetic cases by category

| Category | Cases | What it is |
|---|---|---|
| valid | 44 | Two compliant documents per paragraph |
| valid_with_benign_defects | 22 | One compliant document per paragraph with typos or an unfilled placeholder. Should still pass |
| mutation | 66 | A compliant document with exactly one requirement broken |
| hard_negative_pass | 1 | Looks like a failure but is valid: an undertaking with a cross-undertaking about schooling |
| cross_cutting | 10 | Wrong paragraph claimed, name mismatch, long report, multi-document bundles, child as victim, unreadable scan, untranslated letter |

### Coverage by paragraph (excluding cross-cutting cases)

| Para | Total | Pass | Fail | Refer |
|---|---|---|---|---|
| 1 | 8 | 3 | 4 | 1 |
| 2 | 7 | 3 | 4 | 0 |
| 3 | 6 | 3 | 3 | 0 |
| 4 | 6 | 3 | 3 | 0 |
| 5 | 5 | 3 | 2 | 0 |
| 6 | 5 | 3 | 2 | 0 |
| 6A | 5 | 3 | 1 | 1 |
| 7 | 6 | 3 | 3 | 0 |
| 8 | 6 | 4 | 2 | 0 |
| 9 | 7 | 3 | 4 | 0 |
| 10 | 6 | 3 | 2 | 1 |
| 11 | 7 | 3 | 3 | 1 |
| 12 | 6 | 3 | 3 | 0 |
| 13 | 5 | 3 | 2 | 0 |
| 14 | 6 | 3 | 3 | 0 |
| 15 | 5 | 3 | 2 | 0 |
| 16 | 7 | 3 | 4 | 0 |
| 17 | 7 | 3 | 4 | 0 |
| 18 | 6 | 3 | 3 | 0 |
| 19 | 6 | 3 | 3 | 0 |
| 20 | 6 | 3 | 3 | 0 |
| 21 | 5 | 0 | 0 | 5 |

### MoJ cases

7 accepted and 5 rejected, covering paragraphs 11, 14, 17, 18 and 19. The overall labels are MoJ's. The requirement-level labels for the rejections are our reading, made by comparing each rejected letter with its accepted pair.

## 10.2 Case format

```json
{
  "id": "P17-vague_matters-01",
  "source": "synthetic",
  "category": "mutation",
  "application": {
    "applicant": "Olivia Begum",
    "other_party": "Liam Hughes",
    "relationship": "former partner",
    "child": "Zayn Hughes",
    "application_date": "2026-09-14",
    "proceedings": "Child arrangements order (Children Act 1989, section 8)"
  },
  "documents": [
    {
      "doc_id": "D1",
      "claimed_para": "17",
      "text": "...",
      "expected": {
        "outcome": "fail",
        "elements": {
          "specific_matters": {"description": "...", "status": "not_met"}
        },
        "reason": "...",
        "recategorise_to": null
      }
    }
  ],
  "expected_overall": "fail"
}
```

| Field | Meaning |
|---|---|
| `id` | `P<para>-<variant>-NN` for paragraph cases, `X-<name>` for cross-cutting, `MOJ-...` for MoJ cases |
| `category` | See the table above |
| `application` | Case details the engine checks against |
| `documents[].claimed_para` | The paragraph the evidence is submitted under |
| `documents[].expected.outcome` | pass, fail or refer for that document |
| `documents[].expected.elements` | Expected status per requirement: met, not_met or unclear |
| `documents[].expected.recategorise_to` | The paragraph the document actually meets, if different |
| `expected_overall` | Case outcome: pass if any document passes, otherwise refer if any refers, otherwise fail |

## 10.3 How labels are set

Labels are set when each case is built, not by reviewing outputs afterwards. A compliant document is written from the guidance checklist for its paragraph. A mutation changes exactly one requirement, so the expected result is known in advance. This also means the labels reflect our reading of the guidance. A sample should be checked by MoJ or LAA staff.

Regenerate or extend the set with:

```bash
python3 scripts/generate_da_evidence.py --out data/synthetic_cases.json
python3 scripts/generate_da_evidence.py --seed 7 --valid 4 --out data/extra_cases.json
```

## 10.4 Measures

| Measure | Definition | Target |
|---|---|---|
| Agreement | Share of cases where the service's case outcome matches the expected outcome | 90 to 95% or better (MoJ) |
| False approval rate | Cases expected fail or refer that the service marks pass, as a share of all expected fail or refer | As close to zero as possible |
| False rejection rate | Cases expected pass that the service marks fail, as a share of all expected pass | Very low |
| Refer rate | Share of cases marked refer | Kept low enough to save caseworker time |
| Requirement accuracy | Share of requirement statuses that match | Tracked per paragraph |
| Recategorisation accuracy | Share of wrong-paragraph cases where the right paragraph is suggested | Tracked |
| Quote validity | Share of "met" results whose quote appears word for word in the document | 100% (enforced in code) |

A false approval is the most serious error, because it puts an ineligible application through. Where the service is uncertain, it should refer rather than pass.

## 10.5 Method

1. Develop and tune against the synthetic cases.
2. Keep the MoJ cases aside. Run them once at the end and report the results as they are.
3. Report results per paragraph as well as overall, so weak areas are visible.
4. Review every disagreement and record whether the service or the label was wrong.

## 10.6 Limits of the test data

- Synthetic letters are cleaner and more regular than real ones.
- Most mutations break one requirement at a time. Real documents can have several problems.
- Text is provided directly, so text recognition on photos and scans is only lightly tested (`X-illegible_scan`).
- Labels are our interpretation of the guidance and need checking by LAA staff.
