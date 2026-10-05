# 11. Demo plan

Semi-finals are on Tuesday 6 October, 11:00 to 12:30, with the finale at 13:40.

## 11.1 Story

Follow one case through all three parts, then show one return to prove the loop is quick.

| Time | Screen | What we show |
|---|---|---|
| 0:00 | Title | The problem in one sentence: evidence is found to be wrong only after submission, which costs time and delays help for people who need it |
| 0:20 | Applicant app | Amira starts a case and gets a reference. The evidence finder suggests a GP letter. She uploads a GP letter and sees "May need a little more detail. Your solicitor will help." Show the quick exit |
| 1:10 | Solicitor workspace | Tom opens the case. Paragraph 11 checklist: judgement not met, with the hedged sentence quoted. One click drafts the request to the GP. The corrected letter is uploaded and passes, with every requirement quoted |
| 2:00 | Solicitor workspace | Tom submits (Licensed Work). The submission pack shows the paragraph, checklist and quotes. Tom is prompted to update Amira |
| 2:20 | LAA caseworker view | Priya's queue. She opens the case: independent check, quotes highlighted, no differences. She approves in seconds |
| 2:40 | LAA caseworker view | A second case, a refuge letter with no perpetrator named. She clicks "return" and the message drafts itself, naming paragraph 18 |
| 3:00 | Results | Accuracy on the synthetic set and on MoJ's own examples, with false approvals shown |
| 3:20 | Close | People decide. The service shows its working. It is built to extend to Schedule 2 and other evidence |

## 11.2 Test cases for the demo

| Moment | Case |
|---|---|
| Hedged GP letter | `P11-hedged_judgement-01` |
| Corrected GP letter | `P11-valid-01` |
| Refuge letter with no perpetrator | `P18-perpetrator_not_named-01` or `MOJ-P18-rejected-02` |
| Backup: wrong paragraph | `X-wrong_para_17_claimed_as_14` |
| Backup: long report | `X-long_report_key_sentence_buried` |

## 11.3 Likely questions

| Question | Answer |
|---|---|
| Is it safe for victims? | Web app with no icon, quick exit, nothing stored on the device, one-time codes to a safe contact, no notifications by default, neutral wording, and the applicant controls who sees the case |
| Does it make decisions? | No. It recommends and drafts. Economic abuse always goes to a person |
| What stops a solicitor gaming it? | The LAA runs its own independent check on what is submitted and sees any differences |
| How accurate is it? | Show the measures, including false approvals, and the MoJ examples run once at the end |
| How do you stop it making things up? | Every "met" must quote the document, and the quote is checked in code. Rules come from a fixed requirements file |
| What about Controlled Work? | The solicitor decides, and the service produces an audit-ready file note |
| How would this fit LAA systems? | Link 2 improves the existing provider-to-LAA channel. The LAA reference stays the LAA's |
| Can it be reused? | Requirements are data, not code, so Schedule 2 and other evidence-based processes can be added |

## 11.4 Fallbacks

- Pre-recorded video of the full flow in case of network problems
- Screenshots of each key screen
- Results table saved locally
