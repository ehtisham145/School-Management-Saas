"use client";

import { useEffect, useState } from "react";
import { Check, Plus, Sparkles } from "lucide-react";
import { cn } from "cn";
import { useLocale, useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DateField } from "@/components/ui/date-field";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  LoadFeedback,
  PageHeader,
  Pagination,
  SearchBox,
} from "@/features/platform/components/panel-ui";
import { useLoad } from "@/features/platform/use-load";
import {
  dayDate,
  dayDateToIso,
  isoToDayDate,
  maskDayDate,
  optional,
  required,
  useValidatedForm,
} from "@/lib/use-validated-form";
import {
  createLessonPlan,
  deleteLessonPlan,
  downloadPresentation,
  downloadWordDocument,
  generateLessonPlan,
  listClasses,
  listLessonPlans,
  updateLessonPlan,
} from "../api";
import type { LessonDraft, LessonPlan } from "../schemas";
import {
  ConfirmDelete,
  ErrorNote,
  FormButtons,
  useFormatDate,
  useTeacherError,
  useWorkspace,
} from "./teacher-ui";

const SECTIONS = ["objectives", "materials", "activities", "assessment", "homework"] as const;
const SECTION_MAX = 5000;

function LessonDialog({
  plan,
  draft,
  onClose,
  onSaved,
}: {
  plan: LessonPlan | null;
  /** An AI draft to review. Nothing is saved until the teacher saves it. */
  draft?: LessonDraft;
  onClose: () => void;
  onSaved: () => void;
}) {
  const t = useTranslations("Teacher.lessons");
  const tCommon = useTranslations("Teacher.common");
  const describe = useTeacherError();
  const classes = useLoad(listClasses, "lesson-classes");
  const form = useValidatedForm({
    initial: {
      title: (plan ?? draft)?.title ?? "",
      classroom: (plan ?? draft)?.classroom ? String((plan ?? draft)?.classroom) : "",
      subject: (plan ?? draft)?.subject ?? "",
      grade: (plan ?? draft)?.grade ?? "",
      lesson_date: isoToDayDate(plan?.lesson_date),
      objectives: (plan ?? draft)?.objectives ?? "",
      materials: (plan ?? draft)?.materials ?? "",
      activities: (plan ?? draft)?.activities ?? "",
      assessment: (plan ?? draft)?.assessment ?? "",
      homework: (plan ?? draft)?.homework ?? "",
    },
    idPrefix: "lesson-",
    validators: {
      title: required(200),
      subject: optional(100),
      grade: optional(50),
      lesson_date: dayDate(),
      objectives: optional(SECTION_MAX),
      materials: optional(SECTION_MAX),
      activities: optional(SECTION_MAX),
      assessment: optional(SECTION_MAX),
      homework: optional(SECTION_MAX),
    },
    submit: async (values) => {
      const body = {
        ...values,
        classroom: values.classroom ? Number(values.classroom) : null,
        lesson_date: dayDateToIso(values.lesson_date),
      };
      if (plan) await updateLessonPlan(plan.id, body);
      else await createLessonPlan({ ...body, source: draft ? "ai" : "manual" });
    },
    sanitizers: { lesson_date: maskDayDate },
    onSuccess: onSaved,
    describeError: describe,
  });

  return (
    <Modal
      open
      onClose={onClose}
      title={plan ? t("editTitle") : draft ? t("reviewTitle") : t("newTitle")}
      closeLabel={tCommon("close")}
      size={draft ? "wide" : "default"}
    >
      <form onSubmit={form.handleSubmit} noValidate className="flex flex-col gap-3">
        {draft && (
          <p className="flex items-start gap-2 rounded-control bg-navy-soft p-3 text-sm text-navy-deep">
            <Sparkles aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
            {t("reviewHint")}
          </p>
        )}
        <Field id="lesson-title" label={t("lessonTitle")} required error={form.errorFor("title")}>
          <Input {...form.bind("title")} />
        </Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field id="lesson-classroom" label={t("classroom")}>
            <Select {...form.bind("classroom")} className="h-11">
              <option value="">{t("noClass")}</option>
              {classes.state.name === "ready" &&
                classes.state.data.map((classroom) => (
                  <option key={classroom.id} value={classroom.id}>
                    {classroom.name}
                  </option>
                ))}
            </Select>
          </Field>
          <Field id="lesson-lesson_date" label={t("date")} error={form.errorFor("lesson_date")}>
            <DateField
              {...form.bind("lesson_date")}
              onPick={(value) => form.setValue("lesson_date", value)}
              calendarLabel={t("openCalendar")}
              className="h-11"
            />
          </Field>
          <Field id="lesson-subject" label={t("subject")} error={form.errorFor("subject")}>
            <Input {...form.bind("subject")} />
          </Field>
          <Field id="lesson-grade" label={t("grade")} error={form.errorFor("grade")}>
            <Input {...form.bind("grade")} />
          </Field>
        </div>
        {SECTIONS.map((section) => (
          <Field
            key={section}
            id={`lesson-${section}`}
            label={t(`sections.${section}`)}
            hint={section === "objectives" ? t("sectionHint") : undefined}
            error={form.errorFor(section)}
          >
            <Textarea {...form.bind(section)} rows={draft ? 5 : 3} />
          </Field>
        ))}
        <ErrorNote message={form.formError} />
        {draft ? (
          <div className="flex justify-end gap-2 pt-1">
            <Button type="button" variant="outline" size="sm" onClick={onClose}>
              {t("discard")}
            </Button>
            <Button type="submit" size="sm" loading={form.saving}>
              {form.saving ? tCommon("saving") : t("saveDraft")}
            </Button>
          </div>
        ) : (
          <FormButtons saving={form.saving} onCancel={onClose} />
        )}
      </form>
    </Modal>
  );
}

