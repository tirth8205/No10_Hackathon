import { ClientLayout } from "../../components/layout";
import { useTitle } from "../../hooks/govuk";

export interface ClientCheckingProps {
  firmName: string;
  /** For example "2 photos of your letter". */
  description: string;
  uploadedAt: string;
}

const time = (iso: string) => {
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
};

export function ClientChecking({ firmName, description, uploadedAt }: ClientCheckingProps) {
  useTitle("Checking – Upload documents");
  return (
    <ClientLayout>
      <span className="govuk-caption-m">{firmName}</span>
      <h1 className="govuk-heading-l">Checking your document</h1>
      <p className="govuk-body" role="status">
        <span className="app-spinner" aria-hidden="true" />
        This takes about 20 seconds.
      </p>

      <div className="app-file-card">
        <div className="app-thumb" aria-hidden="true">
          <span />
          <span />
          <span />
          <span />
        </div>
        <div>
          <p className="govuk-body govuk-!-font-weight-bold govuk-!-margin-bottom-1">{description}</p>
          <p className="govuk-body-s app-secondary-text govuk-!-margin-bottom-0">Uploaded at {time(uploadedAt)}</p>
        </div>
      </div>

      <ul className="govuk-task-list">
        <li className="govuk-task-list__item">
          <div className="govuk-task-list__name-and-hint">Reading your document</div>
          <div className="govuk-task-list__status">Done</div>
        </li>
        <li className="govuk-task-list__item">
          <div className="govuk-task-list__name-and-hint govuk-!-font-weight-bold">Checking it has what’s needed</div>
          <div className="govuk-task-list__status">
            <strong className="govuk-tag">Checking</strong>
          </div>
        </li>
        <li className="govuk-task-list__item">
          <div className="govuk-task-list__name-and-hint">Writing your result</div>
          <div className="govuk-task-list__status govuk-task-list__status--cannot-start-yet">Waiting</div>
        </li>
      </ul>

      <p className="govuk-body">You can close this page if you need to. Your solicitor will still get the result.</p>
    </ClientLayout>
  );
}
