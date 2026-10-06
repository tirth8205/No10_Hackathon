// Demo-only view switcher: jump between the three personas for the demo case,
// or open the stage that shows all three side by side. Not part of the service;
// remove before any real use (client screens must carry no navigation).

import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router";
import { demo, type DemoState } from "../api/backend";
import { paths } from "../paths";

export function DemoBar() {
  const [state, setState] = useState<DemoState | null>(null);
  const { pathname } = useLocation();
  useEffect(() => {
    demo().then(setState).catch(() => setState(null));
  }, [pathname]);
  // Not on the stage itself, and not inside the stage's frames.
  if (pathname.startsWith("/stage") || window.self !== window.top) return null;
  const persona = pathname.startsWith("/client") ? "client" : pathname.startsWith("/caseworker") ? "caseworker" : "provider";
  const item = (key: string, to: string, label: string) => (
    <li className="app-demo-bar__item" key={key}>
      <Link to={to} className="app-demo-bar__link" aria-current={persona === key ? "page" : undefined}>
        {label}
      </Link>
    </li>
  );
  return (
    <nav className="app-demo-bar" aria-label="Demo view switcher">
      <span className="app-demo-bar__label">
        Demo{state ? ` · ${state.applicantName} (${state.ref})` : ""} · View as
      </span>
      <ul className="app-demo-bar__list">
        {state && item("client", paths.client(state.clientToken), "Client's phone")}
        {item("provider", state ? paths.caseEvidence(state.caseId) : paths.provider, "Solicitor")}
        {item("caseworker", paths.queue, "Caseworker")}
      </ul>
      <Link to="/stage" className="app-demo-bar__link app-demo-bar__stage">
        All three at once
      </Link>
    </nav>
  );
}
