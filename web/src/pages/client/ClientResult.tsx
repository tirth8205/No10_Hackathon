import { Link } from "react-router";
import { CopyButton } from "../../components/CopyButton";
import { ButtonLink, Details, InsetText, Panel, Tag } from "../../components/govuk";
import { ClientLayout } from "../../components/layout";
import { useTitle } from "../../hooks/govuk";
import { docVerdict } from "../../lib/labels";
import { clientMessage } from "../../lib/outputs";
import type { CheckResult } from "../../lib/types";

export interface ClientResultProps {
  firmName: string;
  result: CheckResult;
  /** A message the client can send to the letter writer. Shown when the letter needs a change. */
  messageToWriter: string;
  uploadTo: string;
}

/**
 * The client's result. Plain words only: no legal reasoning, no blame, and never
 * "rejected" or "fail". Organisation names are kept short in case someone else sees the phone.
 */
export function ClientResult({ firmName, result, messageToWriter, uploadTo }: ClientResultProps) {
  const verdict = docVerdict(result).key;
  const message = clientMessage(result);
  useTitle(`${message.title} – Upload documents`);
  const writer = result.shortOrg ?? "the person who wrote it";

  if (verdict === "pass") {
    return (
      <ClientLayout>
        <Panel title={message.title}>{message.body}</Panel>
        <p className="govuk-body">We’ve sent the result to {firmName}. They’ll contact you about what happens next.</p>
        <h2 className="govuk-heading-m">What happens to your letter</h2>
        <p className="govuk-body">Your solicitor gets a copy. Nothing is saved on this phone.</p>
        <p className="govuk-body">You can close this page now.</p>
        <p className="govuk-body">
          <Link className="govuk-link" to={uploadTo}>
            Upload another document
          </Link>
        </p>
      </ClientLayout>
    );
  }

  if (verdict === "fail") {
    return (
      <ClientLayout>
        <Tag colour="yellow" className="govuk-!-margin-bottom-3">
          Needs a change
        </Tag>
        <h1 className="govuk-heading-l">{message.title}</h1>
        <p className="govuk-body">{message.body}</p>
        <InsetText>
          <p className="govuk-body govuk-!-font-weight-bold govuk-!-margin-bottom-1">{message.addTitle}</p>
          <p className="govuk-body govuk-!-margin-bottom-0">{message.addBody}</p>
        </InsetText>
        <p className="govuk-body">Your solicitor can see this. You can leave it to them, or send the writer a message yourself.</p>
        <div className="app-stacked-buttons">
          <CopyButton text={messageToWriter} label={`Copy a message to send to ${writer}`} />
          <ButtonLink to={uploadTo} variant="secondary">
            Upload a new letter
          </ButtonLink>
        </div>
        <Details summary="Read the message first">
          <div className="app-letter">{messageToWriter}</div>
        </Details>
      </ClientLayout>
    );
  }

  return (
    <ClientLayout>
      <h1 className="govuk-heading-l">{message.title}</h1>
      <p className="govuk-body">{message.body}</p>
      {verdict === "not_prescribed" && (
        <p className="govuk-body">Your solicitor will talk to you about other letters that could help. You only need one.</p>
      )}
      <p className="govuk-body">
        <Link className="govuk-link" to={uploadTo}>
          Upload another document
        </Link>
      </p>
    </ClientLayout>
  );
}
