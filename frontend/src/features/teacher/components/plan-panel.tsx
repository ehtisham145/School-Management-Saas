"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { cn } from "cn";
import { Link } from "@/i18n/navigation";
import { Button, buttonVariants } from "@/components/ui/button";
import { PageHeader } from "@/features/platform/components/panel-ui";
import { requestUpgrade } from "../api";
import type { TeacherPlanCode } from "../schemas";
import { ErrorNote, Panel, useFormatDate, useTeacherError, useWorkspace } from "./teacher-ui";

const PLANS: TeacherPlanCode[] = ["teacher", "teacher_pro"];
type UsageKey = "ai" | "aiTests" | "presentations" | "lessons" | "classes" | "students";

export function PlanPanel() {
  const t = useTranslations("Teacher.plan");
  const tPricing = useTranslations("Marketing.pricing");
  const describe = useTeacherError();
  const formatDate = useFormatDate();
  const { workspace, reload } = useWorkspace();
  const [busy, setBusy] = useState<TeacherPlanCode | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { access, usage, limits, pending_upgrade: pending, features } = workspace;

  async function choose(plan: TeacherPlanCode) {
    setBusy(plan);
    setError(null);
    try {
      await requestUpgrade(plan);
      reload();
    } catch (err) {
      setError(describe(err));
    } finally {
      setBusy(null);
    }
  }

  const rows: { key: UsageKey; used: number; limit: number | null }[] = [
    { key: "ai", used: usage.ai_used, limit: limits.ai_lessons },
    { key: "aiTests", used: usage.ai_exams_used, limit: limits.ai_exams },
    { key: "presentations", used: usage.presentation_exports, limit: limits.presentation_exports },
    { key: "lessons", used: usage.lesson_plans, limit: limits.lesson_plans },
    // Classes belong to the school plan (ADR-0027); shown only where they are on.
    ...(features.classes
      ? [
          { key: "classes" as const, used: usage.classes, limit: limits.classes },
          { key: "students" as const, used: usage.students, limit: limits.students },
        ]
      : []),
  ];

  return (
    <>
      <PageHeader title={t("title")} subtitle={t("subtitle")} />

      <Panel title={t(`tiers.${access.tier}`)}>
        {access.ends_on && (
          <p className="mb-4 text-sm text-ink-soft">
            {t("endsOn", { date: formatDate(access.ends_on) })}
          </p>
        )}
        <dl className="grid gap-3 sm:grid-cols-2">
          {rows.map((row) => {
            const share = row.limit ? Math.min(row.used / row.limit, 1) : 0;
            return (
              <div key={row.key} className="flex flex-col gap-2 rounded-control bg-bg-tint p-3">
                <div className="flex items-baseline justify-between gap-2">
                  <dt className="text-sm text-ink">{t(`usage.${row.key}`)}</dt>
                  <dd className="font-bold text-navy-deep tabular-nums">
                    {row.limit === null
                      ? t("unlimited", { used: row.used })
                      : `${row.used} / ${row.limit}`}
                  </dd>
                </div>
                {row.limit !== null && (
                  <div aria-hidden="true" className="h-1.5 overflow-hidden rounded-full bg-bg">
                    <div
                      className={cn("h-full rounded-full", share >= 1 ? "bg-red-600" : "bg-orange")}
                      style={{ inlineSize: `${share * 100}%` }}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </dl>
      </Panel>

      {pending && (
        <p role="status" className="rounded-control bg-emerald-50 p-3 text-sm text-emerald-800">
          {t("pending", { plan: tPricing(`tiers.${pending.plan}.name`) })}
        </p>
      )}
      <ErrorNote message={error} />

      <div className="grid gap-4 md:grid-cols-2">
        {PLANS.map((plan) => {
          const features = tPricing.raw(`tiers.${plan}.features`) as string[];
          const featured = plan === "teacher_pro";
          const current = access.tier === plan;
          return (
            <article
              key={plan}
              className={cn(
                "flex flex-col rounded-card border bg-bg p-6",
                featured ? "border-navy" : "border-line",
              )}
            >
              <h2 className="text-xl text-navy-deep">{tPricing(`tiers.${plan}.name`)}</h2>
              <p className="mt-2 flex items-baseline gap-2">
                <bdi className="text-3xl font-bold text-navy-deep tabular-nums">
                  {tPricing(`tiers.${plan}.price`)}
                </bdi>
                <span className="text-sm text-ink-soft">{tPricing("perMonth")}</span>
              </p>
              <ul className="mt-4 flex flex-1 flex-col gap-2 text-sm text-ink">
                {features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2.5">
                    <span
                      aria-hidden="true"
                      className="mt-[7px] size-1.5 shrink-0 rounded-full bg-orange"
                    />
                    {feature}
                  </li>
                ))}
              </ul>
              <Button
                className="mt-5 w-full"
                variant={featured ? "orange" : "outline"}
                disabled={current || pending?.plan === plan}
                loading={busy === plan}
                onClick={() => choose(plan)}
              >
                {current ? t("current") : pending?.plan === plan ? t("requested") : t("choose")}
              </Button>
            </article>
          );
        })}
      </div>
      <p className="text-sm text-ink-soft">{t("payment")}</p>

      {!features.classes && (
        <section className="flex flex-col items-start gap-3 rounded-card border border-line bg-bg p-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg text-navy-deep">{t("schoolTitle")}</h2>
            <p className="mt-1 text-sm text-ink-soft">{t("schoolBody")}</p>
          </div>
          <Link href="/contact" className={buttonVariants({ variant: "outline", size: "sm" })}>
            {t("schoolCta")}
          </Link>
        </section>
      )}
    </>
  );
}
