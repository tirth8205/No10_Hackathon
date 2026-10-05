import type { VerificationCheck, VerificationStatus } from "../lib/types";

const TAG: Record<VerificationStatus, { label: string; colour: string }> = {
  pass: { label: "Checks out", colour: "green" },
  warn: { label: "Look closer", colour: "yellow" },
  fail: { label: "Does not match", colour: "red" },
  unknown: { label: "Not checked", colour: "grey" },
};

/** Links can originate from the document itself; render only http(s). */
const isSafeHref = (u: string | null): u is string => {
  if (!u) return false;
  try {
    const p = new URL(u, window.location.origin);
    return p.protocol === "https:" || p.protocol === "http:";
  } catch {
    return false;
  }
};

/** Checks on the author and organisation, with a link to verify each one. They support a person's decision; they never make it. */
export function VerificationList({ checks }: { checks?: VerificationCheck[] | null }) {
  if (!checks || checks.length === 0) return null;
  return (
    <section aria-labelledby="verification-title" className="govuk-!-margin-top-6">
      <h3 className="govuk-heading-s govuk-!-margin-bottom-1" id="verification-title">
        Verifying the author and organisation
      </h3>
      <p className="govuk-body-s app-secondary-text">Automatic look-ups to help you check. They do not change the result.</p>
      <dl className="govuk-summary-list govuk-summary-list--no-border">
        {checks.map((v) => (
          <div className="govuk-summary-list__row" key={v.id}>
            <dt className="govuk-summary-list__key govuk-!-font-size-16">{v.label}</dt>
            <dd className="govuk-summary-list__value govuk-!-font-size-16">
              <strong className={`govuk-tag govuk-tag--${TAG[v.status].colour} govuk-!-margin-right-1`}>{TAG[v.status].label}</strong> {v.detail}
            </dd>
            <dd className="govuk-summary-list__actions govuk-!-font-size-16">
              {isSafeHref(v.link) && (
                <a className="govuk-link" href={v.link} target="_blank" rel="noreferrer noopener">
                  Check it<span className="govuk-visually-hidden"> ({v.label}, opens in a new tab)</span>
                </a>
              )}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
