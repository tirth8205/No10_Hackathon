import { Details } from "../../components/govuk";
import { ClientLayout } from "../../components/layout";
import { FileLink, PhoneUpload } from "../../components/Upload";
import { useTitle } from "../../hooks/govuk";
import { dayMonth } from "../../lib/dates";

export interface ClientUploadProps {
  firstName: string;
  /** The firm's name as the client knows it, for example "Hartley & Webb". */
  firmName: string;
  /** What the solicitor asked for, in the solicitor's words. */
  askLabel: string;
  linkExpiresAt: string;
  onFiles: (files: File[]) => void;
}

export function ClientUpload({ firstName, firmName, askLabel, linkExpiresAt, onFiles }: ClientUploadProps) {
  useTitle("Upload documents");
  return (
    <ClientLayout>
      <span className="govuk-caption-m">{firmName}</span>
      <h1 className="govuk-heading-l">Send your letter</h1>
      <p className="govuk-body">Hi {firstName}. We’ll check it straight away and tell you if anything needs to change.</p>

      <div className="app-ask">
        <div className="app-ask__header">
          <span className="govuk-body-s app-secondary-text govuk-!-display-block govuk-!-margin-bottom-0">Your solicitor asked for</span>
          <span className="govuk-body govuk-!-font-weight-bold govuk-!-display-block govuk-!-margin-bottom-0">{askLabel}</span>
        </div>
        <div className="app-ask__body">
          <PhoneUpload onFiles={onFiles} />
          <p className="govuk-hint govuk-!-margin-bottom-0">More than one page? Take a photo of each page. We’ll keep them together.</p>
        </div>
      </div>

      <p className="govuk-body">
        Have a different letter that might help? <FileLink label="Add it here" onFiles={onFiles} />
      </p>

      <Details summary="What happens to my letter?">
        We check it and send it to your solicitor. Nothing is saved on this phone.
      </Details>

      <p className="govuk-body-s app-secondary-text">This link works until {dayMonth(linkExpiresAt)}.</p>
    </ClientLayout>
  );
}
