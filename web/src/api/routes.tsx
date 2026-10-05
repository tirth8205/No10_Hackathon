// Connects each screen to the backend (/web API) and to the next screen in the flow.
// The screens themselves only take props; this file loads data, polls while a
// check is running, and calls the API from the callbacks.
//
// Every callback that calls the API runs through `useActionError().run`, so a refused
// upload or a failed save shows as an error summary at the top of the screen (the
// layouts render it) instead of failing silently. The next successful action clears it.

import { useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router";
import { downloadText, downloadUrl } from "../components/CopyButton";
import { ActionErrorProvider } from "../components/ErrorBanner";
import { groupEvidence } from "../lib/evidence";
import { clientRequestMessage } from "../lib/outputs";
import type { Case, CaseDocument, CaseWithDocuments, DecisionAction } from "../lib/types";
import { CaseClient } from "../pages/provider/CaseClient";
import { CaseDetails } from "../pages/provider/CaseDetails";
import { CaseEvidence } from "../pages/provider/CaseEvidence";
import { CaseSubmit } from "../pages/provider/CaseSubmit";
import { DocumentCheck } from "../pages/provider/DocumentCheck";
import { DocumentFile } from "../pages/provider/DocumentFile";
import { ProviderCases } from "../pages/provider/ProviderCases";
import { ProviderNewCase } from "../pages/provider/ProviderNewCase";
import { ClientChecking } from "../pages/client/ClientChecking";
import { ClientExpired } from "../pages/client/ClientExpired";
import { ClientResult } from "../pages/client/ClientResult";
import { ClientUpload } from "../pages/client/ClientUpload";
import { Inbox, type InboxDraft } from "../pages/caseworker/Inbox";
import { Queue, type QueueFilter } from "../pages/caseworker/Queue";
import { Review } from "../pages/caseworker/Review";
import { NotFound } from "../pages/HowTheCheckWorks";
import { paths } from "../paths";
import * as api from "./backend";
import { useActionError, useAsync, usePolling } from "./useAsync";

/** The demo firm. The backend stores it on each case; the screens show it in the header. */
export const FIRM = "Hartley & Webb Solicitors";

const stillChecking = (docs: CaseDocument[]) => docs.some((d) => d.result === null);

function Loading({ what = "Loading" }: { what?: string }) {
  return (
    <main className="govuk-main-wrapper" id="main-content">
      <p className="govuk-body">{what}…</p>
    </main>
  );
}

function Failed({ error }: { error: Error }) {
  return (
    <main className="govuk-main-wrapper" id="main-content">
      <h1 className="govuk-heading-l">Something went wrong</h1>
      <p className="govuk-body">{error.message}</p>
      <p className="govuk-body">Check that the back end is running, then reload the page.</p>
    </main>
  );
}

/** A Case shaped object for the client's screens, which only need the first name and firm. */
function clientCase(firstName: string, firm: string): Case {
  return {
    id: "", ref: "", firm, applicantName: firstName, otherPartyName: "", caseType: "", createdAt: "", clientToken: null,
    tokenExpiresAt: null, askLabel: "", documentIds: [], selectedDocumentIds: [], selectionTouched: false, submittedAt: null,
    submittedDocumentIds: [], submitReason: null, decision: null,
  };
}

// ---------------------------------------------------------------------------
// Client
// ---------------------------------------------------------------------------

export function ClientUploadRoute() {
  const { token = "" } = useParams();
  const navigate = useNavigate();
  const act = useActionError();
  const view = useAsync(() => api.clientView(token), [token]);
  if (view.loading) return <Loading />;
  const v = view.data;
  const expires = v?.linkExpiresAt;
  if (view.error || !v || !expires) return <ClientExpired />;
  return (
    <ActionErrorProvider message={act.message}>
      <ClientUpload
        firstName={v.firstName}
        firmName={v.firmName}
        askLabel={v.askLabel}
        linkExpiresAt={expires}
        onFiles={(files) =>
          void act.run(async () => {
            const { documentId } = await api.clientUpload(token, files);
            navigate(`${paths.clientChecking(token)}?doc=${documentId}`);
          })
        }
      />
    </ActionErrorProvider>
  );
}

export function ClientCheckingRoute() {
  const { token = "" } = useParams();
  const [search] = useSearchParams();
  const navigate = useNavigate();
  const docId = search.get("doc") ?? "";
  const view = useAsync(() => api.clientView(token), [token]);
  const doc = useAsync(() => api.clientDocument(token, docId), [token, docId]);
  const checking = !doc.error && doc.data?.document.result === null;
  usePolling(checking, doc.reload);
  if (doc.data?.state) {
    navigate(`${paths.clientResult(token, doc.data.state)}?doc=${docId}`, { replace: true });
    return null;
  }
  if (view.error || doc.error) return <ClientExpired />;
  if (!view.data || !doc.data) return <Loading what="Checking your document" />;
  const n = doc.data.document.pages.length;
  const photos = doc.data.document.pages.every((p) => p.contentType.startsWith("image/"));
  const description = photos ? `${n} photo${n === 1 ? "" : "s"} of your letter` : "your letter";
  return <ClientChecking firmName={view.data.firmName} description={description} uploadedAt={doc.data.document.uploadedAt} />;
}

export function ClientResultRoute() {
  const { token = "" } = useParams();
  const [search] = useSearchParams();
  const docId = search.get("doc") ?? "";
  const view = useAsync(() => api.clientView(token), [token]);
  const doc = useAsync(() => (docId ? api.clientDocument(token, docId) : api.clientView(token).then((v) => ({ document: v.latestDocument!, state: v.state }))), [token, docId]);
  if (view.loading || doc.loading) return <Loading />;
  if (view.error || doc.error || !doc.data?.document?.result) return <ClientExpired />;
  const d = doc.data.document;
  return (
    <ClientResult
      firmName={view.data!.firmName}
      result={d.result!}
      messageToWriter={clientRequestMessage(clientCase(view.data!.firstName, view.data!.firmName), d)}
      uploadTo={paths.client(token)}
    />
  );
}

// ---------------------------------------------------------------------------
// Solicitor
// ---------------------------------------------------------------------------

function useCase(caseId: string) {
  const data = useAsync(() => api.getCase(caseId), [caseId]);
  usePolling(Boolean(data.data && stillChecking(data.data.documents)), data.reload);
  return data;
}

export function ProviderCasesRoute() {
  const navigate = useNavigate();
  const act = useActionError();
  const cases = useAsync(() => api.listCases(), []);
  usePolling(Boolean(cases.data?.some((c) => stillChecking(c.documents))), cases.reload);
  if (cases.loading) return <Loading />;
  if (cases.error) return <Failed error={cases.error} />;
  return (
    <ActionErrorProvider message={act.message}>
      <ProviderCases
        firm={FIRM}
        cases={cases.data ?? []}
        onDropLetter={(files) =>
          void act.run(async () => {
            const created = await api.createCaseFromLetter(files);
            navigate(paths.caseDocument(created.case.id, created.documentId));
          })
        }
        firstTimeRight={{ yours: 7, outOf: 10 }}
      />
    </ActionErrorProvider>
  );
}

export function ProviderNewCaseRoute() {
  const navigate = useNavigate();
  const act = useActionError();
  return (
    <ActionErrorProvider message={act.message}>
      <ProviderNewCase
        firm={FIRM}
        onCreate={(input) =>
          void act.run(async () => {
            const created = await api.createCase(input);
            navigate(paths.caseClient(created.case.id));
          })
        }
      />
    </ActionErrorProvider>
  );
}

export function CaseEvidenceRoute() {
  const { caseId = "" } = useParams();
  const act = useActionError();
  const data = useCase(caseId);
  if (data.loading) return <Loading />;
  if (data.error || !data.data) return <NotFound />;
  // The screen keeps its own selection state from first render. While the solicitor has not
  // touched it, follow the server's default (which changes when a check finishes).
  const c = data.data.case;
  const key = c.selectionTouched ? caseId : `${caseId}:${c.selectedDocumentIds.join(",")}`;
  return (
    <ActionErrorProvider message={act.message}>
      <CaseEvidence
        key={key}
        data={data.data}
        onSelectionChange={(ids) => void act.run(() => api.setSelection(caseId, ids))}
        onAddDocument={(files) =>
          void act.run(async () => {
            await api.addDocument(caseId, files);
            await data.reload();
          })
        }
      />
    </ActionErrorProvider>
  );
}

export function CaseClientRoute() {
  const { caseId = "" } = useParams();
  const act = useActionError();
  const data = useCase(caseId);
  if (data.loading) return <Loading />;
  if (data.error || !data.data) return <NotFound />;
  const c = data.data.case;
  const update = (next: Case) => data.set({ case: next, documents: data.data!.documents });
  return (
    <ActionErrorProvider message={act.message}>
      <CaseClient
        data={data.data}
        clientLinkUrl={c.clientToken && c.tokenExpiresAt ? `${window.location.origin}${paths.client(c.clientToken)}` : null}
        onTurnOffLink={() => void act.run(async () => update(await api.revokeClientLink(caseId)))}
        onCreateLink={() => void act.run(async () => update(await api.createClientLink(caseId)))}
      />
    </ActionErrorProvider>
  );
}

export function CaseDetailsRoute() {
  const { caseId = "" } = useParams();
  const navigate = useNavigate();
  const act = useActionError();
  const data = useCase(caseId);
  if (data.loading) return <Loading />;
  if (data.error || !data.data) return <NotFound />;
  return (
    <ActionErrorProvider message={act.message}>
      <CaseDetails
        c={data.data.case}
        onSave={(input) =>
          void act.run(async () => {
            await api.updateCase(caseId, input);
            navigate(paths.caseClient(caseId));
          })
        }
      />
    </ActionErrorProvider>
  );
}

export function DocumentCheckRoute() {
  const { caseId = "", docId = "" } = useParams();
  const navigate = useNavigate();
  const act = useActionError();
  const data = useCase(caseId);
  if (data.loading) return <Loading />;
  const doc = data.data?.documents.find((d) => d.id === docId);
  if (data.error || !data.data || !doc) return <NotFound />;
  const group = groupEvidence(data.data.documents).find((g) => g.items.some((i) => i.doc.id === doc.id));
  const newest = group?.items[0]?.doc;
  return (
    <ActionErrorProvider message={act.message}>
      <DocumentCheck
        key={docId}
        c={data.data.case}
        doc={doc}
        replacedBy={newest && newest.id !== doc.id ? newest : null}
        onUploadCorrected={(files) =>
          void act.run(async () => {
            // Straight to the corrected letter's own page: it polls while the check runs, then
            // shows what the new letter changed against this one.
            const added = await api.addDocument(caseId, files, { replaces: docId });
            navigate(added?.id ? paths.caseDocument(caseId, added.id) : paths.caseEvidence(caseId));
          })
        }
      />
    </ActionErrorProvider>
  );
}

export function DocumentFileRoute() {
  const { caseId = "", docId = "" } = useParams();
  const data = useCase(caseId);
  if (data.loading) return <Loading />;
  const doc = data.data?.documents.find((d) => d.id === docId);
  if (data.error || !data.data || !doc) return <NotFound />;
  return <DocumentFile c={data.data.case} doc={doc} />;
}

export function CaseSubmitRoute() {
  const { caseId = "" } = useParams();
  const [search] = useSearchParams();
  const [done, setDone] = useState(false);
  const act = useActionError();
  const data = useCase(caseId);
  if (data.loading) return <Loading />;
  if (data.error || !data.data) return <NotFound />;
  const param = search.get("selected");
  const selectedIds = param !== null ? param.split(",").filter(Boolean) : data.data.case.selectedDocumentIds;
  return (
    <ActionErrorProvider message={act.message}>
      <CaseSubmit
        data={data.data}
        selectedIds={selectedIds}
        done={done}
        onDownload={(reason) =>
          void act.run(async () => {
            const pack = await api.submitCase(caseId, selectedIds, reason);
            // The real pack (letters plus verification summary, one zip) is built by the back end.
            // Without a submission id, fall back to the summary text alone.
            const submissionId = pack.case.submissionId;
            if (submissionId) downloadUrl(api.submissionPackUrl(submissionId), `${pack.case.ref} submission pack.zip`);
            else downloadText(pack.filename, pack.summary);
            setDone(true);
            window.scrollTo(0, 0);
            void data.reload();
          })
        }
      />
    </ActionErrorProvider>
  );
}

// ---------------------------------------------------------------------------
// LAA caseworker
// ---------------------------------------------------------------------------

export function QueueRoute() {
  const [search] = useSearchParams();
  const filter = (search.get("filter") ?? "all") as QueueFilter;
  const decidedRef = search.get("decided");
  const decided = decidedRef
    ? { ref: decidedRef, action: (search.get("action") ?? "accept") as DecisionAction, agreedWithTool: search.get("agreed") === "1" }
    : null;
  const items = useAsync(() => api.queue(), []);
  if (items.loading) return <Loading />;
  if (items.error) return <Failed error={items.error} />;
  return (
    <Queue
      items={(items.data ?? []).filter((item: CaseWithDocuments) => item.case.ref !== decidedRef)}
      filter={filter}
      filterTo={(f) => (f === "all" ? paths.queue : `${paths.queue}?filter=${f}`)}
      decided={decided}
    />
  );
}

export function ReviewRoute() {
  const { caseId = "" } = useParams();
  const [search] = useSearchParams();
  const navigate = useNavigate();
  const act = useActionError();
  const data = useAsync(() => api.review(caseId), [caseId]);
  if (data.loading) return <Loading />;
  if (data.error || !data.data) return <NotFound />;
  const d = data.data;
  const activeDocId = search.get("doc") ?? d.documents[0]?.id ?? "";
  const onDecide = (action: DecisionAction, note: string) =>
    void act.run(async () => {
      const decision = await api.decide(caseId, action, note, d.case.submissionId); // this submission, not the case's latest
      navigate(`${paths.queue}?decided=${d.case.ref}&action=${decision.action}&agreed=${decision.agreedWithTool ? 1 : 0}`);
    });
  return (
    <ActionErrorProvider message={act.message}>
      <Review key={caseId} data={d} activeDocId={activeDocId} onDecide={onDecide} />
    </ActionErrorProvider>
  );
}

export function InboxRoute() {
  const [draft, setDraft] = useState<InboxDraft | null>(null);
  const [busy, setBusy] = useState(false);
  const act = useActionError();
  if (busy) return <Loading what="Checking the attachments" />;
  return (
    <ActionErrorProvider message={act.message}>
      <Inbox
        key={draft ? "drafted" : "empty"}
        draft={draft}
        onDraft={(email, files) => {
          setBusy(true);
          void act
            .run(async () => {
              const r = await api.draftInboxReply(email, files);
              setDraft({ email: r.email, documents: r.documents, reply: r.reply });
            })
            .finally(() => setBusy(false));
        }}
      />
    </ActionErrorProvider>
  );
}
