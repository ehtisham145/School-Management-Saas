"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { Search } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "cn";
import { Link } from "@/i18n/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Spinner } from "@/components/ui/spinner";
import { ApiError } from "@/lib/api";
import {
  LIST_PAGE_SIZE,
  type DemoStatus,
  type QuotationStatus,
  type SubscriptionStatus,
} from "../schemas";
import type { LoadState } from "../use-load";

export function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-2xl text-navy-deep">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-ink-soft">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

/** Shows the loading, no-access and failed states. Renders nothing once data is ready. */
export function LoadFeedback<T>({ state, onRetry }: { state: LoadState<T>; onRetry: () => void }) {
  const t = useTranslations("Platform.common");

  if (state.name === "loading") {
    return (
      <p role="status" className="flex items-center gap-2 py-10 text-sm text-ink-soft">
        <Spinner />
        {t("loading")}
      </p>
    );
  }
  if (state.name === "denied") {
    return (
      <div className="flex flex-col items-center gap-3 py-12 text-center">
        <p role="alert" className="text-sm text-ink-soft">
          {t("accessDenied")}
        </p>
        <Link href="/login" className="text-sm font-semibold text-navy underline">
          {t("signIn")}
        </Link>
      </div>
    );
  }
  if (state.name === "failed") {
    return (
      <div className="flex flex-col items-start gap-3 py-6">
        <p role="alert" className="text-sm text-red-700">
          {t("loadFailed")}
        </p>
        <Button variant="outline" size="sm" onClick={onRetry}>
          {t("retry")}
        </Button>
      </div>
    );
  }
  return null;
}

const SEARCH_DELAY_MS = 300;

export function SearchBox({
  label,
  onSearch,
}: {
  label: string;
  onSearch: (term: string) => void;
}) {
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => () => clearTimeout(timer.current), []);

  return (
    <div className="relative w-full sm:max-w-xs">
      <Search
        aria-hidden="true"
        className="pointer-events-none absolute start-3 top-1/2 size-4 -translate-y-1/2 text-ink-soft"
      />
      <Input
        type="search"
        aria-label={label}
        placeholder={label}
        maxLength={100}
        className="h-[42px] ps-9 text-sm"
        onChange={(event) => {
          const term = event.target.value.trim();
          clearTimeout(timer.current);
          timer.current = setTimeout(() => onSearch(term), SEARCH_DELAY_MS);
        }}
      />
    </div>
  );
}

type FilterOption<V> = { value: V; label: string; count?: number };

