import { Link } from "react-router";
import { CaseHeading, CaseTabs } from "../../components/CaseParts";
import { CopyButton } from "../../components/CopyButton";
import { Breadcrumbs, Button, SummaryList, VerdictTag } from "../../components/govuk";
import { ProviderLayout } from "../../components/layout";
import { useTitle } from "../../hooks/govuk";
import { capitalise, dayMonth, when } from "../../lib/dates";
import { documentTitle } from "../../lib/evidence";
import { caseVerdict, docVerdict } from "../../lib/labels";
import { clientMessage, firstName } from "../../lib/outputs";
import type { CaseWithDocuments } from "../../lib/types";
import { paths } from "../../paths";

export interface CaseClientProps {
  data: CaseWithDocuments;
  /** Full URL of the client's one-time link, or null if there is none. */
  clientLinkUrl: string | null;
  onTurnOffLink: () => void;
  onCreateLink: () => void;
}

/** The client side of the case: details used for the name check, the upload link, and what the client was told. */
export function CaseClient({ data, clientLinkUrl, onTurnOffLink, onCreateLink }: CaseClientProps) {
  const { case: c, documents } = data;
  const name = firstName(c);
  useTitle(`${c.applicantName} – Client – Gateway Check`);
  const verdict = caseVerdict(documents.map((d) => d.result));
  const fromClient = documents.filter((d) => d.uploadedBy === "client").sort((a, b) => b.uploadedAt.localeCompare(a.uploadedAt));

  return (
    <ProviderLayout firm={c.firm} beforeContent={<Breadcrumbs items={[{ text: "Cases", to: paths.provider }, { text: c.applicantName }]} />}>
      <CaseHeading c={c} verdict={verdict} />
      <CaseTabs caseId={c.id} active="client" evidenceCount={documents.length} />

      <div className="govuk-grid-row">
        <div className="govuk-grid-column-two-thirds">
          <h2 className="govuk-heading-m">Details</h2>
          <SummaryList
            className="govuk-!-margin-bottom-9"
            rows={[
              { key: "Client", value: c.applicantName },
              {
                key: "Other party",
                value: (
                  <>
                    {c.otherPartyName || "Not known yet"}
                    <span className="govuk-hint govuk-!-display-block govuk-!-margin-top-1 govuk-!-margin-bottom-0">
                      We check letters against this name. It must match your application.
                    </span>
                  </>
                ),
                action: { to: paths.caseDetails(c.id), text: "Change", hidden: "other party" },
              },
              { key: "Case type", value: c.caseType },
              { key: "Reference", value: c.ref },
            ]}
          />

          <h2 className="govuk-heading-m">Upload link</h2>
          {clientLinkUrl && c.tokenExpiresAt ? (
            <>
              <SummaryList
                rows={[
                  {
                    key: `Asking ${name} for`,
                    value: (
                      <>
                        {c.askLabel}
                        <span className="govuk-hint govuk-!-display-block govuk-!-margin-top-1 govuk-!-margin-bottom-0">
                          {name} sees these words. Keep them safe if someone else might see their phone.
                        </span>
                      </>
                    ),
                    action: { to: paths.caseDetails(c.id), text: "Change", hidden: "what you are asking for" },
                  },
                  { key: "Link", value: <span className="app-break-anywhere">{clientLinkUrl}</span> },
                  { key: "Works until", value: dayMonth(c.tokenExpiresAt) },
                ]}
              />
              <div className="govuk-button-group">
                <CopyButton text={clientLinkUrl} label="Copy link" variant="secondary" />
                <Button variant="secondary" onClick={onTurnOffLink}>
                  Turn off link
                </Button>
              </div>
              <p className="govuk-body-s app-secondary-text govuk-!-margin-bottom-9">
                Share it in a way that is safe for {name}. Gateway Check never contacts your client.
              </p>
            </>
          ) : (
            <>
              <p className="govuk-body">There is no active link.</p>
              <Button variant="secondary" onClick={onCreateLink}>
                Create a new link
              </Button>
            </>
          )}

          <h2 className="govuk-heading-m">What {name} has sent</h2>
          {fromClient.length === 0 ? (
            <p className="govuk-body">Nothing yet.</p>
          ) : (
            <>
              <p className="govuk-body">After each upload {name} sees a short result. This is exactly what {name} was told.</p>
              <ol className="app-timeline">
                {fromClient.map((doc) => {
                  const v = docVerdict(doc.result);
                  const told = doc.result ? clientMessage(doc.result) : null;
                  return (
                    <li key={doc.id} className={v.key === "pass" ? "app-timeline__item app-timeline__item--success" : "app-timeline__item"}>
                      <p className="govuk-body-s app-secondary-text govuk-!-margin-bottom-1">
                        {capitalise(when(doc.uploadedAt))} · {doc.pages.length === 1 ? "1 file" : `${doc.pages.length} files`}
                      </p>
                      <p className="govuk-body govuk-!-margin-bottom-2">
                        <Link className="govuk-link govuk-!-font-weight-bold" to={paths.caseEvidence(c.id)}>
                          {documentTitle(doc)}
                        </Link>{" "}
                        <VerdictTag verdict={v} />
                      </p>
                      {told && (
                        <div className="govuk-inset-text govuk-!-margin-top-2 govuk-!-margin-bottom-0">
                          <span className="govuk-body-s app-secondary-text govuk-!-display-block govuk-!-margin-bottom-1">{name} was told</span>
                          <span className="govuk-body-s">
                            “{[told.title + ".", told.body, told.addBody].filter(Boolean).join(" ")}”
                          </span>
                        </div>
                      )}
                    </li>
                  );
                })}
              </ol>
            </>
          )}
        </div>
      </div>
    </ProviderLayout>
  );
}
