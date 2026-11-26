"use client";

import type { ReactNode } from "react";
import { ArrowRight, BookOpenText, ClipboardCheck, Presentation } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "cn";
import { Link } from "@/i18n/navigation";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/features/platform/components/panel-ui";
import { useLoad } from "@/features/platform/use-load";
import { required, useValidatedForm } from "@/lib/use-validated-form";
import { listExams, listLessonPlans, saveSetup } from "../api";
import { ErrorNote, Panel, useFormatDate, useTeacherError, useWorkspace } from "./teacher-ui";

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
    <div className="flex flex-col gap-3 border-t border-line pt-5">
      <div>
        <h3 className="text-base font-bold text-navy-deep">{t("setupTitle")}</h3>
        <p className="mt-1 text-sm text-ink-soft">{t("setupHint")}</p>
      </div>
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
          <Button type="submit" className="w-full sm:w-auto" loading={form.saving}>
            {t("setupSubmit")}
          </Button>
        </div>
      </form>
    </div>
  );
}

const WELCOME_STEPS = ["lesson", "presentation", "test"] as const;

/** The first screen after sign-up: what the app makes, then two questions to start. */
function Welcome() {
  const t = useTranslations("Teacher.overview.welcome");
  return (
    <section className="flex flex-col gap-5 rounded-card border border-line bg-bg p-5 sm:p-6">
      <div>
        <h2 className="text-xl text-navy-deep">{t("title")}</h2>
        <p className="mt-1 text-sm text-ink-soft">{t("body")}</p>
      </div>
      <ol className="grid gap-3 sm:grid-cols-3">
        {WELCOME_STEPS.map((step, index) => (
          <li key={step} className="flex items-start gap-3 rounded-control bg-bg-tint p-3">
            <span
              aria-hidden="true"
              className="flex size-7 shrink-0 items-center justify-center rounded-full bg-navy text-xs font-bold text-on-dark"
            >
              {index + 1}
            </span>
            <span className="flex flex-col text-sm">
              <span className="font-bold text-navy-deep">{t(`${step}.title`)}</span>
              <span className="text-ink-soft">{t(`${step}.body`)}</span>
            </span>
          </li>
        ))}
      </ol>
      <SetupForm />
    </section>
  );
}

/** One big way in to each AI tool, so a new teacher knows where to start. */
function ToolCard({
  href,
  icon: Icon,
  title,
  body,
  action,
  tone,
}: {
  href: "/teacher/lessons" | "/teacher/presentations" | "/teacher/tests";
  icon: typeof BookOpenText;
  title: string;
  body: string;
  action: string;
  tone: "navy" | "orange";
}) {
  return (
    <li>
      <Link
        href={href}
        className="group flex h-full flex-col gap-3 rounded-card border border-line bg-bg p-5 transition-colors hover:border-navy-line"
      >
        <span
          aria-hidden="true"
          className={cn(
            "flex size-12 items-center justify-center rounded-control",
            tone === "orange" ? "bg-orange-soft text-orange-text" : "bg-navy-soft text-navy",
          )}
        >
          <Icon className="size-6" />
        </span>
        <span className="text-lg font-bold text-navy-deep">{title}</span>
        <span className="text-sm text-ink-soft">{body}</span>
        <span className="mt-auto flex items-center gap-1.5 pt-1 text-sm font-bold text-navy">
          {action}
          <ArrowRight
            aria-hidden="true"
            className="size-4 transition-transform group-hover:translate-x-0.5 rtl:rotate-180"
          />
        </span>
      </Link>
    </li>
  );
}

function Meter({ label, used, limit }: { label: string; used: number; limit: number | null }) {
  const t = useTranslations("Teacher.overview");
  const share = limit ? Math.min(used / limit, 1) : 0;
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between gap-2 text-sm">
        <span className="text-ink">{label}</span>
        <span className="font-bold text-navy-deep tabular-nums">
          {limit === null ? t("unlimited") : t("usedOf", { used, limit })}
        </span>
      </div>
      {limit !== null && (
        <div aria-hidden="true" className="h-1.5 overflow-hidden rounded-full bg-bg-tint">
          <div
            className={cn("h-full rounded-full", share >= 1 ? "bg-red-600" : "bg-orange")}
            style={{ inlineSize: `${share * 100}%` }}
          />
        </div>
      )}
    </div>
  );
}

