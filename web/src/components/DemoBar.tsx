// Prototype-only view switcher: jump between the three personas for the demo case,
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
  if (pathname.startsWith("/stage")) return null;
  const persona = pathname.startsWith("/client") ? "client" : pathname.startsWith("/caseworker") ? "caseworker" : "provider";
  const item = (key: string, to: string, label: string) => (
    <Link
      to={to}
      className="app-demo-bar__link"
      aria-current={persona === key ? "page" : undefined}
      style={{ fontWeight: persona === key ? 700 : 400, textDecoration: persona === key ? "none" : "underline" }}
    >
      {label}
    </Link>
  );
  return (
    <div className="app-demo-bar" role="navigation" aria-label="Prototype view switcher"
         style={{ background: "#0b0c0c", color: "#fff", fontSize: 14, padding: "4px 16px", display: "flex", gap: 16, alignItems: "center" }}>
      <span style={{ opacity: 0.8 }}>Prototype view{state ? ` · ${state.applicantName} (${state.ref})` : ""}:</span>
      {state && item("client", paths.client(state.clientToken), "Client's phone")}
      {item("provider", state ? paths.caseEvidence(state.caseId) : paths.provider, "Solicitor")}
      {item("caseworker", paths.queue, "Caseworker")}
      <Link to="/stage" className="app-demo-bar__link" style={{ marginLeft: "auto" }}>All three at once</Link>
    </div>
  );
}
