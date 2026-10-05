# 5. Use cases

Each use case lists the actors, trigger, starting conditions, main steps, alternatives, expected outcome, and the matching cases in the test data (`data/synthetic_cases.json` and `data/moj_gold_cases.json`).

---

## UC-01 Applicant has no evidence yet

| | |
|---|---|
| Actors | Applicant |
| Trigger | Applicant starts a case with no documents |
| Preconditions | Case reference created |
| Main flow | 1. Applicant answers the evidence finder questions. 2. Service lists the easiest routes, for example a GP letter (paragraph 11) and a support organisation letter (paragraph 17). 3. Each route shows who to ask, what to ask for and the GOV.UK template |
| Alternative | Applicant answers "no" to everything. Service explains that a solicitor can advise on other routes and how to find one |
| Outcome | Applicant knows which document to ask for and from whom |
| Test data | Demo only |

## UC-02 Health letter with a hedged judgement

| | |
|---|---|
| Actors | Applicant, solicitor, GP |
| Trigger | A GP letter says the condition "may possibly be consistent" with domestic abuse |
| Preconditions | Document uploaded |
| Main flow | 1. Pre-check shows the applicant "may need a little more detail". 2. Solicitor sees paragraph 11, with the judgement requirement marked not met and the hedged sentence quoted. 3. Service drafts a request to the GP. 4. Solicitor sends it. 5. Corrected letter passes |
| Outcome | Fixed before submission. No LAA return |
| Test data | `P11-hedged_judgement-01`, `MOJ-P11-rejected-02` |

## UC-03 Support organisation letter with vague "matters relied on"

| | |
|---|---|
| Actors | Solicitor, support organisation |
| Trigger | The letter lists the matters relied on as "victim testimony and referral" |
| Main flow | 1. Paragraph 17 check marks "specific matters" as not met and explains that the letter names a source of information, not what happened. 2. Service drafts a request asking the author to describe the specific matters |
| Outcome | Corrected letter passes |
| Test data | `P17-vague_matters-01`, `MOJ-P17-rejected-04` |

## UC-04 Evidence submitted under the wrong paragraph

| | |
|---|---|
| Actors | Solicitor |
| Trigger | A support organisation letter is claimed as an IDVA letter (paragraph 14) |
| Main flow | 1. Check against paragraph 14 fails because the author is not an IDVA. 2. Service checks other paragraphs and finds that the letter meets paragraph 17. 3. Solicitor switches the claimed paragraph |
| Outcome | Passes under the right paragraph |
| Test data | `X-wrong_para_17_claimed_as_14`, `X-wrong_para_14_claimed_as_17` |

## UC-05 Several documents, only one valid

| | |
|---|---|
| Actors | Solicitor |
| Trigger | Three documents uploaded: a hedged GP letter, a vague support letter and a valid MARAC letter |
| Main flow | 1. Each document is checked separately. 2. The MARAC letter meets paragraph 13. 3. Overall result: pass, relying on the MARAC letter |
| Outcome | Application can proceed. Weaker documents stay on link 1 and are not submitted |
| Test data | `X-bundle_one_valid`, `X-bundle_all_invalid` |

## UC-06 Arrest followed by no further action

| | |
|---|---|
| Actors | Solicitor |
| Trigger | A police email confirms an arrest, then a decision to take no further action |
| Main flow | 1. Paragraph 1 check marks "arrest still current" as not met. 2. Service explains that B must still be under investigation, on bail or charged. 3. Service suggests other routes |
| Outcome | Fail for this document, with next steps |
| Test data | `P1-no_further_action-01` |

## UC-07 Long report with the key sentence buried

| | |
|---|---|
| Actors | Solicitor, caseworker |
| Trigger | A children's services assessment of several pages is uploaded |
| Main flow | 1. Paragraph 19 check finds the one passage that records the assessment of abuse by B. 2. The passage is quoted and highlighted in the document. 3. The submission pack includes the passage relied on |
| Outcome | Pass. Caseworker can confirm without reading the whole report |
| Test data | `X-long_report_key_sentence_buried` |

## UC-08 Name on the evidence does not match the application

| | |
|---|---|
| Actors | Solicitor |
| Trigger | Letter names "Amira Hussain"; the application is for "Amira Hussaun" |
| Main flow | 1. Service flags the mismatch. 2. Outcome is refer, not fail. 3. Solicitor confirms identity or corrects the record |
| Outcome | Resolved by a person |
| Test data | `X-name_mismatch` |

## UC-09 Economic abuse

| | |
|---|---|
| Actors | Solicitor, caseworker |
| Trigger | Evidence relies on paragraph 21 |
| Main flow | 1. Service summarises the behaviour described, whether it shows control rather than an ordinary financial dispute, and what supporting documents exist. 2. Outcome is always refer |
| Outcome | A person decides, using the summary |
| Test data | `P21-valid-01`, `P21-ordinary_financial_dispute-01`, `P21-narrative_only_no_explanation-01` |

## UC-10 Unreadable scan or untranslated document

| | |
|---|---|
| Actors | Applicant, solicitor |
| Trigger | The key sentence cannot be read, or a letter from overseas has no English translation |
| Main flow | 1. Service marks the affected requirements as unclear. 2. Outcome is refer. 3. Applicant is asked for a clearer photo, or the solicitor is told a translation and the original are both needed |
| Outcome | Better copy requested instead of a rejection |
| Test data | `X-illegible_scan`, `X-untranslated_overseas_letter` |

## UC-11 Typos and template errors

| | |
|---|---|
| Actors | Solicitor |
| Trigger | A letter that meets every requirement contains typos or an unfilled "[NAME OF CLIENT]" placeholder |
| Main flow | 1. Service checks substance and passes the document. 2. It may note the cosmetic issue without counting it against the letter |
| Outcome | Pass. Avoids a false rejection |
| Test data | Any case ending `-benign_defects-01`, and `MOJ-P14-accepted-01` |

## UC-12 Caseworker returns an application

| | |
|---|---|
| Actors | Caseworker, solicitor, applicant |
| Trigger | A requirement is not met in a Licensed Work submission |
| Main flow | 1. Caseworker selects "return". 2. Service drafts the message naming the paragraph and requirement. 3. Solicitor receives it, fixes the gap and resubmits under the same LAA reference. 4. Solicitor updates the applicant |
| Outcome | One return, resolved quickly |
| Test data | Demo flow, using any mutation case |

## UC-13 Applicant interrupted

| | |
|---|---|
| Actors | Applicant |
| Trigger | Someone comes into the room while the applicant is using the app |
| Main flow | 1. Applicant taps quick exit. 2. Screen is replaced by a neutral website and the session ends |
| Outcome | Nothing left on screen or on the device |
| Test data | Demo only |

## UC-14 Applicant changes solicitor

| | |
|---|---|
| Actors | Applicant, two firms |
| Trigger | Applicant wants a different firm |
| Main flow | 1. Applicant removes the first firm. 2. Approves the new firm. 3. New firm sees the case from that point plus documents the applicant chooses to share |
| Outcome | Applicant stays in control of who can see the case |
| Test data | Demo only |
