"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { logout } from "../api";
import { useSession } from "../session-store";

export function DashboardView() {
  const t = useTranslations("Dashboard");
  const tRoles = useTranslations("Roles");
  const locale = useLocale();
  const router = useRouter();
  const { session, clearSession } = useSession();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  if (!session) {
    return null;
  }

  const schoolName = locale === "ar" ? session.school.name_ar : session.school.name_en;

  async function handleLogout() {
    setIsLoggingOut(true);
    try {
      await logout();
    } finally {
      clearSession();
      router.push("/login");
    }
  }

  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 p-8">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>{t("title")}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <p className="text-sm text-muted-foreground">
            {t("welcome", { role: tRoles(session.role), school: schoolName })}
          </p>
          <p className="text-sm text-muted-foreground">{t("placeholder")}</p>
          <Button onClick={handleLogout} disabled={isLoggingOut}>
            {isLoggingOut ? t("loggingOut") : t("logoutButton")}
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}
