import { useCallback, useEffect, useRef, useSyncExternalStore } from "react";

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

/** Whether a CSS media query matches, kept up to date as the window changes. */
export function useMediaQuery(query: string, fallback: boolean): boolean {
  const supported = typeof window !== "undefined" && typeof window.matchMedia === "function";
  const subscribe = useCallback(
    (onChange: () => void) => {
      if (!supported) return () => {};
      const list = window.matchMedia(query);
      list.addEventListener("change", onChange);
      return () => list.removeEventListener("change", onChange);
    },
    [query, supported],
  );
  return useSyncExternalStore(
    subscribe,
    () => (supported ? window.matchMedia(query).matches : fallback),
    () => fallback,
  );
}

/**
 * A touch screen, or a window as narrow as a phone (GOV.UK's tablet breakpoint is 641px).
 * Defaults to true where the browser cannot tell: most clients use a phone.
 */
export function usePhoneLayout(): boolean {
  return useMediaQuery("(pointer: coarse), (max-width: 640px)", true);
}