function RecentList({
  title,
  href,
  items,
  empty,
}: {
  title: string;
  href: "/teacher/lessons" | "/teacher/tests";
  items: { id: number; title: string; detail: string }[] | null;
  empty: string;
}) {
  const t = useTranslations("Teacher.overview");
  return (
    <Panel
      title={title}
      action={
        <Link href={href} className="text-sm font-semibold text-navy hover:underline">
          {t("seeAll")}
        </Link>
      }
    >
      {items === null ? (
        <p className="text-sm text-ink-soft">{t("loading")}</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-ink-soft">{empty}</p>
      ) : (
        <ul className="flex flex-col divide-y divide-line">
          {items.map((item) => (
            <li key={item.id} className="flex flex-col py-2.5 first:pt-0 last:pb-0">
              <span className="truncate font-semibold text-ink" dir="auto">
                {item.title}
              </span>
              <span className="text-xs text-ink-soft">{item.detail}</span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

const RECENT = 3;

export function OverviewPanel() {
  const t = useTranslations("Teacher.overview");
  const tTests = useTranslations("Teacher.tests");
  const formatDate = useFormatDate();
  const { workspace } = useWorkspace();
  const { usage, limits, profile } = workspace;
  const lessons = useLoad((signal) => listLessonPlans("", 1, signal), "overview-lessons");
  const exams = useLoad((signal) => listExams("", 1, signal), "overview-tests");

  const steps: { title: ReactNode; done: boolean }[] = [
    { title: t("steps.setup"), done: profile !== null },
    { title: t("steps.lesson"), done: usage.lesson_plans > 0 },
    { title: t("steps.presentation"), done: usage.presentation_exports > 0 },
    { title: t("steps.test"), done: usage.exams > 0 },
  ];
  const remaining = steps.filter((step) => !step.done).length;

  return (
    <>
      <PageHeader
        title={t("title", { name: workspace.teacher_name })}
        subtitle={profile ? `${profile.subject} · ${profile.grade_levels}` : t("subtitle")}
      />

      {/* A new teacher sees only the welcome until they say what they teach. */}
      {!profile && !workspace.access.read_only ? (
        <Welcome />
      ) : (
        <>
          <section className="flex flex-col gap-3">
            <h2 className="text-lg text-navy-deep">{t("toolsTitle")}</h2>
            <ul className="grid gap-3 md:grid-cols-3">
              <ToolCard
                href="/teacher/lessons"
                icon={BookOpenText}
                title={t("tools.lesson.title")}
                body={t("tools.lesson.body")}
                action={t("tools.lesson.action")}
                tone="navy"
              />
              <ToolCard
                href="/teacher/presentations"
                icon={Presentation}
                title={t("tools.presentation.title")}
                body={t("tools.presentation.body")}
                action={t("tools.presentation.action")}
                tone="orange"
              />
              <ToolCard
                href="/teacher/tests"
                icon={ClipboardCheck}
                title={t("tools.test.title")}
                body={t("tools.test.body")}
                action={t("tools.test.action")}
                tone="navy"
              />
            </ul>
          </section>

          <div className="grid gap-4 lg:grid-cols-[1fr_1fr_1fr]">
            <RecentList
              title={t("recentLessons")}
              href="/teacher/lessons"
              empty={t("noLessons")}
              items={
                lessons.state.name === "ready"
                  ? lessons.state.data.results.slice(0, RECENT).map((plan) => ({
                      id: plan.id,
                      title: plan.title,
                      detail: formatDate(plan.updated_at),
                    }))
                  : lessons.state.name === "loading"
                    ? null
                    : []
              }
            />
            <RecentList
              title={t("recentTests")}
              href="/teacher/tests"
              empty={t("noTests")}
              items={
                exams.state.name === "ready"
                  ? exams.state.data.results.slice(0, RECENT).map((exam) => ({
                      id: exam.id,
                      title: exam.title,
                      detail: tTests("questionCount", { count: exam.question_count }),
                    }))
                  : exams.state.name === "loading"
                    ? null
                    : []
              }
            />
            <Panel title={t("allowanceTitle")}>
              <div className="flex flex-col gap-4">
                <Meter label={t("aiLessons")} used={usage.ai_used} limit={limits.ai_lessons} />
                <Meter label={t("aiTests")} used={usage.ai_exams_used} limit={limits.ai_exams} />
                <Meter
                  label={t("presentations")}
                  used={usage.presentation_exports}
                  limit={limits.presentation_exports}
                />
                <Link
                  href="/teacher/plan"
                  className="text-sm font-semibold text-navy hover:underline"
                >
                  {t("seePlan")}
                </Link>
              </div>
            </Panel>
          </div>

          {remaining > 0 && (
            <Panel title={t("checklist")}>
              <ul className="flex flex-col gap-2">
                {steps.map((step, index) => (
                  <li key={index} className="flex items-center gap-3 text-sm">
                    <span
                      aria-hidden="true"
                      className={
                        step.done
                          ? "size-2.5 shrink-0 rounded-full bg-emerald-600"
                          : "size-2.5 shrink-0 rounded-full border-2 border-navy-line"
                      }
                    />
                    <span className={step.done ? "text-ink-soft line-through" : "text-ink"}>
                      {step.title}
                    </span>
                  </li>
                ))}
              </ul>
            </Panel>
          )}
        </>
      )}
    </>
  );
}
