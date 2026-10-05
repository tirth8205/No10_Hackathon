# Gateway Check: front end

React screens for the three interfaces: the client (on their phone), the solicitor and the LAA caseworker. Built with GOV.UK Frontend.

This is the front end only. The screens show **sample data** and are **not connected to a back end**.

## Run it

Node 22.16 or later.

```bash
npm install
npm run dev        # http://localhost:5173 (or the next free port)
npm test           # logic tests and a render test for every screen
npm run build      # type check and production build into dist/
```

The start page (`/`) lists every screen and state.

## Screens

| Who | Route | Screen |
|---|---|---|
| Client | `/client/:token` | Send your letter (one-time link) |
| | `/client/:token/checking` | Checking your document |
| | `/client/:token/result/:state` | Result: `change`, `ready`, `check` or `other` |
| | `/client/expired` | Link no longer works |
| Solicitor | `/provider` | Cases, and drop a letter to start a case |
| | `/provider/new` | Get an upload link for your client |
| | `/provider/cases/:caseId` | Case › Evidence: every upload, grouped, with older versions kept; choose what to submit |
| | `/provider/cases/:caseId/client` | Case › Client: names used for the check, upload link, what the client was told |
| | `/provider/cases/:caseId/details` | Change the other party's name and what the client is asked for |
| | `/provider/cases/:caseId/documents/:docId` | One document's check: the fix and the drafted request |
| | `/provider/cases/:caseId/documents/:docId/file` | The document itself |
| | `/provider/cases/:caseId/submit?selected=…` | Check what you're submitting, download for Civil Apply |
| Caseworker | `/caseworker` | Evidence queue, sorted by the tool's verdict |
| | `/caseworker/cases/:caseId?doc=…` | Review: quotes highlighted in the document, findings, decision |
| | `/caseworker/inbox` | Draft a reply to an evidence-check query |

## Connecting a back end

The screens in `src/pages/` take everything through props and callbacks. They do not fetch data.

- `src/lib/types.ts` holds the data shapes. A check result follows the engine's output format in `docs/07-checking-engine.md`: outcome `pass` / `fail` / `refer`, and each requirement `met` / `not_met` / `unclear` with a verbatim quote.
- `src/sample/routes.tsx` wires each screen to the sample data and to the next screen. **This is the file to replace**: load real data, pass it in, and call the back end from the callbacks (`onFiles`, `onAddDocument`, `onDownload`, `onDecide` and so on).
- `src/sample/` (letters and cases) can then be deleted.

Some text is drafted in the browser from the check result, in `src/lib/outputs.ts`: the request to the letter writer, the client's message to the writer, the caseworker's return note, the inbox reply and the verification summary. If the back end produces these instead, pass them in as props.

Labels are mapped from engine outcomes in one place, `src/lib/labels.ts`. The screens never show "approved", "rejected", "pass" or "fail".

## Design decisions

- **GOV.UK Frontend 6.** Uses the generic header (for services not on GOV.UK), service navigation, notification banner, panel, summary list, warning text, details, task list, tags and Exit this page. There is no crown, no GOV.UK logotype and no GDS Transport font, because those are only for gov.uk domains. Arial is used instead.
- **Client safety.** Every client screen has Exit this page: pressing Shift 3 times or Escape 3 times leaves the page. The page title is neutral ("Upload documents"). There is no service name, no navigation and first name only. Organisation names are shortened, and the solicitor sets the words the client sees ("Asking Jane for"). Nothing is stored in the browser. The hosting should also send `Cache-Control: no-store` and `Referrer-Policy: no-referrer` for `/client/*`.
- **Getting paid.** The solicitor sees how many working days it takes to get to approval. The return figure is shown as a minimum ("at least 23"), because it does not include the time to get a new letter. Estimates live in `src/lib/nudges.ts`.
- **The caseworker decides.** The three decision buttons are deliberately equal in weight.
- **Version pins.** React Router 7 and jsdom 26 are pinned because the newest majors need Node 22.22 or later.
