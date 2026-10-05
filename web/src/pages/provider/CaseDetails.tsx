import type { FormEvent } from "react";
import { BackLink, Button } from "../../components/govuk";
import { ProviderLayout } from "../../components/layout";
import { useTitle } from "../../hooks/govuk";
import { firstName } from "../../lib/outputs";
import type { Case } from "../../lib/types";
import { paths } from "../../paths";

export interface CaseDetailsProps {
  c: Case;
  onSave: (input: { otherPartyName: string; askLabel: string }) => void;
}

/** Change the names the check relies on and what the client is asked for. */
export function CaseDetails({ c, onSave }: CaseDetailsProps) {
  useTitle(`Change details – ${c.applicantName} – Gateway Check`);
  const name = firstName(c);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    onSave({
      otherPartyName: String(form.get("otherPartyName") ?? "").trim(),
      askLabel: String(form.get("askLabel") ?? "").trim(),
    });
  };

  return (
    <ProviderLayout firm={c.firm} beforeContent={<BackLink to={paths.caseClient(c.id)} />}>
      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds">
          <span className="govuk-caption-l">
            {c.applicantName} · {c.ref}
          </span>
          <h1 className="govuk-heading-l">Change details</h1>
          <form onSubmit={submit} noValidate>
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
                {name} sees these words. Keep them safe if someone else might see their phone.
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