const AI_STEPS = ["read", "objectives", "activities", "assessment"] as const;

/** Shown while the AI writes, which takes a few seconds. */
function AiProgress() {
  const t = useTranslations("Teacher.lessons");
  const [step, setStep] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(
      () => setStep((current) => Math.min(current + 1, AI_STEPS.length - 1)),
      2200,
    );
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div role="status" aria-live="polite" className="flex flex-col gap-4 py-2">
      <div className="h-1.5 overflow-hidden rounded-full bg-bg-tint">
        <div
          className="h-full rounded-full bg-navy transition-[inline-size] duration-700"
          style={{ inlineSize: `${((step + 1) / AI_STEPS.length) * 100}%` }}
        />
      </div>
      <ol className="flex flex-col gap-2.5">
        {AI_STEPS.map((item, index) => (
          <li
            key={item}
            className={cn(
              "flex items-center gap-3 text-sm transition-opacity",
              index > step ? "opacity-40" : "opacity-100",
            )}
          >
            <span
              aria-hidden="true"
              className={cn(
                "flex size-6 shrink-0 items-center justify-center rounded-full border",
                index < step && "border-navy bg-navy text-on-dark",
                index === step && "animate-pulse border-navy text-navy",
                index > step && "border-line text-ink-soft",
              )}
            >
              {index < step ? <Check className="size-3.5" /> : index + 1}
            </span>
            <span className={index === step ? "font-semibold text-ink" : "text-ink-soft"}>
              {t(`aiSteps.${item}`)}
            </span>
          </li>
        ))}
      </ol>
      <div aria-hidden="true" className="flex flex-col gap-2">
        {["w-3/4", "w-full", "w-5/6", "w-2/3"].map((width) => (
          <div key={width} className={cn("h-3 animate-pulse rounded-full bg-bg-tint", width)} />
        ))}
      </div>
    </div>
  );
}

function useAiAllowance() {
  const { workspace } = useWorkspace();
  const limit = workspace.limits.ai_lessons;
  const used = workspace.usage.ai_used;
  return { used, limit, left: Math.max(limit - used, 0), period: workspace.limits.ai_period };
}

