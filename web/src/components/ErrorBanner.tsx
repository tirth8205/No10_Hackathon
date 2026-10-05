// A GOV.UK error summary for something that went wrong after the page loaded: an upload
// the back end refused, a save that failed. The routes put the message in context and
// the layouts render it at the top of the main content, where GOV.UK puts error summaries.

import { createContext, useContext, useEffect, useRef, type ReactNode } from "react";

export function ErrorBanner({ message, title = "There is a problem" }: { message: ReactNode | null; title?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (message) ref.current?.focus();
  }, [message]);
  if (!message) return null;
  return (
    <div className="govuk-error-summary" data-module="govuk-error-summary" ref={ref} tabIndex={-1}>
      <div role="alert">
        <h2 className="govuk-error-summary__title">{title}</h2>
        <div className="govuk-error-summary__body">
          <p className="govuk-body">{message}</p>
        </div>
      </div>
    </div>
  );
}

const ActionErrorContext = createContext<string | null>(null);

/** Wraps a screen so the layouts can show the message of its last failed action. */
export function ActionErrorProvider({ message, children }: { message: string | null; children: ReactNode }) {
  return <ActionErrorContext.Provider value={message}>{children}</ActionErrorContext.Provider>;
}

/** Rendered by the layouts at the top of the main content. Nothing when no action has failed. */
export function ActionErrorBanner() {
  const message = useContext(ActionErrorContext);
  return <ErrorBanner message={message} />;
}
