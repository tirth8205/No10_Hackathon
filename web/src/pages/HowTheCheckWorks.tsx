import { PlainLayout } from "../components/layout";
import { useTitle } from "../hooks/govuk";
import { PARAS } from "../lib/labels";

export function HowTheCheckWorks() {
  useTitle("How the check works – Gateway Check");
  return (
    <PlainLayout>
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds">
          <h1 className="govuk-heading-xl">How the check works</h1>
          <p className="govuk-body-l">
            Each document is checked against one paragraph of Schedule 1 to the Civil Legal Aid (Procedure) Regulations 2012 and the LAA’s
            evidence requirements guidance, version 15.
          </p>
          <ul className="govuk-list govuk-list--bullet">
            <li>Every requirement is marked included, missing or unclear.</li>
            <li>Anything marked included quotes the exact wording it relied on, and the quote is checked against the document.</li>
            <li>Hedged wording such as “might be consistent with” does not meet a requirement that needs a clear judgement.</li>
            <li>If the checks disagree or a quote cannot be found, a caseworker decides.</li>
            <li>One document that meets every requirement is enough.</li>
            <li>The tool never approves or refuses anything. People decide.</li>
          </ul>

          <h2 className="govuk-heading-m">Evidence types</h2>
          <table className="govuk-table">
            <thead className="govuk-table__head">
              <tr className="govuk-table__row">
                <th scope="col" className="govuk-table__header">Paragraph</th>
                <th scope="col" className="govuk-table__header">Evidence</th>
                <th scope="col" className="govuk-table__header">Guidance</th>
              </tr>
            </thead>
            <tbody className="govuk-table__body">
              {Object.values(PARAS).map((p) => (
                <tr className="govuk-table__row" key={p.number}>
                  <td className="govuk-table__cell">{p.number}</td>
                  <td className="govuk-table__cell">{p.singular}</td>
                  <td className="govuk-table__cell">{p.guidance}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </PlainLayout>
  );
}

export function NotFound() {
  useTitle("Page not found");
  return (
    <PlainLayout>
      <h1 className="govuk-heading-l">Page not found</h1>
      <p className="govuk-body">If you typed the web address, check it is correct.</p>
    </PlainLayout>
  );
}
