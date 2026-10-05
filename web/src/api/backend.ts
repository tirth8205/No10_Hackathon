// Typed client for the backend's frontend-shaped API (/web). Every function returns
// the shapes in ../lib/types.ts, so routes.tsx can swap the sample data for these calls.
//
// Dev setup: run the API (`uvicorn app.main:app --port 8000`) and either add a Vite
// proxy for `/web` to http://localhost:8000, or set VITE_API_BASE=http://localhost:8000.

import type { Case, CaseDocument, CaseWithDocuments, Decision, DecisionAction } from "../lib/types";

const BASE = (import.meta.env?.VITE_API_BASE as string | undefined) ?? "";

export type ClientResultState = "change" | "ready" | "check" | "other";

export interface ClientView {
  firstName: string;
  firmName: string;
  askLabel: string;
  linkExpiresAt: string | null;
  latestDocument: CaseDocument | null;
  state: ClientResultState | null;
}

export interface InboxDraft {
  email: string;
  firm: string | null;
  caseId: string;
  documents: CaseDocument[];
  reply: string;
}

export interface SubmitResult extends CaseWithDocuments {
  summary: string;
  filename: string;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}/web${path}`, { ...init, headers: { Accept: "application/json", ...(init.headers ?? {}) } });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

const multipart = (files: File[], extra: Record<string, string | undefined> = {}): FormData => {
  const form = new FormData();
  for (const f of files) form.append("files", f, f.name);
  for (const [k, v] of Object.entries(extra)) if (v !== undefined) form.append(k, v);
  return form;
};

// ---------------------------------------------------------------- solicitor
export const listCases = () => request<CaseWithDocuments[]>("/cases");
export const getCase = (caseId: string) => request<CaseWithDocuments>(`/cases/${caseId}`);

export interface NewCaseInput {
  applicantName: string;
  otherPartyName: string;
  caseType: string;
  askLabel: string;
}
/** Creates the case and its client link; the returned case has clientToken set. */
export const createCase = (input: NewCaseInput) => request<CaseWithDocuments>("/cases", json("POST", input));

/** Start a case by dropping a letter: names are filled in later on the Details tab. */
export const createCaseFromLetter = (files: File[]) =>
  request<CaseWithDocuments & { documentId: string }>("/cases/from-letter", { method: "POST", body: multipart(files) });

/** Changing a name re-checks every letter on the case. */
export const updateCase = (caseId: string, patch: { applicantName?: string; otherPartyName?: string; caseType?: string; askLabel?: string }) =>
  request<CaseWithDocuments>(`/cases/${caseId}`, json("PATCH", patch));

export const setSelection = (caseId: string, documentIds: string[]) =>
  request<Case>(`/cases/${caseId}/selection`, json("PUT", { documentIds }));

/** Several files are the pages of one letter. Returns the document with result null; poll getDocument until it is set. */
export const addDocument = (caseId: string, files: File[], opts: { replaces?: string; uploadedBy?: "provider" | "client" } = {}) =>
  request<CaseDocument>(`/cases/${caseId}/documents`, { method: "POST", body: multipart(files, { replaces: opts.replaces, uploadedBy: opts.uploadedBy }) });

export const getDocument = (caseId: string, documentId: string) => request<CaseDocument>(`/cases/${caseId}/documents/${documentId}`);

export const createClientLink = (caseId: string) => request<Case>(`/cases/${caseId}/client-link`, { method: "POST" });
export const revokeClientLink = (caseId: string) => request<Case>(`/cases/${caseId}/client-link`, { method: "DELETE" });

/** Freezes the chosen documents as a submission and returns the verification summary text to download. */
export const submitCase = (caseId: string, documentIds: string[], reason: string | null) =>
  request<SubmitResult>(`/cases/${caseId}/submit`, json("POST", { documentIds, reason }));

// ---------------------------------------------------------------- client (one-time link)
export const clientView = (token: string) => request<ClientView>(`/client/${token}`);
export const clientUpload = (token: string, files: File[]) =>
  request<{ documentId: string; pages: number }>(`/client/${token}/upload`, { method: "POST", body: multipart(files) });
export const clientDocument = (token: string, documentId: string) =>
  request<{ document: CaseDocument; state: ClientResultState | null }>(`/client/${token}/documents/${documentId}`);

/** Resolves when the check has finished. */
export async function waitForDocument(poll: () => Promise<CaseDocument>, intervalMs = 2000, timeoutMs = 120_000): Promise<CaseDocument> {
  const started = Date.now();
  for (;;) {
    const doc = await poll();
    if (doc.result) return doc;
    if (Date.now() - started > timeoutMs) return doc;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

// ---------------------------------------------------------------- caseworker
/** Submitted, undecided cases with their submitted documents only. */
export const queue = () => request<CaseWithDocuments[]>("/queue");
export const review = (caseId: string) => request<CaseWithDocuments>(`/queue/${caseId}`);
export const decide = (caseId: string, action: DecisionAction, note: string) =>
  request<Decision>(`/queue/${caseId}/decision`, json("POST", { action, note }));

/** Inbox mode: the check runs before this returns (one request, up to a minute). */
export const draftInboxReply = (email: string, files: File[]) =>
  request<InboxDraft>("/inbox", { method: "POST", body: multipart(files, { email }) });
