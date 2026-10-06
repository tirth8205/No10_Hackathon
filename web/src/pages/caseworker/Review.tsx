import { VerificationList } from "../../components/Verification";
import { useEffect, useState } from "react";
import { Link } from "react-router";
import { DocumentText, HighlightKey } from "../../components/DocumentText";
import { PdfView } from "../../components/PdfView";
import { BackLink, Button, Details, ElementTag, InsetText, SummaryList, VerdictTag, WarningText } from "../../components/govuk";
import { CaseworkerLayout } from "../../components/layout";
import { useTitle } from "../../hooks/govuk";
import { when } from "../../lib/dates";
import { documentTitle } from "../../lib/evidence";
import { caseVerdict, docVerdict, paraOf } from "../../lib/labels";
import { returnNote } from "../../lib/outputs";
import type { Case, CaseDocument, CaseWithDocuments, DecisionAction } from "../../lib/types";
import { paths } from "../../paths";

export interface ReviewProps {
  /** The case with the submitted documents only. */
  data: CaseWithDocuments;
  activeDocId: string;
  onDecide: (action: DecisionAction, note: string) => void;
}

// Paragraphs where the other party must be named in the evidence (spec 8.3).
const NAMES_OTHER_PARTY = ["7", "13", "15", "18", "19"];

const sameName = (a: string | null | undefined, b: string | null | undefined) =>
  Boolean(a && b && a.trim().toLowerCase() === b.trim().toLowerCase());

function PartyCheck({ doc, applicant, otherParty }: { doc: CaseDocument; applicant: string; otherParty: string }) {
  const r = doc.result;
  if (!r) return null;
  const para = r.matchedPara;
  const otherNeeded = para !== null && NAMES_OTHER_PARTY.includes(para);
  const otherNamed = r.elements.find((e) => e.key === "perpetrator_named");
  return (
    <>
      <h3 className="govuk-heading-s">Party check</h3>
      <SummaryList
        rows={[
          {
            key: "Client in the letter",
            value: sameName(r.victimName, applicant)
              ? `${r.victimName}. Matches the application.`
              : `${r.victimName ?? "Not found"}. Check this against the application (${applicant}).`,
          },
          {
            key: "Other party",
            value: !otherNeeded
              ? `Not required for paragraph ${para}`
              : otherNamed?.status === "met"
                ? `${otherParty}. Matches the application.`
                : `Not named. The letter must name ${otherParty}.`,
          },
        ]}
      />
    </>
  );
}

/** One line on the LAA's own run of the check (link 2 of the flow). Nothing until the back end reports one. */
function LaaCheckLine({ check }: { check: Case["laaCheck"] }) {
  if (!check) return null;
  if (!check.done) return <InsetText>Independent LAA check: still running</InsetText>;
  if (check.differences === 0) return <InsetText>Independent LAA check: agrees with the provider’s check</InsetText>;
  return <WarningText>Independent LAA check: {check.differences === 1 ? "1 difference" : `${check.differences} differences`}</WarningText>;
}

