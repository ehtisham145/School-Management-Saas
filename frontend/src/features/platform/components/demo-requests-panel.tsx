"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { Button, buttonVariants } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Table, TableCell, TableHead, TableHeaderCell, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { optional, useValidatedForm } from "@/lib/use-validated-form";
import { getDemoRequestCounts, listDemoRequests, updateDemoRequest } from "../api";
import { DEMO_STATUSES, type DemoRequest, type DemoStatus } from "../schemas";
import { useLoad } from "../use-load";
import {
  DemoStatusBadge,
  DetailRow,
  FilterTabs,
  formatDate,
  LoadFeedback,
  PageHeader,
  Pagination,
  SearchBox,
} from "./panel-ui";

const ALL = "all";
type StatusFilter = DemoStatus | typeof ALL;

/** Converted is set only by creating a school, so it is offered only when it already applies. */
const statusOptions = (current: DemoStatus) =>
  DEMO_STATUSES.filter((status) => status !== "converted" || current === "converted");

function DemoRequestDialog({
  demo,
  onClose,
  onSaved,
}: {
  demo: DemoRequest;
  onClose: () => void;
  onSaved: () => void;
}) {
  const t = useTranslations("Platform.demoRequests");
  const tCommon = useTranslations("Platform.common");
  const tPlans = useTranslations("Marketing.pricing");
  const locale = useLocale();
  const isConverted = demo.status === "converted";

  const form = useValidatedForm({
    initial: { status: demo.status as string, admin_notes: demo.admin_notes },
    validators: { admin_notes: optional(2000) },
    validateWhileTyping: true,
    idPrefix: "demo-",
    submit: async (values) => {
      await updateDemoRequest(demo.id, {
        status: values.status as DemoStatus,
        admin_notes: values.admin_notes,
      });
    },
    onSuccess: onSaved,
  });

  return (
    <Modal open onClose={onClose} title={t("detail.title")} closeLabel={tCommon("close")}>
      <dl className="grid gap-3 rounded-control bg-bg-tint p-4 sm:grid-cols-2">
        <DetailRow label={t("columns.contact")}>
          <bdi>{demo.name}</bdi>
        </DetailRow>
        <DetailRow label={t("detail.school")}>
          <bdi>{demo.school_name}</bdi>
        </DetailRow>
        <DetailRow label={t("detail.email")}>
          <a href={`mailto:${demo.email}`} className="text-navy underline" dir="ltr">
            {demo.email}
          </a>
        </DetailRow>
        <DetailRow label={t("detail.phone")}>
          {demo.phone ? (
            <a href={`tel:${demo.phone}`} className="text-navy underline" dir="ltr">
              {demo.phone}
            </a>
          ) : (
            tCommon("notProvided")
          )}
        </DetailRow>
        <DetailRow label={t("detail.plan")}>
          {demo.plan ? tPlans(`tiers.${demo.plan}.name`) : t("detail.noPlan")}
        </DetailRow>
        <DetailRow label={t("detail.received")}>{formatDate(demo.created_at, locale)}</DetailRow>
        <div className="sm:col-span-2">
          <DetailRow label={t("detail.message")}>
            <bdi className="whitespace-pre-wrap">{demo.message || t("detail.noMessage")}</bdi>
          </DetailRow>
        </div>
      </dl>

      <form onSubmit={form.handleSubmit} noValidate className="mt-4 flex flex-col gap-3">
        <Field
          id="demo-status"
          label={t("detail.statusLabel")}
          hint={
            isConverted && demo.converted_school_code
              ? t("detail.statusConvertedHint", { code: demo.converted_school_code })
              : isConverted
                ? undefined
                : t("detail.statusSetByCreating")
          }
        >
          <Select {...form.bind("status")} disabled={isConverted} className="h-11">
            {statusOptions(demo.status).map((status) => (
              <option key={status} value={status}>
                {t(`status.${status}`)}
              </option>
            ))}
          </Select>
        </Field>
        <Field
          id="demo-admin_notes"
          label={t("detail.notesLabel")}
          hint={t("detail.notesHint")}
          error={form.errorFor("admin_notes")}
        >
          <Textarea
            {...form.bind("admin_notes")}
            rows={3}
            placeholder={t("detail.notesPlaceholder")}
          />
        </Field>

        {form.formError && (
          <p role="alert" className="rounded-control bg-red-50 p-3 text-sm text-red-800">
            {form.formError}
          </p>
        )}

        <div className="flex flex-wrap justify-end gap-2">
          {(demo.status === "new" ||
            demo.status === "contacted" ||
            demo.status === "demo_scheduled") && (
            <Link
              href={`/platform/quotations/new?demo=${demo.id}`}
              className={buttonVariants({ variant: "outline", size: "sm" })}
            >
              {t("detail.createQuotation")}
            </Link>
          )}
          {!isConverted && (
            <Link
              href={`/platform/schools/new?demo=${demo.id}`}
              className={buttonVariants({ variant: "outline", size: "sm" })}
            >
              {t("detail.createSchool")}
            </Link>
          )}
          <Button type="submit" size="sm" loading={form.saving}>
            {form.saving ? t("detail.saving") : t("detail.save")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export function DemoRequestsPanel() {
  const t = useTranslations("Platform.demoRequests");
  const tCommon = useTranslations("Platform.common");
  const tPlans = useTranslations("Marketing.pricing");
  const locale = useLocale();

  const [query, setQuery] = useState({ page: 1, search: "", status: ALL as StatusFilter });
  const [selected, setSelected] = useState<DemoRequest | null>(null);
  const [savedNotice, setSavedNotice] = useState(false);

  const list = useLoad(
    (signal) =>
      listDemoRequests(
        {
          page: query.page,
          search: query.search,
          status: query.status === ALL ? undefined : query.status,
        },
        signal,
      ),
    JSON.stringify(query),
  );
  const counts = useLoad(getDemoRequestCounts, "counts");
  const byStatus = counts.state.name === "ready" ? counts.state.data : null;

  function handleSaved() {
    setSelected(null);
    setSavedNotice(true);
    list.reload();
    counts.reload();
  }

  const isFiltered = query.search !== "" || query.status !== ALL;

  return (
    <>
      <PageHeader title={t("title")} subtitle={t("subtitle")} />

      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <FilterTabs<StatusFilter>
          label={t("columns.status")}
          value={query.status}
          onChange={(status) => setQuery((current) => ({ ...current, status, page: 1 }))}
          options={[
            { value: ALL, label: t("all"), count: byStatus?.total },
            ...DEMO_STATUSES.map((status) => ({
              value: status,
              label: t(`status.${status}`),
              count: byStatus?.by_status[status],
            })),
          ]}
        />
        <SearchBox
          label={t("searchLabel")}
          onSearch={(search) => setQuery((current) => ({ ...current, search, page: 1 }))}
        />
      </div>

      {savedNotice && (
        <p role="status" className="rounded-control bg-emerald-50 p-3 text-sm text-emerald-800">
          {t("detail.saved")}
        </p>
      )}

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
                <TableHeaderCell>{t("columns.contact")}</TableHeaderCell>
                <TableHeaderCell>{t("columns.school")}</TableHeaderCell>
                <TableHeaderCell>{t("columns.plan")}</TableHeaderCell>
                <TableHeaderCell>{t("columns.status")}</TableHeaderCell>
                <TableHeaderCell>{t("columns.received")}</TableHeaderCell>
                <TableHeaderCell>{t("columns.actions")}</TableHeaderCell>
              </TableRow>
            </TableHead>
            <tbody>
              {list.state.data.results.map((demo) => (
                <TableRow key={demo.id}>
                  <TableCell>
                    <span className="block font-semibold text-ink">
                      <bdi>{demo.name}</bdi>
                    </span>
                    <span className="block text-xs text-ink-soft">
                      <bdi>{demo.email}</bdi>
                    </span>
                    {demo.phone && (
                      <span className="block text-xs text-ink-soft">
                        <bdi>{demo.phone}</bdi>
                      </span>
                    )}
                  </TableCell>
                  <TableCell>
                    <bdi>{demo.school_name}</bdi>
                  </TableCell>
                  <TableCell>{demo.plan ? tPlans(`tiers.${demo.plan}.name`) : "-"}</TableCell>
                  <TableCell>
                    <DemoStatusBadge status={demo.status} />
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    {formatDate(demo.created_at, locale)}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setSavedNotice(false);
                        setSelected(demo);
                      }}
                    >
                      {tCommon("view")}
                    </Button>
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

      {selected && (
        <DemoRequestDialog
          key={selected.id}
          demo={selected}
          onClose={() => setSelected(null)}
          onSaved={handleSaved}
        />
      )}
    </>
  );
}
