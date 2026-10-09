// The front door: what Gateway Check is and how one case moves through it, in six steps,
// each with a link into the live demo case. Written for someone opening the link cold.

import { useEffect, useState } from "react";
import { Link } from "react-router";
import { demo, type DemoState } from "../api/backend";
import { PlainLayout } from "../components/layout";
import { useTitle } from "../hooks/govuk";
import { paths } from "../paths";

interface Step {
  heading: string;
  body: string;
  /** Where to see it, given the demo case. */
  link: (d: DemoState | null) => { to: string; text: string } | null;
}

const STEPS: Step[] = [
  {
    heading: "The solicitor opens a case and gives the client a code",
    body: "A case holds the applicant, the other party and what the solicitor needs from the client: a letter from a GP, a refuge, the police. The client gets a link or an 8-character code to type.",
    link: (d) => (d ? { to: paths.caseClient(d.caseId), text: "See the code on Jane Doe's case" } : null),
  },
  {
    heading: "The client sends the letter from their phone",
    body: "Camera or file, no account, no legal wording. The screen says ready, needs a change, or your solicitor will look at it. It never says rejected.",
    link: (d) => (d ? { to: paths.client(d.clientToken), text: "Open Jane's phone" } : null),
  },
  {
    heading: "The letter is checked in about 20 seconds",
    body: "The check finds which paragraph of Schedule 1 the letter is evidence under, then marks every requirement included, missing or unclear. Each included requirement quotes the sentence it rests on, found word for word in the letter. Three independent checks must agree.",
    link: (d) => (d ? { to: paths.caseEvidence(d.caseId), text: "See Jane Doe's evidence and the check" } : null),
  },
  {
    heading: "If something is missing, the fix is already drafted",
    body: "The solicitor sees the one sentence that falls short and a request to the letter writer, ready to send. When the corrected letter arrives it is compared with the old one: what it fixed, what is still missing, anything it lost.",
    link: (d) => (d ? { to: paths.caseEvidence(d.caseId), text: "Open a letter that needs a change" } : null),
  },
  {
    heading: "The solicitor chooses what to submit",
    body: "One letter that meets the requirements is enough. The LAA receives a frozen copy of exactly what was submitted and re-checks it independently.",
    link: (d) => (d ? { to: paths.caseEvidence(d.caseId), text: "Choose what to submit" } : null),
  },
  {
    heading: "The caseworker decides",
    body: "The queue is sorted by the tool's verdict so complete evidence is a quick confirmation. Each review shows the letter itself with the marks on it, whether the names match the application, and look-ups on the author and organisation. Accept, return with a drafted note, or refer. The tool never decides.",
    link: () => ({ to: paths.queue, text: "Open the evidence queue" }),
  },
];

export function Welcome() {
  useTitle("Gateway Check");
  const [state, setState] = useState<DemoState | null>(null);
  useEffect(() => {
    demo().then(setState).catch(() => setState(null));
  }, []);
  return (
    <PlainLayout>
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds">
          <span className="govuk-caption-xl">Domestic abuse evidence for legal aid</span>
          <h1 className="govuk-heading-xl">Gateway Check</h1>
          <p className="govuk-body-l">
            Checks a domestic abuse evidence letter against Schedule 1 before the legal aid application is submitted, so it is
            right first time: the client knows what to send, the solicitor knows what to fix, and the LAA caseworker sees the
            letter with the check's workings on it.
          </p>
          <p className="govuk-body">
            This is a working demo with sample cases. Follow the six steps below on one case, Jane Doe, or{" "}
            <Link className="govuk-link" to="/stage">
              watch all three people side by side
            </Link>
            .
          </p>

          <h2 className="govuk-heading-l govuk-!-margin-top-8">How one case moves through it</h2>
          <ol className="app-steps">
            {STEPS.map((step, i) => {
              const link = step.link(state);
              return (
                <li className="app-steps__item" key={step.heading}>
                  <span className="app-steps__number" aria-hidden="true">
                    {i + 1}
                  </span>
                  <div className="app-steps__body">
                    <h3 className="govuk-heading-m govuk-!-margin-bottom-2">{step.heading}</h3>
                    <p className="govuk-body">{step.body}</p>
                    {link && (
                      <p className="govuk-body">
                        <Link className="govuk-link" to={link.to}>
                          {link.text}
                        </Link>
                      </p>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>

          <h2 className="govuk-heading-l govuk-!-margin-top-8">What keeps it safe</h2>
          <ul className="govuk-list govuk-list--bullet">
            <li>Nothing is marked included without a quote found word for word in the document.</li>
            <li>Three independent checks must agree; if they disagree, a person decides.</li>
            <li>The applicant's and other party's names are matched against the application in code, not by the model.</li>
            <li>Hedged wording, unreadable scans, letters in another language and economic abuse evidence all go to a caseworker.</li>
            <li>The tool suggests. The caseworker decides, and the decision is recorded with whether it matched.</li>
          </ul>
          <p className="govuk-body">
            <Link className="govuk-link" to={paths.howTheCheckWorks}>
              How the check works, paragraph by paragraph
            </Link>
          </p>

          <h2 className="govuk-heading-l govuk-!-margin-top-8">Does it work?</h2>
          <table className="govuk-table">
            <thead className="govuk-table__head">
              <tr className="govuk-table__row">
                <th scope="col" className="govuk-table__header">Test set</th>
                <th scope="col" className="govuk-table__header govuk-table__header--numeric">Letters</th>
                <th scope="col" className="govuk-table__header govuk-table__header--numeric">Agreed</th>
                <th scope="col" className="govuk-table__header govuk-table__header--numeric">False approvals</th>
              </tr>
            </thead>
            <tbody className="govuk-table__body">
              <tr className="govuk-table__row">
                <td className="govuk-table__cell">MoJ's own example letters, as PDFs</td>
                <td className="govuk-table__cell govuk-table__cell--numeric">24</td>
                <td className="govuk-table__cell govuk-table__cell--numeric">24</td>
                <td className="govuk-table__cell govuk-table__cell--numeric">0</td>
              </tr>
              <tr className="govuk-table__row">
                <td className="govuk-table__cell">MoJ's own example letters, as text</td>
                <td className="govuk-table__cell govuk-table__cell--numeric">12</td>
                <td className="govuk-table__cell govuk-table__cell--numeric">11</td>
                <td className="govuk-table__cell govuk-table__cell--numeric">0</td>
              </tr>
              <tr className="govuk-table__row">
                <td className="govuk-table__cell">Synthetic cases across all 22 paragraphs</td>
                <td className="govuk-table__cell govuk-table__cell--numeric">146</td>
                <td className="govuk-table__cell govuk-table__cell--numeric">146</td>
                <td className="govuk-table__cell govuk-table__cell--numeric">0</td>
              </tr>
              <tr className="govuk-table__row">
                <td className="govuk-table__cell">Unseen writing styles</td>
                <td className="govuk-table__cell govuk-table__cell--numeric">35</td>
                <td className="govuk-table__cell govuk-table__cell--numeric">35</td>
                <td className="govuk-table__cell govuk-table__cell--numeric">0</td>
              </tr>
            </tbody>
          </table>
          <p className="govuk-body-s app-secondary-text">
            Built in two days at the 10DS hackathon, 5 and 6 October 2026. Sample data only; no real cases.
          </p>
        </div>
      </div>
    </PlainLayout>
  );
}
