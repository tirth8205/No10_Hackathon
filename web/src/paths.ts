// Every screen's URL, in one place.

export type ClientResultState = "change" | "ready" | "check" | "other";

export const paths = {
  index: "/",
  howTheCheckWorks: "/how-the-check-works",

  client: (token: string) => `/client/${token}`,
  clientChecking: (token: string) => `/client/${token}/checking`,
  clientResult: (token: string, state: ClientResultState) => `/client/${token}/result/${state}`,
  clientExpired: "/client/expired",

  provider: "/provider",
  providerNewCase: "/provider/new",
  caseEvidence: (caseId: string) => `/provider/cases/${caseId}`,
  caseClient: (caseId: string) => `/provider/cases/${caseId}/client`,
  caseDetails: (caseId: string) => `/provider/cases/${caseId}/details`,
  caseDocument: (caseId: string, docId: string) => `/provider/cases/${caseId}/documents/${docId}`,
  caseDocumentFile: (caseId: string, docId: string) => `/provider/cases/${caseId}/documents/${docId}/file`,
  caseSubmit: (caseId: string, selectedIds?: string[]) =>
    `/provider/cases/${caseId}/submit${selectedIds ? `?selected=${selectedIds.join(",")}` : ""}`,

  queue: "/caseworker",
  review: (caseId: string, docId?: string) => `/caseworker/cases/${caseId}${docId ? `?doc=${docId}` : ""}`,
  inbox: "/caseworker/inbox",
};
