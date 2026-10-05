// Small data-loading hooks for the wired routes: load once, reload on demand,
// poll while a predicate says the data is still changing (a check running),
// and surface the failure of an action (an upload, a save) to the screen.

import { useCallback, useEffect, useRef, useState } from "react";

export interface Async<T> {
  data: T | null;
  error: Error | null;
  loading: boolean;
  reload: () => Promise<void>;
  /** Replace the data locally after a mutation, without a round trip. */
  set: (data: T) => void;
}

export function useAsync<T>(load: () => Promise<T>, deps: unknown[]): Async<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);
  const alive = useRef(true);
  // Each load takes a number. Only the latest one may touch the state, so a slow
  // response from an earlier load (older deps, or an earlier poll) is discarded.
  const sequence = useRef(0);

  const reload = useCallback(async () => {
    const mine = ++sequence.current;
    const current = () => alive.current && mine === sequence.current;
    try {
      const next = await load();
      if (current()) {
        setData(next);
        setError(null);
      }
    } catch (e) {
      if (current()) setError(e instanceof Error ? e : new Error(String(e)));
    } finally {
      if (current()) setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    alive.current = true;
    // New deps: what was loaded for the old ones is no longer this hook's data.
    setData(null);
    setError(null);
    setLoading(true);
    void reload();
    return () => {
      alive.current = false;
    };
  }, [reload]);

  return { data, error, loading, reload, set: setData };
}

/** Call `reload` every `intervalMs` while `active` is true. */
export function usePolling(active: boolean, reload: () => Promise<void>, intervalMs = 2000): void {
  useEffect(() => {
    if (!active) return;
    const id = window.setInterval(() => void reload(), intervalMs);
    return () => window.clearInterval(id);
  }, [active, reload, intervalMs]);
}

export interface ActionError {
  /** The message of the last action that failed. Cleared by the next action that succeeds. */
  message: string | null;
  /** Runs an action. Its failure becomes `message`; its success clears any earlier one. Never rejects. */
  run: (action: () => Promise<unknown>) => Promise<void>;
  clear: () => void;
}

/** A plain sentence for an error from the API layer or the browser. */
export function errorMessage(e: unknown): string {
  if (e instanceof Error) return e.message || "Something went wrong. Try again.";
  return String(e) || "Something went wrong. Try again.";
}

/**
 * Keeps the message of the last failed action so the screen can show it. The routes
 * wrap every API call made from a callback in `run`, so nothing fails silently.
 */
export function useActionError(): ActionError {
  const [message, setMessage] = useState<string | null>(null);
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  const run = useCallback(async (action: () => Promise<unknown>) => {
    try {
      await action();
      if (alive.current) setMessage(null);
    } catch (e) {
      if (alive.current) setMessage(errorMessage(e));
    }
  }, []);
  const clear = useCallback(() => setMessage(null), []);

  return { message, run, clear };
}
