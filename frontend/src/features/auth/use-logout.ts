"use client";

import { useCallback, useState } from "react";
import { useLocale } from "next-intl";
import { ApiError } from "@/lib/api";
import { logout } from "./api";

export function useLogout() {
  const locale = useLocale();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const handleLogout = useCallback(async () => {
    setIsLoggingOut(true);

    try {
      await logout();
    } catch (err) {
      // Stay on the page unless the session has already ended on the server.
      if (!(err instanceof ApiError && err.code === "not_authenticated")) {
        setIsLoggingOut(false);
        return;
      }
    }

    // A full page load, because Next.js keeps visited routes alive in memory
    // (cacheComponents) and the next user must not inherit any of that state.
    window.location.replace(`/${locale}/login`);
  }, [locale]);

  return { handleLogout, isLoggingOut };
}
