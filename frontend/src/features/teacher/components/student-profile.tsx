"use client";

import { useState } from "react";
import { ArrowLeft } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { cn } from "cn";
import { Button, buttonVariants } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadFeedback } from "@/features/platform/components/panel-ui";
import { useLoad } from "@/features/platform/use-load";
import { downloadReportCard, getStudentProfile } from "../api";
import {
  ATTENDANCE_STATUSES,
  PROFILE_PERIODS,
  type AttendanceStatus,
  type ProfilePeriod,
  type StudentProfile as Profile,
} from "../schemas";
import {
  ErrorNote,
  Panel,
  ProBadge,
  useFormatDate,
  useTeacherError,
  useWorkspace,
} from "./teacher-ui";

/** Each status has its own letter too, so the colours are never the only clue. */
export const STATUS_CHIP: Record<AttendanceStatus, string> = {
  present: "bg-navy text-on-dark",
  late: "bg-orange text-on-orange",
  excused: "bg-navy-line text-navy-deep",
  absent: "bg-red-600 text-white",
};

export const studentHref = (classId: number, studentId: number) => `#${classId}/s/${studentId}`;

const initialsOf = (name: string) =>
  name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => word[0])
    .join("")
    .toUpperCase();

function Stat({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="rounded-tile border border-line bg-bg p-4">
      <p className="text-sm text-ink-soft">{label}</p>
      <p className="mt-1 text-[28px] leading-tight font-bold text-navy-deep tabular-nums">
        {value}
      </p>
      {note && <p className="mt-0.5 text-xs text-ink-soft">{note}</p>}
    </div>
  );
}

function PercentBar({ value, average }: { value: number | null; average: number | null }) {
  return (
    <div className="relative h-2 w-full min-w-20 rounded-full bg-bg-tint" aria-hidden="true">
      {value !== null && (
        <div
          className="h-2 rounded-full bg-navy"
          style={{ inlineSize: `${Math.min(value, 100)}%` }}
        />
      )}
      {average !== null && (
        <div
          className="absolute -top-1 h-4 w-0.5 rounded-full bg-orange"
          style={{ insetInlineStart: `calc(${Math.min(average, 100)}% - 1px)` }}
        />
      )}
    </div>
  );
}

function AttendancePanel({ profile }: { profile: Profile }) {
  const t = useTranslations("Teacher.profile");
  const tStatus = useTranslations("Teacher.attendance");
  const formatDate = useFormatDate();
  const { attendance } = profile;

  return (
    <Panel title={t("attendanceTitle")}>
      {attendance.total === 0 ? (
        <p className="text-sm text-ink-soft">{t("noAttendance")}</p>
      ) : (
        <div className="flex flex-col gap-4">
          <ul className="flex flex-wrap gap-2" aria-label={t("legend")}>
            {ATTENDANCE_STATUSES.map((status) => (
              <li
                key={status}
                className="flex items-center gap-2 rounded-full border border-line px-3 py-1 text-sm text-ink"
              >
                <span
                  aria-hidden="true"
                  className={cn(
                    "flex size-5 items-center justify-center rounded-full text-[10px] font-bold",
                    STATUS_CHIP[status],
                  )}
                >
                  {t(`short.${status}`)}
                </span>
                {tStatus(status)}
                <span className="font-bold tabular-nums">{attendance[status]}</span>
              </li>
            ))}
          </ul>
          <ol className="flex flex-wrap gap-1.5" aria-label={t("days")}>
            {attendance.days.map((day) => (
              <li
                key={day.date}
                title={`${formatDate(day.date)}: ${tStatus(day.status)}`}
                className={cn(
                  "flex size-8 items-center justify-center rounded-md text-[11px] font-bold",
                  STATUS_CHIP[day.status],
                )}
              >
                <span aria-hidden="true">{t(`short.${day.status}`)}</span>
                <span className="sr-only">
                  {formatDate(day.date)}: {tStatus(day.status)}
                </span>
              </li>
            ))}
          </ol>
          <p className="text-xs text-ink-soft">{t("daysHint")}</p>
        </div>
      )}
    </Panel>
  );
}

