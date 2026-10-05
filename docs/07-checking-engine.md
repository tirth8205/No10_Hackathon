# 7. Checking engine

The checking engine compares a document with the requirements of a Schedule 1 paragraph and reports the result requirement by requirement. The same engine is used for the applicant pre-check, the solicitor check and the LAA's independent check.

## 7.1 Inputs

| Input | Source | Notes |
|---|---|---|
| Document | Upload | PDF, photo or email. Text is extracted, with text recognition for scans and photos |
| Applicant name | Case record | Used to check the evidence is about the right person |
| Other party (B) name | Case record | Used to check the evidence names the right person |
| Application date | Case record | Used for date-dependent rules (paragraphs 1, 3, 9, 20) |
| Work type | Case record | Controlled Work, Licensed Work or not yet known |
| Claimed paragraph | Solicitor, optional | If not given, the engine suggests one |
| Requirements | Rules file | One entry per paragraph, taken from the LAA guidance checklists |
| Rules version and guidance version | Rules file | Recorded on every result |

## 7.2 How a document is checked

1. **Read the document.** Extract the text. If the text is unreadable or incomplete, mark the affected requirements as unclear and set the outcome to refer.
2. **Identify the type and paragraph.** Decide what kind of document it is and which paragraph or paragraphs it could meet. If a paragraph is claimed, check that one first, then check whether the document meets a different paragraph better.
3. **Check each requirement.** For each requirement of the paragraph, look for the wording that meets it. Record:
   - the status: met, not met or unclear
   - the exact quote from the document
   - a short explanation in plain English
4. **Apply the rule that quotes come first.** A requirement can only be met if there is a quote from the document that supports it. The quote must appear word for word in the extracted text. This is checked automatically.
5. **Cross-check against the case.**
   - Names: does the applicant's name match? Does the named perpetrator match the other party?
   - Relationship: is the victim the applicant, or another person the paragraph allows?
   - Dates: for example, was a finding made before the application date?
6. **Check the language of judgements.** Words such as "might", "may possibly", "could be" or "it is possible that" in the judgement statement mean the judgement requirement is not met. The same words elsewhere in the letter do not count against it.
7. **Allow harmless defects.** Typos, unfilled template placeholders in parts that do not carry a requirement, and informal wording do not affect the result if the meaning is clear.
8. **Decide the document outcome.**
   - **pass:** every requirement met
   - **fail:** at least one requirement not met
   - **refer:** nothing is clearly not met, but at least one requirement is unclear, or a rule says a person must decide
9. **Decide the case outcome.**
   - **pass** if at least one document passes
   - otherwise **refer** if at least one document is refer
   - otherwise **fail**
10. **Write the outputs** for each audience (see 7.4).

## 7.3 When the outcome is refer

| Situation | Why a person must decide |
|---|---|
| Paragraph 21 (economic abuse) | The decision is the Director's discretion |
| Unreadable text | The engine cannot see the wording |
| No English translation | A translation and the original are both needed |
| Name mismatch | Identity must be confirmed |
| Missing registration number in a health professional email | The author's status cannot be confirmed |
| A DAPN apparently from outside the pilot areas | The notice needs verifying |
| Expert report without stated qualifications | Expert status cannot be confirmed |
| Solicitor and LAA checks disagree | A person should review the difference |

## 7.4 Outputs

| Audience | What they get |
|---|---|
| Applicant | One plain-language message (see [04 User flows](04-user-flows.md), section 4.13) |
| Solicitor | Matched paragraph, requirement checklist with quotes, flags, suggested paragraph if different, drafted follow-up request |
| Caseworker | Same checklist on the submitted pack, quotes highlighted in the document, flags, comparison with the solicitor's check, drafted return message if needed |

### Result format

```json
{
  "doc_id": "D1",
  "claimed_para": "18",
  "matched_para": "18",
  "outcome": "fail",
  "reason": "No perpetrator is named, so the refusal cannot be linked to abuse by the other party.",
  "recategorise_to": null,
  "elements": {
    "organisation_identified": {"status": "met", "quote": "Domestic Abuse Support Officer, New Pathways Support Trust", "explanation": "The organisation is named."},
    "perpetrator_named": {"status": "not_met", "quote": null, "explanation": "No perpetrator is named anywhere in the letter."},
    "victim_named": {"status": "met", "quote": "Name of applicant: Hannah Shah", "explanation": "Matches the applicant."},
    "refusal_date": {"status": "met", "quote": "was refused admission to a refuge on 15 September 2026", "explanation": "Date given."},
    "sought_because_of_abuse_by_other_party": {"status": "unclear", "quote": "sought admission to a refuge because of allegations of domestic abuse", "explanation": "Abuse is mentioned but not attributed to anyone."}
  },
  "flags": [],
  "rules_version": "schedule1-v15-2026-06-15",
  "checked_at": "2026-10-06T09:42:00Z"
}
```

The test data uses the same element keys, so results can be compared with expected answers directly.

## 7.5 How the AI model is kept in check

- **Fixed requirements.** The model checks against a fixed list of requirements per paragraph, held in a rules file taken from the LAA guidance. It is not asked to recall the rules.
- **Quotes or nothing.** Every "met" must carry a quote that appears in the document, and this is verified in code. A requirement without a verifiable quote cannot be met.
- **Rules in code where possible.** Date comparisons, name matching against the case record, which paragraphs allow another victim, and the case-level outcome are calculated in code, not by the model.
- **Versioned results.** Every result records the rules version and guidance version.
- **Independent second check.** The LAA runs its own check on the submitted pack, and any difference from the solicitor's check is flagged.
- **People decide.** No result approves or refuses anything by itself.

## 7.6 Limits

- It does not confirm that a document is genuine. Registration checks and calls to the police remain manual.
- It does not assess means or merits.
- It can be wrong. Accuracy is measured against labelled test data (see [10 Test data and evaluation](10-test-data-and-evaluation.md)), and results are monitored in use through the caseworker decision log.
