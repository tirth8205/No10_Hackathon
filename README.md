# Gateway Check

Checks domestic abuse evidence for legal aid against Schedule 1 of the Civil Legal Aid (Procedure) Regulations 2012, before it is submitted. Built for the 10 Downing Street / Ministry of Justice hackathon, October 2026.

Three people use it:

- **The client** uploads a letter or a photo from their phone through a one-off link and gets a plain answer: ready, needs a change, or their solicitor will look at it.
- **The solicitor** sees which of the paragraph's requirements the letter meets, the exact sentence each one rests on, what is missing, and a drafted request to the letter writer. A corrected letter is compared with the one it replaces.
- **The LAA caseworker** gets the submitted evidence with the same marks on the letter itself, an independent re-check, verification look-ups on the author and organisation, and makes the decision.

The model never decides on its own: every "included" rests on a quote found word for word in the document, three independent checks must agree, names are matched against the application in code, and anything unclear goes to a person.

## Run it

```bash
cp .env.example .env            # add OPENAI_API_KEY
uv sync                         # Python 3.12, FastAPI, pypdf, python-docx, Pillow
cd web && npm install && cd ..  # React + Vite + govuk-frontend
uvicorn app.main:app --port 8000 --reload
cd web && npm run dev           # http://localhost:5173
```

Open `http://localhost:5173/stage` for all three views side by side, with **Reset demo data** to seed nine realistic cases (letterheaded PDFs, Word files, phone photos, a police email).

One container for deployment: `docker build -t gateway-check . && docker run -p 8000:8000 -e OPENAI_API_KEY=... -v data:/data gateway-check`.

## Where things are

| | |
|---|---|
| `engine/` | The checking engine: ingest → classify → three parallel assessments → quote verification → name and language gates → verdict. `engine/verification.py` holds the author and organisation look-ups. |
| `rules/` | One YAML per Schedule 1 paragraph (22), with the requirements, fixes and client wording. |
| `app/` | FastAPI: the engine-shaped `/api`, the frontend-shaped `/web`, SQLite store, role-aware mappers. Contract in `BACKEND.md`. |
| `web/` | The three interfaces. |
| `eval/` | Evaluation harness and results: `eval/RESULTS.md`. Synthetic 146/146, unseen style 35/35, MoJ gold letters 11/12 as text and 24/24 as PDFs, no false approvals. |
| `data/` | The hackathon pack, the gold letters and the synthetic cases. |
| `demo/` | The demo cases and the generator for their documents. |
| `docs/` | Background, personas, flows, data model, safety and the demo plan. |
| `tests/` | 148 backend tests; `cd web && npx vitest run` for the 80 frontend tests. |

Open questions and risks: `OPEN_QUESTIONS.md`.
