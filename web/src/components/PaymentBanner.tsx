// "Getting paid": the incentive for the solicitor. GOV.UK notification banner,
// emphasis from the type scale only. The return figure is a minimum.

import type { SelectionState } from "../lib/evidence";
import { daysIfRight, ESTIMATE_NOTE, minDaysIfReturned, minDaysSaved } from "../lib/nudges";
import { NotificationBanner, WarningText } from "./govuk";

function Figure({ value, label, prefix, secondary }: { value: number; label: string; prefix?: string; secondary?: boolean }) {
  return (
    <div className={secondary ? "app-key-figure app-key-figure--secondary" : "app-key-figure"}>
      {prefix && <span className="app-key-figure__prefix">{prefix}</span>}
      <span className="app-key-figure__number">{value}</span>
      <span className="app-key-figure__label">{label}</span>
    </div>
  );
}

/** On a document that needs a change: fixing it first gets the solicitor paid sooner. */
export function FixFirstBanner() {
  return (
    <NotificationBanner title="Getting paid">
      <p className="govuk-notification-banner__heading">Get paid at least {minDaysSaved} working days sooner</p>
      <p className="govuk-body">The LAA pays you once eligibility is approved. Fix this letter before you submit to avoid a likely return.</p>
      <div className="app-key-figures">
        <Figure value={daysIfRight} label="working days to approval if you fix it first" />
        <Figure
          value={minDaysIfReturned}
          prefix="At least"
          label="if you submit now. It’s likely to be returned, and you’ll need a new letter before it can be approved."
          secondary
        />
      </div>
      <p className="govuk-body-s app-secondary-text govuk-!-margin-bottom-0">{ESTIMATE_NOTE}</p>
    </NotificationBanner>
  );
}

/** On the Evidence tab: follows what is selected for submission. */
export function SelectionBanner({ state }: { state: SelectionState }) {
  return (
    <NotificationBanner title="Getting paid">
      <p className="govuk-notification-banner__heading">The LAA pays you once eligibility is approved.</p>
      {state === "good" && (
        <div className="app-key-figures">
          <Figure value={daysIfRight} label="working days to approval if you submit what you’ve selected" />
          <Figure value={minDaysIfReturned} prefix="At least" label="if the evidence is returned" secondary />
        </div>
      )}
      {state === "risky" && (
        <>
          <WarningText>None of the documents you’ve selected meets the requirements. It is likely to be returned.</WarningText>
          <div className="app-key-figures">
            <Figure
              value={minDaysIfReturned}
              prefix="At least"
              label="working days to approval. You’ll need a new letter before it can be approved."
            />
            <Figure value={daysIfRight} label="if you select a letter that meets the requirements" secondary />
          </div>
        </>
      )}
      {state === "none" && <p className="govuk-body">Select a document below to see how long approval should take.</p>}
      <p className="govuk-body-s app-secondary-text govuk-!-margin-bottom-0">{ESTIMATE_NOTE}</p>
    </NotificationBanner>
  );
}
