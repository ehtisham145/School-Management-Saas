"use client";

import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useLogout } from "@/features/auth/use-logout";
import { usePlatformUser } from "../platform-user";
import { DetailRow, PageHeader } from "./panel-ui";
import { initialsOf } from "./profile-menu";

export function ProfilePanel() {
  const t = useTranslations("Platform");
  const user = usePlatformUser();
  const { handleLogout, isLoggingOut } = useLogout();

  return (
    <>
      <PageHeader title={t("profile.title")} subtitle={t("profile.subtitle")} />
      <Card className="max-w-2xl">
        <CardContent className="flex flex-col gap-5">
          <div className="flex items-center gap-4">
            <span
              aria-hidden="true"
              className="flex size-14 items-center justify-center rounded-full bg-navy text-lg font-bold text-on-dark"
            >
              {initialsOf(user)}
            </span>
            <div className="min-w-0">
              <span className="block truncate text-lg font-bold text-navy-deep">
                <bdi>{user.full_name || user.username}</bdi>
              </span>
              <span className="text-sm text-ink-soft">{t("profile.roleValue")}</span>
            </div>
          </div>

          <dl className="grid gap-4 border-t border-line pt-5 sm:grid-cols-2">
            <DetailRow label={t("profile.fullName")}>
              <bdi>{user.full_name || t("common.notProvided")}</bdi>
            </DetailRow>
            <DetailRow label={t("profile.username")}>
              <bdi>{user.username}</bdi>
            </DetailRow>
            <DetailRow label={t("profile.email")}>
              <bdi>{user.email || t("common.notProvided")}</bdi>
            </DetailRow>
            <DetailRow label={t("profile.role")}>{t("profile.roleValue")}</DetailRow>
          </dl>

          <div className="border-t border-line pt-5">
            <Button variant="outline" size="sm" loading={isLoggingOut} onClick={handleLogout}>
              {isLoggingOut ? t("loggingOut") : t("logout")}
            </Button>
          </div>
        </CardContent>
      </Card>
    </>
  );
}
