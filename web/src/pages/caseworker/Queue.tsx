import { Link } from "react-router";
import { ButtonLink, NotificationBanner, VerdictTag } from "../../components/govuk";
import { CaseworkerLayout } from "../../components/layout";
import { useTitle } from "../../hooks/govuk";
import { short } from "../../lib/dates";
import { caseVerdict, paraOf, VERDICTS, type Verdict } from "../../lib/labels";
import type { CaseWithDocuments, DecisionAction } from "../../lib/types";
import { paths } from "../../paths";

export type QueueFilter = "all" | "pass" | "refer" | "fail";

export interface QueueProps {
  items: CaseWithDocuments[];
  filter: QueueFilter;
  filterTo: (filter: QueueFilter) => string;
  /** Shown after a decision is recorded. */
  decided?: { ref: string; action: DecisionAction; agreedWithTool: boolean } | null;
}

// Cases that meet the requirements are quick reviews, so they come first (spec 11.4).
const ORDER: Verdict["key"][] = ["pass", "refer", "fail"];

const ACTION_TEXT: Record<DecisionAction, string> = {
  accept: "Evidence accepted",
  return: "Returned with a note",
  refer: "Referred to a senior caseworker",
};

function flagsFor({ case: c, documents }: CaseWithDocuments, verdict: Verdict) {
  const flags = [...new Set(documents.flatMap((d) => d.result?.flags ?? []))];
  const lines = verdict.key === "pass" ? [documents[0]?.result?.agreement ?? ""] : flags;
  return (
    <>
      {lines.map((line) => (
        <span className={`govuk-!-display-block${verdict.key === "pass" ? " app-secondary-text" : ""}`} key={line}>
          {line}
        </span>
      ))}
      {c.submitReason && <span className="govuk-!-display-block govuk-!-font-weight-bold">Submitted with a reason</span>}
    </>
  );
}

export function Queue({ items, filter, filterTo, decided }: QueueProps) {
  useTitle("Evidence queue – Gateway Check");
  const rows = items
    .filter((item) => !item.case.decision)
    .map((data) => ({ data, verdict: caseVerdict(data.documents.map((d) => d.result)) }))
    .sort(
      (a, b) =>
        ORDER.indexOf(a.verdict.key) - ORDER.indexOf(b.verdict.key) ||
        (a.data.case.submittedAt ?? "").localeCompare(b.data.case.submittedAt ?? ""),
    );
  const visible = filter === "all" ? rows : rows.filter((r) => r.verdict.key === filter);
  const count = (key: QueueFilter) => (key === "all" ? rows.length : rows.filter((r) => r.verdict.key === key).length);
  const next = visible[0];

  const tabs: { key: QueueFilter; text: string }[] = [
    { key: "all", text: "All" },
    { key: "pass", text: VERDICTS.pass.label },
    { key: "refer", text: VERDICTS.refer.label },
    { key: "fail", text: VERDICTS.fail.label },
  ];

  return (
    <CaseworkerLayout active="queue">
      {decided && (
        <NotificationBanner title="Success" success>
          <p className="govuk-notification-banner__heading">
            {ACTION_TEXT[decided.action]} for {decided.ref}
          </p>
          <p className="govuk-body">
            {decided.agreedWithTool ? "This matches the tool’s suggestion." : "This is different from the tool’s suggestion."} Both are recorded.
          </p>
        </NotificationBanner>
      )}

      <div className="app-heading-with-action">
        <div>
          <span className="govuk-caption-l">Domestic abuse gateway</span>
          <h1 className="govuk-heading-xl govuk-!-margin-bottom-0">Evidence queue</h1>
        </div>
        {next && (
          <ButtonLink to={paths.review(next.data.case.id)} className="govuk-!-margin-bottom-0">
            Review next case
          </ButtonLink>
        )}
      </div>

      <nav className="app-sub-nav" aria-label="Filter by tool verdict">
        <ul className="app-sub-nav__list">
          {tabs.map((tab) => (
            <li key={tab.key}>
              <Link className="govuk-link app-sub-nav__link" to={filterTo(tab.key)} aria-current={filter === tab.key ? "page" : undefined}>
                {tab.text} ({count(tab.key)})
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      <p className="govuk-body-s app-secondary-text">
        Sorted by the tool’s verdict, then oldest first. Cases that meet the requirements are quick reviews.
      </p>

      <div className="app-table-wrapper">
        <table className="govuk-table">
          <thead className="govuk-table__head">
            <tr className="govuk-table__row">
              <th scope="col" className="govuk-table__header">Case</th>
              <th scope="col" className="govuk-table__header">Provider</th>
              <th scope="col" className="govuk-table__header">Submitted</th>
              <th scope="col" className="govuk-table__header">Evidence</th>
              <th scope="col" className="govuk-table__header">Tool verdict</th>
              <th scope="col" className="govuk-table__header">Flags</th>
            </tr>
          </thead>
          <tbody className="govuk-table__body">
            {visible.map(({ data, verdict }) => (
              <tr className="govuk-table__row" key={data.case.id}>
                <td className="govuk-table__cell">
                  <Link className="govuk-link govuk-!-font-weight-bold" to={paths.review(data.case.id)}>
                    {data.case.ref}
                  </Link>
                  <span className="govuk-!-display-block app-secondary-text">{data.case.applicantName}</span>
                </td>
                <td className="govuk-table__cell">{data.case.firm}</td>
                <td className="govuk-table__cell">{data.case.submittedAt ? short(data.case.submittedAt) : ""}</td>
                <td className="govuk-table__cell">
                  {data.documents.map((d) => {
                    const para = paraOf(d.result);
                    return (
                      <span className="govuk-!-display-block" key={d.id}>
                        {para?.singular ?? "Not matched"}
                        {para && <span className="app-secondary-text"> · Para {para.number}</span>}
                      </span>
                    );
                  })}
                </td>
                <td className="govuk-table__cell">
                  <VerdictTag verdict={verdict} />
                </td>
                <td className="govuk-table__cell">{flagsFor(data, verdict)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {visible.length === 0 && <p className="govuk-body">No cases here.</p>}
    </CaseworkerLayout>
  );
}
