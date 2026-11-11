"use client";

import { useState } from "react";
import { Download, Plus } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import { Button, buttonVariants } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Modal } from "@/components/ui/modal";
import { Table, TableCell, TableHead, TableHeaderCell, TableRow } from "@/components/ui/table";
import { ApiError, saveFile } from "@/lib/api";
import { downloadQuotationPdf, getQuotationCounts, listQuotations, quotationAction } from "../api";
import { QUOTATION_STATUSES, type Quotation, type QuotationStatus } from "../schemas";
import { useLoad } from "../use-load";
import {
  ConfirmDialog,
  DayWithHijri,
  DetailRow,
  FilterTabs,
  formatDateTime,
  LoadFeedback,
  localName,
  Money,
  Notice,
  PageHeader,
  Pagination,
  QuotationStatusBadge,
  SearchBox,
} from "./panel-ui";

const ALL = "all";
type StatusFilter = QuotationStatus | typeof ALL;
type Action = "send" | "accept" | "reject";

function QuotationDialog({
  quotation,
  onClose,
  onChanged,
}: {
  quotation: Quotation;
  onClose: () => void;
  onChanged: (action: Action) => void;
}) {
  const t = useTranslations("Platform.quotations");
  const tCommon = useTranslations("Platform.common");
  const locale = useLocale();
  const [confirming, setConfirming] = useState<Action | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  async function download() {
    setDownloading(true);
    setDownloadError(null);
    try {
      const { blob, filename } = await downloadQuotationPdf(quotation.id);
      saveFile(blob, filename ?? `${quotation.number}.pdf`);
    } catch (err) {
      const unavailable = err instanceof ApiError && err.code === "pdf_unavailable";
      setDownloadError(unavailable ? t("pdfUnavailable") : tCommon("actionFailed"));
    } finally {
      setDownloading(false);
    }
  }

  const canSend = quotation.status === "draft" || quotation.status === "sent";
  const canAnswer = quotation.status === "sent";

  if (confirming) {
    return (
      <ConfirmDialog
        title={t(`confirm.${confirming}Title`, { number: quotation.number })}
        description={t(`confirm.${confirming}Body`, { email: quotation.recipient_email })}
        confirmLabel={t(`actions.${confirming}`)}
        destructive={confirming === "reject"}
        onClose={() => setConfirming(null)}
        onConfirm={async () => {
          await quotationAction(quotation.id, confirming);
          onChanged(confirming);
        }}
      />
    );
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={t("detail.title", { number: quotation.number })}
      closeLabel={tCommon("close")}
    >
      <div className="mb-3">
        <QuotationStatusBadge status={quotation.status} isExpired={quotation.is_expired} />
      </div>
      <dl className="grid gap-3 rounded-control bg-bg-tint p-4 sm:grid-cols-2">
        <DetailRow label={t("detail.organization")}>
          <bdi>{quotation.recipient_organization}</bdi>
        </DetailRow>
        <DetailRow label={t("detail.recipient")}>
          <bdi>{quotation.recipient_name}</bdi>
          <span className="block text-ink-soft" dir="ltr">
            {quotation.recipient_email}
          </span>
        </DetailRow>
        <DetailRow label={t("detail.plan")}>
          {quotation.plan ? localName(quotation.plan, locale) : "-"}
          {quotation.billing_cycle && ` · ${tCommon(`cycles.${quotation.billing_cycle}`)}`}
        </DetailRow>
        <DetailRow label={t("detail.validUntil")}>
          <DayWithHijri value={quotation.valid_until} locale={locale} />
        </DetailRow>
        <DetailRow label={t("detail.language")}>{t(`languages.${quotation.language}`)}</DetailRow>
        <DetailRow label={t("detail.sentAt")}>
          {quotation.sent_at ? formatDateTime(quotation.sent_at, locale) : "-"}
        </DetailRow>
      </dl>

      <Table className="mt-4">
        <TableHead>
          <TableRow>
            <TableHeaderCell>{t("detail.description")}</TableHeaderCell>
            <TableHeaderCell>{t("detail.quantity")}</TableHeaderCell>
            <TableHeaderCell className="text-end">{t("detail.amount")}</TableHeaderCell>
          </TableRow>
        </TableHead>
        <tbody>
          {quotation.items.map((item, index) => (
            <TableRow key={index}>
              <TableCell>
                <bdi>{item.description}</bdi>
              </TableCell>
              <TableCell>{item.quantity.toLocaleString(locale)}</TableCell>
              <TableCell className="text-end">
                <Money value={item.amount} locale={locale} />
              </TableCell>
            </TableRow>
          ))}
        </tbody>
      </Table>

      <dl className="ms-auto mt-3 grid max-w-xs grid-cols-2 gap-x-4 gap-y-1 text-sm">
        <dt className="text-ink-soft">{t("detail.subtotal")}</dt>
        <dd className="text-end">
          <Money value={quotation.subtotal} locale={locale} />
        </dd>
        <dt className="text-ink-soft">{t("detail.vat", { rate: Number(quotation.vat_rate) })}</dt>
        <dd className="text-end">
          <Money value={quotation.vat_amount} locale={locale} />
        </dd>
        <dt className="border-t border-line pt-1 font-bold text-navy-deep">{t("detail.total")}</dt>
        <dd className="border-t border-line pt-1 text-end font-bold text-navy-deep">
          <Money value={quotation.total} locale={locale} />
        </dd>
      </dl>

      {quotation.notes && (
        <p className="mt-3 text-sm whitespace-pre-wrap text-ink-soft">
          <bdi>{quotation.notes}</bdi>
        </p>
      )}

      {downloadError && (
        <p role="alert" className="mt-3 rounded-control bg-red-50 p-3 text-sm text-red-800">
          {downloadError}
        </p>
      )}

      <div className="mt-4 flex flex-wrap justify-end gap-2">
        <Button variant="outline" size="sm" loading={downloading} onClick={download}>
          <Download aria-hidden="true" />
          {t("actions.download")}
        </Button>
        {quotation.status === "draft" && (
          <Link
            href={`/platform/quotations/new?edit=${quotation.id}`}
            className={buttonVariants({ variant: "outline", size: "sm" })}
          >
            {tCommon("edit")}
          </Link>
        )}
        {canAnswer && (
          <>
            <Button variant="outline" size="sm" onClick={() => setConfirming("reject")}>
              {t("actions.reject")}
            </Button>
            <Button variant="outline" size="sm" onClick={() => setConfirming("accept")}>
              {t("actions.accept")}
            </Button>
          </>
        )}
        {canSend && (
          <Button size="sm" onClick={() => setConfirming("send")}>
            {quotation.status === "sent" ? t("actions.resend") : t("actions.send")}
          </Button>
        )}
      </div>
    </Modal>
  );
}

