"use client";

import { useState } from "react";
import { ArrowLeft } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { cn } from "cn";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { LoadFeedback, PageHeader } from "@/features/platform/components/panel-ui";
import { useLoad } from "@/features/platform/use-load";
import {
  email,
  required,
  requiredDate,
  todayInRiyadh,
  useValidatedForm,
} from "@/lib/use-validated-form";
import {
  addStudents,
  createAssessment,
  deleteAssessment,
  deleteStudent,
  downloadReportCard,
  getAttendance,
  getClass,
  getGradebook,
  getMarkSheet,
  listAssessments,
  listStudents,
  saveAttendance,
  saveMarks,
  updateStudent,
} from "../api";
import {
  ATTENDANCE_STATUSES,
  type AttendanceRoster,
  type AttendanceStatus,
  type MarkSheet,
  type Student,
} from "../schemas";
import {
  ConfirmDelete,
  ErrorNote,
  FormButtons,
  Panel,
  ProBadge,
  SavedNote,
  useFormatDate,
  useTeacherError,
  useWorkspace,
} from "./teacher-ui";

const TABS = ["students", "attendance", "marks"] as const;
type Tab = (typeof TABS)[number];

function AddStudentsDialog({
  classId,
  onClose,
  onSaved,
}: {
  classId: number;
  onClose: () => void;
  onSaved: () => void;
}) {
  const t = useTranslations("Teacher.students");
  const tCommon = useTranslations("Teacher.common");
  const describe = useTeacherError();
  const form = useValidatedForm({
    initial: { names: "" },
    idPrefix: "students-",
    validators: { names: required(10000) },
    submit: async (values) => {
      const students = values.names
        .split("\n")
        .map((name) => name.trim())
        .filter(Boolean)
        .map((full_name) => ({ full_name }));
      await addStudents(classId, students);
    },
    onSuccess: onSaved,
    describeError: (error) => describe(error) ?? t("namesInvalid"),
  });

  return (
    <Modal open onClose={onClose} title={t("addTitle")} closeLabel={tCommon("close")}>
      <form onSubmit={form.handleSubmit} noValidate className="flex flex-col gap-3">
        <Field
          id="students-names"
          label={t("names")}
          required
          hint={t("namesHint")}
          error={form.errorFor("names")}
        >
          <Textarea {...form.bind("names")} rows={7} />
        </Field>
        <ErrorNote message={form.formError} />
        <FormButtons saving={form.saving} onCancel={onClose} />
      </form>
    </Modal>
  );
}

function EditStudentDialog({
  student,
  onClose,
  onSaved,
}: {
  student: Student;
  onClose: () => void;
  onSaved: () => void;
}) {
  const t = useTranslations("Teacher.students");
  const tCommon = useTranslations("Teacher.common");
  const describe = useTeacherError();
  const form = useValidatedForm({
    initial: { full_name: student.full_name, parent_email: student.parent_email },
    idPrefix: "student-",
    validators: {
      full_name: required(150),
      parent_email: (value) => (value.trim() ? email(value) : null),
    },
    submit: async (values) => {
      await updateStudent(student.id, {
        full_name: values.full_name.trim(),
        parent_email: values.parent_email.trim(),
      });
    },
    onSuccess: onSaved,
    describeError: describe,
  });

  return (
    <Modal open onClose={onClose} title={t("editTitle")} closeLabel={tCommon("close")}>
      <form onSubmit={form.handleSubmit} noValidate className="flex flex-col gap-3">
        <Field
          id="student-full_name"
          label={t("fullName")}
          required
          error={form.errorFor("full_name")}
        >
          <Input {...form.bind("full_name")} />
        </Field>
        <Field
          id="student-parent_email"
          label={t("parentEmail")}
          error={form.errorFor("parent_email")}
        >
          <Input {...form.bind("parent_email")} type="email" dir="ltr" className="rtl:text-end" />
        </Field>
        <ErrorNote message={form.formError} />
        <FormButtons saving={form.saving} onCancel={onClose} />
      </form>
    </Modal>
  );
}

