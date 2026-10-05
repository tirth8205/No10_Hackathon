// Pieces shared by the solicitor's case screens.

import type { ReactNode } from "react";
import { Link } from "react-router";
import type { Verdict } from "../lib/labels";
import type { Case, ElementResult } from "../lib/types";
import { paths } from "../paths";
import { ElementTag, VerdictTag } from "./govuk";

export function CaseHeading({ c, verdict }: { c: Case; verdict: Verdict }) {
  return (
    <>
      <span className="govuk-caption-l">
        {c.ref} · {c.caseType}
      </span>
      <div className="app-heading-with-tag">
        <h1 className="govuk-heading-xl govuk-!-margin-bottom-0">{c.applicantName || "New case"}</h1>
        <VerdictTag verdict={verdict} />
      </div>
      <p className="govuk-body app-secondary-text">Other party: {c.otherPartyName || "not known yet"}</p>
    </>
  );
}

export function CaseTabs({ caseId, active, evidenceCount }: { caseId: string; active: "evidence" | "client"; evidenceCount: number }) {
  const tabs = [
    { key: "evidence", to: paths.caseEvidence(caseId), text: `Evidence (${evidenceCount})` },
    { key: "client", to: paths.caseClient(caseId), text: "Client" },
  ];
  return (
    <nav className="app-sub-nav" aria-label="Case sections">
      <ul className="app-sub-nav__list">
        {tabs.map((tab) => (
          <li key={tab.key}>
            <Link className="govuk-link app-sub-nav__link" to={tab.to} aria-current={active === tab.key ? "page" : undefined}>
              {tab.text}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}

/** Every requirement for the paragraph, with its status and the wording relied on. */
export function RequirementsList({ elements }: { elements: ElementResult[] }) {
  return (
    <dl className="govuk-summary-list">
      {elements.map((e) => (
        <div className="govuk-summary-list__row" key={e.key}>
          <dt className="govuk-summary-list__key">{e.label}</dt>
          <dd className="govuk-summary-list__value">
            <ElementTag status={e.status} />
            {e.status === "met" && e.quote && <p className="govuk-body-s app-secondary-text govuk-!-margin-top-2 govuk-!-margin-bottom-0">“{e.quote}”</p>}
            {e.status !== "met" && <p className="govuk-body-s govuk-!-margin-top-2 govuk-!-margin-bottom-0">{e.explanation}</p>}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function AsideBlock({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="app-aside-block" aria-label={title}>
      <h2 className="govuk-heading-s govuk-!-margin-bottom-2">{title}</h2>
      {children}
    </section>
  );
}
