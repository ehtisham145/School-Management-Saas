"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { me } from "@/features/auth/api";
import { TotpSetup } from "@/features/auth/components/totp-setup";
import { useLogout } from "@/features/auth/use-logout";

type GuardState = "loading" | "totp-setup" | "ready" | "failed";

export function RequirePlatformAdmin({ children }: { children: ReactNode }) {
  const t = useTranslations("Platform");
  const tSession = useTranslations("Auth.session");
  const router = useRouter();

  const [guard, setGuard] = useState<GuardState>("loading");
  const [attempt, setAttempt] = useState(0);
  const { handleLogout, isLoggingOut } = useLogout();

  const reload = useCallback(() => {
    setGuard("loading");
    setAttempt((current) => current + 1);
  }, []);

  useEffect(() => {
    let cancelled = false;

    me()
      .then((result) => {
        if (cancelled) return;

        if (!result.is_platform_admin) {
          router.replace("/dashboard");
        } else if (result.requires_2fa_setup) {
          setGuard("totp-setup");
        } else {
          setGuard("ready");
        }
      })
      .catch((err: { status?: number }) => {
        if (cancelled) return;

        if (err.status === 401 || err.status === 403) {
          router.replace("/login");
        } else {
          setGuard("failed");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [router, attempt]);

  if (guard === "totp-setup") {
    return (
      <main className="flex flex-1 flex-col items-center justify-center p-8">
        <Card className="w-full max-w-sm">
          <CardContent>
            <TotpSetup onDone={reload} />
          </CardContent>
        </Card>
      </main>
    );
  }

  if (guard === "failed") {
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

  if (guard === "loading") {
    return (
      <main className="flex flex-1 items-center justify-center p-8">
        <p className="text-sm text-muted-foreground">{tSession("loading")}</p>
      </main>
    );
  }

  return (
    <div className="flex flex-1 flex-col">
      <header className="flex items-center justify-between gap-3 border-b border-border px-4 py-3 sm:px-6">
        <span className="font-semibold">{t("title")}</span>
        <Button variant="ghost" onClick={handleLogout} disabled={isLoggingOut}>
          {isLoggingOut ? t("loggingOut") : t("logout")}
        </Button>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 p-4 sm:p-6">{children}</main>
    </div>
  );
}
