import { BackLink } from "../../components/govuk";
import { ProviderLayout } from "../../components/layout";
import { useTitle } from "../../hooks/govuk";
import { when } from "../../lib/dates";
import { documentTitle } from "../../lib/evidence";
import type { Case, CaseDocument } from "../../lib/types";
import { paths } from "../../paths";

/** The uploaded document itself: photos or files, and the text read from them. */
export function DocumentFile({ c, doc }: { c: Case; doc: CaseDocument }) {
  const title = documentTitle(doc);
  useTitle(`${title} – Gateway Check`);
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

      {doc.text && (
        <>
          <h2 className="govuk-heading-m">Text read from the document</h2>
          <div className="app-document">{doc.text}</div>
        </>
      )}
    </ProviderLayout>
  );
}
