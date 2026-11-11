"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Table, TableCell, TableHead, TableHeaderCell, TableRow } from "@/components/ui/table";
import { getUsageTotals, listUsage } from "../api";
import { SCHOOL_STATUS_FILTERS, type SchoolStatusFilter } from "../schemas";
import { useLoad } from "../use-load";
import {
  DayWithHijri,
  FilterTabs,
  LoadFeedback,
  localName,
  PageHeader,
  Pagination,
  SchoolStatusBadge,
  SearchBox,
  StatCard,
} from "./panel-ui";

const ALL = "all";
type StatusFilter = SchoolStatusFilter | typeof ALL;

export function UsagePanel() {
  const t = useTranslations("Platform.usage");
  const tSchools = useTranslations("Platform.schools");
  const locale = useLocale();
  const number = (value: number) => value.toLocaleString(locale);

  const [query, setQuery] = useState({ page: 1, search: "", status: ALL as StatusFilter });
  const list = useLoad(
    (signal) =>
      listUsage(
        {
          page: query.page,
          search: query.search,
          status: query.status === ALL ? undefined : query.status,
        },
        signal,
      ),
    JSON.stringify(query),
  );
  const totals = useLoad(getUsageTotals, "totals");
  const isFiltered = query.search !== "" || query.status !== ALL;

  return (
    <>
      <PageHeader title={t("title")} subtitle={t("subtitle")} />

      {totals.state.name === "ready" && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          <StatCard label={t("totals.schools")} value={number(totals.state.data.active_schools)} />
          <StatCard
            label={t("totals.subscriptions")}
            value={number(totals.state.data.active_subscriptions)}
          />
          <StatCard label={t("totals.students")} value={number(totals.state.data.students)} />
          <StatCard label={t("totals.teachers")} value={number(totals.state.data.teachers)} />
          <StatCard label={t("totals.parents")} value={number(totals.state.data.parents)} />
          <StatCard
            label={t("totals.activeUsers")}
            value={number(totals.state.data.active_users)}
            hint={t("activeHint", { days: totals.state.data.active_user_days })}
          />
        </div>
      )}

      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <FilterTabs<StatusFilter>
          label={t("columns.status")}
          value={query.status}
          onChange={(status) => setQuery((current) => ({ ...current, status, page: 1 }))}
          options={[
            { value: ALL, label: tSchools("all") },
            ...SCHOOL_STATUS_FILTERS.map((status) => ({ value: status, label: tSchools(status) })),
          ]}
        />
        <SearchBox
          label={t("searchLabel")}
          onSearch={(search) => setQuery((current) => ({ ...current, search, page: 1 }))}
        />
      </div>

      <LoadFeedback state={list.state} onRetry={list.reload} />

      {list.state.name === "ready" && list.state.data.count === 0 && (
        <EmptyState title={isFiltered ? t("noResults") : t("empty")} />
      )}

      {list.state.name === "ready" && list.state.data.count > 0 && (
        <>
          <Table className="bg-bg">
            <TableHead>
              <TableRow>
                <TableHeaderCell>{t("columns.school")}</TableHeaderCell>
                <TableHeaderCell>{t("columns.plan")}</TableHeaderCell>
                <TableHeaderCell>{t("columns.students")}</TableHeaderCell>
                <TableHeaderCell>{t("columns.teachers")}</TableHeaderCell>
                <TableHeaderCell>{t("columns.parents")}</TableHeaderCell>
                <TableHeaderCell>{t("columns.staff")}</TableHeaderCell>
                <TableHeaderCell>{t("columns.activeUsers")}</TableHeaderCell>
                <TableHeaderCell>{t("columns.status")}</TableHeaderCell>
              </TableRow>
            </TableHead>
            <tbody>
              {list.state.data.results.map((school) => (
                <TableRow key={school.id}>
                  <TableCell>
                    <span className="block font-semibold text-ink">
                      <bdi>{localName(school, locale)}</bdi>
                    </span>
                    <span className="block text-xs text-ink-soft" dir="ltr">
                      {school.code}
                    </span>
                  </TableCell>
                  <TableCell>
                    {school.plan ? (
                      <>
                        <span className="block">{localName(school.plan, locale)}</span>
                        {school.subscription_ends_on && (
                          <span className="block text-xs text-ink-soft">
                            {t("until")}{" "}
                            <DayWithHijri value={school.subscription_ends_on} locale={locale} />
                          </span>
                        )}
                      </>
                    ) : (
                      <Badge tone="warning">{t("noPlan")}</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <span className="whitespace-nowrap">
                      {number(school.students)}
                      {school.plan?.max_students != null && (
                        <span className="text-ink-soft"> / {number(school.plan.max_students)}</span>
                      )}
                    </span>
                    {school.over_student_limit && (
                      <Badge tone="danger" className="mt-1">
                        {t("overLimit")}
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell>{number(school.teachers)}</TableCell>
                  <TableCell>{number(school.parents)}</TableCell>
                  <TableCell>{number(school.staff)}</TableCell>
                  <TableCell>{number(school.active_users)}</TableCell>
                  <TableCell>
                    <SchoolStatusBadge isActive={school.is_active} />
                  </TableCell>
                </TableRow>
              ))}
            </tbody>
          </Table>
          <Pagination
            page={query.page}
            count={list.state.data.count}
            onPage={(page) => setQuery((current) => ({ ...current, page }))}
          />
        </>
      )}
    </>
  );
}
