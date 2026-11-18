"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { apiFetch, ApiError } from "@/lib/api";
import { FilterTabs, LoadFeedback, PageHeader, Pagination, SearchBox } from "./panel-ui";
import { useLoad } from "../use-load";

type Status = "all" | "trial" | "paid" | "ended";
const STATUSES: Status[] = ["all", "trial", "paid", "ended"];
const EXTENSION_DAYS = 7;

type Teacher = {
  id: number;
  name: string;
  email: string | null;
  created_at: string;
  class_count: number;
  student_count: number;
  plan_code: string | null;
  is_trial: boolean | null;
  ends_on: string | null;
  requested_plan: "teacher" | "teacher_pro" | null;
};

function listTeachers(search: string, status: Status, page: number, signal: AbortSignal) {
  const query = new URLSearchParams({ page: String(page) });
  if (search) query.set("search", search);
  if (status !== "all") query.set("status", status);
  return apiFetch<{ count: number; results: Teacher[] }>(`/platform/teachers/?${query}`, {
    signal,
  });
}

export function TeachersPanel() {
  const t = useTranslations("Platform.teachers");
  const locale = useLocale();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<Status>("all");
  const [page, setPage] = useState(1);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { state, reload } = useLoad(
    (signal) => listTeachers(search, status, page, signal),
    `${search}:${status}:${page}`,
  );

  async function act(teacher: Teacher, action: string, body: Record<string, unknown>) {
    setBusy(`${teacher.id}:${action}:${String(body.plan ?? "")}`);
    setError(null);
    try {
      await apiFetch(`/platform/teachers/${teacher.id}/${action}/`, { method: "POST", body });
      reload();
    } catch (err) {
      setError(err instanceof ApiError && err.status === 400 ? t("actionRejected") : t("failed"));
    } finally {
      setBusy(null);
    }
  }

  const formatDate = (value: string) =>
    new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(new Date(value));
  const planName = (code: string) => (code === "teacher_pro" ? t("planPro") : t("planTeacher"));

  return (
    <>
      <PageHeader title={t("title")} subtitle={t("subtitle")} />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <FilterTabs
          label={t("filter")}
          value={status}
          onChange={(value) => {
            setStatus(value);
            setPage(1);
          }}
          options={STATUSES.map((value) => ({ value, label: t(`status.${value}`) }))}
        />
        <SearchBox
          label={t("search")}
          onSearch={(term) => {
            setSearch(term);
            setPage(1);
          }}
        />
      </div>

      {error && (
        <p role="alert" className="rounded-control bg-red-50 p-3 text-sm text-red-700">
          {error}
        </p>
      )}
      <LoadFeedback state={state} onRetry={reload} />

      {state.name === "ready" && state.data.count === 0 && (
        <EmptyState title={t("emptyTitle")} description={t("emptyHint")} />
      )}

      {state.name === "ready" && state.data.count > 0 && (
        <>
          <ul className="flex flex-col gap-3">
            {state.data.results.map((teacher) => {
              const ended = teacher.plan_code === null;
              return (
                <li key={teacher.id} className="rounded-card border border-line bg-bg p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="flex flex-wrap items-center gap-2 font-semibold text-navy-deep">
                        {teacher.name}
                        <Badge tone={ended ? "danger" : teacher.is_trial ? "warning" : "success"}>
                          {ended
                            ? t("status.ended")
                            : teacher.is_trial
                              ? t("status.trial")
                              : planName(teacher.plan_code ?? "")}
                        </Badge>
                      </p>
                      <p className="mt-1 truncate text-sm text-ink-soft" dir="ltr">
                        {teacher.email}
                      </p>
                      <p className="mt-1 text-sm text-ink-soft">
                        {t("usage", {
                          classes: teacher.class_count,
                          students: teacher.student_count,
                        })}
                        {teacher.ends_on &&
                          ` · ${t("endsOn", { date: formatDate(teacher.ends_on) })}`}
                      </p>
                      {teacher.requested_plan && (
                        <p className="mt-1 text-sm font-semibold text-orange-text">
                          {t("requested", { plan: planName(teacher.requested_plan) })}
                        </p>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {(ended || teacher.is_trial) && (
                        <Button
                          variant="outline"
                          size="sm"
                          loading={busy === `${teacher.id}:extend-trial:`}
                          onClick={() => act(teacher, "extend-trial", { days: EXTENSION_DAYS })}
                        >
                          {t("extend", { days: EXTENSION_DAYS })}
                        </Button>
                      )}
                      {(["teacher", "teacher_pro"] as const).map((plan) => (
                        <Button
                          key={plan}
                          size="sm"
                          variant={teacher.requested_plan === plan ? "orange" : "outline"}
                          disabled={teacher.is_trial === false && teacher.plan_code === plan}
                          loading={busy === `${teacher.id}:activate-plan:${plan}`}
                          onClick={() => act(teacher, "activate-plan", { plan })}
                        >
                          {t("activate", { plan: planName(plan) })}
                        </Button>
                      ))}
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
          <Pagination page={page} count={state.data.count} onPage={setPage} />
        </>
      )}
    </>
  );
}
