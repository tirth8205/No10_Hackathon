import { useEffect, useRef } from "react";
import { Route, Routes, useLocation } from "react-router";
import { HowTheCheckWorks, NotFound } from "./pages/HowTheCheckWorks";
import { ScreensIndex } from "./pages/ScreensIndex";
import { Welcome } from "./pages/Welcome";
import { ClientExpired } from "./pages/client/ClientExpired";
import { Stage } from "./pages/Stage";
import * as live from "./api/routes";
import * as sample from "./sample/routes";

/** Sample data (VITE_SAMPLE_DATA=1, used by the tests and the screens index) or the back end. */
const SAMPLE = import.meta.env.VITE_SAMPLE_DATA === "1";
const R = SAMPLE ? sample : live;

/** After each navigation, start at the top and move focus to the new page's content. */
function useNewPageFocus() {
  const { pathname } = useLocation();
  // Compare paths rather than counting runs: React's development mode runs effects twice on load.
  const last = useRef(pathname);
  useEffect(() => {
    if (last.current === pathname) return;
    last.current = pathname;
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
    <>
    <Routes>
      <Route path="/stage" element={<Stage />} />
      <Route path="/" element={SAMPLE ? <ScreensIndex /> : <Welcome />} />
      <Route path="/screens" element={<ScreensIndex />} />
      <Route path="/how-the-check-works" element={<HowTheCheckWorks />} />

      <Route path="/client" element={<R.ClientStartRoute />} />
      <Route path="/client/expired" element={<ClientExpired />} />
      <Route path="/client/:token" element={<R.ClientUploadRoute />} />
      <Route path="/client/:token/checking" element={<R.ClientCheckingRoute />} />
      <Route path="/client/:token/result/:state" element={<R.ClientResultRoute />} />

      <Route path="/provider" element={<R.ProviderCasesRoute />} />
      <Route path="/provider/new" element={<R.ProviderNewCaseRoute />} />
      <Route path="/provider/cases/:caseId" element={<R.CaseEvidenceRoute />} />
      <Route path="/provider/cases/:caseId/client" element={<R.CaseClientRoute />} />
      <Route path="/provider/cases/:caseId/details" element={<R.CaseDetailsRoute />} />
      <Route path="/provider/cases/:caseId/submit" element={<R.CaseSubmitRoute />} />
      <Route path="/provider/cases/:caseId/documents/:docId" element={<R.DocumentCheckRoute />} />
      <Route path="/provider/cases/:caseId/documents/:docId/file" element={<R.DocumentFileRoute />} />

      <Route path="/caseworker" element={<R.QueueRoute />} />
      <Route path="/caseworker/cases/:caseId" element={<R.ReviewRoute />} />
      <Route path="/caseworker/inbox" element={<R.InboxRoute />} />

      <Route path="*" element={<NotFound />} />
    </Routes>
    </>
  );
}