export function FilterTabs<V extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: FilterOption<V>[];
  value: V;
  onChange: (value: V) => void;
}) {
  return (
    <div role="group" aria-label={label} className="flex flex-wrap gap-1.5">
      {options.map((option) => {
        const selected = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={selected}
            onClick={() => onChange(option.value)}
            className={cn(
              "inline-flex min-h-9 cursor-pointer items-center gap-1.5 rounded-control border px-3 text-sm font-semibold transition-colors",
              selected
                ? "border-navy bg-navy text-on-dark"
                : "border-line bg-bg text-ink-soft hover:border-navy-line hover:text-navy",
            )}
          >
            {option.label}
            {option.count !== undefined && (
              <span className={cn("text-xs tabular-nums", selected ? "opacity-80" : "opacity-70")}>
                {option.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

export function Pagination({
  page,
  count,
  onPage,
}: {
  page: number;
  count: number;
  onPage: (page: number) => void;
}) {
  const t = useTranslations("Platform.common");
  const pages = Math.ceil(count / LIST_PAGE_SIZE);
  if (pages <= 1) return null;

  return (
    <div className="flex items-center justify-between gap-3">
      <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        {t("previous")}
      </Button>
      <span className="text-sm text-ink-soft tabular-nums">{t("page", { page, pages })}</span>
      <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => onPage(page + 1)}>
        {t("next")}
      </Button>
    </div>
  );
}

export function SchoolStatusBadge({ isActive }: { isActive: boolean }) {
  const t = useTranslations("Platform.schools");
  return (
    <Badge tone={isActive ? "success" : "neutral"}>{isActive ? t("active") : t("inactive")}</Badge>
  );
}

const DEMO_STATUS_TONES = {
  new: "info",
  contacted: "warning",
  demo_scheduled: "navy",
  converted: "success",
  rejected: "danger",
} as const;

export function DemoStatusBadge({ status }: { status: DemoStatus }) {
  const t = useTranslations("Platform.demoRequests.status");
  return <Badge tone={DEMO_STATUS_TONES[status]}>{t(status)}</Badge>;
}

/** One label and value, for the detail dialogs and the profile page. */
export function DetailRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs font-semibold text-ink-soft">{label}</dt>
      <dd className="text-sm break-words text-ink">{children}</dd>
    </div>
  );
}

/** Dates are stored in UTC and shown in Saudi time. */
export function formatDate(value: string, locale: string) {
  return new Date(value).toLocaleDateString(locale, { timeZone: "Asia/Riyadh" });
}

/** A timestamp with its time, in Saudi time. */
export function formatDateTime(value: string, locale: string) {
  return new Date(value).toLocaleString(locale, {
    timeZone: "Asia/Riyadh",
    dateStyle: "medium",
    timeStyle: "short",
  });
}

/** A calendar day from the API ("2026-11-01"), which has no time and no time zone. */
export function formatDay(value: string, locale: string) {
  return new Date(`${value}T00:00:00Z`).toLocaleDateString(locale, { timeZone: "UTC" });
}

/** The same day in the Umm al-Qura calendar, for display only (ADR-0005). */
export function formatHijriDay(value: string, locale: string) {
  return new Date(`${value}T00:00:00Z`).toLocaleDateString(`${locale}-u-ca-islamic-umalqura`, {
    timeZone: "UTC",
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/** Gregorian first, Hijri beside it in smaller text. */
export function DayWithHijri({ value, locale }: { value: string; locale: string }) {
  return (
    <span className="whitespace-nowrap">
      {formatDay(value, locale)}
      <span className="block text-xs text-ink-soft">{formatHijriDay(value, locale)}</span>
    </span>
  );
}

/** "1500.00" -> "1,500.00". The API sends money as text; this is display only. */
export function formatMoney(value: string, locale: string) {
  return Number(value).toLocaleString(locale, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function Money({ value, locale }: { value: string; locale: string }) {
  const t = useTranslations("Platform.common");
  return (
    <span className="whitespace-nowrap tabular-nums">
      <bdi>{formatMoney(value, locale)}</bdi> {t("currency")}
    </span>
  );
}

export function localName(item: { name_en: string; name_ar: string }, locale: string) {
  return locale === "ar" ? item.name_ar : item.name_en;
}

/** A notice that a change was saved, or an error, above a list. */
export function Notice({ tone, children }: { tone: "success" | "error"; children: ReactNode }) {
  return (
    <p
      role={tone === "error" ? "alert" : "status"}
      className={cn(
        "rounded-control p-3 text-sm",
        tone === "error" ? "bg-red-50 text-red-800" : "bg-emerald-50 text-emerald-800",
      )}
    >
      {children}
    </p>
  );
}

/** Asks before an action that can't be undone, and shows a failure in place. */
export function ConfirmDialog({
  title,
  description,
  confirmLabel,
  destructive = false,
  onConfirm,
  onClose,
}: {
  title: string;
  description: string;
  confirmLabel: string;
  destructive?: boolean;
  onConfirm: () => Promise<void>;
  onClose: () => void;
}) {
  const t = useTranslations("Platform.common");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function confirm() {
    setSaving(true);
    setError(null);
    try {
      await onConfirm();
    } catch (err) {
      setError(errorMessage(err) ?? t("actionFailed"));
      setSaving(false);
    }
  }

  return (
    <Modal open onClose={onClose} title={title} description={description} closeLabel={t("close")}>
      {error && (
        <p role="alert" className="mb-3 rounded-control bg-red-50 p-3 text-sm text-red-800">
          {error}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <Button variant="ghost" size="sm" onClick={onClose}>
          {t("cancel")}
        </Button>
        <Button
          variant={destructive ? "destructive" : "default"}
          size="sm"
          loading={saving}
          onClick={confirm}
        >
          {confirmLabel}
        </Button>
      </div>
    </Modal>
  );
}

/** The first message the API gave for a refused change, such as "already expired". */
export function errorMessage(err: unknown): string | null {
  if (!(err instanceof ApiError) || err.status !== 400 || !err.fields) return null;
  for (const value of Object.values(err.fields)) {
    if (Array.isArray(value) && typeof value[0] === "string") return value[0];
    if (typeof value === "string") return value;
  }
  return null;
}

const SUBSCRIPTION_TONES = { active: "success", expired: "neutral" } as const;

export function SubscriptionStatusBadge({ status }: { status: SubscriptionStatus }) {
  const t = useTranslations("Platform.subscriptions.status");
  return <Badge tone={SUBSCRIPTION_TONES[status]}>{t(status)}</Badge>;
}

const QUOTATION_TONES = {
  draft: "neutral",
  sent: "info",
  accepted: "success",
  rejected: "danger",
} as const;

export function QuotationStatusBadge({
  status,
  isExpired = false,
}: {
  status: QuotationStatus;
  isExpired?: boolean;
}) {
  const t = useTranslations("Platform.quotations.status");
  if (isExpired) return <Badge tone="warning">{t("expired")}</Badge>;
  return <Badge tone={QUOTATION_TONES[status]}>{t(status)}</Badge>;
}

/** A number on a dashboard-style card. */
export function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
}) {
  return (
    <div className="rounded-card border border-line bg-bg p-4">
      <p className="text-sm text-ink-soft">{label}</p>
      <p className="mt-1 text-2xl font-bold text-navy-deep tabular-nums">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-ink-soft">{hint}</p>}
    </div>
  );
}
