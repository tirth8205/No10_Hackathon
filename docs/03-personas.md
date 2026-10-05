# 3. Personas

These personas are fictional composites. They are based on the MoJ brief, the LAA guidance and the example evidence. They should be tested with real applicants, solicitors and caseworkers before any live use.

## 3.1 Amira, the applicant

| | |
|---|---|
| Age | 31 |
| Situation | Separated from her partner three months ago. They have a four-year-old daughter. She wants a child arrangements order |
| Home | A rented flat she moved into after leaving |
| Device | One smartphone. Her former partner used to check it and knew the passcode |
| Contact with services so far | One GP appointment where she mentioned what was happening at home, and a phone call with a local domestic abuse support service |
| What she knows | That legal aid exists. Not that it depends on a specific kind of document, or which documents count |

**Goals**
- Get legal help for the child arrangements case without paying for it
- Do this without her former partner finding out what she is doing
- Avoid telling her story again and again to different people

**Worries**
- Being found out because of something on her phone
- Being told, in effect, that she is "not a victim"
- Not understanding the forms and getting something wrong
- Delay while she waits for letters from professionals

**What she needs from the service**
- To be able to use it safely, and to leave instantly if someone walks in
- To be told, in plain words, which document she could get and who to ask
- Reassurance that her solicitor will handle the detail
- To see progress without having to chase anyone

**What success looks like for Amira**
She knows within one sitting which document to ask for and who to ask. Her solicitor has everything they need in one go, and she hears about the decision from her solicitor.

**Design implications**
- A web app reached by link, not an installed app, so there is no icon on her phone
- A quick exit on every screen, no notifications by default, and nothing stored on the device
- Sign-in with the case reference and a one-time code sent to a contact she has marked as safe
- Plain-language results that never say "rejected" and never include legal reasoning

## 3.2 Tom, the legal aid solicitor

| | |
|---|---|
| Age | 38 |
| Role | Family solicitor at a small high-street firm with a legal aid contract |
| Caseload | Around 40 open matters, with both Controlled Work and Licensed Work |
| How evidence reaches him | Photos on email, scanned letters, forwarded police emails, long social services reports |
| Biggest frustration | Applications returned by the LAA for something he could have fixed in five minutes if he had spotted it |

**Goals**
- Know before submitting that the evidence meets the requirements
- Spend less time reading long documents to find the one sentence that matters
- Avoid nil-assessed Controlled Work claims
- Keep the client informed without constant phone calls

**Frustrations**
- Evidence authors write letters that almost meet the requirements, such as a hedged judgement or a missing perpetrator name
- Not knowing exactly what the caseworker will object to
- Chasing professionals for corrected letters

**What he needs from the service**
- A requirement-by-requirement checklist for each document, with the supporting wording quoted
- A clear suggestion when a document fits a different paragraph better
- A drafted request to the evidence author that names exactly what is missing
- A tidy submission pack for Licensed Work, and an audit-ready file note for Controlled Work
- Control over what the client sees about the LAA stage

**What success looks like for Tom**
Fewer returned applications, fewer nil assessments, less time per case on evidence, and clients who understand where things stand.

**Design implications**
- The full check is the core of his workspace
- Drafting, not sending: Tom approves every message
- The workspace prompts him to update the client after LAA events and suggests wording

## 3.3 Priya, the LAA caseworker

| | |
|---|---|
| Role | Caseworker in the civil applications team at the Legal Aid Agency |
| Workload | Dozens of applications a day, many with domestic abuse evidence |
| Constraints | Must apply the regulations exactly. No discretion except where the Director decides economic abuse cases. Decisions must stand up to review and appeal |
| Quality | Her decisions are sampled and checked for consistency |

**Goals**
- Make correct, consistent decisions quickly
- Find the relevant part of a long document without reading all of it
- Write clear return requests that get the right document back first time

**Frustrations**
- Submissions where the provider has not said which part of a report they rely on
- Applications that have to go back because of a small, avoidable gap
- Re-reading the same kinds of letters to check the same wording

**What she needs from the service**
- A queue sorted by likely outcome, with flagged cases first
- For each submission: the paragraph claimed, the checklist, quotes highlighted in the document, and any flags
- An independent check run on the LAA side, compared with the solicitor's check
- One-click approve, refuse or return, with a drafted return message that names the paragraph and the missing requirement
- A record of where she agreed or disagreed with the service

**What success looks like for Priya**
Most submissions can be confirmed in a minute or two. Returns are rare and specific. Her decisions are consistent with her colleagues'.

**Design implications**
- No automatic approvals. The service recommends and she decides
- Every "met" result must show its quote, so she can verify rather than re-read
- Economic abuse cases always come to a person with a summary of the evidence

## 3.4 Secondary persona: the evidence author

Examples include a GP, a health visitor, an IDVA, a support worker at a domestic abuse charity, a police officer or Witness Care Officer, and a council housing officer.

**Needs**
- A short, specific request that says exactly what the letter must confirm
- The relevant GOV.UK template where one exists
- As little effort as possible, as most write these letters alongside a full caseload

**Design implications**
- Requests drafted by the service should be brief, polite and specific. For example: "Please confirm that you examined the patient in person, by phone or by video, and state your professional judgement without qualification."
- Requests are sent by the solicitor, not by the service
