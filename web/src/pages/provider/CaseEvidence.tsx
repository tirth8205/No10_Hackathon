import { useState } from "react";
import { Link } from "react-router";
import { CaseHeading, CaseTabs } from "../../components/CaseParts";
import { Breadcrumbs, ButtonLink, Tag, VerdictTag } from "../../components/govuk";
import { ProviderLayout } from "../../components/layout";
import { SelectionBanner } from "../../components/PaymentBanner";
import { DropZone } from "../../components/Upload";
import { useTitle } from "../../hooks/govuk";
import { when } from "../../lib/dates";
import { documentTitle, groupEvidence, selectionState, type EvidenceItem } from "../../lib/evidence";
import { caseVerdict } from "../../lib/labels";
import { daysIfRight, minDaysIfReturned } from "../../lib/nudges";
import { firstName } from "../../lib/outputs";
import type { CaseDocument, CaseWithDocuments } from "../../lib/types";
import { paths } from "../../paths";

export interface CaseEvidenceProps {
  data: CaseWithDocuments;
  onSelectionChange?: (documentIds: string[]) => void;
  onAddDocument: (files: File[]) => void;
}

function pagesLabel(doc: CaseDocument): string {
  const images = doc.pages.filter((p) => p.contentType.startsWith("image/")).length;
  if (images === doc.pages.length) return images === 1 ? "1 photo" : `${images} photos`;
  if (doc.pages[0]?.contentType === "application/pdf") return "PDF";
  return doc.pages[0]?.filename ?? "";
}

function problemSummary(doc: CaseDocument): string | null {
  const gap = doc.result?.elements.find((e) => e.status !== "met");
  if (!gap) return null;
  if (gap.status === "not_met" && gap.quote && gap.quote.length < 40) return `Says “${gap.quote.replace(/\.$/, "")}”`;
  return `${gap.label}: ${gap.status === "not_met" ? "missing" : "unclear"}`;
}

function EvidenceRow({
  item,
  caseId,
  uploaderName,
  checked,
  onToggle,
}: {
  item: EvidenceItem;
  caseId: string;
  uploaderName: string;
  checked: boolean;
  onToggle: () => void;
}) {
  const { doc } = item;
  const id = `select-${doc.id}`;
  const uploader = doc.uploadedBy === "client" ? `Uploaded by ${uploaderName}` : doc.uploadedBy === "provider" ? "Uploaded by you" : "From the inbox";
  const problem = problemSummary(doc);
  return (
    <li className="app-evidence-item">
      <div className="govuk-checkboxes" data-module="govuk-checkboxes">
        <div className="govuk-checkboxes__item">
          <input className="govuk-checkboxes__input" id={id} type="checkbox" checked={checked} onChange={onToggle} disabled={!doc.result} />
          <label className="govuk-label govuk-checkboxes__label govuk-!-font-weight-bold" htmlFor={id}>
            <span className="govuk-visually-hidden">Submit </span>
            {item.title}
          </label>
        </div>
      </div>
      <div className="app-evidence-item__body">
        <div className="app-evidence-item__tags">
          {doc.result ? (
            <VerdictTag verdict={item.verdict} />
          ) : (
            <span className="govuk-body-s">
              <span className="app-spinner" aria-hidden="true" />
              Checking against Schedule 1
            </span>
          )}
          {item.suggested && <Tag colour="purple">Suggested</Tag>}
        </div>
        <p className="govuk-body-s app-secondary-text govuk-!-margin-bottom-1">
          {[`${uploader} ${when(doc.uploadedAt)}`, pagesLabel(doc), problem].filter(Boolean).join(" · ")}
        </p>
        {item.relation && (
          <p className="govuk-body-s govuk-!-margin-bottom-1">
            <strong>{item.relation.label}</strong> {item.relation.text}
          </p>
        )}
        {!doc.result?.matchedPara && doc.result && <p className="govuk-body-s govuk-!-margin-bottom-1">{doc.result.reason}</p>}
        <p className="govuk-body-s govuk-!-margin-bottom-0 app-evidence-item__links">
          <Link className="govuk-link" to={paths.caseDocumentFile(caseId, doc.id)}>
            Open the document<span className="govuk-visually-hidden">: {item.title}</span>
          </Link>
          {doc.result?.matchedPara && (
            <Link className="govuk-link" to={paths.caseDocument(caseId, doc.id)}>
              See the check<span className="govuk-visually-hidden">: {item.title}</span>
            </Link>
          )}
        </p>
      </div>
    </li>
  );
}