function MarksPanel({ profile }: { profile: Profile }) {
  const t = useTranslations("Teacher.profile");
  const formatDate = useFormatDate();

  return (
    <Panel title={t("marksTitle")}>
      {profile.marks.length === 0 ? (
        <p className="text-sm text-ink-soft">{t("noMarks")}</p>
      ) : (
        <div className="flex flex-col gap-3">
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm tabular-nums">
              <thead className="bg-bg-tint text-ink-soft">
                <tr>
                  <th scope="col" className="p-2.5 text-start font-semibold">
                    {t("test")}
                  </th>
                  <th scope="col" className="p-2.5 text-start font-semibold whitespace-nowrap">
                    {t("score")}
                  </th>
                  <th scope="col" className="w-2/5 p-2.5 text-start font-semibold">
                    {t("percent")}
                  </th>
                  <th scope="col" className="p-2.5 text-start font-semibold whitespace-nowrap">
                    {t("classAverage")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {profile.marks.map((mark) => {
                  const percent = mark.percent === null ? null : Number(mark.percent);
                  const average =
                    mark.class_average_percent === null ? null : Number(mark.class_average_percent);
                  return (
                    <tr key={mark.id} className="border-t border-line">
                      <th scope="row" className="p-2.5 text-start font-normal">
                        <span className="block font-semibold text-ink">{mark.title}</span>
                        <span className="text-xs text-ink-soft">{formatDate(mark.date)}</span>
                      </th>
                      <td className="p-2.5 whitespace-nowrap text-ink">
                        {mark.value === null
                          ? t("notMarked")
                          : `${Number(mark.value)} / ${Number(mark.max_marks)}`}
                      </td>
                      <td className="p-2.5">
                        <div className="flex items-center gap-3">
                          <PercentBar value={percent} average={average} />
                          <span className="w-12 shrink-0 text-end font-semibold text-ink">
                            {percent === null ? "-" : `${percent}%`}
                          </span>
                        </div>
                      </td>
                      <td className="p-2.5 text-ink-soft">
                        {average === null ? "-" : `${average}%`}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="flex items-center gap-2 text-xs text-ink-soft">
            <span aria-hidden="true" className="h-3 w-0.5 rounded-full bg-orange" />
            {t("averageMarker")}
          </p>
        </div>
      )}
    </Panel>
  );
}

export function StudentProfile({ classId, studentId }: { classId: number; studentId: number }) {
  const t = useTranslations("Teacher.profile");
  const locale = useLocale();
  const describe = useTeacherError();
  const { workspace } = useWorkspace();
  const [period, setPeriod] = useState<ProfilePeriod>("month");
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const { state, reload } = useLoad(
    (signal) => getStudentProfile(studentId, period, signal),
    `p${studentId}:${period}`,
  );

  async function reportCard() {
    setError(null);
    setDownloading(true);
    try {
      await downloadReportCard({ id: studentId }, locale);
    } catch (err) {
      setError(describe(err));
    } finally {
      setDownloading(false);
    }
  }

  const profile = state.name === "ready" ? state.data : null;
  const student = profile?.student;
  const tested = profile?.marks.filter((mark) => mark.value !== null).length ?? 0;

  return (
    <>
      <div>
        <a href={`#${classId}`} className={buttonVariants({ variant: "ghost", size: "sm" })}>
          <ArrowLeft aria-hidden="true" className="size-4 rtl:rotate-180" />
          {student ? t("backTo", { name: student.classroom_name }) : t("back")}
        </a>
      </div>

      {state.name !== "ready" && <LoadFeedback state={state} onRetry={reload} />}

      {profile && student && (
        <>
          <header className="flex flex-wrap items-center gap-4">
            <span
              aria-hidden="true"
              className="flex size-14 shrink-0 items-center justify-center rounded-full bg-navy-soft text-lg font-bold text-navy"
            >
              {initialsOf(student.full_name)}
            </span>
            <div className="min-w-0 flex-1">
              <h1 className="text-2xl text-navy-deep">{student.full_name}</h1>
              <p className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-sm text-ink-soft">
                <span>{student.classroom_name}</span>
                {student.student_number && (
                  <span>
                    {t("id")}: <bdi>{student.student_number}</bdi>
                  </span>
                )}
                {student.father_name && (
                  <span>
                    {t("father")}: <bdi>{student.father_name}</bdi>
                  </span>
                )}
              </p>
            </div>
            <Button variant="outline" size="sm" loading={downloading} onClick={reportCard}>
              {t("reportCard")}
              {!workspace.limits.pro_features && <ProBadge />}
            </Button>
          </header>

          <ErrorNote message={error} />

          <div role="group" aria-label={t("periodLabel")} className="flex flex-wrap gap-1.5">
            {PROFILE_PERIODS.map((item) => (
              <button
                key={item}
                type="button"
                aria-pressed={period === item}
                onClick={() => setPeriod(item)}
                className={cn(
                  "min-h-10 cursor-pointer rounded-control border px-4 text-sm font-semibold transition-colors",
                  period === item
                    ? "border-navy bg-navy text-on-dark"
                    : "border-line bg-bg text-ink-soft hover:border-navy-line hover:text-navy",
                )}
              >
                {t(`periods.${item}`)}
              </button>
            ))}
          </div>

          {profile.attendance.total === 0 && profile.marks.length === 0 ? (
            <EmptyState title={t("emptyTitle")} description={t("emptyHint")} />
          ) : (
            <>
              <div className="grid gap-3 sm:grid-cols-3">
                <Stat
                  label={t("attendanceRate")}
                  value={
                    profile.attendance.rate === null ? "-" : `${Number(profile.attendance.rate)}%`
                  }
                  note={t("daysRecorded", { count: profile.attendance.total })}
                />
                <Stat
                  label={t("averageMark")}
                  value={
                    profile.average_percent === null ? "-" : `${Number(profile.average_percent)}%`
                  }
                />
                <Stat label={t("testsTaken")} value={`${tested} / ${profile.marks.length}`} />
              </div>
              <AttendancePanel profile={profile} />
              <MarksPanel profile={profile} />
            </>
          )}
        </>
      )}
    </>
  );
}
