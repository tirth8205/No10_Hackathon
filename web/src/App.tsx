import { useEffect, useRef } from "react";
import { Route, Routes, useLocation } from "react-router";
import { HowTheCheckWorks, NotFound } from "./pages/HowTheCheckWorks";
import { ScreensIndex } from "./pages/ScreensIndex";
import { ClientExpired } from "./pages/client/ClientExpired";
import {
  CaseClientRoute,
  CaseDetailsRoute,
  CaseEvidenceRoute,
  CaseSubmitRoute,
  ClientCheckingRoute,
  ClientResultRoute,
  ClientUploadRoute,
  DocumentCheckRoute,
  DocumentFileRoute,
  InboxRoute,
  ProviderCasesRoute,
  ProviderNewCaseRoute,
  QueueRoute,
  ReviewRoute,
} from "./sample/routes";

/** After each navigation, start at the top and move focus to the new page's content. */
function useNewPageFocus() {
  const { pathname } = useLocation();
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    window.scrollTo(0, 0);
    const main = document.getElementById("main-content");
    if (main) {
      main.setAttribute("tabindex", "-1");
      main.focus({ preventScroll: true });
    }
  }, [pathname]);
}

export function App() {
  useNewPageFocus();
  return (
    <Routes>
      <Route path="/" element={<ScreensIndex />} />
      <Route path="/how-the-check-works" element={<HowTheCheckWorks />} />

      <Route path="/client/expired" element={<ClientExpired />} />
      <Route path="/client/:token" element={<ClientUploadRoute />} />
      <Route path="/client/:token/checking" element={<ClientCheckingRoute />} />
      <Route path="/client/:token/result/:state" element={<ClientResultRoute />} />

      <Route path="/provider" element={<ProviderCasesRoute />} />
      <Route path="/provider/new" element={<ProviderNewCaseRoute />} />
      <Route path="/provider/cases/:caseId" element={<CaseEvidenceRoute />} />
      <Route path="/provider/cases/:caseId/client" element={<CaseClientRoute />} />
      <Route path="/provider/cases/:caseId/details" element={<CaseDetailsRoute />} />
      <Route path="/provider/cases/:caseId/submit" element={<CaseSubmitRoute />} />
      <Route path="/provider/cases/:caseId/documents/:docId" element={<DocumentCheckRoute />} />
      <Route path="/provider/cases/:caseId/documents/:docId/file" element={<DocumentFileRoute />} />

      <Route path="/caseworker" element={<QueueRoute />} />
      <Route path="/caseworker/cases/:caseId" element={<ReviewRoute />} />
      <Route path="/caseworker/inbox" element={<InboxRoute />} />

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
