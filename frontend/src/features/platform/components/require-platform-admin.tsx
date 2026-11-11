"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { Button } from "@/components/ui/button";
import { me } from "@/features/auth/api";
import type { MeResponse } from "@/features/auth/schemas";
import { PlatformUserProvider } from "../platform-user";
import { PlatformShell } from "./platform-shell";

type GuardState = { name: "loading" } | { name: "ready"; user: MeResponse } | { name: "failed" };

export function RequirePlatformAdmin({ children }: { children: ReactNode }) {
  const tSession = useTranslations("Auth.session");
  const router = useRouter();

  const [guard, setGuard] = useState<GuardState>({ name: "loading" });
  const [attempt, setAttempt] = useState(0);

  const reload = useCallback(() => {
    setGuard({ name: "loading" });
    setAttempt((current) => current + 1);
  }, []);

  useEffect(() => {
    let cancelled = false;

    me()
      .then((result) => {
        if (cancelled) return;

        if (!result.is_platform_admin) {
          router.replace("/dashboard");
        } else {
          setGuard({ name: "ready", user: result });
        }
      })
      .catch((err: { status?: number }) => {
        if (cancelled) return;

        if (err.status === 401 || err.status === 403) {
          router.replace("/login");
        } else {
          setGuard({ name: "failed" });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [router, attempt]);

  if (guard.name === "failed") {
    return (
      <main className="flex flex-1 flex-col items-center justify-center gap-3 p-8">
        <p role="alert" className="text-sm text-destructive">
          {tSession("loadFailed")}
        </p>
        <Button variant="outline" onClick={reload}>
          {tSession("retry")}
        </Button>
      </main>
    );
  }

  if (guard.name === "loading") {
    return (
      <main className="flex flex-1 items-center justify-center p-8">
        <p className="text-sm text-muted-foreground">{tSession("loading")}</p>
      </main>
    );
  }

  return (
    <PlatformUserProvider user={guard.user}>
      <PlatformShell user={guard.user}>{children}</PlatformShell>
    </PlatformUserProvider>
  );
}
