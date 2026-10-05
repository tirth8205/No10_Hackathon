import { useState, type FormEvent } from "react";
import { ErrorBanner } from "../../components/ErrorBanner";
import { BackLink, Button, cx } from "../../components/govuk";
import { ProviderLayout } from "../../components/layout";
import { useTitle } from "../../hooks/govuk";
import { firstName } from "../../lib/outputs";
import type { Case } from "../../lib/types";
import { paths } from "../../paths";

export interface CaseDetailsInput {
  applicantName: string;
  otherPartyName: string;
  askLabel: string;
}

export interface CaseDetailsProps {
  c: Case;
  onSave: (input: CaseDetailsInput) => void;
}

const NAME_ERROR = "Enter your client’s full name";

/**
 * Change the names the check relies on and what the client is asked for. A case started by
 * dropping a letter has no client name yet, so the name is required here before anything else.
 */
export function CaseDetails({ c, onSave }: CaseDetailsProps) {
  const known = c.applicantName.trim() !== "";
  useTitle(`${known ? "Change details" : "Add your client’s details"} – ${known ? c.applicantName : c.ref} – Gateway Check`);
  const name = known ? firstName(c) : "your client";
  const [nameError, setNameError] = useState<string | null>(null);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const applicantName = String(form.get("applicantName") ?? "").trim();
    if (!applicantName) {
      setNameError(NAME_ERROR);
      return;
    }
    setNameError(null);
    onSave({
      applicantName,
      otherPartyName: String(form.get("otherPartyName") ?? "").trim(),
      askLabel: String(form.get("askLabel") ?? "").trim(),
    });
  };

  return (
    <ProviderLayout firm={c.firm} beforeContent={<BackLink to={paths.caseClient(c.id)} />}>
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds">
          <ErrorBanner
            message={
              nameError && (
                <a className="govuk-link" href="#applicantName">
                  {nameError}
                </a>
              )
            }
          />
          <span className="govuk-caption-l">{known ? `${c.applicantName} · ${c.ref}` : c.ref}</span>
          <h1 className="govuk-heading-l">{known ? "Change details" : "Add your client’s details"}</h1>
          <form onSubmit={submit} noValidate>
            <div className={cx("govuk-form-group", nameError && "govuk-form-group--error")}>
              <label className="govuk-label govuk-label--s" htmlFor="applicantName">
                Your client’s full name
              </label>
              <div className="govuk-hint" id="applicantName-hint">
                We check that each letter names your client, so it must match your application. Changing it checks every letter again.
              </div>
              {nameError && (
                <p className="govuk-error-message" id="applicantName-error">
                  <span className="govuk-visually-hidden">Error:</span> {nameError}
                </p>
              )}
              <input
                className={cx("govuk-input govuk-!-width-two-thirds", nameError && "govuk-input--error")}
                id="applicantName"
                name="applicantName"
                type="text"
                defaultValue={c.applicantName}
                autoComplete="off"
                aria-describedby={nameError ? "applicantName-hint applicantName-error" : "applicantName-hint"}
                aria-required="true"
              />
            </div>
            <div className="govuk-form-group">
              <label className="govuk-label govuk-label--s" htmlFor="otherPartyName">
                Other party’s full name
              </label>
              <div className="govuk-hint" id="otherPartyName-hint">
                We check letters against this name, so it must match your application. Changing it checks every letter again.
              </div>
              <input
                className="govuk-input govuk-!-width-two-thirds"
                id="otherPartyName"
                name="otherPartyName"
                type="text"
                defaultValue={c.otherPartyName}
                autoComplete="off"
                aria-describedby="otherPartyName-hint"
              />
            </div>
            <div className="govuk-form-group">
              <label className="govuk-label govuk-label--s" htmlFor="askLabel">
                What are you asking {name} for?
              </label>
              <div className="govuk-hint" id="askLabel-hint">
                {known ? name : "Your client"} sees these words. Keep them safe if someone else might see their phone.
              </div>
              <input className="govuk-input" id="askLabel" name="askLabel" type="text" defaultValue={c.askLabel} autoComplete="off" aria-describedby="askLabel-hint" />
            </div>
            <Button type="submit">Save</Button>
          </form>
        </div>
      </div>
    </ProviderLayout>
  );
}
