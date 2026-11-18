"use client";

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { Button, buttonVariants } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { ApiError } from "@/lib/api";
import type { Workspace } from "../schemas";

type WorkspaceContextValue = { workspace: Workspace; reload: () => void };
const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({
  value,
  children,
}: {
  value: WorkspaceContextValue;
  children: ReactNode;
}) {
  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("useWorkspace must be used inside the teacher app");
  return value;
}

const KNOWN_ERRORS = [
  "plan_limit_reached",
  "pro_required",
  "workspace_read_only",
  "ai_quota_reached",
  "service_unavailable",
] as const;

/** The message for a plan or service error. Null for field errors, which show on the field. */
export function useTeacherError() {
  const t = useTranslations("Teacher.errors");
  return useCallback(
    (error: unknown) => {
      if (!(error instanceof ApiError)) return t("generic");
      const known = KNOWN_ERRORS.find((code) => code === error.code);
      if (known) return t(known);
      if (error.status === 429) return t("rateLimited");
      return error.status === 400 ? null : t("generic");
    },
    [t],
  );
}

export function useFormatDate() {
  const locale = useLocale();
  return useCallback(
    (value: string) =>
      new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeZone: "Asia/Riyadh" }).format(
        new Date(value.length === 10 ? `${value}T12:00:00+03:00` : value),
      ),
    [locale],
  );
}

export function Panel({
  title,
  action,
  children,
}: {
  title?: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-card border border-line bg-bg p-5">
      {(title || action) && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          {title && <h2 className="text-lg text-navy-deep">{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function ErrorNote({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p role="alert" className="rounded-control bg-red-50 p-3 text-sm text-red-700">
      {message}
    </p>
  );
}

export function SavedNote({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p role="status" className="rounded-control bg-emerald-50 p-3 text-sm text-emerald-800">
      {message}
    </p>
  );
}

export function ProBadge() {
  const t = useTranslations("Teacher.common");
  return (
    <span className="rounded-full bg-orange-soft px-2 py-0.5 text-[11px] font-bold text-orange-text">
      {t("pro")}
    </span>
  );
}

export function UpgradeLink() {
  const t = useTranslations("Teacher.common");
  return (
    <Link href="/teacher/plan" className={buttonVariants({ variant: "orange", size: "sm" })}>
      {t("upgrade")}
    </Link>
  );
}

export function ConfirmDelete({
  title,
  body,
  onConfirm,
  onClose,
}: {
  title: string;
  body: string;
  onConfirm: () => Promise<void>;
  onClose: () => void;
}) {
  const t = useTranslations("Teacher.common");
  const describe = useTeacherError();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function confirm() {
    setBusy(true);
    setError(null);
    try {
      await onConfirm();
      onClose();
    } catch (err) {
      setError(describe(err) ?? t("deleteFailed"));
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title={title} description={body} closeLabel={t("close")}>
      <div className="flex flex-col gap-3">
        <ErrorNote message={error} />
        <div className="flex justify-end gap-2">
          <Button variant="outline" size="sm" onClick={onClose}>
            {t("cancel")}
          </Button>
          <Button size="sm" loading={busy} onClick={confirm}>
            {t("delete")}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

export function FormButtons({ saving, onCancel }: { saving: boolean; onCancel: () => void }) {
  const t = useTranslations("Teacher.common");
  return (
    <div className="flex justify-end gap-2 pt-1">
      <Button type="button" variant="outline" size="sm" onClick={onCancel}>
        {t("cancel")}
      </Button>
      <Button type="submit" size="sm" loading={saving}>
        {saving ? t("saving") : t("save")}
      </Button>
    </div>
  );
}
