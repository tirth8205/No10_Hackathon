// Sample cases used to render the screens until the back end is connected.
// Static data only: nothing here changes at runtime.

import { defaultSelection } from "../lib/evidence";
import type { Case, CaseDocument, CaseWithDocuments, Uploader } from "../lib/types";
import { letter } from "./letters";

export const FIRM = "Hartley & Webb Solicitors";
/** The demo client's one-time link token. */
export const CLIENT_TOKEN = "jd7k4q";

const iso = (d: Date) => d.toISOString();
const minutesAgo = (m: number) => iso(new Date(Date.now() - m * 60_000));
const daysAgo = (d: number, hour = 11, minute = 0) => {
  const date = new Date();
  date.setDate(date.getDate() - d);
  date.setHours(hour, minute, 0, 0);
  return iso(date);
};
const inDays = (d: number) => iso(new Date(Date.now() + d * 86_400_000));

function doc(id: string, caseId: string, letterId: string, uploadedBy: Uploader, uploadedAt: string, photos = 1): CaseDocument {
  const l = letter(letterId);
  const isPhoto = l.filename.endsWith(".jpg");
  const pages = Array.from({ length: isPhoto ? photos : 1 }, (_, i) => ({
    filename: isPhoto && photos > 1 ? l.filename.replace(".jpg", ` (${i + 1}).jpg`) : l.filename,
    contentType: isPhoto ? "image/jpeg" : "application/pdf",
  }));
  return { id, caseId, pages, text: l.text, uploadedBy, uploadedAt, result: l.result };
}

function makeCase(c: Partial<Case> & Pick<Case, "id" | "ref" | "firm" | "applicantName" | "otherPartyName">, documents: CaseDocument[]): CaseWithDocuments {
  const full: Case = {
    caseType: "Child arrangements",
    createdAt: daysAgo(6),
    clientToken: null,
    tokenExpiresAt: null,
    askLabel: "Letter from your support worker",
    documentIds: documents.map((d) => d.id),
    selectedDocumentIds: defaultSelection(documents),
    selectionTouched: false,
    submittedAt: null,
    submittedDocumentIds: [],
    submitReason: null,
    decision: null,
    ...c,
  };
  return { case: full, documents };
}

// ---------------------------------------------------------------------------
// Hartley & Webb (the solicitor's view)
// ---------------------------------------------------------------------------

const janeDoeDocs = (caseId: string) => [
  doc("d-gp", caseId, "p11-hedged-jane-doe", "provider", daysAgo(5, 15, 20)),
  doc("d-statement", caseId, "statement-jane-doe", "client", daysAgo(3, 19, 5), 3),
  doc("d-brookfield-1", caseId, "p17-vague-jane-doe", "client", minutesAgo(200)),
];

const janeDoeBase = {
  ref: "GC-0142",
  firm: FIRM,
  applicantName: "Jane Doe",
  otherPartyName: "John Doe",
  clientToken: CLIENT_TOKEN,
  tokenExpiresAt: inDays(7),
  askLabel: "Corrected letter from Brookfield",
};

/** Jane Doe before the corrected letter arrives: the Brookfield letter needs a change. */
export const janeDoe = makeCase({ id: "gc-0142", ...janeDoeBase }, janeDoeDocs("gc-0142"));

/** Jane Doe after she uploads the corrected Brookfield letter. */
export const janeDoeCorrected = makeCase({ id: "gc-0142-corrected", ...janeDoeBase }, [
  ...janeDoeDocs("gc-0142-corrected"),
  doc("d-brookfield-2", "gc-0142-corrected", "p17-valid-jane-doe", "client", minutesAgo(20), 2),
]);

const joeBloggs = makeCase(
  { id: "gc-0141", ref: "GC-0141", firm: FIRM, applicantName: "Joe Bloggs", otherPartyName: "Sam Bloggs", createdAt: daysAgo(2) },
  [doc("d-moorside", "gc-0141", "p17-valid-joe-bloggs", "provider", minutesAgo(300))],
);

const maryMajor = makeCase(
  { id: "gc-0139", ref: "GC-0139", firm: FIRM, applicantName: "Mary Major", otherPartyName: "Paul Major", createdAt: daysAgo(7) },
  [doc("d-idva-major", "gc-0139", "p14-unclear-mary-major", "client", daysAgo(3, 9, 40))],
);