function GenerateDialog({
  onClose,
  onDraft,
}: {
  onClose: () => void;
  onDraft: (draft: LessonDraft) => void;
}) {
  const t = useTranslations("Teacher.lessons");
  const tCommon = useTranslations("Teacher.common");
  const locale = useLocale();
  const describe = useTeacherError();
  const { workspace } = useWorkspace();
  const allowance = useAiAllowance();
  const classes = useLoad(listClasses, "ai-classes");
  const form = useValidatedForm({
    initial: {
      classroom: "",
      topic: "",
      subject: workspace.profile?.subject ?? "",
      grade: "",
      language: locale === "ar" ? "ar" : "en",
    },
    idPrefix: "ai-",
    validators: { topic: required(200), subject: required(100), grade: required(50) },
    submit: async (values) => {
      const draft = await generateLessonPlan({
        ...values,
        classroom: values.classroom ? Number(values.classroom) : null,
        language: values.language as "en" | "ar",
      });
      onDraft(draft);
    },
    describeError: describe,
  });

  return (
    <Modal
      open
      onClose={onClose}
      title={t("aiTitle")}
      description={t("aiHint")}
      closeLabel={tCommon("close")}
    >
      {form.saving && <AiProgress />}
      <form
        onSubmit={form.handleSubmit}
        noValidate
        className={cn("flex flex-col gap-3", form.saving && "hidden")}
      >
        <div className="rounded-control bg-bg-tint p-3">
          <div className="flex items-center justify-between gap-2 text-sm">
            <span className="font-semibold text-ink">
              {t(allowance.period === "trial" ? "aiLeftTrial" : "aiLeftMonth", {
                left: allowance.left,
                limit: allowance.limit,
              })}
            </span>
          </div>
          <div aria-hidden="true" className="mt-2 h-1.5 overflow-hidden rounded-full bg-bg">
            <div
              className="h-full rounded-full bg-orange"
              style={{
                inlineSize: `${allowance.limit ? (allowance.left / allowance.limit) * 100 : 0}%`,
              }}
            />
          </div>
        </div>
        <Field id="ai-topic" label={t("topic")} required error={form.errorFor("topic")}>
          <Input {...form.bind("topic")} placeholder={t("topicExample")} />
        </Field>
        <div className="grid gap-3 sm:grid-cols-3">
          <Field id="ai-subject" label={t("subject")} required error={form.errorFor("subject")}>
            <Input {...form.bind("subject")} />
          </Field>
          <Field id="ai-grade" label={t("grade")} required error={form.errorFor("grade")}>
            <Input {...form.bind("grade")} />
          </Field>
          <Field id="ai-language" label={t("language")}>
            <Select {...form.bind("language")} className="h-11">
              <option value="en">English</option>
              <option value="ar">العربية</option>
            </Select>
          </Field>
        </div>
        <Field id="ai-classroom" label={t("classroom")}>
          <Select {...form.bind("classroom")} className="h-11">
            <option value="">{t("noClass")}</option>
            {classes.state.name === "ready" &&
              classes.state.data.map((classroom) => (
                <option key={classroom.id} value={classroom.id}>
                  {classroom.name}
                </option>
              ))}
          </Select>
        </Field>
        <p className="text-xs text-ink-soft">{t("aiPrivacy")}</p>
        <ErrorNote message={form.formError} />
        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="outline" size="sm" onClick={onClose}>
            {tCommon("cancel")}
          </Button>
          <Button type="submit" size="sm" disabled={allowance.left === 0}>
            <Sparkles aria-hidden="true" className="size-4" />
            {t("generate")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export function LessonsPanel() {
  const t = useTranslations("Teacher.lessons");
  const tCommon = useTranslations("Teacher.common");
  const describe = useTeacherError();
  const formatDate = useFormatDate();
  const { workspace, reload: reloadWorkspace } = useWorkspace();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const { state, reload } = useLoad(
    (signal) => listLessonPlans(search, page, signal),
    `${search}:${page}`,
  );
  const [dialog, setDialog] = useState<LessonPlan | "new" | "ai" | { draft: LessonDraft } | null>(
    null,
  );
  const [removing, setRemoving] = useState<LessonPlan | null>(null);
  // "12:pptx" while lesson 12 downloads as PowerPoint.
  const [downloading, setDownloading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const readOnly = workspace.access.read_only;
  const allowance = useAiAllowance();

  function refresh() {
    setDialog(null);
    reload();
    reloadWorkspace();
  }

  async function download(plan: LessonPlan, format: "pptx" | "docx") {
    setDownloading(`${plan.id}:${format}`);
    setError(null);
    try {
      if (format === "pptx") {
        await downloadPresentation(plan);
        // PowerPoint downloads count against the trial's limit.
        reloadWorkspace();
      } else {
        await downloadWordDocument(plan);
      }
    } catch (err) {
      setError(describe(err));
    } finally {
      setDownloading(null);
    }
  }

  return (
    <>
      <PageHeader
        title={t("title")}
        subtitle={t("subtitle")}
        action={
          !readOnly && (
            <div className="flex flex-wrap gap-2">
              <Button
                variant="orange"
                size="sm"
                disabled={allowance.left === 0}
                onClick={() => setDialog("ai")}
              >
                <Sparkles aria-hidden="true" className="size-4" />
                {t("ai")}
                <span className="rounded-full bg-on-orange/20 px-1.5 text-[11px] tabular-nums">
                  {t("aiLeftShort", { left: allowance.left })}
                </span>
              </Button>
              <Button size="sm" onClick={() => setDialog("new")}>
                <Plus aria-hidden="true" className="size-4" />
                {t("new")}
              </Button>
            </div>
          )
        }
      />

      <SearchBox
        label={t("search")}
        onSearch={(term) => {
          setSearch(term);
          setPage(1);
        }}
      />
      <ErrorNote message={error} />
      <LoadFeedback state={state} onRetry={reload} />

      {state.name === "ready" && state.data.count === 0 && (
        <EmptyState title={t("emptyTitle")} description={t("emptyHint")} />
      )}

      {state.name === "ready" && state.data.count > 0 && (
        <>
          <ul className="flex flex-col gap-3">
            {state.data.results.map((plan) => (
              <li key={plan.id} className="rounded-card border border-line bg-bg p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="flex flex-wrap items-center gap-2 text-[16px] font-semibold text-navy-deep">
                      {plan.title}
                      {plan.source === "ai" && <Badge tone="info">{t("aiBadge")}</Badge>}
                    </p>
                    <p className="mt-1 text-sm text-ink-soft">
                      {[
                        plan.classroom_name,
                        plan.subject,
                        plan.lesson_date && formatDate(plan.lesson_date),
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      loading={downloading === `${plan.id}:pptx`}
                      onClick={() => download(plan, "pptx")}
                    >
                      {t("download")}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      loading={downloading === `${plan.id}:docx`}
                      onClick={() => download(plan, "docx")}
                    >
                      {t("downloadWord")}
                    </Button>
                    {!readOnly && (
                      <>
                        <Button variant="outline" size="sm" onClick={() => setDialog(plan)}>
                          {tCommon("edit")}
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => setRemoving(plan)}>
                          {tCommon("delete")}
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
          <Pagination page={page} count={state.data.count} onPage={setPage} />
        </>
      )}

      {dialog === "ai" && (
        <GenerateDialog
          onClose={() => setDialog(null)}
          onDraft={(draft) => {
            setDialog({ draft });
            // The allowance went down by one.
            reloadWorkspace();
          }}
        />
      )}
      {dialog && typeof dialog === "object" && "draft" in dialog && (
        <LessonDialog
          plan={null}
          draft={dialog.draft}
          onClose={() => setDialog(null)}
          onSaved={refresh}
        />
      )}
      {(dialog === "new" || (dialog && typeof dialog === "object" && "id" in dialog)) && (
        <LessonDialog
          plan={dialog === "new" ? null : dialog}
          onClose={() => setDialog(null)}
          onSaved={refresh}
        />
      )}
      {removing && (
        <ConfirmDelete
          title={t("deleteTitle", { name: removing.title })}
          body={t("deleteBody")}
          onConfirm={async () => {
            await deleteLessonPlan(removing.id);
            refresh();
          }}
          onClose={() => setRemoving(null)}
        />
      )}
    </>
  );
}
