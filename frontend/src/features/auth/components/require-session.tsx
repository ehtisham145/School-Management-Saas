"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { me } from "../api";
import { toActiveSession, type Membership } from "../schemas";
import { useSession } from "../session-store";
import { SchoolPicker } from "./school-picker";
import { TotpSetup } from "./totp-setup";

type GuardState =
  | { name: "loading" }
  | { name: "totp-setup" }
  | { name: "choose-school"; memberships: Membership[] }
  | { name: "failed" };

function CenteredCard({ children }: { children: ReactNode }) {
  return (
    <main className="flex flex-1 flex-col items-center justify-center p-8">
      <Card className="w-full max-w-sm">
        <CardContent>{children}</CardContent>
      </Card>
    </main>
  );
}

export function RequireSession({ children }: { children: ReactNode }) {
  const t = useTranslations("Auth.session");
  const locale = useLocale();
  const router = useRouter();
  const { session, setSession } = useSession();
  const [guard, setGuard] = useState<GuardState>({ name: "loading" });
  const [attempt, setAttempt] = useState(0);

  const reload = useCallback(() => {
    setGuard({ name: "loading" });
    setAttempt((current) => current + 1);
  }, []);

  useEffect(() => {
    if (session) return;

    let cancelled = false;

    me()
      .then((result) => {
        if (cancelled) return;

        const active = result.memberships.find(
          (membership) => membership.membership_id === result.active_membership_id,
        );

        if (result.requires_2fa_setup) {
          setGuard({ name: "totp-setup" });
        } else if (active) {
          setSession(toActiveSession(active));
        } else if (result.memberships.length > 1) {
          setGuard({ name: "choose-school", memberships: result.memberships });
        } else {
          router.replace(result.is_platform_admin ? "/platform" : "/login");
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
  }, [session, setSession, router, attempt]);

  if (session) {
    return children;
  }

  if (guard.name === "totp-setup") {
    return (
      <CenteredCard>
        <TotpSetup onDone={reload} />
      </CenteredCard>
    );
  }

  if (guard.name === "choose-school") {
    return (
      <CenteredCard>
        <SchoolPicker memberships={guard.memberships} locale={locale} />
      </CenteredCard>
    );
  }

  if (guard.name === "failed") {
    return (
      <main className="flex flex-1 flex-col items-center justify-center gap-3 p-8">
        <p role="alert" className="text-sm text-destructive">
          {t("loadFailed")}
        </p>
        <Button variant="outline" onClick={reload}>
          {t("retry")}
        </Button>
      </main>
    );
  }

  return (
    <main className="flex flex-1 items-center justify-center p-8">
      <p className="text-sm text-muted-foreground">{t("loading")}</p>
    </main>
  );
}
