"use client";

import type { ComponentType, ReactNode } from "react";
import { CalendarCheck, CircleCheck, CircleSlash, School } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getDashboard } from "../api";
import { DEMO_STATUSES, type DemoRequestCounts } from "../schemas";
import { useLoad } from "../use-load";
import {
  DemoStatusBadge,
  formatDate,
  LoadFeedback,
  localName,
  PageHeader,
  SchoolStatusBadge,
} from "./panel-ui";

function StatTile({
  label,
  value,
  href,
  icon: Icon,
}: {
  label: string;
  value: number;
  href: string;
  icon: ComponentType<{ className?: string; "aria-hidden"?: "true" }>;
}) {
  return (
    <Link
      href={href}
      className="flex flex-col gap-3 rounded-card border border-line bg-bg p-4 transition-[border-color,box-shadow] hover:border-navy-line hover:shadow-soft sm:p-5"
    >
      <span className="flex size-9 shrink-0 items-center justify-center rounded-tile bg-navy-soft text-navy sm:size-11">
        <Icon aria-hidden="true" className="size-[18px] sm:size-5" />
      </span>
      <span className="flex flex-col gap-0.5">
        <span className="text-xs font-medium text-ink-soft sm:text-sm">{label}</span>
        <span className="text-2xl leading-tight font-bold text-navy-deep tabular-nums sm:text-3xl">
          {value}
        </span>
      </span>
    </Link>
  );
}

function Pipeline({ counts }: { counts: DemoRequestCounts }) {
  const t = useTranslations("Platform.dashboard");
  const tStatus = useTranslations("Platform.demoRequests.status");
  const largest = Math.max(1, ...Object.values(counts.by_status));

  if (counts.total === 0) {
    return <p className="py-6 text-center text-sm text-ink-soft">{t("pipelineEmpty")}</p>;
  }

  return (
    <ul className="flex flex-col gap-3.5">
      {DEMO_STATUSES.map((status) => {
        const count = counts.by_status[status];
        const label = tStatus(status);
        return (
          <li key={status} title={`${label}: ${count}`} className="flex flex-col gap-1.5">
            <span className="flex items-baseline justify-between gap-3 text-sm">
              <span className="text-ink-soft">{label}</span>
              <span className="font-semibold text-ink tabular-nums">{count}</span>
            </span>
            <span className="block h-2 rounded-full bg-bg-tint">
              <span
                className="block h-full rounded-full bg-navy"
                style={{ inlineSize: count === 0 ? 0 : `${(count / largest) * 100}%` }}
              />
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function RecentCard({
  title,
  href,
  children,
}: {
  title: string;
  href: string;
  children: ReactNode;
}) {
  const t = useTranslations("Platform.common");
  return (
    <Card className="gap-4">
      <CardHeader className="flex-row items-center justify-between gap-3">
        <CardTitle>{title}</CardTitle>
        <Link href={href} className="text-sm font-semibold text-navy hover:underline">
          {t("viewAll")}
        </Link>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function RecentRow({
  title,
  detail,
  date,
  badge,
}: {
  title: string;
  detail: string;
  date: string;
  badge: ReactNode;
}) {
  return (
    <li className="flex items-center justify-between gap-3 border-t border-line py-3 first:border-t-0 first:pt-0 last:pb-0">
      <span className="min-w-0">
        <span className="block truncate text-sm font-semibold text-ink">
          <bdi>{title}</bdi>
        </span>
        <span className="block truncate text-xs text-ink-soft">
          <bdi>{detail}</bdi> · {date}
        </span>
      </span>
      {badge}
    </li>
  );
}

export function DashboardPanel() {
  const t = useTranslations("Platform.dashboard");
  const tDemo = useTranslations("Platform.demoRequests");
  const locale = useLocale();
  const { state, reload } = useLoad(getDashboard, "dashboard");

  return (
    <>
      <PageHeader title={t("title")} subtitle={t("subtitle")} />
      <LoadFeedback state={state} onRetry={reload} />

      {state.name === "ready" && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
            <StatTile
              label={t("totalSchools")}
              value={state.data.schools.total}
              href="/platform/schools"
              icon={School}
            />
            <StatTile
              label={t("activeSchools")}
              value={state.data.schools.active}
              href="/platform/schools"
              icon={CircleCheck}
            />
            <StatTile
              label={t("inactiveSchools")}
              value={state.data.schools.inactive}
              href="/platform/schools"
              icon={CircleSlash}
            />
            <StatTile
              label={t("newDemoRequests")}
              value={state.data.demo_requests.by_status.new}
              href="/platform/demo-requests"
              icon={CalendarCheck}
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <Card className="gap-4">
              <CardHeader>
                <CardTitle>{t("pipeline")}</CardTitle>
                <p className="text-xs text-ink-soft">
                  {t("pipelineTotal", { count: state.data.demo_requests.total })}
                </p>
              </CardHeader>
              <CardContent>
                <Pipeline counts={state.data.demo_requests} />
              </CardContent>
            </Card>

            <RecentCard title={t("recentDemoRequests")} href="/platform/demo-requests">
              {state.data.recent_demo_requests.length === 0 ? (
                <p className="py-6 text-center text-sm text-ink-soft">{tDemo("empty")}</p>
              ) : (
                <ul>
                  {state.data.recent_demo_requests.map((demo) => (
                    <RecentRow
                      key={demo.id}
                      title={demo.school_name}
                      detail={demo.name}
                      date={formatDate(demo.created_at, locale)}
                      badge={<DemoStatusBadge status={demo.status} />}
                    />
                  ))}
                </ul>
              )}
            </RecentCard>

            <RecentCard title={t("recentSchools")} href="/platform/schools">
              {state.data.recent_schools.length === 0 ? (
                <p className="py-6 text-center text-sm text-ink-soft">{t("noRecentSchools")}</p>
              ) : (
                <ul>
                  {state.data.recent_schools.map((school) => (
                    <RecentRow
                      key={school.id}
                      title={localName(school, locale)}
                      detail={school.code}
                      date={formatDate(school.created_at, locale)}
                      badge={<SchoolStatusBadge isActive={school.is_active} />}
                    />
                  ))}
                </ul>
              )}
            </RecentCard>
          </div>
        </>
      )}
    </>
  );
}
