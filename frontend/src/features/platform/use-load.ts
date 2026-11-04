"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "@/lib/api";

export type LoadState<T> =
  { name: "loading" } | { name: "ready"; data: T } | { name: "denied" } | { name: "failed" };

/**
 * Loads data whenever `key` changes, and again each time the page is shown, because
 * Next.js keeps visited pages alive (cacheComponents) and the data may be out of date.
 * Each result remembers its request, so an old result never shows under new filters.
 */
export function useLoad<T>(load: (signal: AbortSignal) => Promise<T>, key: string) {
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{ request: string; state: LoadState<T> } | null>(null);
  const request = `${attempt}:${key}`;

  const loadRef = useRef(load);
  useEffect(() => {
    loadRef.current = load;
  });

  useEffect(() => {
    const controller = new AbortController();

    loadRef
      .current(controller.signal)
      .then((data) => setResult({ request, state: { name: "ready", data } }))
      .catch((err) => {
        if (controller.signal.aborted) return;
        const denied = err instanceof ApiError && err.status === 403;
        setResult({ request, state: { name: denied ? "denied" : "failed" } });
      });

    return () => controller.abort();
  }, [request]);

  const reload = useCallback(() => setAttempt((current) => current + 1), []);
  const state: LoadState<T> = result?.request === request ? result.state : { name: "loading" };

  return { state, reload };
}
