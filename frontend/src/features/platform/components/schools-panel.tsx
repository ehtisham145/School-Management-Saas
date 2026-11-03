"use client";

import { useCallback, useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError } from "@/lib/api";
import { listSchools } from "../api";
import { SCHOOLS_PAGE_SIZE, type PlatformSchool, type SchoolsPage } from "../schemas";
import { SchoolForm } from "./school-form";

type LoadState =
  | { name: "loading" }
  | { name: "ready"; data: SchoolsPage }
  | { name: "denied" }
  | { name: "failed" };

export function SchoolsPanel() {
  const t = useTranslations("Platform.schools");
  const tForm = useTranslations("Platform.form");
  const locale = useLocale();

  const [page, setPage] = useState(1);
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<LoadState>({ name: "loading" });
  const [isCreating, setIsCreating] = useState(false);
  const [createdName, setCreatedName] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    listSchools(page, controller.signal)
      .then((data) => setState({ name: "ready", data }))
      .catch((err) => {
        if (controller.signal.aborted) return;
        setState(
          err instanceof ApiError && err.status === 403 ? { name: "denied" } : { name: "failed" },
        );
      });

    return () => controller.abort();
  }, [page, reloadKey]);

  const reload = useCallback(() => {
    setState({ name: "loading" });
    setReloadKey((current) => current + 1);
  }, []);

  function goToPage(nextPage: number) {
    setState({ name: "loading" });
    setPage(nextPage);
  }

  const schoolName = (school: PlatformSchool) =>
    locale === "ar" ? school.name_ar : school.name_en;

  function handleCreated(school: PlatformSchool) {
    setIsCreating(false);
    setCreatedName(schoolName(school));
    if (page === 1) {
      reload();
    } else {
      goToPage(1);
    }
  }

  if (state.name === "denied") {
    return (
      <div className="flex flex-col items-center gap-3 py-12 text-center">
        <p role="alert" className="text-sm text-muted-foreground">
          {t("accessDenied")}
        </p>
        <Link href="/login" className="text-sm font-medium underline">
          {t("signIn")}
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">{t("title")}</h1>
          {state.name === "ready" && (
            <p className="text-sm text-muted-foreground">
              {t("total", { count: state.data.count })}
            </p>
          )}
        </div>
        {!isCreating && (
          <Button
            onClick={() => {
              setCreatedName(null);
              setIsCreating(true);
            }}
          >
            {t("newSchool")}
          </Button>
        )}
      </div>

      {createdName && (
        <p role="status" className="rounded-lg bg-muted p-3 text-sm">
          {tForm("success", { school: createdName })}
        </p>
      )}

      {isCreating && (
        <Card>
          <CardHeader>
            <CardTitle>{tForm("title")}</CardTitle>
          </CardHeader>
          <CardContent>
            <SchoolForm onCreated={handleCreated} onCancel={() => setIsCreating(false)} />
          </CardContent>
        </Card>
      )}

      {state.name === "loading" && <p className="text-sm text-muted-foreground">{t("loading")}</p>}

      {state.name === "failed" && (
        <div className="flex flex-col items-start gap-3">
          <p role="alert" className="text-sm text-destructive">
            {t("loadFailed")}
          </p>
          <Button variant="outline" onClick={reload}>
            {t("retry")}
          </Button>
        </div>
      )}

      {state.name === "ready" && state.data.count === 0 && (
        <p className="py-8 text-center text-sm text-muted-foreground">{t("empty")}</p>
      )}

      {state.name === "ready" && state.data.count > 0 && (
        <>
          <div className="overflow-x-auto rounded-lg ring-1 ring-foreground/10">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 text-muted-foreground">
                <tr>
                  <th className="p-3 text-start font-medium">{t("name")}</th>
                  <th className="p-3 text-start font-medium">{t("code")}</th>
                  <th className="p-3 text-start font-medium">{t("status")}</th>
                  <th className="p-3 text-start font-medium">{t("members")}</th>
                  <th className="p-3 text-start font-medium">{t("created")}</th>
                </tr>
              </thead>
              <tbody>
                {state.data.results.map((school) => (
                  <tr key={school.id} className="border-t border-border">
                    <td className="p-3 font-medium">{schoolName(school)}</td>
                    <td className="p-3 font-mono text-xs">
                      <bdi>{school.code}</bdi>
                    </td>
                    <td className="p-3">{school.is_active ? t("active") : t("inactive")}</td>
                    <td className="p-3">{school.member_count}</td>
                    <td className="p-3 whitespace-nowrap">
                      {new Date(school.created_at).toLocaleDateString(locale, {
                        timeZone: "Asia/Riyadh",
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {(state.data.next || state.data.previous) && (
            <div className="flex items-center justify-between gap-3">
              <Button
                variant="outline"
                disabled={!state.data.previous}
                onClick={() => goToPage(page - 1)}
              >
                {t("previous")}
              </Button>
              <span className="text-sm text-muted-foreground">
                {t("page", {
                  page,
                  pages: Math.ceil(state.data.count / SCHOOLS_PAGE_SIZE),
                })}
              </span>
              <Button
                variant="outline"
                disabled={!state.data.next}
                onClick={() => goToPage(page + 1)}
              >
                {t("next")}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
