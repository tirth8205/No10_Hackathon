// Shapes shared by the screens and the API layer.
//
// A check result follows the engine's output format in docs/07-checking-engine.md:
// outcome pass / fail / refer, and each element met / not_met / unclear.

export type Outcome = "pass" | "fail" | "refer";
export type ElementStatus = "met" | "not_met" | "unclear";
export type Uploader = "client" | "provider" | "inbox";
export type DecisionAction = "accept" | "return" | "refer";

export interface ElementResult {
  key: string;
  label: string;
  status: ElementStatus;
  /** Verbatim wording from the document. For a missing element, the problem wording if there is one. */
  quote: string | null;
  explanation: string;
  /** What the letter writer needs to add, written for the solicitor. */
  fix?: string | null;
  /** The same ask in plain words for the client. */
  clientHint?: string | null;
}

export type VerificationStatus = "pass" | "warn" | "fail" | "unknown";

/** A check on the author or organisation that helps a person verify the letter. Never changes the verdict. */
export interface VerificationCheck {
  id: string;
  label: string;
  status: VerificationStatus;
  detail: string;
  /** Where a person can check it themselves. */
  link: string | null;
}

export interface CheckResult {
  /** Schedule 1 paragraph, or null when the document is not an accepted evidence type. */
  matchedPara: string | null;
  outcome: Outcome;
  reason: string;
  elements: ElementResult[];
  flags: string[];
  /** How the names in the letter differ from the case, when they do (the back end adds it). */
  nameCheck?: string | null;
  authorOrg: string | null;
  /** Short, safer name for the organisation, used on the client's screens. */
  shortOrg: string | null;
  authorName: string | null;
  authorRole: string | null;
  /** ISO date of the letter. */
  letterDate: string | null;
  victimName: string | null;
  otherPartyName: string | null;
  agreement: string;
  /** Verification checks on the author and organisation (optional; the back end adds them). */
  verification?: VerificationCheck[];
  rulesVersion: string;
  checkedAt: string;
}

export interface DocumentPage {
  filename: string;
  contentType: string;
  /** Object URL or data URL for viewing. Absent for text-only demo documents. */
  url?: string;
}

export interface CaseDocument {
  id: string;
  caseId: string;
  pages: DocumentPage[];
  /** Extracted text, used to show quotes in context. */
  text: string;
  uploadedBy: Uploader;
  /** ISO timestamp. */
  uploadedAt: string;
  /** Null while the check is running. */
  result: CheckResult | null;
}

export interface Decision {
  action: DecisionAction;
  note: string;
  toolVerdict: string;
  agreedWithTool: boolean;
  at: string;
}

export interface Case {
  id: string;
  ref: string;
  firm: string;
  applicantName: string;
  otherPartyName: string;
  caseType: string;
  createdAt: string;
  clientToken: string | null;
  tokenExpiresAt: string | null;
  /** What the solicitor has asked the client for. The client sees these words. */
  askLabel: string;
  documentIds: string[];
  selectedDocumentIds: string[];
  selectionTouched: boolean;
  submittedAt: string | null;
  submittedDocumentIds: string[];
  submitReason: string | null;
  decision: Decision | null;
  /** Set once the case is submitted (null before): the pack for Civil Apply is GET /web/submissions/{submissionId}/pack.zip.
   *  On a caseworker queue row it is the submission that row shows; review and decide by it, not by the case. */
  submissionId?: string | null;
  /** The LAA's own run of the check on the submitted pack, compared with the provider's. Absent until it exists. */
  laaCheck?: { done: boolean; differences: number } | null;
}

export interface CaseWithDocuments {
  case: Case;
  documents: CaseDocument[];
}
