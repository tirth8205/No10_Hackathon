// Page shells for the three interfaces.

import { ServiceNavigation as GovukServiceNavigation } from "govuk-frontend";
import { useEffect, type ReactNode } from "react";
import { Link } from "react-router";
import { useGovukComponent } from "../hooks/govuk";
import { paths } from "../paths";
import { ActionErrorBanner } from "./ErrorBanner";
import { cx, ExitThisPage, PhaseBanner } from "./govuk";

function SkipLink() {
  return (
    <a href="#main-content" className="govuk-skip-link" data-module="govuk-skip-link">
      Skip to main content
    </a>
  );
}

function Header({ home, title, meta, wide }: { home: string; title: string; meta?: string; wide?: boolean }) {
  return (
    <header className="govuk-generic-header app-header">
      <div className={cx("govuk-generic-header__container govuk-width-container", wide && "app-width-container--wide")}>
        <div className="govuk-generic-header__logo">
          <Link to={home} className="govuk-generic-header__homepage-link">
            {title}
          </Link>
        </div>
        {meta && <span className="app-header-meta">{meta}</span>}
      </div>
    </header>
  );
}

export interface NavItem {
  to: string;
  text: string;
  active?: boolean;
}

function ServiceNav({ items, wide }: { items: NavItem[]; wide?: boolean }) {
  const ref = useGovukComponent<HTMLElement>(GovukServiceNavigation);
  return (
    <section ref={ref} aria-label="Service information" className="govuk-service-navigation" data-module="govuk-service-navigation">
      <div className={cx("govuk-width-container", wide && "app-width-container--wide")}>
        <div className="govuk-service-navigation__container">
          <nav aria-label="Menu" className="govuk-service-navigation__wrapper">
            <button
              type="button"
              className="govuk-service-navigation__toggle govuk-js-service-navigation-toggle"
              aria-controls="navigation"
              hidden
              aria-hidden="true"
            >
              Menu
            </button>
            <ul className="govuk-service-navigation__list" id="navigation">
              {items.map((item) => (
                <li
                  key={item.to}
                  className={cx("govuk-service-navigation__item", item.active && "govuk-service-navigation__item--active")}
                >
                  <Link className="govuk-service-navigation__link" to={item.to} aria-current={item.active ? "true" : undefined}>
                    {item.active ? <strong className="govuk-service-navigation__active-fallback">{item.text}</strong> : item.text}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </div>
    </section>
  );
}

function Footer({ links, wide }: { links: NavItem[]; wide?: boolean }) {
  return (
    <footer className="govuk-footer">
      <div className={cx("govuk-width-container", wide && "app-width-container--wide")}>
        <div className="govuk-footer__meta">
          <div className="govuk-footer__meta-item govuk-footer__meta-item--grow">
            <h2 className="govuk-visually-hidden">Support links</h2>
            <ul className="govuk-footer__inline-list">
              {links.map((link) => (
                <li className="govuk-footer__inline-list-item" key={link.to}>
                  <Link className="govuk-footer__link" to={link.to}>
                    {link.text}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </footer>
  );
}

interface ShellProps {
  children: ReactNode;
  beforeContent?: ReactNode;
}

// ---------------------------------------------------------------------------
// Solicitor workspace
// ---------------------------------------------------------------------------

export function ProviderLayout({ children, beforeContent, firm }: ShellProps & { firm: string }) {
  return (
    <>
      <SkipLink />
      <Header home={paths.provider} title="Gateway Check" meta={firm} />
      <ServiceNav
        items={[
          { to: paths.provider, text: "Cases", active: true },
          { to: paths.howTheCheckWorks, text: "How the check works" },
        ]}
      />
      <div className="govuk-width-container">
        <PhaseBanner />
        {beforeContent}
        <main className="govuk-main-wrapper" id="main-content">
          <ActionErrorBanner />
          {children}
        </main>
      </div>
      <Footer
        links={[
          { to: paths.howTheCheckWorks, text: "How the check works" },
          { to: paths.index, text: "All screens" },
        ]}
      />
    </>
  );
}

// ---------------------------------------------------------------------------
// LAA caseworker
// ---------------------------------------------------------------------------

export function CaseworkerLayout({ children, beforeContent, active }: ShellProps & { active: "queue" | "inbox" }) {
  return (
    <>
      <SkipLink />
      <Header home={paths.queue} title="Gateway Check" meta="Caseworker" wide />
      <ServiceNav
        wide
        items={[
          { to: paths.queue, text: "Queue", active: active === "queue" },
          { to: paths.inbox, text: "Inbox", active: active === "inbox" },
          { to: paths.howTheCheckWorks, text: "Rules" },
        ]}
      />
      <div className="govuk-width-container app-width-container--wide">
        <PhaseBanner />
        {beforeContent}
        <main className="govuk-main-wrapper" id="main-content">
          <ActionErrorBanner />
          {children}
        </main>
      </div>
      <Footer
        wide
        links={[
          { to: paths.howTheCheckWorks, text: "Rules applied" },
          { to: paths.index, text: "All screens" },
        ]}
      />
    </>
  );
}

// ---------------------------------------------------------------------------
// Client (on their phone)
// ---------------------------------------------------------------------------

const EXIT_URL = "https://www.gov.uk";

/** Leaves the page when Escape is pressed 3 times within 2 seconds (docs 4.12). */
function useEscapeToExit() {
  useEffect(() => {
    let presses: number[] = [];
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      const now = Date.now();
      presses = [...presses.filter((t) => now - t < 2000), now];
      if (presses.length >= 3) window.location.replace(EXIT_URL);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);
}

/**
 * Neutral shell for the client: no service name that reveals the subject,
 * no navigation, Exit this page on every screen.
 */
export function ClientLayout({ children }: { children: ReactNode }) {
  useEscapeToExit();
  return (
    <>
      <SkipLink />
      <header className="govuk-generic-header app-header">
        <div className="govuk-generic-header__container govuk-width-container">
          <div className="govuk-generic-header__logo">
            <span className="govuk-generic-header__homepage-link">Document upload</span>
          </div>
        </div>
      </header>
      <div className="govuk-width-container app-client">
        <PhaseBanner />
        <ExitThisPage href={EXIT_URL} />
        <main className="govuk-main-wrapper govuk-!-padding-top-4" id="main-content">
          <ActionErrorBanner />
          {children}
        </main>
      </div>
    </>
  );
}

/** Plain shell for pages outside the three interfaces. */
export function PlainLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <SkipLink />
      <Header home={paths.index} title="Gateway Check" />
      <div className="govuk-width-container">
        <PhaseBanner />
        <main className="govuk-main-wrapper" id="main-content">
          <ActionErrorBanner />
          {children}
        </main>
      </div>
      <Footer links={[{ to: paths.index, text: "All screens" }]} />
    </>
  );
}
