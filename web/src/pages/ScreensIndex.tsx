import { Link } from "react-router";
import { PlainLayout } from "../components/layout";
import { useTitle } from "../hooks/govuk";
import { paths } from "../paths";
import { CLIENT_TOKEN } from "../sample/cases";

interface ScreenLink {
  to: string;
  text: string;
  hint?: string;
}

const CLIENT: ScreenLink[] = [
  { to: paths.client(CLIENT_TOKEN), text: "Send your letter", hint: "Upload by one-time link" },
  { to: paths.clientChecking(CLIENT_TOKEN), text: "Checking your document" },
  { to: paths.clientResult(CLIENT_TOKEN, "change"), text: "Result: needs a change" },
  { to: paths.clientResult(CLIENT_TOKEN, "ready"), text: "Result: meets the requirements" },
  { to: paths.clientResult(CLIENT_TOKEN, "check"), text: "Result: your solicitor will check" },
  { to: paths.clientResult(CLIENT_TOKEN, "other"), text: "Result: not an accepted evidence type" },
  { to: paths.clientExpired, text: "Link no longer works" },
];

const PROVIDER: ScreenLink[] = [
  { to: paths.provider, text: "Cases", hint: "Drop a letter to start a case" },
  { to: paths.providerNewCase, text: "Get an upload link for your client" },
  { to: paths.caseEvidence("gc-0142"), text: "Case › Evidence", hint: "Before the corrected letter" },
  { to: paths.caseDocument("gc-0142", "d-brookfield-1"), text: "Letter needs a change", hint: "The fix and the drafted request" },
  { to: paths.caseEvidence("gc-0142-corrected"), text: "Case › Evidence", hint: "After the corrected letter: suggested, older versions kept" },
  { to: paths.caseClient("gc-0142-corrected"), text: "Case › Client", hint: "Upload link and what the client was told" },
  { to: paths.caseDocument("gc-0142-corrected", "d-brookfield-2"), text: "Letter meets the requirements" },
  { to: paths.caseSubmit("gc-0142-corrected", ["d-brookfield-2"]), text: "Check what you’re submitting" },
  { to: paths.caseSubmit("gc-0142", ["d-brookfield-1"]), text: "Check what you’re submitting", hint: "Likely to be returned: reason needed" },
  { to: paths.caseDetails("gc-0142-corrected"), text: "Change details" },
];

const CASEWORKER: ScreenLink[] = [
  { to: paths.queue, text: "Evidence queue" },
  { to: paths.review("gc-0130"), text: "Review", hint: "Hedged GP letter and a refuge letter that does not name the other party" },
  { to: paths.review("gc-0142-submitted"), text: "Review", hint: "Meets the requirements" },
  { to: paths.review("gc-0134"), text: "Review", hint: "Instructions to the reviewer hidden in the letter" },
  { to: paths.inbox, text: "Inbox: draft a reply" },
  { to: `${paths.inbox}?state=drafted`, text: "Inbox: reply drafted" },
];

function Group({ title, intro, links }: { title: string; intro: string; links: ScreenLink[] }) {
  return (
    <section className="govuk-!-margin-bottom-8">
      <h2 className="govuk-heading-m govuk-!-margin-bottom-1">{title}</h2>
      <p className="govuk-body app-secondary-text">{intro}</p>
      <ul className="govuk-list govuk-list--spaced">
        {links.map((link) => (
          <li key={link.to}>
            <Link className="govuk-link" to={link.to}>
              {link.text}
            </Link>
            {link.hint && <span className="govuk-body-s app-secondary-text"> · {link.hint}</span>}
          </li>
        ))}
      </ul>
    </section>
  );
}

export function ScreensIndex() {
  useTitle("Screens – Gateway Check");
  return (
    <PlainLayout>
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds">
          <h1 className="govuk-heading-xl">Gateway Check screens</h1>
          <p className="govuk-body-l">Front-end screens for the three people involved in a domestic abuse gateway application.</p>
          <p className="govuk-body">The screens show sample data and are not connected to a back end yet.</p>
          <Group title="1. Client" intro="On their phone. Assume someone else may see it." links={CLIENT} />
          <Group title="2. Solicitor" intro="At their desk, on a case." links={PROVIDER} />
          <Group title="3. LAA caseworker" intro="Reviewing what was submitted." links={CASEWORKER} />
        </div>
      </div>
    </PlainLayout>
  );
}