/** The caseworker's co-pilot: the document with quotes highlighted, the tool's findings, and the decision. */
export function Review({ data, activeDocId, onDecide }: ReviewProps) {
  const { case: c, documents } = data;
  useTitle(`${c.ref} – Review – Gateway Check`);
  const doc = documents.find((d) => d.id === activeDocId) ?? documents[0];
  const verdict = caseVerdict(documents.map((d) => d.result));
  const needsNote = verdict.key !== "pass";
  const [note, setNote] = useState(needsNote ? returnNote(c, documents) : "");
  const r = doc?.result;
  const para = paraOf(r ?? null);
  // Show the submitted file itself when we hold it: a PDF with the check's marks drawn on the page, photos as uploaded.
  const pdfPage = doc?.pages.find((p) => p.url && p.contentType === "application/pdf");
  const photoPages = pdfPage ? [] : (doc?.pages.filter((p) => p.url && p.contentType.startsWith("image/")) ?? []);
  const [pdfHasText, setPdfHasText] = useState<boolean | null>(null);
  useEffect(() => setPdfHasText(null), [pdfPage?.url]);

  return (
    <CaseworkerLayout active="queue" beforeContent={<BackLink to={paths.queue}>Back to queue</BackLink>}>
      <span className="govuk-caption-m">
        {c.ref} · {c.caseType} · Submitted {c.submittedAt ? when(c.submittedAt) : ""} by {c.firm}
      </span>
      <div className="app-heading-with-tag">
        <h1 className="govuk-heading-xl govuk-!-margin-bottom-0">
          {c.applicantName} v {c.otherPartyName}
        </h1>
        <span className="govuk-body-s app-secondary-text govuk-!-margin-bottom-0">
          Tool verdict <VerdictTag verdict={verdict} />
        </span>
      </div>

      {c.submitReason && (
        <InsetText>
          <p className="govuk-body govuk-!-font-weight-bold govuk-!-margin-bottom-1">Submitted with a reason</p>
          <p className="govuk-body govuk-!-margin-bottom-0">“{c.submitReason}”</p>
        </InsetText>
      )}

      <ul className="app-doc-tabs" aria-label="Documents">
        {documents.map((d) => (
          <li key={d.id}>
            <Link className="govuk-link app-doc-tabs__link" to={paths.review(c.id, d.id)} aria-current={d.id === doc?.id ? "true" : undefined}>
              {documentTitle(d)} <VerdictTag verdict={docVerdict(d.result)} />
            </Link>
          </li>
        ))}
      </ul>

      {doc && r && (
        <div className="app-doc-panel">
          <div className="app-split">
            <section aria-labelledby="doc-title" className="app-split__document">
              <h2 className="govuk-heading-m govuk-!-margin-bottom-1" id="doc-title">
                {photoPages.length > 0 ? "The photos" : "The document"}
              </h2>
              <p className="govuk-body-s app-secondary-text">
                {doc.pages.length === 1 ? "1 page" : `${doc.pages.length} pages`}
                {para ? ` · ${para.singular}` : ""}
                {pdfPage && pdfHasText !== false ? " · each numbered mark is the sentence the check relied on" : ""}
                {pdfPage && pdfHasText === false ? " · a scan: the marks are shown on the text we read from it, below" : ""}
              </p>
              {pdfPage && (
                <>
                  <PdfView key={pdfPage.url} url={pdfPage.url!} elements={r.elements} onTextLayer={setPdfHasText} />
                  <p className="govuk-body-s">
                    <a className="govuk-link" href={pdfPage.url} target="_blank" rel="noreferrer">
                      Open the document in a new tab
                    </a>{" "}
                    to read it at full size.
                  </p>
                </>
              )}
              {photoPages.map((page) => (
                <img key={page.filename} className="app-doc-photo" src={page.url} alt={`${page.filename}, as submitted`} />
              ))}
              {pdfPage && pdfHasText !== false ? (
                <Details summary="Text we read from the document">
                  <DocumentText text={doc.text} elements={r.elements} />
                </Details>
              ) : (
                <DocumentText text={doc.text} elements={r.elements} />
              )}
              <HighlightKey />
            </section>

            <section aria-labelledby="found-title" className="app-split__findings">
              <h2 className="govuk-heading-m govuk-!-margin-bottom-1" id="found-title">
                What the tool found
              </h2>
              <p className="govuk-body-s app-secondary-text">
                {[para && `Schedule 1, paragraph ${para.number}`, para?.guidance, r.agreement].filter(Boolean).join(" · ")}
              </p>
              <LaaCheckLine check={c.laaCheck} />
              {r.flags.map((flag) => (
                <WarningText key={flag}>{flag}</WarningText>
              ))}
              {r.elements.length === 0 && <p className="govuk-body">{r.reason}</p>}
              <ol className="app-findings">
                {r.elements.map((e, i) => (
                  <li className="app-findings__item" key={e.key}>
                    <span className={e.status === "met" ? "app-mark__number" : "app-mark__number app-mark__number--problem"} aria-hidden="true">
                      {i + 1}
                    </span>
                    <div className="app-findings__body">
                      <div className="app-findings__head">
                        <span className="govuk-body govuk-!-font-weight-bold govuk-!-margin-bottom-0">{e.label}</span>
                        <ElementTag status={e.status} />
                      </div>
                      {e.quote && <p className="govuk-body-s app-secondary-text govuk-!-margin-bottom-1">“{e.quote}”</p>}
                      {e.status !== "met" && <p className="govuk-body-s govuk-!-margin-bottom-0">{e.explanation}</p>}
                    </div>
                  </li>
                ))}
              </ol>
              <PartyCheck doc={doc} applicant={c.applicantName} otherParty={c.otherPartyName} />
              <VerificationList checks={r.verification} />
            </section>
          </div>
        </div>
      )}

      <section aria-labelledby="decision-title" className="app-decision">
        <h2 className="govuk-heading-l" id="decision-title">
          Your decision
        </h2>
        <div className="govuk-form-group">
          <label className="govuk-label govuk-label--s" htmlFor="note">
            {needsNote ? "Return note" : "Note (optional)"}
          </label>
          <div className="govuk-hint" id="note-hint">
            {needsNote ? "Drafted from what is missing in the submitted documents. Edit it before you send it." : "Add a note to the case record if you need to."}
          </div>
          <textarea
            className="govuk-textarea"
            id="note"
            name="note"
            rows={needsNote ? 14 : 3}
            value={note}
            onChange={(event) => setNote(event.target.value)}
            aria-describedby="note-hint"
          />
        </div>
        {/* Equal weight on purpose: the caseworker decides, not the tool. */}
        <div className="govuk-button-group">
          <Button variant="secondary" onClick={() => onDecide("return", note)}>
            Return with note
          </Button>
          <Button variant="secondary" onClick={() => onDecide("accept", note)}>
            Accept evidence
          </Button>
          <Button variant="secondary" onClick={() => onDecide("refer", note)}>
            Refer to senior caseworker
          </Button>
        </div>
        <p className="govuk-body-s app-secondary-text">
          This tool supports your decision. The decision is yours. We record your decision and whether it matches the tool’s verdict.
        </p>
      </section>
    </CaseworkerLayout>
  );
}
