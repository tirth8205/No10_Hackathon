// Thin wrappers around GOV.UK Frontend markup.

import { Button as GovukButton, ExitThisPage as GovukExitThisPage, NotificationBanner as GovukNotificationBanner } from "govuk-frontend";
import { useId, type ReactNode } from "react";
import { Link } from "react-router";
import { useGovukComponent } from "../hooks/govuk";
import { ELEMENT_LABELS, type TagColour, type Verdict } from "../lib/labels";
import type { ElementStatus } from "../lib/types";

const cx = (...classes: (string | false | null | undefined)[]) => classes.filter(Boolean).join(" ");

export function Tag({ colour, children, className }: { colour: TagColour | "blue"; children: ReactNode; className?: string }) {
  return <strong className={cx("govuk-tag", colour !== "blue" && `govuk-tag--${colour}`, className)}>{children}</strong>;
}

export function VerdictTag({ verdict, className }: { verdict: Verdict; className?: string }) {
  return (
    <Tag colour={verdict.colour} className={className}>
      {verdict.label}
    </Tag>
  );
}

export function ElementTag({ status }: { status: ElementStatus }) {
  const { label, colour } = ELEMENT_LABELS[status];
  return <Tag colour={colour}>{label}</Tag>;
}

export function ButtonLink({
  to,
  children,
  variant,
  className,
}: {
  to: string;
  children: ReactNode;
  variant?: "secondary" | "warning";
  className?: string;
}) {
  const ref = useGovukComponent<HTMLAnchorElement>(GovukButton);
  return (
    <Link
      ref={ref}
      to={to}
      role="button"
      draggable={false}
      className={cx("govuk-button", variant && `govuk-button--${variant}`, className)}
      data-module="govuk-button"
    >
      {children}
    </Link>
  );
}

export function Button({
  children,
  variant,
  onClick,
  type = "button",
  className,
}: {
  children: ReactNode;
  variant?: "secondary" | "warning";
  onClick?: () => void;
  type?: "button" | "submit";
  className?: string;
}) {
  return (
    <button
      type={type}
      className={cx("govuk-button", variant && `govuk-button--${variant}`, className)}
      data-module="govuk-button"
      onClick={onClick}
    >
      {children}
    </button>
  );
}

export function WarningText({ children }: { children: ReactNode }) {
  return (
    <div className="govuk-warning-text">
      <span className="govuk-warning-text__icon" aria-hidden="true">
        !
      </span>
      <strong className="govuk-warning-text__text">
        <span className="govuk-visually-hidden">Warning</span>
        {children}
      </strong>
    </div>
  );
}

export function InsetText({ children }: { children: ReactNode }) {
  return <div className="govuk-inset-text">{children}</div>;
}

export function Details({ summary, open, children }: { summary: ReactNode; open?: boolean; children: ReactNode }) {
  return (
    <details className="govuk-details" open={open}>
      <summary className="govuk-details__summary">
        <span className="govuk-details__summary-text">{summary}</span>
      </summary>
      <div className="govuk-details__text">{children}</div>
    </details>
  );
}

export function NotificationBanner({
  title,
  success,
  children,
}: {
  title: string;
  success?: boolean;
  children: ReactNode;
}) {
  const ref = useGovukComponent<HTMLDivElement>(GovukNotificationBanner);
  const titleId = useId();
  return (
    <div
      ref={ref}
      className={cx("govuk-notification-banner", success && "govuk-notification-banner--success")}
      role={success ? "alert" : "region"}
      aria-labelledby={titleId}
      data-module="govuk-notification-banner"
    >
      <div className="govuk-notification-banner__header">
        <h2 className="govuk-notification-banner__title" id={titleId}>
          {title}
        </h2>
      </div>
      <div className="govuk-notification-banner__content">{children}</div>
    </div>
  );
}

export function Panel({ title, children, headingLevel = 1 }: { title: ReactNode; children?: ReactNode; headingLevel?: 1 | 2 }) {
  const Heading = headingLevel === 1 ? "h1" : "h2";
  return (
    <div className="govuk-panel govuk-panel--confirmation">
      <Heading className="govuk-panel__title">{title}</Heading>
      {children && <div className="govuk-panel__body">{children}</div>}
    </div>
  );
}

export interface Crumb {
  text: string;
  to?: string;
}

export function Breadcrumbs({ items }: { items: Crumb[] }) {
  return (
    <nav className="govuk-breadcrumbs" aria-label="Breadcrumb">
      <ol className="govuk-breadcrumbs__list">
        {items.map((item) => (
          <li className="govuk-breadcrumbs__list-item" key={item.text}>
            {item.to ? (
              <Link className="govuk-breadcrumbs__link" to={item.to}>
                {item.text}
              </Link>
            ) : (
              <span aria-current="page">{item.text}</span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

export function BackLink({ to, children = "Back" }: { to: string; children?: ReactNode }) {
  return (
    <Link to={to} className="govuk-back-link">
      {children}
    </Link>
  );
}

export function PhaseBanner() {
  return (
    <div className="govuk-phase-banner">
      <p className="govuk-phase-banner__content">
        <strong className="govuk-tag govuk-phase-banner__content__tag">Prototype</strong>
        <span className="govuk-phase-banner__text">Sample data only. This is not a real service.</span>
      </p>
    </div>
  );
}

/** GOV.UK "Exit this page". Its JavaScript also exits when Shift is pressed 3 times. */
export function ExitThisPage({ href = "https://www.bbc.co.uk/weather" }: { href?: string }) {
  const ref = useGovukComponent<HTMLDivElement>(GovukExitThisPage);
  return (
    <div ref={ref} className="govuk-exit-this-page" data-module="govuk-exit-this-page">
      <a
        href={href}
        role="button"
        draggable={false}
        className="govuk-button govuk-button--warning govuk-exit-this-page__button govuk-js-exit-this-page-button"
        data-module="govuk-button"
        rel="nofollow noreferrer"
      >
        <span className="govuk-visually-hidden">Emergency</span> Exit this page
      </a>
    </div>
  );
}

export interface SummaryRow {
  key: ReactNode;
  value: ReactNode;
  action?: { to: string; text: string; hidden: string };
}

export function SummaryList({ rows, className }: { rows: SummaryRow[]; className?: string }) {
  const anyActions = rows.some((r) => r.action);
  return (
    <dl className={cx("govuk-summary-list", className)}>
      {rows.map((row, i) => (
        <div className={cx("govuk-summary-list__row", anyActions && !row.action && "govuk-summary-list__row--no-actions")} key={i}>
          <dt className="govuk-summary-list__key">{row.key}</dt>
          <dd className="govuk-summary-list__value">{row.value}</dd>
          {row.action && (
            <dd className="govuk-summary-list__actions">
              <Link className="govuk-link" to={row.action.to}>
                {row.action.text}
                <span className="govuk-visually-hidden"> {row.action.hidden}</span>
              </Link>
            </dd>
          )}
        </div>
      ))}
    </dl>
  );
}

export { cx };
