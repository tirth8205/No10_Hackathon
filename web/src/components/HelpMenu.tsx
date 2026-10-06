// Prototype-only: a (?) in the header that opens shortcuts to the three views and the
// side-by-side stage, for demonstrating the service. Remove before any real use: a
// client's screens should carry nothing that reveals what the service is.

import { useEffect, useId, useRef, useState } from "react";
import { Link, useLocation } from "react-router";
import { paths } from "../paths";

const VIEWS = [
  { key: "client", to: paths.clientStart, label: "Client", hint: "Enter a code, as a client would on their phone" },
  { key: "provider", to: paths.provider, label: "Solicitor", hint: "Cases at Hartley & Webb" },
  { key: "caseworker", to: paths.queue, label: "LAA caseworker", hint: "The evidence queue" },
  { key: "stage", to: "/stage", label: "All three side by side", hint: "For a demo on one screen" },
] as const;

function currentView(pathname: string): string {
  if (pathname.startsWith("/client")) return "client";
  if (pathname.startsWith("/caseworker")) return "caseworker";
  if (pathname.startsWith("/provider")) return "provider";
  return "";
}

const QuestionIcon = () => (
  <svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true" focusable="false">
    <circle cx="14" cy="14" r="12" fill="none" stroke="currentColor" strokeWidth="2.25" />
    <path d="M10.6 11.1a3.5 3.5 0 1 1 5.1 3.1c-1.1.6-1.7 1.3-1.7 2.5v.6" fill="none" stroke="currentColor" strokeWidth="2.25" strokeLinecap="round" />
    <circle cx="14" cy="20.6" r="1.4" fill="currentColor" />
  </svg>
);

export function HelpMenu() {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const root = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const { pathname } = useLocation();
  const current = currentView(pathname);

  // Close on navigation, on a click elsewhere, and on Escape (returning focus to the button).
  useEffect(() => setOpen(false), [pathname]);
  useEffect(() => {
    if (!open) return;
    const onDown = (event: MouseEvent) => {
      if (root.current && !root.current.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        button.current?.focus();
      }
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  // The stage shows each view in a frame of its own; the shortcuts would only get in the way there.
  if (typeof window !== "undefined" && window.self !== window.top) return null;

  return (
    <div className="app-help" ref={root}>
      <button
        ref={button}
        type="button"
        className="app-help__button"
        aria-expanded={open}
        aria-controls={panelId}
        aria-label="Help: switch between the client, solicitor and caseworker views"
        title="Switch view"
        onClick={() => setOpen((o) => !o)}
      >
        <QuestionIcon />
      </button>
      <div className="app-help__panel" id={panelId} hidden={!open}>
        <h2 className="govuk-heading-s govuk-!-margin-bottom-1">Switch view</h2>
        <p className="govuk-body-s app-secondary-text">Prototype shortcuts for demonstrating the service.</p>
        <ul className="govuk-list govuk-!-margin-bottom-0">
          {VIEWS.map((view) => (
            <li key={view.key} className="app-help__item">
              <Link
                className="govuk-link govuk-link--no-visited-state"
                to={view.to}
                aria-current={current === view.key ? "page" : undefined}
                onClick={() => setOpen(false)}
              >
                {view.label}
              </Link>
              {current === view.key && <span className="govuk-body-s app-secondary-text"> (you are here)</span>}
              <span className="govuk-body-s app-secondary-text govuk-!-display-block">{view.hint}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