const johnSmith = makeCase(
  {
    id: "gc-0145",
    ref: "GC-0145",
    firm: FIRM,
    applicantName: "John Smith",
    otherPartyName: "Alex Smith",
    caseType: "Finances",
    clientToken: "js3p8w",
    tokenExpiresAt: inDays(4),
    createdAt: daysAgo(3, 16, 0),
  },
  [],
);

/** The solicitor's open cases, in the order the list shows them. */
export const providerCases: CaseWithDocuments[] = [janeDoe, maryMajor, johnSmith, joeBloggs];

// ---------------------------------------------------------------------------
// Submitted applications (the caseworker's queue)
// ---------------------------------------------------------------------------

function submitted(
  ref: string,
  firm: string,
  applicantName: string,
  otherPartyName: string,
  letterIds: string[],
  submittedAt: string,
  submitReason: string | null = null,
): CaseWithDocuments {
  const id = ref.toLowerCase();
  const docs = letterIds.map((l, i) => doc(`${id}-d${i + 1}`, id, l, "provider", submittedAt));
  const data = makeCase({ id, ref, firm, applicantName, otherPartyName, submittedAt, submitReason }, docs);
  data.case.submittedDocumentIds = docs.map((d) => d.id);
  return data;
}

const janeDoeSubmitted: CaseWithDocuments = (() => {
  const data = makeCase({ id: "gc-0142-submitted", ...janeDoeBase, submittedAt: minutesAgo(10) }, janeDoeCorrected.documents);
  data.case.submittedDocumentIds = ["d-brookfield-2"];
  return { case: data.case, documents: data.documents.filter((d) => d.id === "d-brookfield-2") };
})();

export const queue: CaseWithDocuments[] = [
  submitted("GC-0133", "Riverside Legal", "Sarah Jones", "Tom Jones", ["p17-valid-sarah-jones"], daysAgo(4, 10, 30)),
  submitted("GC-0136", "Ashdown Law", "Fred Bloggs", "Kim Bloggs", ["p11-valid-fred-bloggs"], daysAgo(3, 14, 5)),
  janeDoeSubmitted,
  submitted("GC-0134", "Riverside Legal", "Jane Roe", "Richard Roe", ["p17-injection-jane-roe"], daysAgo(4, 15, 10)),
  submitted("GC-0135", "Northgate Family Law", "Alex Doe", "Sam Doe", ["p14-unclear-alex-doe"], daysAgo(3, 9, 50)),
  submitted("GC-0137", "Ashdown Law", "Lucy Brown", "Dan Brown", ["p11-email-lucy-brown"], daysAgo(3, 16, 30)),
  submitted(
    "GC-0130",
    "Northgate Family Law",
    "Jane Smith",
    "Mark Smith",
    ["p11-hedged-jane-smith", "p18-unnamed-jane-smith"],
    daysAgo(6, 12, 0),
    "The GP is reissuing the letter. Our client needs urgent protection, so we are submitting now to avoid delay.",
  ),
  submitted("GC-0132", "Riverside Legal", "Mary Smith", "Paul Smith", ["p19-hedged-mary-smith"], daysAgo(5, 11, 15)),
];

// ---------------------------------------------------------------------------
// Lookups
// ---------------------------------------------------------------------------

const all = [janeDoe, janeDoeCorrected, ...providerCases.slice(1), ...queue];

export function findCase(caseId: string): CaseWithDocuments | undefined {
  return all.find((c) => c.case.id === caseId);
}

export function findCaseByToken(token: string): CaseWithDocuments | undefined {
  return providerCases.find((c) => c.case.clientToken === token);
}

/** A sample letter that is being checked, for the "Checking" states. */
export function checkingDocument(caseId: string, filename: string, photos: number): CaseDocument {
  return {
    id: "d-checking",
    caseId,
    pages: Array.from({ length: photos }, (_, i) => ({ filename: `${filename} (${i + 1}).jpg`, contentType: "image/jpeg" })),
    text: "",
    uploadedBy: "client",
    uploadedAt: minutesAgo(0),
    result: null,
  };
}
