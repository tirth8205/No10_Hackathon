import { useState, type FormEvent } from "react";
import { CopyButton } from "../../components/CopyButton";
import { Button, VerdictTag } from "../../components/govuk";
import { CaseworkerLayout } from "../../components/layout";
import { DropZone } from "../../components/Upload";
import { useTitle } from "../../hooks/govuk";
import { docVerdict, paraOf } from "../../lib/labels";
import type { CaseDocument } from "../../lib/types";

export interface InboxDraft {
  email: string;
  documents: CaseDocument[];
  reply: string;
}

export interface InboxProps {
  /** The drafted reply, once the attachments have been checked. */
  draft?: InboxDraft | null;
  onDraft: (email: string, files: File[]) => void;
}

/** Evidence-check inbox: paste a provider's query, add the attachments, get a drafted reply. */
export function Inbox({ draft, onDraft }: InboxProps) {
  useTitle("Draft a reply – Inbox – Gateway Check");
  const [files, setFiles] = useState<File[]>([]);
  const [reply, setReply] = useState(draft?.reply ?? "");

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const email = String(new FormData(event.currentTarget).get("email") ?? "");
    onDraft(email, files);
  };

  const attachments = draft ? draft.documents.map((d) => d.pages[0]?.filename ?? "Attachment") : files.map((f) => f.name);

  return (
    <CaseworkerLayout active="inbox">
      <span className="govuk-caption-l">Evidence check inbox</span>
      <h1 className="govuk-heading-xl">Draft a reply</h1>
      <p className="govuk-body govuk-!-margin-bottom-8">
        Paste the provider’s email and add the attachments. Each document is checked and a reply is drafted for you to edit.
      </p>

      <div className="app-split">
        <section aria-labelledby="query-title">
          <h2 className="govuk-heading-m" id="query-title">
            The query
          </h2>
          <form onSubmit={submit} noValidate>
            <div className="govuk-form-group">
              <label className="govuk-label govuk-label--s" htmlFor="email">
                Email from the provider
              </label>
              <textarea className="govuk-textarea" id="email" name="email" rows={10} defaultValue={draft?.email} />
            </div>

            <h3 className="govuk-heading-s">Attachments</h3>
            {attachments.length > 0 && (
              <ul className="govuk-list app-attachment-list">
                {attachments.map((name) => (
                  <li key={name}>{name}</li>
                ))}
              </ul>
            )}
            <DropZone compact label="Drop attachments here" onFiles={(added) => setFiles((current) => [...current, ...added])} />
            <Button type="submit">Draft reply</Button>
          </form>
        </section>

        <section aria-labelledby="reply-title">
          <h2 className="govuk-heading-m" id="reply-title">
            Draft reply
          </h2>
          {draft ? (
            <>
              <ul className="govuk-list app-inbox-results">
                {draft.documents.map((d) => {
                  const para = paraOf(d.result);
                  return (
                    <li key={d.id}>
                      <span className="govuk-!-font-weight-bold govuk-!-display-block">{d.pages[0]?.filename}</span>
                      <span className="govuk-body-s app-secondary-text">
                        {[para ? `${para.singular} · Para ${para.number}` : "Not matched", d.result?.agreement].filter(Boolean).join(" · ")}
                      </span>
                      <VerdictTag verdict={docVerdict(d.result)} />
                    </li>
                  );
                })}
              </ul>
              <div className="govuk-form-group">
                <label className="govuk-label govuk-label--s" htmlFor="reply">
                  Reply
                </label>
                <div className="govuk-hint" id="reply-hint">
                  Check and edit it before you send it.
                </div>
                <textarea
                  className="govuk-textarea"
                  id="reply"
                  name="reply"
                  rows={18}
                  value={reply}
                  onChange={(event) => setReply(event.target.value)}
                  aria-describedby="reply-hint"
                />
              </div>
              <CopyButton text={reply} label="Copy reply" />
            </>
          ) : (
            <p className="govuk-body app-secondary-text">The reply appears here once the attachments are checked.</p>
          )}
        </section>
      </div>
    </CaseworkerLayout>
  );
}
