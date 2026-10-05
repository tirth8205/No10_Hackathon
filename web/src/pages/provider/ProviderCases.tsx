import { Link } from "react-router";
import { NotificationBanner, VerdictTag } from "../../components/govuk";
import { ProviderLayout } from "../../components/layout";
import { DropZone } from "../../components/Upload";
import { useTitle } from "../../hooks/govuk";
import { dayMonth, short } from "../../lib/dates";
import { suggestedDocument } from "../../lib/evidence";
import { caseVerdict, paraOf } from "../../lib/labels";
import type { CaseWithDocuments } from "../../lib/types";
import { paths } from "../../paths";

export interface ProviderCasesProps {
  firm: string;
  cases: CaseWithDocuments[];
  /** Files dropped to start a new case. */
  onDropLetter: (files: File[]) => void;
  /** Illustrative social-norm nudge. Labelled as such on screen. */
  firstTimeRight?: { yours: number; outOf: number };
}

// Cases that need the solicitor come first.
const ORDER = ["fail", "refer", "none", "checking", "pass"];

function evidenceSummary({ case: c, documents }: CaseWithDocuments) {
  if (documents.length === 0) {
    return (
      <span className="app-secondary-text">
        Waiting for the client to upload
        <span className="govuk-!-display-block govuk-!-margin-top-1">Link shared {dayMonth(c.createdAt)}</span>
      </span>
    );
  }
  const main = suggestedDocument(documents) ?? documents[documents.length - 1];
  const type = paraOf(main.result)?.singular ?? "Document";
  const detail = documents.length > 1 ? `${documents.length} documents` : main.uploadedBy === "client" ? "Uploaded by client" : "Uploaded by you";
  return (
    <>
      {type}
      <span className="govuk-!-display-block govuk-!-margin-top-1 app-secondary-text">{detail}</span>
    </>
  );
}

const lastUpdated = ({ case: c, documents }: CaseWithDocuments) =>
  documents.map((d) => d.uploadedAt).sort().at(-1) ?? c.createdAt;

export function ProviderCases({ firm, cases, onDropLetter, firstTimeRight }: ProviderCasesProps) {
  useTitle("Cases – Gateway Check");
  const rows = [...cases]
    .map((data) => ({ data, verdict: caseVerdict(data.documents.map((d) => d.result)) }))
    .sort((a, b) => ORDER.indexOf(a.verdict.key) - ORDER.indexOf(b.verdict.key));

  return (
    <ProviderLayout firm={firm}>
      <h1 className="govuk-heading-xl">Cases</h1>

      <h2 className="govuk-heading-m">Check a letter</h2>
      <p className="govuk-body">We find the evidence type and the names, then tell you exactly what to fix. It takes about 20 seconds.</p>
      <DropZone label="Drop a letter here to start a new case" hint="PDF, Word or a photo" onFiles={onDropLetter} />
      <p className="govuk-body govuk-!-margin-bottom-9">
        Or{" "}
        <Link className="govuk-link" to={paths.providerNewCase}>
          get an upload link for your client
        </Link>
        . They upload from their phone and you see the result here.
      </p>

      <h2 className="govuk-heading-m govuk-!-margin-bottom-1">Open cases</h2>
      <p className="govuk-body-s app-secondary-text">Cases that need you are at the top.</p>
      <div className="app-table-wrapper">
        <table className="govuk-table">
          <thead className="govuk-table__head">
            <tr className="govuk-table__row">
              <th scope="col" className="govuk-table__header">Client</th>
              <th scope="col" className="govuk-table__header">Other party</th>
              <th scope="col" className="govuk-table__header">Evidence</th>
              <th scope="col" className="govuk-table__header">Status</th>
              <th scope="col" className="govuk-table__header">Updated</th>
            </tr>
          </thead>
          <tbody className="govuk-table__body">
            {rows.map(({ data, verdict }) => (
              <tr className="govuk-table__row" key={data.case.id}>
                <td className="govuk-table__cell">
                  <Link className="govuk-link govuk-!-font-weight-bold" to={paths.caseEvidence(data.case.id)}>
                    {data.case.applicantName}
                  </Link>
                  <span className="govuk-!-display-block govuk-!-margin-top-1 app-secondary-text">
                    {data.case.ref} · {data.case.caseType}
                  </span>
                </td>
                <td className="govuk-table__cell">{data.case.otherPartyName}</td>
                <td className="govuk-table__cell">{evidenceSummary(data)}</td>
                <td className="govuk-table__cell">
                  <VerdictTag verdict={verdict} />
                </td>
                <td className="govuk-table__cell">{short(lastUpdated(data))}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {firstTimeRight && (
        <div className="govuk-!-margin-top-9">
          <NotificationBanner title="This quarter">
            <p className="govuk-notification-banner__heading">
              Most firms get gateway evidence right first time. Yours: {firstTimeRight.yours} of {firstTimeRight.outOf} cases.
            </p>
          </NotificationBanner>
        </div>
      )}
    </ProviderLayout>
  );
}
