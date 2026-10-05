// Small data-loading hooks for the wired routes: load once, reload on demand,
// and poll while a predicate says the data is still changing (a check running).

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

  const reload = useCallback(async () => {
    try {
      const next = await load();
      if (alive.current) {
        setData(next);
        setError(null);
      }
    } catch (e) {
      if (alive.current) setError(e instanceof Error ? e : new Error(String(e)));
    } finally {
      if (alive.current) setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    alive.current = true;
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
