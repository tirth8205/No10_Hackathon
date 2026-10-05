# 9. Safety, privacy and security

## 9.1 Applicant safety

### What we are protecting against

Many applicants live with, are monitored by, or share devices and accounts with the person they are applying about. Assume that person may:

- see the applicant's phone, including the home screen, notifications, browser history and email
- know the applicant's passcodes or have access to shared accounts
- be in the room while the app is open
- try to find out where the applicant lives or what they are doing

### Controls

| Control | Why |
|---|---|
| Web app reached by link, not an installed app | No icon on the phone |
| Quick-exit button on every screen, plus Escape pressed three times | Replaces the page with a neutral website instantly |
| Nothing stored on the device: no saved passwords, no offline copies, session ends on close | Nothing to find afterwards |
| Sign-in with case reference and a one-time code sent to a contact the applicant has marked as safe | No password to be coerced or guessed, and codes go only where it is safe |
| No notifications unless the applicant turns them on, and then with neutral wording | Nothing appears on the lock screen |
| Neutral case reference and page titles | Nothing revealing in browser history or tabs |
| Applicant chooses safe contact times and can say "do not contact me" | The solicitor knows how and when it is safe to get in touch |
| Applicant approves and can remove the solicitor | The applicant stays in control of who can see the case |
| Address and contact details shown only to the linked solicitor | Reduces the risk of disclosure |

### Wording

- Never say "rejected", "fail" or "not a victim" to the applicant.
- Explain next steps, not legal reasoning.
- Decisions are given by the solicitor, not by a status change.
- Content should be reviewed with domestic abuse specialists before any live use.

## 9.2 Data protection

The service handles information about domestic abuse, health, and criminal allegations and offences. This is among the most sensitive data there is. Health data is special category data under UK GDPR, and criminal offence data has its own additional conditions.

Before any live use:

- complete a data protection impact assessment
- confirm the lawful basis and conditions for processing with MoJ and LAA data protection officers
- agree who is controller for each part: the applicant app, the firm's workspace and the LAA view may have different controllers
- agree retention periods (see [08 Data model and access](08-data-model-and-access.md))
- agree terms with any AI model provider: UK or agreed hosting, no use of data for training, and no retention beyond processing

### Data minimisation by design

- Link 1 and link 2 are separate. Only the submission pack crosses to the LAA.
- The LAA never sees the applicant's messages, evidence-finder answers or superseded documents.
- The applicant sees LAA events only as the solicitor chooses to share them.

## 9.3 Security

| Area | Approach |
|---|---|
| Professional users | Verified firms only, individual accounts, multi-factor authentication, role-based access |
| Applicant | One-time codes, rate limiting, short sessions |
| Documents | Encrypted in transit and at rest, scanned for malware on upload |
| Access | Every view and change is written to the audit log |
| Separation | Link 1 and link 2 data are stored and permissioned separately |

## 9.4 Accessibility and inclusion

- Meet WCAG 2.2 AA and the GOV.UK Service Standard.
- Plain English throughout the applicant app.
- Works on low-end phones and slow connections.
- Applicant content available in other languages, starting with Welsh.
- Photos of documents accepted, as many applicants will not have a scanner.

## 9.5 Hackathon data

Only fictional data is used in this prototype. The synthetic cases use invented names, organisations, addresses and reference numbers. The MoJ examples use placeholder names such as "Jane Doe".
