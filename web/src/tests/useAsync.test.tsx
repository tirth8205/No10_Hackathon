import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { ApiError } from "../api/backend";
import { useActionError, useAsync } from "../api/useAsync";

afterEach(cleanup);

interface Deferred<T> {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (reason: unknown) => void;
}

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("useAsync", () => {
  it("ignores the response of a superseded load when the deps change", async () => {
    const loads: Record<string, Deferred<string>> = { a: deferred<string>(), b: deferred<string>() };
    const { result, rerender } = renderHook(({ key }: { key: string }) => useAsync(() => loads[key].promise, [key]), {
      initialProps: { key: "a" },
    });
    expect(result.current.loading).toBe(true);

    rerender({ key: "b" });
    expect(result.current.loading).toBe(true);

    // The newer load finishes first...
    await act(async () => loads.b.resolve("B"));
    expect(result.current.data).toBe("B");
    expect(result.current.loading).toBe(false);

    // ...then the older one. Its result is stale and must be dropped.
    await act(async () => loads.a.resolve("A"));
    expect(result.current.data).toBe("B");
    expect(result.current.error).toBeNull();
  });

  it("ignores the failure of a superseded load too", async () => {
    const loads: Record<string, Deferred<string>> = { a: deferred<string>(), b: deferred<string>() };
    const { result, rerender } = renderHook(({ key }: { key: string }) => useAsync(() => loads[key].promise, [key]), {
      initialProps: { key: "a" },
    });
    rerender({ key: "b" });
    await act(async () => loads.b.resolve("B"));
    await act(async () => loads.a.reject(new Error("old failure")));
    expect(result.current.data).toBe("B");
    expect(result.current.error).toBeNull();
  });

  it("marks loading and drops the old data when the deps change", async () => {
    const loads: Record<string, Deferred<string>> = { a: deferred<string>(), b: deferred<string>() };
    const { result, rerender } = renderHook(({ key }: { key: string }) => useAsync(() => loads[key].promise, [key]), {
      initialProps: { key: "a" },
    });
    await act(async () => loads.a.resolve("A"));
    expect(result.current.data).toBe("A");
    expect(result.current.loading).toBe(false);

    rerender({ key: "b" });
    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();

    await act(async () => loads.b.resolve("B"));
    expect(result.current.data).toBe("B");
  });

  it("keeps the newest reload when an earlier one finishes later", async () => {
    const loads = [deferred<number>(), deferred<number>(), deferred<number>()];
    let n = 0;
    const { result } = renderHook(() => useAsync(() => loads[n++].promise, []));
    await act(async () => loads[0].resolve(0));
    expect(result.current.data).toBe(0);

    let first!: Promise<void>;
    let second!: Promise<void>;
    act(() => {
      first = result.current.reload();
      second = result.current.reload();
    });
    await act(async () => {
      loads[2].resolve(2);
      await second;
    });
    expect(result.current.data).toBe(2);

    await act(async () => {
      loads[1].resolve(1);
      await first;
    });
    expect(result.current.data).toBe(2);
    expect(result.current.loading).toBe(false);
  });
});

describe("useActionError", () => {
  it("shows the message of a failed action and clears it on the next success", async () => {
    const { result } = renderHook(() => useActionError());
    expect(result.current.message).toBeNull();

    await act(() => result.current.run(() => Promise.reject(new ApiError(415, "This file type is not supported: use PDF, Word or a photo"))));
    expect(result.current.message).toBe("This file type is not supported: use PDF, Word or a photo");

    await act(() => result.current.run(() => Promise.reject(new Error("Could not save"))));
    expect(result.current.message).toBe("Could not save");

    await act(() => result.current.run(() => Promise.resolve("ok")));
    expect(result.current.message).toBeNull();
  });

  it("never rejects, so callers can chain cleanup", async () => {
    const { result } = renderHook(() => useActionError());
    let settled = false;
    await act(() => result.current.run(() => Promise.reject(new Error("boom"))).finally(() => (settled = true)));
    expect(settled).toBe(true);
    expect(result.current.message).toBe("boom");
    act(() => result.current.clear());
    expect(result.current.message).toBeNull();
  });
});
