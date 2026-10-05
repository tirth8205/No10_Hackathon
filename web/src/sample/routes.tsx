// Connects each screen to the sample data and to the next screen in the flow.
// When the back end is ready, replace these wrappers with ones that load real
// data and call the API. The screens themselves only take props.

import { useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router";
import { downloadText } from "../components/CopyButton";
import { groupEvidence } from "../lib/evidence";
import { caseVerdict, suggestedAction } from "../lib/labels";
import { clientRequestMessage, firmShortName, firstName, inboxReply, verificationSummary } from "../lib/outputs";
import type { CaseDocument, DecisionAction } from "../lib/types";
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
import { Inbox } from "../pages/caseworker/Inbox";
import { Queue, type QueueFilter } from "../pages/caseworker/Queue";
import { Review } from "../pages/caseworker/Review";
import { NotFound } from "../pages/HowTheCheckWorks";
import { paths, type ClientResultState } from "../paths";
import { FIRM, findCase, findCaseByToken, providerCases, queue } from "./cases";
import { letter } from "./letters";

// ---------------------------------------------------------------------------
// Client
// ---------------------------------------------------------------------------

export function ClientUploadRoute() {
  const { token = "" } = useParams();
  const navigate = useNavigate();
  const data = findCaseByToken(token);
  if (!data?.case.tokenExpiresAt) return <ClientExpired />;
  return (
    <ClientUpload
      firstName={firstName(data.case)}
      firmName={firmShortName(data.case.firm)}
      askLabel={data.case.askLabel}
      linkExpiresAt={data.case.tokenExpiresAt}
      onFiles={() => navigate(paths.clientChecking(token))}
    />
  );
}

export function ClientCheckingRoute() {
  const { token = "" } = useParams();
  const data = findCaseByToken(token);
  if (!data) return <ClientExpired />;
  return <ClientChecking firmName={firmShortName(data.case.firm)} description="2 photos of your letter" uploadedAt={new Date().toISOString()} />;
}

const RESULT_LETTERS: Record<ClientResultState, string> = {
  change: "p17-vague-jane-doe",
  ready: "p17-valid-jane-doe",
  check: "p14-unclear-mary-major",
  other: "statement-jane-doe",
};

export function ClientResultRoute() {
  const { token = "", state = "change" } = useParams();
  const data = findCaseByToken(token);
  const letterId = RESULT_LETTERS[state as ClientResultState];
  if (!data || !letterId) return <ClientExpired />;
  const l = letter(letterId);
  const doc: CaseDocument = {
    id: l.id,
    caseId: data.case.id,
    pages: [],
    text: l.text,
    uploadedBy: "client",
    uploadedAt: new Date().toISOString(),
    result: l.result,
  };
  return (
    <ClientResult
      firmName={firmShortName(data.case.firm)}
      result={l.result}
      messageToWriter={clientRequestMessage(data.case, doc)}
      uploadTo={paths.client(token)}
    />
  );
}

// ---------------------------------------------------------------------------
// Solicitor
// ---------------------------------------------------------------------------

/** The sample case where a corrected letter arrives. */
const BEFORE = "gc-0142";
const AFTER = "gc-0142-corrected";

export function ProviderCasesRoute() {
  const navigate = useNavigate();
  return (
    <ProviderCases
      firm={FIRM}
      cases={providerCases}
      onDropLetter={() => navigate(paths.caseDocument(BEFORE, "d-brookfield-1"))}
      firstTimeRight={{ yours: 7, outOf: 10 }}
    />
  );
}

export function ProviderNewCaseRoute() {
  const navigate = useNavigate();
  return <ProviderNewCase firm={FIRM} onCreate={() => navigate(paths.caseClient("gc-0145"))} />;
}

export function CaseEvidenceRoute() {
  const { caseId = "" } = useParams();
  const navigate = useNavigate();
  const data = findCase(caseId);
  if (!data) return <NotFound />;
  return (
    <CaseEvidence
      key={caseId}
      data={data}
      onAddDocument={() => {
        if (caseId === BEFORE) navigate(paths.caseEvidence(AFTER));
      }}
    />
  );
}

export function CaseClientRoute() {
  const { caseId = "" } = useParams();
  const data = findCase(caseId);
  const [linkOn, setLinkOn] = useState(Boolean(data?.case.clientToken));
  if (!data) return <NotFound />;
  const token = data.case.clientToken ?? "new-link";
  return (
    <CaseClient
      data={data}
      clientLinkUrl={linkOn ? `${window.location.origin}${paths.client(token)}` : null}
      onTurnOffLink={() => setLinkOn(false)}
      onCreateLink={() => setLinkOn(true)}
    />
  );
}

export function CaseDetailsRoute() {
  const { caseId = "" } = useParams();
  const navigate = useNavigate();
  const data = findCase(caseId);
  if (!data) return <NotFound />;
  return <CaseDetails c={data.case} onSave={() => navigate(paths.caseClient(caseId))} />;
}

export function DocumentCheckRoute() {
  const { caseId = "", docId = "" } = useParams();
  const navigate = useNavigate();
  const data = findCase(caseId);
  const doc = data?.documents.find((d) => d.id === docId);
  if (!data || !doc) return <NotFound />;
  const group = groupEvidence(data.documents).find((g) => g.items.some((i) => i.doc.id === doc.id));
  const newest = group?.items[0]?.doc;
  return (
    <DocumentCheck
      key={docId}
      c={data.case}
      doc={doc}
      replacedBy={newest && newest.id !== doc.id ? newest : null}
      onUploadCorrected={() => navigate(paths.caseEvidence(AFTER))}
    />
  );
}

export function DocumentFileRoute() {
  const { caseId = "", docId = "" } = useParams();
  const data = findCase(caseId);
  const doc = data?.documents.find((d) => d.id === docId);
  if (!data || !doc) return <NotFound />;
  return <DocumentFile c={data.case} doc={doc} />;
}

export function CaseSubmitRoute() {
  const { caseId = "" } = useParams();
  const [search] = useSearchParams();
  const [done, setDone] = useState(false);
  const data = findCase(caseId);
  if (!data) return <NotFound />;
  const param = search.get("selected");
  const selectedIds = param !== null ? param.split(",").filter(Boolean) : data.case.selectedDocumentIds;
  return (
    <CaseSubmit
      data={data}
      selectedIds={selectedIds}
      done={done}
      onDownload={() => {
        const selected = data.documents.filter((d) => selectedIds.includes(d.id));
        downloadText(`${data.case.ref} verification summary.txt`, verificationSummary(data.case, selected));
        setDone(true);
        window.scrollTo(0, 0);
      }}
    />
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
  return (
    <Queue
      items={queue.filter((item) => item.case.ref !== decidedRef)}
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
  const data = queue.find((item) => item.case.id === caseId);
  if (!data) return <NotFound />;
  const activeDocId = search.get("doc") ?? data.documents[0]?.id ?? "";
  const onDecide = (action: DecisionAction) => {
    const agreed = suggestedAction(caseVerdict(data.documents.map((d) => d.result))) === action;
    navigate(`${paths.queue}?decided=${data.case.ref}&action=${action}&agreed=${agreed ? 1 : 0}`);
  };
  return <Review key={caseId} data={data} activeDocId={activeDocId} onDecide={onDecide} />;
}

const SAMPLE_QUERY = [
  "From: casework@northgate-family-law.example",
  "Subject: Gateway evidence check – J Smith",
  "",
  "Hello,",
  "",
  "Please could you confirm whether the attached GP letter meets the domestic abuse evidence requirements before we submit the application?",
  "",
  "Thanks,",
  "Casework team, Northgate Family Law",
].join("\n");

export function InboxRoute() {
  const [search] = useSearchParams();
  const navigate = useNavigate();
  const drafted = search.get("state") === "drafted";
  const documents = queue.find((item) => item.case.id === "gc-0130")?.documents.slice(0, 1) ?? [];
  return (
    <Inbox
      key={drafted ? "drafted" : "empty"}
      draft={drafted ? { email: SAMPLE_QUERY, documents, reply: inboxReply("Northgate Family Law", documents) } : null}
      onDraft={() => navigate(`${paths.inbox}?state=drafted`)}
    />
  );
}