/** Every document on the case, grouped and linked, with the solicitor choosing what to submit. */
export function CaseEvidence({ data, onSelectionChange, onAddDocument }: CaseEvidenceProps) {
  const { case: c, documents } = data;
  useTitle(`${c.applicantName} – Evidence – Gateway Check`);
  const [selected, setSelected] = useState<string[]>(c.selectedDocumentIds);
  const groups = groupEvidence(documents);
  const state = selectionState(documents, selected);
  const verdict = caseVerdict(documents.map((d) => d.result));

  const toggle = (docId: string) => {
    const next = selected.includes(docId) ? selected.filter((id) => id !== docId) : [...selected, docId];
    setSelected(next);
    onSelectionChange?.(next);
  };

  const selectedDocs = documents.filter((d) => selected.includes(d.id));
  const count = selectedDocs.length;
  const countText = count === 0 ? "Nothing selected" : count === 1 ? "1 document selected" : `${count} documents selected`;
  const daysText =
    state === "good"
      ? `Approval in about ${daysIfRight} working days (estimate).`
      : state === "risky"
        ? `Likely to be returned. At least ${minDaysIfReturned} working days to approval (estimate).`
        : "Select at least one document to submit.";

  return (
    <ProviderLayout
      firm={c.firm}
      beforeContent={<Breadcrumbs items={[{ text: "Cases", to: paths.provider }, { text: c.applicantName || "New case" }]} />}
    >
      <CaseHeading c={c} verdict={verdict} />
      <CaseTabs caseId={c.id} active="evidence" evidenceCount={documents.length} />

      <SelectionBanner state={state} />

      <h2 className="govuk-heading-l">Choose what to submit</h2>
      <p className="govuk-body govuk-!-margin-bottom-7">
        You only need one letter that meets the requirements. Everything you and {firstName(c)} upload stays here, including older versions.
      </p>

      {groups.map((group) => (
        <section className="app-evidence-group" key={group.key} aria-labelledby={`group-${group.key}`}>
          <h3 className="govuk-heading-m govuk-!-margin-bottom-1" id={`group-${group.key}`}>
            {group.heading}
          </h3>
          <p className="govuk-body-s app-secondary-text">{group.subheading}</p>
          <ul className="app-evidence-list">
            {group.items.map((item) => (
              <EvidenceRow
                key={item.doc.id}
                item={item}
                caseId={c.id}
                uploaderName={firstName(c)}
                checked={selected.includes(item.doc.id)}
                onToggle={() => toggle(item.doc.id)}
              />
            ))}
          </ul>
        </section>
      ))}

      {documents.length === 0 && <p className="govuk-body">No documents yet. Add one below, or share the upload link with your client.</p>}

      <DropZone compact label="Add a document" hint="We check it straight away." onFiles={onAddDocument} />

      <div className="app-selection-summary">
        <div>
          <p className="govuk-heading-m govuk-!-margin-bottom-1" aria-live="polite">
            {countText}
          </p>
          {count > 0 && <p className="govuk-body govuk-!-margin-bottom-1">{selectedDocs.map(documentTitle).join(" · ")}</p>}
          <p className="govuk-body-s app-secondary-text govuk-!-margin-bottom-0">{daysText}</p>
        </div>
        <ButtonLink to={paths.caseSubmit(c.id, selected)}>Continue to submit</ButtonLink>
      </div>
    </ProviderLayout>
  );
}
