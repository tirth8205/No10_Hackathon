import { useState, type FormEvent } from "react";
import { Button, cx, Details } from "../../components/govuk";
import { ClientLayout } from "../../components/layout";
import { useTitle } from "../../hooks/govuk";
import { normaliseClientCode } from "../../lib/clientCode";

export interface ClientStartProps {
  /** Opens the client's upload page for a code. Resolves to false when no live link has that code. */
  onSubmit: (code: string) => Promise<boolean>;
}

const EMPTY = "Enter the code your solicitor gave you";
const NOT_FOUND = "We could not find that code. Check it and try again, or ask your solicitor for a new one";

/** The client's way in when they have a code rather than a link. Neutral wording, like every client screen. */
export function ClientStart({ onSubmit }: ClientStartProps) {
  useTitle("Upload documents");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const code = normaliseClientCode(String(new FormData(event.currentTarget).get("code") ?? ""));
    if (!code) {
      setError(EMPTY);
      return;
    }
    setBusy(true);
    const found = await onSubmit(code).catch(() => false);
    setBusy(false);
    setError(found ? null : NOT_FOUND);
  };

  return (
    <ClientLayout>
      {error && (
        <div className="govuk-error-summary" data-module="govuk-error-summary">
          <div role="alert">
            <h2 className="govuk-error-summary__title">There is a problem</h2>
            <div className="govuk-error-summary__body">
              <ul className="govuk-list govuk-error-summary__list">
                <li>
                  <a href="#code">{error}</a>
                </li>
              </ul>
            </div>
          </div>
        </div>
      )}
      <form onSubmit={submit} noValidate>
        <div className={cx("govuk-form-group", error && "govuk-form-group--error")}>
          <h1 className="govuk-label-wrapper">
            <label className="govuk-label govuk-label--l" htmlFor="code">
              Enter your code
            </label>
          </h1>
          <div className="govuk-hint" id="code-hint">
            Your solicitor gave you a code. It has 8 letters and numbers, for example ZEZP-C3DT.
          </div>
          {error && (
            <p className="govuk-error-message" id="code-error">
              <span className="govuk-visually-hidden">Error:</span> {error}
            </p>
          )}
          <input
            className={cx("govuk-input govuk-input--width-10 app-code-input", error && "govuk-input--error")}
            id="code"
            name="code"
            type="text"
            autoComplete="off"
            autoCapitalize="characters"
            spellCheck={false}
            aria-describedby={error ? "code-hint code-error" : "code-hint"}
          />
        </div>
        <Button type="submit">{busy ? "Checking…" : "Continue"}</Button>
      </form>
      <Details summary="I do not have a code">
        Ask your solicitor. They can give you a new code at any time. If they sent you a link, you can open that instead.
      </Details>
    </ClientLayout>
  );
}
