// The demo stage: the client's phone, the solicitor's cases and the caseworker's queue
// side by side, each a live frame of the real app. Prototype only.
//
// The client frame opens on the code screen, as a client would: take the code from the
// solicitor's Client tab and type it in.

import { useState } from "react";
import { useSearchParams } from "react-router";
import { demo, resetDemo } from "../api/backend";
import { paths } from "../paths";

type View = "all" | "client" | "provider" | "caseworker";
const VIEWS: [View, string][] = [["all", "All three"], ["client", "Client"], ["provider", "Solicitor"], ["caseworker", "Caseworker"]];

export function Stage() {
  const [search, setSearch] = useSearchParams();
  const view = (search.get("view") as View) || "all";
  const setView = (v: View) => setSearch(v === "all" ? {} : { view: v }, { replace: true });
  const [nonce, setNonce] = useState(0);
  const [resetting, setResetting] = useState(false);

  const onReset = async () => {
    setResetting(true);
    await resetDemo();
    // the seed runs in the background; wait for the cases to come back
    for (let i = 0; i < 60; i++) {
      await new Promise((r) => setTimeout(r, 1000));
      const s = await demo().catch(() => null);
      if (s && s.cases.length >= 7) break;
    }
    setNonce((n) => n + 1);
    setResetting(false);
  };

  const frame = (title: string, src: string, width: string) => (
    <section style={{ flex: view === "all" ? `0 0 ${width}` : width === "390px" ? "0 0 390px" : "1 1 auto", display: "flex", flexDirection: "column", minWidth: 0 }}>
      <h2 className="govuk-heading-s" style={{ margin: "0 0 6px" }}>{title}</h2>
      <iframe key={`${src}-${nonce}`} title={title} src={src}
              style={{ flex: 1, width: "100%", border: "1px solid #b1b4b6", background: "#fff" }} />
    </section>
  );

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", padding: 12, boxSizing: "border-box", gap: 8, background: "#f3f2f1" }}>
      <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
        <h1 className="govuk-heading-m" style={{ margin: 0 }}>Gateway Check{view === "all" ? " — all three views" : ""}</h1>
        <div role="group" aria-label="Which views to show" style={{ display: "flex", gap: 4 }}>
          {VIEWS.map(([v, label]) => (
            <button key={v} type="button" className={`govuk-button ${view === v ? "" : "govuk-button--secondary"}`} style={{ margin: 0 }}
                    aria-pressed={view === v} onClick={() => setView(v)}>
              {label}
            </button>
          ))}
        </div>
        <button className="govuk-button govuk-button--secondary" style={{ margin: 0 }} onClick={() => setNonce((n) => n + 1)}>Reload views</button>
        <button className="govuk-button govuk-button--warning" style={{ margin: 0 }} onClick={() => void onReset()} disabled={resetting}>
          {resetting ? "Resetting…" : "Reset demo data"}
        </button>
      </div>
      {resetting ? (
        <p className="govuk-body">Re-seeding the demo cases…</p>
      ) : (
        <div style={{ flex: 1, display: "flex", gap: 12, minHeight: 0, justifyContent: view === "client" ? "center" : "flex-start" }}>
          {(view === "all" || view === "client") && frame("Client · their phone", paths.clientStart, "390px")}
          {(view === "all" || view === "provider") && frame("Solicitor · Hartley & Webb", paths.provider, "1fr")}
          {(view === "all" || view === "caseworker") && frame("LAA caseworker · evidence queue", paths.queue, "34%")}
        </div>
      )}
    </div>
  );
}
