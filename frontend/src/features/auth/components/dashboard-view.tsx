"use client";

import { useLocale, useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useSession } from "../session-store";
import { useLogout } from "../use-logout";

export function DashboardView() {
  const t = useTranslations("Dashboard");
  const tRoles = useTranslations("Roles");
  const locale = useLocale();
  const { session } = useSession();
  const { handleLogout, isLoggingOut } = useLogout();

  if (!session) {
    return null;
  }

  const schoolName = locale === "ar" ? session.school.name_ar : session.school.name_en;

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
