import { ClientLayout } from "../../components/layout";
import { useTitle } from "../../hooks/govuk";

export function ClientExpired() {
  useTitle("Upload documents");
  return (
    <ClientLayout>
      <h1 className="govuk-heading-l">This link no longer works</h1>
      <p className="govuk-body">Links stop working after 7 days, or when your solicitor turns them off.</p>
      <p className="govuk-body">Ask your solicitor for a new link.</p>
    </ClientLayout>
  );
}
