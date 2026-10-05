import { useEffect, useRef } from "react";

type GovukComponentClass = new ($root: Element, config?: Record<string, unknown>) => unknown;

/**
 * Initialises a GOV.UK Frontend JavaScript component on the element the ref
 * points to. Components refuse to initialise twice (for example under React
 * strict mode), which is safe to ignore.
 */
export function useGovukComponent<T extends HTMLElement>(Component: GovukComponentClass) {
  const ref = useRef<T>(null);
  useEffect(() => {
    if (!ref.current || !document.body.classList.contains("govuk-frontend-supported")) return;
    try {
      new Component(ref.current);
    } catch {
      // Already initialised.
    }
  }, [Component]);
  return ref;
}

/** Sets the page title. Client pages use neutral titles. */
export function useTitle(title: string) {
  useEffect(() => {
    document.title = title;
  }, [title]);
}
