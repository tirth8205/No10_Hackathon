import { Link } from "react-router";
import { DocumentText, HighlightKey } from "../../components/DocumentText";
import { VerificationList } from "../../components/Verification";
import { BackLink, ElementTag, WarningText } from "../../components/govuk";
import { ProviderLayout } from "../../components/layout";
import { useTitle } from "../../hooks/govuk";
import { when } from "../../lib/dates";
import { documentTitle } from "../../lib/evidence";
import { docVerdict, paraOf } from "../../lib/labels";
import type { Case, CaseDocument } from "../../lib/types";
import { paths } from "../../paths";

/** The uploaded document itself: photos or files, and the text read from them, with each
 *  sentence the check relied on highlighted and numbered against the requirement list. */
export function DocumentFile({ c, doc }: { c: Case; doc: CaseDocument }) {
  const title = documentTitle(doc);
  useTitle(`${title} – Gateway Check`);
  const r = doc.result;
  const para = paraOf(r);
  const verdict = docVerdict(r);
  const met = r?.elements.filter((e) => e.status === "met").length ?? 0;
  const missing = r?.elements.filter((e) => e.status !== "met") ?? [];
  return (
    <ProviderLayout firm={c.firm} beforeContent={<BackLink to={paths.caseEvidence(c.id)}>Back to evidence</BackLink>}>
      <span className="govuk-caption-l">
        {c.applicantName} · {c.ref}
      </span>
      <h1 className="govuk-heading-l">{title}</h1>
      <p className="govuk-body app-secondary-text">Uploaded {when(doc.uploadedAt)}</p>

      <h2 className="govuk-heading-m">Files</h2>
      <ul className="govuk-list">
        {doc.pages.map((page) => (
          <li key={page.filename}>
            {page.url ? (
              <a className="govuk-link" href={page.url} target="_blank" rel="noreferrer">
                {page.filename} (opens in a new tab)
              </a>
            ) : (
              page.filename
            )}
          </li>
        ))}
      </ul>

      {r && doc.text ? (
        <div className="app-doc-panel">
          <div className="app-split">
            <section aria-labelledby="doc-text-title">
              <h2 className="govuk-heading-m govuk-!-margin-bottom-1" id="doc-text-title">
                Text read from the document
              </h2>
              <p className="govuk-body-s app-secondary-text">
                Each numbered highlight is the sentence the check relied on for that requirement.
              </p>
              <DocumentText text={doc.text} elements={r.elements} />
              <HighlightKey />
            </section>

            <section aria-labelledby="doc-check-title">
              <h2 className="govuk-heading-m govuk-!-margin-bottom-1" id="doc-check-title">
                What matches and what is missing
              </h2>
              <p className="govuk-body-s app-secondary-text">
                {[para ? `Schedule 1, paragraph ${para.number}` : "Not matched to an evidence type", r.agreement].filter(Boolean).join(" · ")}
              </p>
              <p className="govuk-body">
                <strong className={`govuk-tag govuk-tag--${verdict.colour}`}>{verdict.label}</strong>
                {r.elements.length > 0 && (
                  <>
                    {" "}
                    {met} of {r.elements.length} requirements included
                    {missing.length > 0 && `. Missing: ${missing.map((e) => e.label.toLowerCase()).join("; ")}.`}
                  </>
                )}
              </p>
              {r.flags.map((flag) => (
                <WarningText key={flag}>{flag}</WarningText>
              ))}
              {r.elements.length === 0 && <p className="govuk-body">{r.reason}</p>}
              <ol className="app-findings">
                {r.elements.map((e, i) => (
                  <li className="app-findings__item" key={e.key}>
                    <span className={e.status === "met" ? "app-mark__number" : "app-mark__number app-mark__number--problem"} aria-hidden="true">
                      {i + 1}
                    </span>
                    <div className="app-findings__body">
                      <div className="app-findings__head">
                        <span className="govuk-body govuk-!-font-weight-bold govuk-!-margin-bottom-0">{e.label}</span>
                        <ElementTag status={e.status} />
                      </div>
                      {e.quote && <p className="govuk-body-s app-secondary-text govuk-!-margin-bottom-1">“{e.quote}”</p>}
                      {e.status !== "met" && <p className="govuk-body-s govuk-!-margin-bottom-1">{e.explanation}</p>}
                      {e.status !== "met" && e.fix && (
                        <p className="govuk-body-s govuk-!-margin-bottom-0">
                          <strong>Ask the author to:</strong> {e.fix}
                        </p>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
              <VerificationList checks={r.verification} />
              {missing.length > 0 && (
                <p className="govuk-body">
                  <Link className="govuk-link" to={paths.caseDocument(c.id, doc.id)}>
                    See the drafted request to the author
                  </Link>
                </p>
              )}
            </section>
          </div>
        </div>
      ) : (
        doc.text && (
          <>
            <h2 className="govuk-heading-m">Text read from the document</h2>
            <div className="app-document">{doc.text}</div>
          </>
        )
      )}
    </ProviderLayout>
  );
}
