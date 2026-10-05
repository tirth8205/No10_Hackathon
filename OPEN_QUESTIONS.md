# Open questions for MoJ and the LAA

Things the rules or test labels assume that an expert should confirm. Each affects how the engine decides.

| # | Question | Why it matters | Current behaviour |
|---|---|---|---|
| 1 | Paragraph 14: why was the IDVA letter saying "we provided ... support" rejected when "I am providing" was accepted? The regulation allows "are providing, or have provided". Is it the tense, or "we" rather than the IDVA personally? | Decides how `confirms_support` is judged for IDVA letters | A letter that does not show the IDVA personally confirming support is marked **missing** (test label), so it needs a change |
| 2 | Paragraph 10: a Cafcass or Cafcass Cymru report is itself an expert report (guidance 2.50). Does it still need the adviser's qualifications stated? | The synthetic set expects a Cafcass report with no stated qualifications to go to a caseworker | `expert_identity_and_qualifications` → **unclear** (caseworker check), not missing |
| 3 | Paragraph 17: more examples of what caseworkers accept as "specific matters relied on". "Victim testimony and referral" was rejected; how much description is enough? | The most judgement-heavy element in the highest-volume paragraph (43% of applications) | Source-only phrases are missing; any description of what happened is included |
| 4 | Paragraphs 3 and 4: where the victim is the applicant, must the document restate the family relationship with B, or is the application enough? | Clean letters in the test set do not restate it | Applicant as victim → included; another named victim with no stated relationship → unclear |
| 5 | Paragraph 6A: has the DAPN pilot area list (Greater Manchester; Bromley, Croydon, Sutton; Cleveland; North Wales) changed since the guidance was published? | A notice from outside the pilot is referred for verification | Non-pilot force → **unclear** |
| 6 | Name mismatches: when the name on the evidence differs slightly from the application (typo), does the LAA return the application or accept it with confirmation of identity? | Decides needs_caseworker vs needs_change | Near miss → caseworker check; different person → needs a change |
| 7 | Evidence not in English: is a translation plus the original always required, and is this a return or a refusal? | Decides the verdict for overseas letters | Non-English → caseworker check, with a fix asking for original + translation |
| 8 | Would the LAA accept a provider's checklist attached to a submission, or prefer to run only its own check? | Shapes link 2 | Both: the submission carries the provider's frozen checklist and the LAA runs an independent check; differences are shown |
| 9 | How are Controlled Work evidence files audited today? | Format of the audit-ready file note | Submission snapshot (paragraph, checklist, quotes, rules version, time) serves as the note |
| 10 | What retention applies to case records, submissions and audit logs? | Data protection before any live use | Documents are held in memory only (TTL); verdicts, quotes and audit kept in SQLite for the demo |
| 11 | Was the rest of the promised data pack available (application form, police reports, injunctions, MARAC referrals, expired or poor-quality evidence, caseworker feedback)? | Testing paragraphs 1 to 10 against real documents | Synthetic cases only |
| 12 | Can LAA staff spot-check a sample of the synthetic labels? | The labels reflect our reading of the guidance | Not yet checked |
| 13 | MoJ's accepted paragraph 11 example has no signature, profession or registration number in the text. Was the real letter on practice letterhead? | The engine sends an unsigned health letter to a caseworker rather than passing it; this is the one gold-set disagreement | Kept: `appropriate_health_professional` → unclear when the author cannot be identified from the document |

Source notes from the guidance (v15, 15 June 2026) found while writing the rules:
- Section numbers in our first scaffold were wrong for most paragraphs; `rules/*.yaml` now carries the corrected `guidance_ref`.
- Paragraph 7: set-aside is only fatal for without-notice orders (2.41–2.42); an expired order still counts.
- Paragraph 8: only a domestic-abuse-related cross-undertaking disqualifies (2.44); a schooling undertaking does not.
- Paragraph 9: a finding made after the application still counts alongside other evidence (2.47).
- gov.uk sample letters exist only for paragraphs 11 to 19.
