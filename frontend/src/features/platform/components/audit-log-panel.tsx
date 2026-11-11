"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { EmptyState } from "@/components/ui/empty-state";
import { Select } from "@/components/ui/select";
import { Table, TableCell, TableHead, TableHeaderCell, TableRow } from "@/components/ui/table";
import { listAuditEvents } from "../api";
import { AUDIT_ACTIONS, type AuditAction, type AuditEvent } from "../schemas";
import { useLoad } from "../use-load";
import {
  formatDateTime,
  LoadFeedback,
  localName,
  PageHeader,
  Pagination,
  SearchBox,
} from "./panel-ui";

const ALL = "all";

/** A short line for the parts of an entry worth reading, such as a status change. */
function EventDetails({ event }: { event: AuditEvent }) {
  const t = useTranslations("Platform.audit.details");
  const { details } = event;
  const lines: string[] = [];

  const status = details.status;
  if (Array.isArray(status) && status.length === 2 && status[0] !== status[1]) {
    lines.push(t("status", { from: String(status[0]), to: String(status[1]) }));
  }
  if (typeof details.to === "string") lines.push(t("sentTo", { email: details.to }));
  if (typeof details.total === "string") lines.push(t("total", { total: details.total }));
  if (typeof details.price === "string") lines.push(t("price", { price: details.price }));
  if (details.reason === "manual" || details.reason === "ended") {
    lines.push(t(`reason.${details.reason}`));
  }
  const changes = details.changes;
  if (changes && typeof changes === "object") {
    lines.push(t("changed", { fields: Object.keys(changes).join(", ") }));
  }

  if (lines.length === 0) return <span className="text-ink-soft">-</span>;
  return (
    <ul className="flex flex-col gap-0.5 text-xs text-ink-soft">
      {lines.map((line) => (
        <li key={line}>
          <bdi>{line}</bdi>
        </li>
      ))}
    </ul>
  );
}

export function AuditLogPanel() {
  const t = useTranslations("Platform.audit");
  const locale = useLocale();
  const [query, setQuery] = useState({ page: 1, search: "", action: ALL as AuditAction | "all" });

  const list = useLoad(
    (signal) =>
      listAuditEvents(
        {
          page: query.page,
          search: query.search,
          action: query.action === ALL ? undefined : query.action,
        },
        signal,
      ),
    JSON.stringify(query),
  );
  const isFiltered = query.search !== "" || query.action !== ALL;

  return (
    <>
      <PageHeader title={t("title")} subtitle={t("subtitle")} />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="w-full sm:max-w-xs">
          <label htmlFor="audit-action" className="sr-only">
            {t("actionFilter")}
          </label>
          <Select
            id="audit-action"
            value={query.action}
            onChange={(event) =>
              setQuery((current) => ({
                ...current,
                action: event.target.value as AuditAction | "all",
                page: 1,
              }))
            }
            className="h-[42px] text-sm"
          >
            <option value={ALL}>{t("allActions")}</option>
            {AUDIT_ACTIONS.map((action) => (
              <option key={action} value={action}>
                {t(`actions.${action}`)}
              </option>
            ))}
          </Select>
        </div>
        <SearchBox
          label={t("searchLabel")}
          onSearch={(search) => setQuery((current) => ({ ...current, search, page: 1 }))}
        />
      </div>

      <LoadFeedback state={list.state} onRetry={list.reload} />

      {list.state.name === "ready" && list.state.data.count === 0 && (
        <EmptyState
          title={isFiltered ? t("noResults") : t("empty")}
          description={isFiltered ? undefined : t("emptyDescription")}
        />
      )}

      {list.state.name === "ready" && list.state.data.count > 0 && (
        <>
          <Table className="bg-bg">
            <TableHead>
              <TableRow>
                <TableHeaderCell>{t("columns.when")}</TableHeaderCell>
                <TableHeaderCell>{t("columns.who")}</TableHeaderCell>
                <TableHeaderCell>{t("columns.action")}</TableHeaderCell>
                <TableHeaderCell>{t("columns.target")}</TableHeaderCell>
                <TableHeaderCell>{t("columns.details")}</TableHeaderCell>
                <TableHeaderCell>{t("columns.ip")}</TableHeaderCell>
              </TableRow>
            </TableHead>
            <tbody>
              {list.state.data.results.map((event) => (
                <TableRow key={event.id}>
                  <TableCell className="whitespace-nowrap">
                    {formatDateTime(event.created_at, locale)}
                  </TableCell>
                  <TableCell>
                    <bdi>{event.actor_label || t("system")}</bdi>
                  </TableCell>
                  <TableCell className="font-semibold text-ink">
                    {t(`actions.${event.action}`)}
                  </TableCell>
                  <TableCell>
                    <bdi>{event.target_label}</bdi>
                    {event.school && (
                      <span className="block text-xs text-ink-soft">
                        <bdi>{localName(event.school, locale)}</bdi>
                      </span>
                    )}
                  </TableCell>
                  <TableCell>
                    <EventDetails event={event} />
                  </TableCell>
                  <TableCell dir="ltr" className="text-xs text-ink-soft">
                    {event.ip_address ?? "-"}
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
