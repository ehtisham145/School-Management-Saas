"use client";

import { useState, type ReactNode } from "react";
import { Plus } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import { Button, buttonVariants } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Modal } from "@/components/ui/modal";
import { Table, TableCell, TableHead, TableHeaderCell, TableRow } from "@/components/ui/table";
import { getSchoolCounts, listSchools, setSchoolActive } from "../api";
import type { PlatformSchool, SchoolStatusFilter } from "../schemas";
import { useLoad } from "../use-load";
import {
  DetailRow,
  FilterTabs,
  formatDate,
  LoadFeedback,
  localName,
  PageHeader,
  Pagination,
  SchoolStatusBadge,
  SearchBox,
} from "./panel-ui";

const ALL = "all";
type StatusFilter = SchoolStatusFilter | typeof ALL;

function DetailSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <h3 className="text-sm font-bold text-navy-deep">{title}</h3>
      <dl className="grid gap-3 rounded-control bg-bg-tint p-4 sm:grid-cols-2">{children}</dl>
    </section>
  );
}

function SchoolDetailDialog({ school, onClose }: { school: PlatformSchool; onClose: () => void }) {
  const t = useTranslations("Platform.schools.detail");
  const tOptions = useTranslations("Platform.options");
  const tCommon = useTranslations("Platform.common");
  const tSchools = useTranslations("Platform.schools");
  const locale = useLocale();
  const orNone = (value: string | number | null) =>
    value === null || value === "" ? tCommon("notProvided") : value;

  return (
    <Modal
      open
      onClose={onClose}
      title={localName(school, locale)}
      description={t("title")}
      closeLabel={tCommon("close")}
    >
      <div className="flex flex-col gap-4">
        <DetailSection title={t("sectionSchool")}>
          <DetailRow label={tSchools("name")}>
            <bdi>{orNone(locale === "ar" ? school.name_en : school.name_ar)}</bdi>
          </DetailRow>
          <DetailRow label={tSchools("code")}>
            <bdi className="font-mono text-xs">{school.code}</bdi>
          </DetailRow>
          <DetailRow label={tSchools("status")}>
            <SchoolStatusBadge isActive={school.is_active} />
          </DetailRow>
          <DetailRow label={tSchools("created")}>{formatDate(school.created_at, locale)}</DetailRow>
          <DetailRow label={t("type")}>
            {school.school_type ? tOptions(`type.${school.school_type}`) : tCommon("notProvided")}
          </DetailRow>
          <DetailRow label={t("stages")}>
            {school.education_stages.length > 0
              ? school.education_stages.map((stage) => tOptions(`stage.${stage}`)).join("، ")
              : tCommon("notProvided")}
          </DetailRow>
          <DetailRow label={t("students")}>{orNone(school.estimated_students)}</DetailRow>
          <DetailRow label={t("members")}>{school.member_count}</DetailRow>
        </DetailSection>

        <DetailSection title={t("sectionContact")}>
          <DetailRow label={t("email")}>
            <bdi>{orNone(school.email)}</bdi>
          </DetailRow>
          <DetailRow label={t("phone")}>
            <bdi>{orNone(school.phone)}</bdi>
          </DetailRow>
          <DetailRow label={t("region")}>
            {school.region ? tOptions(`region.${school.region}`) : tCommon("notProvided")}
          </DetailRow>
          <DetailRow label={t("city")}>
            <bdi>{orNone(school.city)}</bdi>
          </DetailRow>
          <div className="sm:col-span-2">
            <DetailRow label={t("address")}>
              <bdi>{orNone(school.address)}</bdi>
            </DetailRow>
          </div>
        </DetailSection>

        <DetailSection title={t("sectionLegal")}>
          <DetailRow label={t("crNumber")}>
            <bdi>{orNone(school.cr_number)}</bdi>
          </DetailRow>
          <DetailRow label={t("moeLicense")}>
            <bdi>{orNone(school.moe_license_number)}</bdi>
          </DetailRow>
        </DetailSection>

        <DetailSection title={t("sectionAdmin")}>
          <DetailRow label={t("adminName")}>
            <bdi>{orNone(school.admin_name)}</bdi>
          </DetailRow>
          <DetailRow label={t("adminEmail")}>
            <bdi>{orNone(school.school_admin_email)}</bdi>
          </DetailRow>
          <DetailRow label={t("adminPhone")}>
            <bdi>{orNone(school.admin_phone)}</bdi>
          </DetailRow>
        </DetailSection>
      </div>
    </Modal>
  );
}

