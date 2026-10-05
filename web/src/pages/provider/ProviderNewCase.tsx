import { useState, type FormEvent } from "react";
import { BackLink, Button } from "../../components/govuk";
import { ProviderLayout } from "../../components/layout";
import { useTitle } from "../../hooks/govuk";
import { paths } from "../../paths";

export interface NewCaseInput {
  applicantName: string;
  otherPartyName: string;
  caseType: string;
  askLabel: string;
}

export interface ProviderNewCaseProps {
  firm: string;
  onCreate: (input: NewCaseInput) => void;
}

/** Starts a case without a letter, to share an upload link with the client. */
export function ProviderNewCase({ firm, onCreate }: ProviderNewCaseProps) {
  useTitle("Get an upload link – Gateway Check");
  const [errors, setErrors] = useState<Record<string, string>>({});

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const input = {
      applicantName: String(form.get("applicantName") ?? "").trim(),
      otherPartyName: String(form.get("otherPartyName") ?? "").trim(),
      caseType: String(form.get("caseType") ?? "Child arrangements"),
      askLabel: String(form.get("askLabel") ?? "").trim(),
    };
    const next: Record<string, string> = {};
    if (!input.applicantName) next.applicantName = "Enter your client’s name";
    if (!input.askLabel) next.askLabel = "Enter what you are asking your client for";
    setErrors(next);
    if (Object.keys(next).length === 0) onCreate(input);
  };

  const errorList = Object.entries(errors);

  return (
    <ProviderLayout firm={firm} beforeContent={<BackLink to={paths.provider} />}>
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds">
          {errorList.length > 0 && (
            <div className="govuk-error-summary" data-module="govuk-error-summary">
              <div role="alert">
                <h2 className="govuk-error-summary__title">There is a problem</h2>
                <div className="govuk-error-summary__body">
                  <ul className="govuk-list govuk-error-summary__list">
                    {errorList.map(([field, message]) => (
                      <li key={field}>
                        <a href={`#${field}`}>{message}</a>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          <h1 className="govuk-heading-l">Get an upload link for your client</h1>
          <p className="govuk-body">Your client uploads from their phone. You see each document and its check here.</p>

          <form onSubmit={submit} noValidate>
            <div className={`govuk-form-group${errors.applicantName ? " govuk-form-group--error" : ""}`}>
              <label className="govuk-label govuk-label--s" htmlFor="applicantName">
                Client’s full name
              </label>
              {errors.applicantName && (
                <p className="govuk-error-message">
                  <span className="govuk-visually-hidden">Error:</span> {errors.applicantName}
                </p>
              )}
              <input className="govuk-input govuk-!-width-two-thirds" id="applicantName" name="applicantName" type="text" autoComplete="off" />
            </div>

            <div className="govuk-form-group">
              <label className="govuk-label govuk-label--s" htmlFor="otherPartyName">
                Other party’s full name (optional)
              </label>
              <div className="govuk-hint" id="otherPartyName-hint">
                We check letters against this name. It must match your application.
              </div>
              <input
                className="govuk-input govuk-!-width-two-thirds"
                id="otherPartyName"
                name="otherPartyName"
                type="text"
                autoComplete="off"
                aria-describedby="otherPartyName-hint"
              />
            </div>

            <div className="govuk-form-group">
              <label className="govuk-label govuk-label--s" htmlFor="caseType">
                Case type
              </label>
              <select className="govuk-select" id="caseType" name="caseType" defaultValue="Child arrangements">
                <option>Child arrangements</option>
                <option>Finances</option>
                <option>Child arrangements and finances</option>
              </select>
            </div>

            <div className={`govuk-form-group${errors.askLabel ? " govuk-form-group--error" : ""}`}>
              <label className="govuk-label govuk-label--s" htmlFor="askLabel">
                What are you asking your client for?
              </label>
              <div className="govuk-hint" id="askLabel-hint">
                Your client sees these words. Keep them safe if someone else might see their phone, for example “Letter from your
                support worker”.
              </div>
              {errors.askLabel && (
                <p className="govuk-error-message">
                  <span className="govuk-visually-hidden">Error:</span> {errors.askLabel}
                </p>
              )}
              <input className="govuk-input" id="askLabel" name="askLabel" type="text" autoComplete="off" aria-describedby="askLabel-hint" />
            </div>

            <Button type="submit">Create link</Button>
          </form>
        </div>
      </div>
    </ProviderLayout>
  );
}
