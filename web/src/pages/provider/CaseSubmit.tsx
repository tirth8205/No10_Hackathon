import { useState, type FormEvent } from "react";
import { Link } from "react-router";
import { AsideBlock } from "../../components/CaseParts";
import { Breadcrumbs, Button, NotificationBanner, Panel, Tag, VerdictTag, WarningText } from "../../components/govuk";
import { ProviderLayout } from "../../components/layout";
import { useTitle } from "../../hooks/govuk";
import { documentTitle, selectionState } from "../../lib/evidence";
import { docVerdict, paraOf } from "../../lib/labels";
import { daysIfRight, minDaysIfReturned, minDaysSaved } from "../../lib/nudges";
import type { CaseWithDocuments } from "../../lib/types";
import { paths } from "../../paths";

export interface CaseSubmitProps {
  data: CaseWithDocuments;
  selectedIds: string[];
  /** True once the pack has been downloaded. */
  done?: boolean;
  /** Builds the pack for Civil Apply. A reason is required when nothing selected meets the requirements. */
  onDownload: (reason: string | null) => void;
}

/** Check what you're submitting, then download the pack for Civil Apply. Never blocked. */
export function CaseSubmit({ data, selectedIds, done, onDownload }: CaseSubmitProps) {
  const { case: c, documents } = data;
  useTitle(`Check what you’re submitting – ${c.applicantName} – Gateway Check`);
  const selected = documents.filter((d) => selectedIds.includes(d.id));
  const others = documents.length - selected.length;
  const state = selectionState(documents, selectedIds);
  const passing = selected.find((d) => docVerdict(d.result).key === "pass");
  const [reasonError, setReasonError] = useState<string | null>(null);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const reason = String(new FormData(event.currentTarget).get("reason") ?? "").trim();
    if (state === "risky" && !reason) {
      setReasonError("Enter why you are submitting now");
      return;
    }
    setReasonError(null);
    onDownload(state === "risky" ? reason : null);
  };

  return (
    <ProviderLayout
      firm={c.firm}
      beforeContent={
        <Breadcrumbs
          items={[
            { text: "Cases", to: paths.provider },
            { text: c.applicantName, to: paths.caseEvidence(c.id) },
            { text: "Submit" },
          ]}
        />
      }
    >
      {done && (
        <NotificationBanner title="Success" success>
          <p className="govuk-notification-banner__heading">Your pack for Civil Apply has downloaded</p>
          <p className="govuk-body">Upload it as the evidence in Civil Apply.</p>
        </NotificationBanner>
      )}

      <span className="govuk-caption-l">
        {c.applicantName} · {c.ref}
      </span>
      <h1 className="govuk-heading-xl">Check what you’re submitting</h1>

      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds">
          {state === "good" && passing && (
            <Panel title="Ready to submit" headingLevel={2}>
              The letter you’ve selected meets all {passing.result?.elements.length} requirements for paragraph {passing.result?.matchedPara}.
            </Panel>
          )}
          {state === "risky" && <WarningText>None of the documents you’ve selected meets the requirements. It is likely to be returned.</WarningText>}
          {state === "none" && (
            <div className="govuk-error-summary" data-module="govuk-error-summary">
              <div role="alert">
                <h2 className="govuk-error-summary__title">There is a problem</h2>
                <div className="govuk-error-summary__body">
                  <ul className="govuk-list govuk-error-summary__list">
                    <li>
                      <Link to={paths.caseEvidence(c.id)}>Select at least one document to submit</Link>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          <h2 className="govuk-heading-m">Evidence you’re submitting</h2>
          <dl className="govuk-summary-list">
            {selected.map((d) => {
              const para = paraOf(d.result);
              return (
                <div className="govuk-summary-list__row" key={d.id}>
                  <dt className="govuk-summary-list__key">
                    {documentTitle(d)}
                    <span className="govuk-body-s app-secondary-text govuk-!-display-block govuk-!-font-weight-regular govuk-!-margin-top-1">
                      {para ? `${para.singular} · Schedule 1, paragraph ${para.number}` : "Not an accepted evidence type"}
                    </span>
                  </dt>
                  <dd className="govuk-summary-list__value">
                    <VerdictTag verdict={docVerdict(d.result)} />
                  </dd>
                  <dd className="govuk-summary-list__actions">
                    <Link className="govuk-link" to={paths.caseEvidence(c.id)}>
                      Change<span className="govuk-visually-hidden"> evidence you are submitting</span>
                    </Link>
                  </dd>
                </div>
              );
            })}
          </dl>
          {others > 0 && (
            <p className="govuk-body-s app-secondary-text govuk-!-margin-bottom-8">
              {others === 1 ? "1 other document stays" : `${others} other documents stay`} on file and won’t be included.{" "}
              <Link className="govuk-link" to={paths.caseEvidence(c.id)}>
                See all evidence
              </Link>
            </p>
          )}

          {state !== "none" && (
            <form onSubmit={submit} noValidate>
              {state === "risky" && (
                <div className={`govuk-form-group${reasonError ? " govuk-form-group--error" : ""}`}>
                  <label className="govuk-label govuk-label--s" htmlFor="reason">
                    Why are you submitting now?
                  </label>
                  <div className="govuk-hint" id="reason-hint">
                    The caseworker will see this.
                  </div>
                  {reasonError && (
                    <p className="govuk-error-message" id="reason-error">
                      <span className="govuk-visually-hidden">Error:</span> {reasonError}
                    </p>
                  )}
                  <textarea
                    className={`govuk-textarea${reasonError ? " govuk-textarea--error" : ""}`}
                    id="reason"
                    name="reason"
                    rows={3}
                    aria-describedby={reasonError ? "reason-hint reason-error" : "reason-hint"}
                  />
                </div>
              )}

              <h2 className="govuk-heading-m">Submit in Civil Apply</h2>
              <ol className="govuk-list govuk-list--number">
                <li>
                  <p className="govuk-body">Download the letter and its verification summary.</p>
                  <Button type="submit" className="govuk-!-margin-bottom-2">
                    Download for Civil Apply
                  </Button>
                  <p className="govuk-body-s app-secondary-text">One zip file with the letter and its summary.</p>
                </li>
                <li>Upload both as the evidence in Civil Apply. The caseworker sees what was checked and the sentences relied on.</li>
              </ol>
            </form>
          )}
        </div>

        <div className="govuk-grid-column-one-third">
          <AsideBlock title="Getting paid">
            {state === "risky" ? (
              <>
                <span className="app-key-figure__prefix">At least</span>
                <span className="app-key-figure__number">{minDaysIfReturned}</span>
                <p className="govuk-body govuk-!-margin-top-2">working days to approval if it’s returned. The LAA pays you once eligibility is approved.</p>
              </>
            ) : (
              <>
                <span className="app-key-figure__number">{daysIfRight}</span>
                <p className="govuk-body govuk-!-margin-top-2">working days to approval. The LAA pays you once eligibility is approved.</p>
                <p className="govuk-body">Getting the evidence right first should get you paid at least {minDaysSaved} working days sooner.</p>
              </>
            )}
            <p className="govuk-body-s app-secondary-text">Estimate based on published LAA processing times.</p>
          </AsideBlock>
          <AsideBlock title="Faster review">
            <Tag colour="blue" className="govuk-!-margin-bottom-2">
              Proposed pilot
            </Tag>
            <p className="govuk-body-s">Applications checked before submission could be reviewed faster. This is not in place yet.</p>
          </AsideBlock>
        </div>
      </div>
    </ProviderLayout>
  );
}