function ConfirmStatusDialog({
  school,
  onClose,
  onChanged,
}: {
  school: PlatformSchool;
  onClose: () => void;
  onChanged: () => void;
}) {
  const t = useTranslations("Platform.schools");
  const tCommon = useTranslations("Platform.common");
  const locale = useLocale();
  const [saving, setSaving] = useState(false);
  const [failed, setFailed] = useState(false);

  const name = localName(school, locale);
  const activating = !school.is_active;

  async function confirm() {
    setSaving(true);
    setFailed(false);
    try {
      await setSchoolActive(school.id, activating);
      onChanged();
    } catch {
      setFailed(true);
      setSaving(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={t(activating ? "confirm.activateTitle" : "confirm.deactivateTitle", { school: name })}
      description={t(activating ? "confirm.activateBody" : "confirm.deactivateBody")}
      closeLabel={tCommon("close")}
    >
      {failed && (
        <p role="alert" className="mb-3 rounded-control bg-red-50 p-3 text-sm text-red-800">
          {t("confirm.failed")}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <Button variant="ghost" size="sm" onClick={onClose}>
          {tCommon("cancel")}
        </Button>
        <Button
          variant={activating ? "default" : "destructive"}
          size="sm"
          loading={saving}
          onClick={confirm}
        >
          {activating ? t("activate") : t("deactivate")}
        </Button>
      </div>
    </Modal>
  );
}

function CreatedNotice() {
  const t = useTranslations("Platform.schools");
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const code = searchParams.get("created");

  if (!code) return null;

  return (
    <div
      role="status"
      className="flex items-center justify-between gap-3 rounded-control bg-emerald-50 p-3 text-sm text-emerald-800"
    >
      <span>{t("created_notice", { code })}</span>
      <button
        type="button"
        onClick={() => router.replace(pathname)}
        className="cursor-pointer font-semibold underline"
      >
        {t("dismiss")}
      </button>
    </div>
  );
}

type Dialog = { name: "detail" | "status"; school: PlatformSchool } | null;

export function SchoolsPanel() {
  const t = useTranslations("Platform.schools");
  const tCommon = useTranslations("Platform.common");
  const tOptions = useTranslations("Platform.options");
  const tForm = useTranslations("Platform.form");
  const locale = useLocale();

  const [query, setQuery] = useState({ page: 1, search: "", status: ALL as StatusFilter });
  const [dialog, setDialog] = useState<Dialog>(null);

  const list = useLoad(
    (signal) =>
      listSchools(
        {
          page: query.page,
          search: query.search,
          status: query.status === ALL ? undefined : query.status,
        },
        signal,
      ),
    JSON.stringify(query),
  );
  const counts = useLoad(getSchoolCounts, "counts");
  const summary = counts.state.name === "ready" ? counts.state.data : null;

  function handleStatusChanged() {
    setDialog(null);
    list.reload();
    counts.reload();
  }

  const isFiltered = query.search !== "" || query.status !== ALL;
  const schoolName = (school: PlatformSchool) => localName(school, locale);

  return (
    <>
      <PageHeader
        title={t("title")}
        subtitle={t("subtitle")}
        action={
          <Link href="/platform/schools/new" className={buttonVariants({ size: "sm" })}>
            <Plus aria-hidden="true" />
            {t("newSchool")}
          </Link>
        }
      />

      <CreatedNotice />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <FilterTabs<StatusFilter>
          label={t("filterLabel")}
          value={query.status}
          onChange={(status) => setQuery((current) => ({ ...current, status, page: 1 }))}
          options={[
            { value: ALL, label: t("all"), count: summary?.total },
            { value: "active", label: t("active"), count: summary?.active },
            { value: "inactive", label: t("inactive"), count: summary?.inactive },
          ]}
        />
        <SearchBox
          label={t("searchLabel")}
          onSearch={(search) => setQuery((current) => ({ ...current, search, page: 1 }))}
        />
      </div>

      <LoadFeedback state={list.state} onRetry={list.reload} />

      {list.state.name === "ready" && list.state.data.count === 0 && (
        <EmptyState
          title={isFiltered ? t("noResults") : t("empty")}
          description={isFiltered ? undefined : tForm("description")}
        />
      )}

      {list.state.name === "ready" && list.state.data.count > 0 && (
        <>
          <Table className="bg-bg">
            <TableHead>
              <TableRow>
                <TableHeaderCell>{t("name")}</TableHeaderCell>
                <TableHeaderCell>{t("location")}</TableHeaderCell>
                <TableHeaderCell>{t("admin")}</TableHeaderCell>
                <TableHeaderCell>{t("students")}</TableHeaderCell>
                <TableHeaderCell>{t("members")}</TableHeaderCell>
                <TableHeaderCell>{t("status")}</TableHeaderCell>
                <TableHeaderCell>{t("created")}</TableHeaderCell>
                <TableHeaderCell>{t("actions")}</TableHeaderCell>
              </TableRow>
            </TableHead>
            <tbody>
              {list.state.data.results.map((school) => (
                <TableRow key={school.id}>
                  <TableCell>
                    <span className="block font-semibold text-ink">
                      <bdi>{schoolName(school)}</bdi>
                    </span>
                    <span className="block font-mono text-xs text-ink-soft">
                      <bdi>{school.code}</bdi>
                    </span>
                  </TableCell>
                  <TableCell>
                    {school.city || school.region ? (
                      <>
                        <span className="block">
                          <bdi>{school.city}</bdi>
                        </span>
                        {school.region && (
                          <span className="block text-xs text-ink-soft">
                            {tOptions(`region.${school.region}`)}
                          </span>
                        )}
                      </>
                    ) : (
                      "-"
                    )}
                  </TableCell>
                  <TableCell>
                    <bdi>{school.school_admin_email ?? "-"}</bdi>
                  </TableCell>
                  <TableCell>{school.estimated_students ?? "-"}</TableCell>
                  <TableCell>{school.member_count}</TableCell>
                  <TableCell>
                    <SchoolStatusBadge isActive={school.is_active} />
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    {formatDate(school.created_at, locale)}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1.5">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setDialog({ name: "detail", school })}
                      >
                        {tCommon("view")}
                      </Button>
                      <Button
                        variant={school.is_active ? "ghost" : "secondary"}
                        size="sm"
                        onClick={() => setDialog({ name: "status", school })}
                      >
                        {school.is_active ? t("deactivate") : t("activate")}
                      </Button>
                    </div>
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

      {dialog?.name === "detail" && (
        <SchoolDetailDialog school={dialog.school} onClose={() => setDialog(null)} />
      )}
      {dialog?.name === "status" && (
        <ConfirmStatusDialog
          school={dialog.school}
          onClose={() => setDialog(null)}
          onChanged={handleStatusChanged}
        />
      )}
    </>
  );
}