function StudentsTab({ classId, onChanged }: { classId: number; onChanged: () => void }) {
  const t = useTranslations("Teacher.students");
  const tCommon = useTranslations("Teacher.common");
  const locale = useLocale();
  const describe = useTeacherError();
  const { workspace } = useWorkspace();
  const { state, reload } = useLoad((signal) => listStudents(classId, signal), `s${classId}`);
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<Student | null>(null);
  const [removing, setRemoving] = useState<Student | null>(null);
  const [error, setError] = useState<string | null>(null);
  const readOnly = workspace.access.read_only;

  function refresh() {
    setAdding(false);
    setEditing(null);
    reload();
    onChanged();
  }

  async function reportCard(student: Student) {
    setError(null);
    try {
      await downloadReportCard(student, locale);
    } catch (err) {
      setError(describe(err));
    }
  }

  return (
    <Panel
      title={t("title")}
      action={
        !readOnly && (
          <Button size="sm" onClick={() => setAdding(true)}>
            {t("add")}
          </Button>
        )
      }
    >
      <div className="flex flex-col gap-3">
        <ErrorNote message={error} />
        <LoadFeedback state={state} onRetry={reload} />
        {state.name === "ready" && state.data.length === 0 && (
          <EmptyState title={t("emptyTitle")} description={t("emptyHint")} />
        )}
        {state.name === "ready" && state.data.length > 0 && (
          <ul className="divide-y divide-line">
            {state.data.map((student) => (
              <li key={student.id} className="flex flex-wrap items-center gap-2 py-2.5">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-ink">{student.full_name}</p>
                  {student.parent_email && (
                    <p className="truncate text-xs text-ink-soft" dir="ltr">
                      {student.parent_email}
                    </p>
                  )}
                </div>
                <Button variant="ghost" size="sm" onClick={() => reportCard(student)}>
                  {t("reportCard")}
                  {!workspace.limits.pro_features && <ProBadge />}
                </Button>
                {!readOnly && (
                  <>
                    <Button variant="outline" size="sm" onClick={() => setEditing(student)}>
                      {tCommon("edit")}
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => setRemoving(student)}>
                      {tCommon("delete")}
                    </Button>
                  </>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {adding && (
        <AddStudentsDialog classId={classId} onClose={() => setAdding(false)} onSaved={refresh} />
      )}
      {editing && (
        <EditStudentDialog student={editing} onClose={() => setEditing(null)} onSaved={refresh} />
      )}
      {removing && (
        <ConfirmDelete
          title={t("deleteTitle", { name: removing.full_name })}
          body={t("deleteBody")}
          onConfirm={async () => {
            await deleteStudent(removing.id);
            refresh();
          }}
          onClose={() => setRemoving(null)}
        />
      )}
    </Panel>
  );
}

function AttendanceSheet({
  classId,
  roster,
  onSaved,
}: {
  classId: number;
  roster: AttendanceRoster;
  onSaved: () => void;
}) {
  const t = useTranslations("Teacher.attendance");
  const tCommon = useTranslations("Teacher.common");
  const describe = useTeacherError();
  const { workspace } = useWorkspace();
  const [statuses, setStatuses] = useState<Record<number, AttendanceStatus>>(() =>
    Object.fromEntries(
      roster.students.flatMap((row) => (row.status ? [[row.id, row.status]] : [])),
    ),
  );
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const readOnly = workspace.access.read_only;

  async function save() {
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      await saveAttendance(
        classId,
        roster.date,
        Object.entries(statuses).map(([student, status]) => ({
          student: Number(student),
          status,
        })),
      );
      setNotice(t("saved"));
      onSaved();
    } catch (err) {
      setError(describe(err) ?? tCommon("saveFailed"));
    } finally {
      setSaving(false);
    }
  }

  const unmarked = roster.students.length - Object.keys(statuses).length;

  return (
    <div className="flex flex-col gap-3">
      {!readOnly && (
        <div>
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              setStatuses(
                Object.fromEntries(
                  roster.students.map((row) => [row.id, "present" as AttendanceStatus]),
                ),
              )
            }
          >
            {t("allPresent")}
          </Button>
        </div>
      )}
      <ul className="divide-y divide-line">
        {roster.students.map((row) => (
          <li key={row.id} className="flex flex-wrap items-center justify-between gap-2 py-2.5">
            <span className="text-sm font-semibold text-ink">{row.full_name}</span>
            <div role="group" aria-label={row.full_name} className="flex flex-wrap gap-1">
              {ATTENDANCE_STATUSES.map((status) => {
                const selected = statuses[row.id] === status;
                return (
                  <button
                    key={status}
                    type="button"
                    disabled={readOnly}
                    aria-pressed={selected}
                    onClick={() => setStatuses((current) => ({ ...current, [row.id]: status }))}
                    className={cn(
                      "min-h-9 cursor-pointer rounded-control border px-2.5 text-xs font-semibold transition-colors disabled:cursor-not-allowed",
                      selected
                        ? "border-navy bg-navy text-on-dark"
                        : "border-line bg-bg text-ink-soft hover:border-navy-line",
                    )}
                  >
                    {t(status)}
                  </button>
                );
              })}
            </div>
          </li>
        ))}
      </ul>
      <ErrorNote message={error} />
      <SavedNote message={notice} />
      {!readOnly && (
        <div className="flex flex-wrap items-center gap-3">
          <Button
            size="sm"
            loading={saving}
            disabled={Object.keys(statuses).length === 0}
            onClick={save}
          >
            {saving ? tCommon("saving") : t("save")}
          </Button>
          {unmarked > 0 && (
            <span className="text-sm text-ink-soft">{t("unmarked", { count: unmarked })}</span>
          )}
        </div>
      )}
    </div>
  );
}

function AttendanceTab({ classId }: { classId: number }) {
  const t = useTranslations("Teacher.attendance");
  const { reload: reloadWorkspace } = useWorkspace();
  const today = todayInRiyadh();
  const [date, setDate] = useState(today);
  const { state, reload } = useLoad(
    (signal) => getAttendance(classId, date, signal),
    `a${classId}:${date}`,
  );

  return (
    <Panel
      title={t("title")}
      action={
        <Field id="attendance-date" label={t("date")}>
          <Input
            id="attendance-date"
            type="date"
            value={date}
            max={today}
            onChange={(event) => event.target.value && setDate(event.target.value)}
            className="h-10"
          />
        </Field>
      }
    >
      <LoadFeedback state={state} onRetry={reload} />
      {state.name === "ready" && state.data.students.length === 0 && (
        <EmptyState title={t("emptyTitle")} description={t("emptyHint")} />
      )}
      {state.name === "ready" && state.data.students.length > 0 && (
        <AttendanceSheet
          key={state.data.date}
          classId={classId}
          roster={state.data}
          onSaved={reloadWorkspace}
        />
      )}
    </Panel>
  );
}

function AssessmentDialog({
  classId,
  onClose,
  onSaved,
}: {
  classId: number;
  onClose: () => void;
  onSaved: () => void;
}) {
  const t = useTranslations("Teacher.marks");
  const tCommon = useTranslations("Teacher.common");
  const describe = useTeacherError();
  const form = useValidatedForm({
    initial: { title: "", max_marks: "", date: todayInRiyadh() },
    idPrefix: "assessment-",
    validators: {
      title: required(150),
      max_marks: (value) => (Number(value) > 0 && Number(value) < 10000 ? null : "invalid"),
      date: requiredDate,
    },
    submit: async (values) => {
      await createAssessment({ ...values, classroom: classId });
    },
    onSuccess: onSaved,
    describeError: describe,
  });

  return (
    <Modal open onClose={onClose} title={t("newTitle")} closeLabel={tCommon("close")}>
      <form onSubmit={form.handleSubmit} noValidate className="flex flex-col gap-3">
        <Field id="assessment-title" label={t("name")} required error={form.errorFor("title")}>
          <Input {...form.bind("title")} placeholder={t("nameExample")} />
        </Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field
            id="assessment-max_marks"
            label={t("maxMarks")}
            required
            error={form.errorFor("max_marks")}
          >
            <Input {...form.bind("max_marks")} inputMode="decimal" dir="ltr" />
          </Field>
          <Field id="assessment-date" label={t("date")} required error={form.errorFor("date")}>
            <Input {...form.bind("date")} type="date" />
          </Field>
        </div>
        <ErrorNote message={form.formError} />
        <FormButtons saving={form.saving} onCancel={onClose} />
      </form>
    </Modal>
  );
}

function MarkEntry({ sheet, onSaved }: { sheet: MarkSheet; onSaved: () => void }) {
  const t = useTranslations("Teacher.marks");
  const tCommon = useTranslations("Teacher.common");
  const describe = useTeacherError();
  const { workspace } = useWorkspace();
  const [values, setValues] = useState<Record<number, string>>(() =>
    Object.fromEntries(sheet.students.map((row) => [row.id, row.value ?? ""])),
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const maximum = Number(sheet.assessment.max_marks);
  const readOnly = workspace.access.read_only;

  const isInvalid = (value: string) =>
    value.trim() !== "" && (!/^\d+(\.\d{1,2})?$/.test(value.trim()) || Number(value) > maximum);
  const hasInvalid = Object.values(values).some(isInvalid);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      await saveMarks(
        sheet.assessment.id,
        sheet.students.map((row) => ({
          student: row.id,
          value: values[row.id]?.trim() || null,
        })),
      );
      onSaved();
    } catch (err) {
      setError(describe(err) ?? tCommon("saveFailed"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <ul className="divide-y divide-line">
        {sheet.students.map((row) => {
          const invalid = isInvalid(values[row.id] ?? "");
          return (
            <li key={row.id} className="flex items-center justify-between gap-3 py-2">
              <label htmlFor={`mark-${row.id}`} className="text-sm font-semibold text-ink">
                {row.full_name}
              </label>
              <div className="flex items-center gap-2">
                <Input
                  id={`mark-${row.id}`}
                  value={values[row.id] ?? ""}
                  disabled={readOnly}
                  inputMode="decimal"
                  dir="ltr"
                  aria-invalid={invalid}
                  onChange={(event) =>
                    setValues((current) => ({ ...current, [row.id]: event.target.value }))
                  }
                  className="h-10 w-24 text-center"
                />
                <span className="text-sm text-ink-soft tabular-nums">/ {maximum}</span>
              </div>
            </li>
          );
        })}
      </ul>
      {hasInvalid && (
        <p role="alert" className="text-sm text-red-700">
          {t("invalidMark", { max: maximum })}
        </p>
      )}
      <ErrorNote message={error} />
      {!readOnly && (
        <div>
          <Button size="sm" loading={saving} disabled={hasInvalid} onClick={save}>
            {saving ? tCommon("saving") : t("save")}
          </Button>
        </div>
      )}
    </div>
  );
}

function GradebookTable({ classId, version }: { classId: number; version: number }) {
  const t = useTranslations("Teacher.marks");
  const { state, reload } = useLoad(
    (signal) => getGradebook(classId, signal),
    `g${classId}:${version}`,
  );

  if (state.name !== "ready") return <LoadFeedback state={state} onRetry={reload} />;
  const { assessments, students } = state.data;
  if (assessments.length === 0 || students.length === 0) return null;

  return (
    <Panel title={t("gradebook")}>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm whitespace-nowrap tabular-nums">
          <thead className="bg-bg-tint text-ink-soft">
            <tr>
              <th scope="col" className="p-2.5 text-start font-semibold">
                {t("student")}
              </th>
              {assessments.map((assessment) => (
                <th key={assessment.id} scope="col" className="p-2.5 text-start font-semibold">
                  {assessment.title} ({Number(assessment.max_marks)})
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {students.map((student) => (
              <tr key={student.id} className="border-t border-line">
                <th scope="row" className="p-2.5 text-start font-semibold text-ink">
                  {student.full_name}
                </th>
                {assessments.map((assessment) => {
                  const mark = student.marks[assessment.id];
                  return (
                    <td key={assessment.id} className="p-2.5 text-ink">
                      {mark === undefined ? "-" : Number(mark)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

function MarkSheetLoader({
  assessmentId,
  version,
  onSaved,
}: {
  assessmentId: number;
  version: number;
  onSaved: () => void;
}) {
  const t = useTranslations("Teacher.marks");
  const { state, reload } = useLoad(
    (signal) => getMarkSheet(assessmentId, signal),
    `m${assessmentId}:${version}`,
  );

  if (state.name !== "ready") return <LoadFeedback state={state} onRetry={reload} />;
  if (state.data.students.length === 0) {
    return <EmptyState title={t("noStudents")} description={t("noStudentsHint")} />;
  }
  return <MarkEntry key={`${assessmentId}:${version}`} sheet={state.data} onSaved={onSaved} />;
}

function MarksTab({ classId }: { classId: number }) {
  const t = useTranslations("Teacher.marks");
  const tCommon = useTranslations("Teacher.common");
  const formatDate = useFormatDate();
  const { workspace } = useWorkspace();
  const { state, reload } = useLoad((signal) => listAssessments(classId, signal), `as${classId}`);
  const [selected, setSelected] = useState<number | null>(null);
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [version, setVersion] = useState(0);
  // Kept here because saving reloads the sheet below.
  const [justSaved, setJustSaved] = useState(false);
  const readOnly = workspace.access.read_only;

  const assessments = state.name === "ready" ? state.data : [];
  const current = assessments.find((item) => item.id === selected) ?? assessments.at(-1) ?? null;

  function changed() {
    setVersion((value) => value + 1);
    reload();
  }

  return (
    <>
      <Panel
        title={t("title")}
        action={
          !readOnly && (
            <Button size="sm" onClick={() => setAdding(true)}>
              {t("new")}
            </Button>
          )
        }
      >
        <LoadFeedback state={state} onRetry={reload} />
        {state.name === "ready" && assessments.length === 0 && (
          <EmptyState title={t("emptyTitle")} description={t("emptyHint")} />
        )}
        {current && (
          <div className="flex flex-col gap-4">
            <div className="flex flex-wrap items-end gap-3">
              <div className="min-w-56 flex-1">
                <Field id="assessment-choice" label={t("choose")}>
                  <Select
                    id="assessment-choice"
                    value={current.id}
                    onChange={(event) => {
                      setSelected(Number(event.target.value));
                      setJustSaved(false);
                    }}
                    className="h-11"
                  >
                    {assessments.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.title} · {formatDate(item.date)}
                      </option>
                    ))}
                  </Select>
                </Field>
              </div>
              {!readOnly && (
                <Button variant="ghost" size="sm" onClick={() => setRemoving(true)}>
                  {tCommon("delete")}
                </Button>
              )}
            </div>
            <SavedNote message={justSaved ? t("saved") : null} />
            <MarkSheetLoader
              assessmentId={current.id}
              version={version}
              onSaved={() => {
                setJustSaved(true);
                changed();
              }}
            />
          </div>
        )}
      </Panel>

      <GradebookTable classId={classId} version={version} />

      {adding && (
        <AssessmentDialog
          classId={classId}
          onClose={() => setAdding(false)}
          onSaved={() => {
            setAdding(false);
            setSelected(null);
            changed();
          }}
        />
      )}
      {removing && current && (
        <ConfirmDelete
          title={t("deleteTitle", { name: current.title })}
          body={t("deleteBody")}
          onConfirm={async () => {
            await deleteAssessment(current.id);
            setSelected(null);
            changed();
          }}
          onClose={() => setRemoving(false)}
        />
      )}
    </>
  );
}

export function ClassDetail({ classId, onBack }: { classId: number; onBack: () => void }) {
  const t = useTranslations("Teacher.classes");
  const { reload: reloadWorkspace } = useWorkspace();
  const { state, reload } = useLoad((signal) => getClass(classId, signal), `c${classId}`);
  const [tab, setTab] = useState<Tab>("students");

  return (
    <>
      <div>
        <Button variant="ghost" size="sm" onClick={onBack}>
          <ArrowLeft aria-hidden="true" className="size-4 rtl:rotate-180" />
          {t("back")}
        </Button>
      </div>

      <LoadFeedback state={state} onRetry={reload} />

      {state.name === "ready" && (
        <>
          <PageHeader
            title={state.data.name}
            subtitle={[state.data.subject, state.data.grade].filter(Boolean).join(" · ")}
            action={
              <Badge tone="navy">{t("studentCount", { count: state.data.student_count })}</Badge>
            }
          />

          <div role="tablist" aria-label={t("tabsLabel")} className="flex flex-wrap gap-1.5">
            {TABS.map((item) => (
              <button
                key={item}
                type="button"
                role="tab"
                aria-selected={tab === item}
                onClick={() => setTab(item)}
                className={cn(
                  "min-h-10 cursor-pointer rounded-control border px-4 text-sm font-semibold transition-colors",
                  tab === item
                    ? "border-navy bg-navy text-on-dark"
                    : "border-line bg-bg text-ink-soft hover:border-navy-line hover:text-navy",
                )}
              >
                {t(`tabs.${item}`)}
              </button>
            ))}
          </div>

          {tab === "students" && (
            <StudentsTab
              classId={classId}
              onChanged={() => {
                reload();
                reloadWorkspace();
              }}
            />
          )}
          {tab === "attendance" && <AttendanceTab classId={classId} />}
          {tab === "marks" && <MarksTab classId={classId} />}
        </>
      )}
    </>
  );
}
