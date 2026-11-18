"use client";

import { useState } from "react";
import { Plus, Sparkles } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import { optional, required, useValidatedForm } from "@/lib/use-validated-form";
import {
  createLessonPlan,
  deleteLessonPlan,
  downloadPresentation,
  generateLessonPlan,
  listClasses,
  listLessonPlans,
  updateLessonPlan,
} from "../api";
import type { LessonPlan } from "../schemas";
import {
  ConfirmDelete,
  ErrorNote,
  FormButtons,
  ProBadge,
  useFormatDate,
  useTeacherError,
  useWorkspace,
} from "./teacher-ui";

const SECTIONS = ["objectives", "materials", "activities", "assessment", "homework"] as const;
const SECTION_MAX = 5000;

function LessonDialog({
  plan,
  onClose,
  onSaved,
}: {
  plan: LessonPlan | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const t = useTranslations("Teacher.lessons");
  const tCommon = useTranslations("Teacher.common");
  const describe = useTeacherError();
  const classes = useLoad(listClasses, "lesson-classes");
  const form = useValidatedForm({
    initial: {
      title: plan?.title ?? "",
      classroom: plan?.classroom ? String(plan.classroom) : "",
      subject: plan?.subject ?? "",
      grade: plan?.grade ?? "",
      lesson_date: plan?.lesson_date ?? "",
      objectives: plan?.objectives ?? "",
      materials: plan?.materials ?? "",
      activities: plan?.activities ?? "",
      assessment: plan?.assessment ?? "",
      homework: plan?.homework ?? "",
    },
    idPrefix: "lesson-",
    validators: {
      title: required(200),
      subject: optional(100),
      grade: optional(50),
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
        lesson_date: values.lesson_date || null,
      };
      if (plan) await updateLessonPlan(plan.id, body);
      else await createLessonPlan(body);
    },
    onSuccess: onSaved,
    describeError: describe,
  });

  return (
    <Modal
      open
      onClose={onClose}
      title={plan ? t("editTitle") : t("newTitle")}
      closeLabel={tCommon("close")}
    >
      <form onSubmit={form.handleSubmit} noValidate className="flex flex-col gap-3">
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
          <Field id="lesson-lesson_date" label={t("date")}>
            <Input {...form.bind("lesson_date")} type="date" />
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
            <Textarea {...form.bind(section)} rows={3} />
          </Field>
        ))}
        <ErrorNote message={form.formError} />
        <FormButtons saving={form.saving} onCancel={onClose} />
      </form>
    </Modal>
  );
}

function GenerateDialog({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const t = useTranslations("Teacher.lessons");
  const tCommon = useTranslations("Teacher.common");
  const locale = useLocale();
  const describe = useTeacherError();
  const { workspace } = useWorkspace();
  const form = useValidatedForm({
    initial: {
      topic: "",
      subject: workspace.profile?.subject ?? "",
      grade: "",
      language: locale === "ar" ? "ar" : "en",
    },
    idPrefix: "ai-",
    validators: { topic: required(200), subject: required(100), grade: required(50) },
    submit: async (values) => {
      await generateLessonPlan({ ...values, language: values.language as "en" | "ar" });
    },
    onSuccess: onSaved,
    describeError: describe,
  });

  return (
    <Modal
      open
      onClose={onClose}
      title={t("aiTitle")}
      description={t("aiHint", {
        used: workspace.usage.ai_this_month,
        limit: workspace.limits.ai_per_month,
      })}
      closeLabel={tCommon("close")}
    >
      <form onSubmit={form.handleSubmit} noValidate className="flex flex-col gap-3">
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
        <ErrorNote message={form.formError} />
        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="outline" size="sm" onClick={onClose}>
            {tCommon("cancel")}
          </Button>
          <Button type="submit" size="sm" loading={form.saving}>
            {form.saving ? t("generating") : t("generate")}
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
  const [dialog, setDialog] = useState<LessonPlan | "new" | "ai" | null>(null);
  const [removing, setRemoving] = useState<LessonPlan | null>(null);
  const [downloading, setDownloading] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const readOnly = workspace.access.read_only;
  const canUseAi = workspace.limits.pro_features;

  function refresh() {
    setDialog(null);
    reload();
    reloadWorkspace();
  }

  async function download(plan: LessonPlan) {
    setDownloading(plan.id);
    setError(null);
    try {
      await downloadPresentation(plan);
      reloadWorkspace();
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
                variant="outline"
                size="sm"
                disabled={!canUseAi}
                onClick={() => setDialog("ai")}
              >
                <Sparkles aria-hidden="true" className="size-4" />
                {t("ai")}
                {!canUseAi && <ProBadge />}
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
                      loading={downloading === plan.id}
                      onClick={() => download(plan)}
                    >
                      {t("download")}
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

      {dialog === "ai" && <GenerateDialog onClose={() => setDialog(null)} onSaved={refresh} />}
      {dialog && dialog !== "ai" && (
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
