import { Link } from "react-router";
import { AsideBlock, RequirementsList } from "../../components/CaseParts";
import { CopyButton, downloadText } from "../../components/CopyButton";
import { Breadcrumbs, Button, ButtonLink, Details, InsetText, VerdictTag, WarningText } from "../../components/govuk";
import { ProviderLayout } from "../../components/layout";
import { FixFirstBanner } from "../../components/PaymentBanner";
import { DropZone } from "../../components/Upload";
import { useTitle } from "../../hooks/govuk";
import { dayMonth, when } from "../../lib/dates";
import { documentTitle } from "../../lib/evidence";
import { docVerdict, paraOf } from "../../lib/labels";
import { firstName, requestLetter } from "../../lib/outputs";
import type { Case, CaseDocument } from "../../lib/types";
import { paths } from "../../paths";

export interface DocumentCheckProps {
  c: Case;
  doc: CaseDocument;
  /** A newer version of the same letter, if one has arrived. */
  replacedBy?: CaseDocument | null;
  onUploadCorrected: (files: File[]) => void;
}

/** One document's check: the fix, the drafted request, and every requirement. */
export function DocumentCheck({ c, doc, replacedBy, onUploadCorrected }: DocumentCheckProps) {
  const r = doc.result;
  const title = documentTitle(doc);
  const verdict = docVerdict(r);
  const para = paraOf(r);
  const name = firstName(c);
  useTitle(`${title} – ${verdict.label} – Gateway Check`);

  const uploader = doc.uploadedBy === "client" ? `Uploaded by ${name}` : "Uploaded by you";
  const missing = r?.elements.filter((e) => e.status !== "met") ?? [];
  const metCount = r ? r.elements.length - missing.length : 0;
  const letter = requestLetter(c, doc);
  const writer = r?.shortOrg ?? "the author";

  return (
    <ProviderLayout
      firm={c.firm}
      beforeContent={
        <Breadcrumbs
          items={[
            { text: "Cases", to: paths.provider },
            { text: c.applicantName, to: paths.caseEvidence(c.id) },
            { text: "Evidence", to: paths.caseEvidence(c.id) },
            { text: title },
          ]}
        />
      }
    >
      <span className="govuk-caption-l">
        {c.applicantName} · {c.ref}
      </span>
      <div className="app-heading-with-tag">
        <h1 className="govuk-heading-l govuk-!-margin-bottom-0">{title}</h1>
        <VerdictTag verdict={verdict} />
      </div>
      <p className="govuk-body app-secondary-text">
        {[para?.singular, `${uploader} ${when(doc.uploadedAt)}`].filter(Boolean).join(" · ")}
      </p>

      {replacedBy && (
        <InsetText>
          This letter has been replaced by the letter of {replacedBy.result?.letterDate ? dayMonth(replacedBy.result.letterDate) : "a later date"}.{" "}
          <Link className="govuk-link" to={paths.caseDocument(c.id, replacedBy.id)}>
            See the newer letter
          </Link>
        </InsetText>
      )}

      {!r && (
        <p className="govuk-body-l" role="status">
          <span className="app-spinner" aria-hidden="true" />
          Checking against Schedule 1. This takes about 20 seconds.
        </p>
      )}

      {r && verdict.key === "fail" && !replacedBy && <FixFirstBanner />}

      {r && (
        <div className="govuk-grid-row">
          <div className="govuk-grid-column-two-thirds">
            {verdict.key === "fail" && (
              <>
                <h2 className="govuk-heading-l">{missing.length === 1 ? "One change before you submit" : `${missing.length} changes before you submit`}</h2>
                <p className="govuk-body">
                  The letter{r.authorOrg ? ` from ${r.authorOrg}` : ""} meets {metCount} of {r.elements.length} requirements for{" "}
                  <Link className="govuk-link" to={paths.howTheCheckWorks}>
                    Schedule 1, paragraph {para?.number}
                  </Link>
                  . {r.reason}
                </p>

                {missing.map((gap) => (
                  <div key={gap.key}>
                    <h3 className="govuk-heading-s govuk-!-margin-bottom-1">{gap.label}</h3>
                    {gap.quote && (
                      <>
                        <p className="govuk-body-s app-secondary-text govuk-!-margin-bottom-0">What the letter says</p>
                        <InsetText>“{gap.quote}”</InsetText>
                      </>
                    )}
                    <p className="govuk-body">{gap.explanation}</p>
                  </div>
                ))}

                <h3 className="govuk-heading-s govuk-!-margin-bottom-1">What to ask {writer} for</h3>
                <ul className="govuk-list govuk-list--bullet">
                  {missing
                    .map((gap) => gap.fix)
                    .filter(Boolean)
                    .map((fix) => (
                      <li key={fix}>{fix}</li>
                    ))}
                </ul>

                <div className="govuk-button-group">
                  <CopyButton text={letter} label={`Copy request to ${writer}`} />
                  <Button variant="secondary" onClick={() => downloadText(`Request to ${writer}.txt`, letter)}>
                    Download request
                  </Button>
                </div>

                <Details summary="Preview the request" open>
                  <div className="app-letter">{letter}</div>
                </Details>

                <h2 className="govuk-heading-m govuk-!-margin-top-8">When the new letter arrives</h2>
                <p className="govuk-body">
                  {name} can upload it with the link, or you can drop it here. We’ll check it straight away.
                </p>
                <DropZone compact label="Drop the corrected letter here" onFiles={onUploadCorrected} />
              </>
            )}

            {verdict.key === "pass" && (
              <>
                <h2 className="govuk-heading-l">This letter meets the requirements</h2>
                <p className="govuk-body">{r.reason} One letter that meets the requirements is enough.</p>
                <ButtonLink to={paths.caseEvidence(c.id)}>Choose what to submit</ButtonLink>
              </>
            )}

            {verdict.key === "refer" && (
              <>
                <h2 className="govuk-heading-l">A caseworker will need to check this</h2>
                <p className="govuk-body">{r.reason}</p>
                {r.flags.map((flag) => (
                  <WarningText key={flag}>{flag}</WarningText>
                ))}
              </>
            )}

            {r.elements.length > 0 && (
              <Details summary={`All ${r.elements.length} requirements for paragraph ${para?.number}`} open={verdict.key !== "fail"}>
                <RequirementsList elements={r.elements} />
              </Details>
            )}

            {verdict.key === "fail" && (
              <>
                <h2 className="govuk-heading-m govuk-!-margin-top-8">Submitting</h2>
                <WarningText>If you submit this letter on its own, it is likely to be returned. {r.reason}</WarningText>
                <p className="govuk-body">
                  <Link className="govuk-link" to={paths.caseEvidence(c.id)}>
                    Choose what to submit
                  </Link>
                </p>
              </>
            )}
          </div>

          <div className="govuk-grid-column-one-third">
            <AsideBlock title="Client upload link">
              <p className="govuk-body-s">
                Asking {name} for: {c.askLabel}.{" "}
                <Link className="govuk-link" to={paths.caseDetails(c.id)}>
                  Change<span className="govuk-visually-hidden"> what you are asking for</span>
                </Link>
              </p>
              {c.tokenExpiresAt && <p className="govuk-body-s">Works until {dayMonth(c.tokenExpiresAt)}.</p>}
              <p className="govuk-body-s">
                <Link className="govuk-link" to={paths.caseClient(c.id)}>
                  Manage the link
                </Link>
              </p>
            </AsideBlock>
            <AsideBlock title="About this check">
              <dl className="app-meta-list govuk-body-s">
                <dt>Evidence type</dt>
                <dd>{para ? `${para.singular} (Sch 1 para ${para.number})` : "Not matched"}</dd>
                {para && (
                  <>
                    <dt>Checked against</dt>
                    <dd>{para.guidance}</dd>
                  </>
                )}
                <dt>Agreement</dt>
                <dd>{r.agreement}</dd>
                <dt>Uploaded</dt>
                <dd>
                  {uploader} {when(doc.uploadedAt)}
                </dd>
              </dl>
            </AsideBlock>
          </div>
        </div>
      )}
    </ProviderLayout>
  );
}
