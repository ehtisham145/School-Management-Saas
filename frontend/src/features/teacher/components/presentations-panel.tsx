"use client";

import { useState } from "react";
import { Download, Presentation, Sparkles } from "lucide-react";
import { useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import {
  LoadFeedback,
  PageHeader,
  Pagination,
  SearchBox,
} from "@/features/platform/components/panel-ui";
import { useLoad } from "@/features/platform/use-load";
import { downloadPresentation, listLessonPlans } from "../api";
import type { LessonDraft, LessonPlan } from "../schemas";
import { GenerateDialog, LessonDialog, useAiAllowance } from "./lessons-panel";
import { ErrorNote, SavedNote, useFormatDate, useTeacherError, useWorkspace } from "./teacher-ui";

/**
 * PowerPoint with AI: the teacher gives a topic, checks the lesson the AI writes, and the
 * slides download as soon as it is saved. Built on lesson plans, so every presentation can
 * be downloaded again from here or as Word from Lesson plans.
 */
export function PresentationsPanel() {
  const t = useTranslations("Teacher.presentations");
  const describe = useTeacherError();
  const formatDate = useFormatDate();
  const { workspace, reload: reloadWorkspace } = useWorkspace();
  const allowance = useAiAllowance();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const { state, reload } = useLoad(
    (signal) => listLessonPlans(search, page, signal),
    `presentations:${search}:${page}`,
  );
  const [step, setStep] = useState<"ask" | { draft: LessonDraft } | null>(null);
  const [downloading, setDownloading] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const readOnly = workspace.access.read_only;
  const { presentation_exports: exportLimit } = workspace.limits;
  const exportsLeft =
    exportLimit === null ? null : Math.max(exportLimit - workspace.usage.presentation_exports, 0);

  async function download(plan: LessonPlan) {
    setDownloading(plan.id);
    setError(null);
    setDone(null);
    try {
      await downloadPresentation(plan);
      setDone(t("downloaded", { title: plan.title }));
      // PowerPoint downloads count on the trial.
      reloadWorkspace();
    } catch (err) {
      setError(describe(err));
    } finally {
      setDownloading(null);
    }
  }

  return (
    <>
      <PageHeader title={t("heroTitle")} subtitle={t("heroHint")} />

      {!readOnly && (
        <section className="flex flex-col gap-4 rounded-card border border-line bg-bg p-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <span
              aria-hidden="true"
              className="flex size-11 shrink-0 items-center justify-center rounded-control bg-orange-soft text-orange-text"
            >
              <Presentation className="size-6" />
            </span>
            <div>
              <p className="font-bold text-navy-deep">{t("startTitle")}</p>
              <p className="mt-1 text-sm text-ink-soft">{t("startHint")}</p>
              <p className="mt-2 text-xs text-ink-soft">
                {t("left", { left: allowance.left, limit: allowance.limit })}
                {exportsLeft !== null && ` · ${t("exportsLeft", { left: exportsLeft })}`}
              </p>
            </div>
          </div>
          <Button
            variant="orange"
            className="w-full sm:w-auto"
            disabled={allowance.left === 0 || exportsLeft === 0}
            onClick={() => setStep("ask")}
          >
            <Sparkles aria-hidden="true" className="size-4" />
            {t("start")}
          </Button>
        </section>
      )}

      <ErrorNote message={error} />
      <SavedNote message={done} />

      <h2 className="text-lg text-navy-deep">{t("listTitle")}</h2>
      <SearchBox
        label={t("search")}
        onSearch={(term) => {
          setSearch(term);
          setPage(1);
        }}
      />
      <LoadFeedback state={state} onRetry={reload} />

      {state.name === "ready" && state.data.count === 0 && (
        <EmptyState title={t("emptyTitle")} description={t("emptyHint")} />
      )}

      {state.name === "ready" && state.data.count > 0 && (
        <>
          <ul className="flex flex-col gap-3">
            {state.data.results.map((plan) => (
              <li
                key={plan.id}
                className="flex flex-col gap-3 rounded-card border border-line bg-bg p-4 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0">
                  <p
                    className="flex flex-wrap items-center gap-2 font-semibold text-navy-deep"
                    dir="auto"
                  >
                    {plan.title}
                    {plan.source === "ai" && <Badge tone="info">{t("aiBadge")}</Badge>}
                  </p>
                  <p className="mt-1 text-sm text-ink-soft">
                    {[plan.subject, plan.grade, formatDate(plan.updated_at)]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full sm:w-auto"
                  loading={downloading === plan.id}
                  onClick={() => download(plan)}
                >
                  <Download aria-hidden="true" className="size-4" />
                  {t("download")}
                </Button>
              </li>
            ))}
          </ul>
          <Pagination page={page} count={state.data.count} onPage={setPage} />
        </>
      )}

      {step === "ask" && (
        <GenerateDialog
          title={t("dialogTitle")}
          hint={t("dialogHint")}
          submitLabel={t("dialogSubmit")}
          onClose={() => setStep(null)}
          onDraft={(draft) => {
            setStep({ draft });
            // The AI allowance went down by one.
            reloadWorkspace();
          }}
        />
      )}
      {step && typeof step === "object" && (
        <LessonDialog
          plan={null}
          draft={step.draft}
          onClose={() => setStep(null)}
          onSaved={(plan) => {
            setStep(null);
            reload();
            void download(plan);
          }}
        />
      )}
    </>
  );
}
