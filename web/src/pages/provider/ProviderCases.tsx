import { useState } from "react";
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

type CaseFilter = "all" | "fail" | "refer" | "pass";
type CaseSort = "needs-you" | "updated" | "name";

const FILTERS: { key: CaseFilter; text: string }[] = [
  { key: "all", text: "All" },
  { key: "fail", text: "Needs a change" },
  { key: "refer", text: "Needs a caseworker check" },
  { key: "pass", text: "Meets the requirements" },
];
const SORTS: { key: CaseSort; text: string }[] = [
  { key: "needs-you", text: "Cases that need you first" },
  { key: "updated", text: "Most recently updated" },
  { key: "name", text: "Client name A to Z" },
];

export function ProviderCases({ firm, cases, onDropLetter, firstTimeRight }: ProviderCasesProps) {
  useTitle("Cases – Gateway Check");
  const [filter, setFilter] = useState<CaseFilter>("all");
  const [sort, setSort] = useState<CaseSort>("needs-you");
  const all = cases.map((data) => ({ data, verdict: caseVerdict(data.documents.map((d) => d.result)) }));
  const byUpdated = (a: (typeof all)[number], b: (typeof all)[number]) => lastUpdated(b.data).localeCompare(lastUpdated(a.data));
  const rows = all
    .filter((r) => filter === "all" || r.verdict.key === filter)
    .sort((a, b) =>
      sort === "name"
        ? a.data.case.applicantName.localeCompare(b.data.case.applicantName)
        : sort === "updated"
          ? byUpdated(a, b)
          : // Cases that need the solicitor first; within a group, the most recently updated at the top.
            ORDER.indexOf(a.verdict.key) - ORDER.indexOf(b.verdict.key) || byUpdated(a, b),
    );
  const count = (key: CaseFilter) => (key === "all" ? all.length : all.filter((r) => r.verdict.key === key).length);

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
      <nav className="app-sub-nav" aria-label="Filter by status">
        <ul className="app-sub-nav__list">
          {FILTERS.map((tab) => (
            <li key={tab.key}>
              <button
                type="button"
                className="govuk-link app-sub-nav__link app-link-button"
                aria-current={filter === tab.key ? "page" : undefined}
                aria-pressed={filter === tab.key}
                onClick={() => setFilter(tab.key)}
              >
                {tab.text} ({count(tab.key)})
              </button>
            </li>
          ))}
        </ul>
      </nav>
      <div className="govuk-form-group govuk-!-margin-bottom-3">
        <label className="govuk-label govuk-label--s" htmlFor="case-sort">
          Sort by
        </label>
        <select className="govuk-select" id="case-sort" value={sort} onChange={(e) => setSort(e.target.value as CaseSort)}>
          {SORTS.map((s) => (
            <option key={s.key} value={s.key}>
              {s.text}
            </option>
          ))}
        </select>
      </div>
      {rows.length === 0 && <p className="govuk-body">No cases with this status.</p>}
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