function SavedNotice() {
  const t = useTranslations("Platform.quotations");
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const number = searchParams.get("saved");
  if (!number) return null;

  return (
    <div
      role="status"
      className="flex items-center justify-between gap-3 rounded-control bg-emerald-50 p-3 text-sm text-emerald-800"
    >
      <span>{t("notices.saved", { number })}</span>
      <button
        type="button"
        onClick={() => router.replace(pathname)}
        className="cursor-pointer font-semibold underline"
      >
        {t("notices.dismiss")}
      </button>
    </div>
  );
}

export function QuotationsPanel() {
  const t = useTranslations("Platform.quotations");
  const tCommon = useTranslations("Platform.common");
  const locale = useLocale();

  const [query, setQuery] = useState({ page: 1, search: "", status: ALL as StatusFilter });
  const [selected, setSelected] = useState<Quotation | null>(null);
  const [notice, setNotice] = useState<Action | null>(null);

  const list = useLoad(
    (signal) =>
      listQuotations(
        {
          page: query.page,
          search: query.search,
          status: query.status === ALL ? undefined : query.status,
        },
        signal,
      ),
    JSON.stringify(query),
  );
  const counts = useLoad(getQuotationCounts, "counts");
  const byStatus = counts.state.name === "ready" ? counts.state.data : null;
  const isFiltered = query.search !== "" || query.status !== ALL;

  function handleChanged(action: Action) {
    setSelected(null);
    setNotice(action);
    list.reload();
    counts.reload();
  }

  return (
    <>
      <PageHeader
        title={t("title")}
        subtitle={t("subtitle")}
        action={
          <Link href="/platform/quotations/new" className={buttonVariants({ size: "sm" })}>
            <Plus aria-hidden="true" />
            {t("new")}
          </Link>
        }
      />

      <SavedNotice />

      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <FilterTabs<StatusFilter>
          label={t("columns.status")}
          value={query.status}
          onChange={(status) => setQuery((current) => ({ ...current, status, page: 1 }))}
          options={[
            { value: ALL, label: t("all"), count: byStatus?.total },
            ...QUOTATION_STATUSES.map((status) => ({
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

      {notice && <Notice tone="success">{t(`notices.${notice}`)}</Notice>}

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
                <TableHeaderCell>{t("columns.number")}</TableHeaderCell>
                <TableHeaderCell>{t("columns.recipient")}</TableHeaderCell>
                <TableHeaderCell>{t("columns.total")}</TableHeaderCell>
                <TableHeaderCell>{t("columns.validUntil")}</TableHeaderCell>
                <TableHeaderCell>{t("columns.status")}</TableHeaderCell>
                <TableHeaderCell>{tCommon("actions")}</TableHeaderCell>
              </TableRow>
            </TableHead>
            <tbody>
              {list.state.data.results.map((quotation) => (
                <TableRow key={quotation.id}>
                  <TableCell className="font-semibold whitespace-nowrap" dir="ltr">
                    {quotation.number}
                  </TableCell>
                  <TableCell>
                    <span className="block text-ink">
                      <bdi>{quotation.recipient_organization}</bdi>
                    </span>
                    <span className="block text-xs text-ink-soft">
                      {quotation.school ? t("forSchool") : t("forProspect")}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Money value={quotation.total} locale={locale} />
                  </TableCell>
                  <TableCell>
                    <DayWithHijri value={quotation.valid_until} locale={locale} />
                  </TableCell>
                  <TableCell>
                    <QuotationStatusBadge
                      status={quotation.status}
                      isExpired={quotation.is_expired}
                    />
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setNotice(null);
                        setSelected(quotation);
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
        <QuotationDialog
          key={selected.id}
          quotation={selected}
          onClose={() => setSelected(null)}
          onChanged={handleChanged}
        />
      )}
    </>
  );
}
