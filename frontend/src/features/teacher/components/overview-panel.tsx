"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/features/platform/components/panel-ui";
import { required, useValidatedForm } from "@/lib/use-validated-form";
import { saveSetup } from "../api";
import { ErrorNote, Panel, useTeacherError, useWorkspace } from "./teacher-ui";

function SetupForm() {
  const t = useTranslations("Teacher.overview");
  const describe = useTeacherError();
  const { reload } = useWorkspace();
  const form = useValidatedForm({
    initial: { subject: "", grade_levels: "" },
    idPrefix: "setup-",
    validators: { subject: required(100), grade_levels: required(100) },
    submit: async (values) => saveSetup(values),
    onSuccess: reload,
    describeError: describe,
  });

  return (
    <Panel title={t("setupTitle")}>
      <p className="mb-4 text-sm text-ink-soft">{t("setupHint")}</p>
      <form onSubmit={form.handleSubmit} noValidate className="grid gap-3 sm:grid-cols-2">
        <Field id="setup-subject" label={t("subject")} required error={form.errorFor("subject")}>
          <Input {...form.bind("subject")} placeholder={t("subjectExample")} />
        </Field>
        <Field
          id="setup-grade_levels"
          label={t("grades")}
          required
          error={form.errorFor("grade_levels")}
        >
          <Input {...form.bind("grade_levels")} placeholder={t("gradesExample")} />
        </Field>
        <div className="sm:col-span-2">
          <ErrorNote message={form.formError} />
        </div>
        <div className="sm:col-span-2">
          <Button type="submit" size="sm" loading={form.saving}>
            {t("setupSubmit")}
          </Button>
        </div>
      </form>
    </Panel>
  );
}

function Stat({ label, used, limit }: { label: string; used: number; limit: number | null }) {
  const t = useTranslations("Teacher.overview");
  return (
    <div className="rounded-card border border-line bg-bg p-4">
      <p className="text-sm text-ink-soft">{label}</p>
      <p className="mt-1 text-2xl font-bold text-navy-deep tabular-nums">
        {limit === null ? used : t("usedOf", { used, limit })}
      </p>
    </div>
  );
}

export function OverviewPanel() {
  const t = useTranslations("Teacher.overview");
  const { workspace } = useWorkspace();
  const { usage, limits, profile } = workspace;

  const steps = [
    { key: "setup", done: profile !== null, href: "/teacher" },
    { key: "class", done: usage.classes > 0, href: "/teacher/classes" },
    { key: "students", done: usage.students > 0, href: "/teacher/classes" },
    { key: "lesson", done: usage.lesson_plans > 0, href: "/teacher/lessons" },
    { key: "attendance", done: usage.attendance_records > 0, href: "/teacher/classes" },
    { key: "presentation", done: usage.presentation_exports > 0, href: "/teacher/lessons" },
  ] as const;
  const remaining = steps.filter((step) => !step.done);

  return (
    <>
      <PageHeader
        title={t("title", { name: workspace.teacher_name })}
        subtitle={profile ? `${profile.subject} · ${profile.grade_levels}` : t("subtitle")}
      />

      {!profile && !workspace.access.read_only && <SetupForm />}

      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label={t("classes")} used={usage.classes} limit={limits.classes} />
        <Stat label={t("students")} used={usage.students} limit={limits.students} />
        <Stat label={t("lessons")} used={usage.lesson_plans} limit={limits.lesson_plans} />
      </div>

      {remaining.length > 0 && (
        <Panel title={t("checklist")}>
          <ul className="flex flex-col gap-2">
            {steps.map((step) => (
              <li key={step.key} className="flex items-center gap-3 text-sm">
                <span
                  aria-hidden="true"
                  className={
                    step.done
                      ? "size-2.5 shrink-0 rounded-full bg-emerald-600"
                      : "size-2.5 shrink-0 rounded-full border-2 border-navy-line"
                  }
                />
                {step.done ? (
                  <span className="text-ink-soft line-through">{t(`steps.${step.key}`)}</span>
                ) : (
                  <Link href={step.href} className="font-semibold text-navy hover:underline">
                    {t(`steps.${step.key}`)}
                  </Link>
                )}
              </li>
            ))}
          </ul>
        </Panel>
      )}
    </>
  );
}
