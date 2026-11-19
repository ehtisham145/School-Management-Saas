"use client";

import { useRef, useState } from "react";
import { Plus, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { ApiError } from "@/lib/api";
import { email, optional, required, useValidatedForm } from "@/lib/use-validated-form";
import { addStudents, updateStudent } from "../api";
import type { Student } from "../schemas";
import { ErrorNote, FormButtons, useTeacherError, useWorkspace } from "./teacher-ui";

const ROW_FIELDS = ["first_name", "last_name", "father_name", "student_number"] as const;
type RowField = (typeof ROW_FIELDS)[number];
const MAX_LENGTH: Record<RowField, number> = {
  first_name: 100,
  last_name: 100,
  father_name: 100,
  student_number: 30,
};
/** The API takes up to 200 students in one request. */
const MAX_ROWS = 200;

const nameOf = (row: number, field: RowField) => `${field}_${row}`;
const blankRow = (row: number) =>
  Object.fromEntries(ROW_FIELDS.map((field) => [nameOf(row, field), ""]));

/** The row of the first student whose ID the server says is already used in the class. */
function takenIdRow(error: unknown) {
  if (!(error instanceof ApiError) || !Array.isArray(error.fields?.students)) return null;
  const index = (error.fields.students as Record<string, unknown>[]).findIndex(
    (row) => row && typeof row === "object" && "student_number" in row,
  );
  return index === -1 ? null : index;
}

export function AddStudentsDialog({
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
  const { workspace } = useWorkspace();
  const [rows, setRows] = useState<number[]>([0]);
  const nextRow = useRef(1);

  const { students: limit } = workspace.limits;
  const remaining = limit === null ? null : Math.max(limit - workspace.usage.students, 0);
  const maxRows = Math.min(MAX_ROWS, remaining ?? MAX_ROWS);

  const isBlank = (row: number, all: Record<string, string>) =>
    ROW_FIELDS.every((field) => !all[nameOf(row, field)]?.trim());
  const filledRows = (all: Record<string, string>) => {
    const filled = rows.filter((row) => !isBlank(row, all));
    return filled.length > 0 ? filled : rows.slice(0, 1);
  };

  const validators = Object.fromEntries(
    rows.flatMap((row) => [
      [
        nameOf(row, "first_name"),
        (value: string, all: Record<string, string>) =>
          // An empty extra row is simply left out.
          rows.length > 1 && isBlank(row, all) ? null : required(MAX_LENGTH.first_name)(value),
      ],
      [nameOf(row, "last_name"), optional(MAX_LENGTH.last_name)],
      [nameOf(row, "father_name"), optional(MAX_LENGTH.father_name)],
      [
        nameOf(row, "student_number"),
        (value: string, all: Record<string, string>) => {
          if (value.length > MAX_LENGTH.student_number) return "tooLong";
          const id = value.trim();
          const repeated =
            id &&
            rows.some(
              (other) => other !== row && all[nameOf(other, "student_number")]?.trim() === id,
            );
          return repeated ? "repeatedId" : null;
        },
      ],
    ]),
  );

  // Rows sent in the last request, to point a server error at the right row.
  const sent = useRef<number[]>([]);
  const form = useValidatedForm<Record<string, string>>({
    initial: blankRow(0),
    idPrefix: "students-",
    validators,
    submit: async (values) => {
      sent.current = filledRows(values);
      await addStudents(
        classId,
        sent.current.map((row) => ({
          first_name: values[nameOf(row, "first_name")].trim(),
          last_name: values[nameOf(row, "last_name")].trim(),
          father_name: values[nameOf(row, "father_name")].trim(),
          student_number: values[nameOf(row, "student_number")].trim(),
          parent_email: "",
        })),
      );
    },
    onSuccess: onSaved,
    describeError: (error) => {
      const index = takenIdRow(error);
      if (index !== null) {
        return t("idTaken", { number: rows.indexOf(sent.current[index]) + 1 });
      }
      return describe(error) ?? t("rowsInvalid");
    },
  });

  function addRow() {
    const row = nextRow.current++;
    for (const field of ROW_FIELDS) form.setValue(nameOf(row, field), "");
    setRows((current) => [...current, row]);
    requestAnimationFrame(() =>
      document.getElementById(`students-${nameOf(row, "first_name")}`)?.focus(),
    );
  }

  function removeRow(row: number) {
    setRows((current) => current.filter((item) => item !== row));
  }

  const count = filledRows(form.values).length;

  return (
    <Modal
      open
      onClose={onClose}
      title={t("addTitle")}
      description={t("addHint")}
      closeLabel={tCommon("close")}
      size="wide"
    >
      <form onSubmit={form.handleSubmit} noValidate className="flex flex-col gap-3">
        <ol className="flex flex-col gap-3">
          {rows.map((row, index) => (
            <li key={row} className="rounded-tile border border-line bg-bg-tint/40 p-3 sm:p-4">
              <div className="mb-2 flex items-center justify-between gap-2">
                <span className="text-xs font-bold tracking-wide text-ink-soft uppercase">
                  {t("rowLabel", { number: index + 1 })}
                </span>
                {rows.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeRow(row)}
                    aria-label={t("removeRow", { number: index + 1 })}
                    className="flex size-8 cursor-pointer items-center justify-center rounded-control text-ink-soft hover:bg-navy-soft hover:text-navy"
                  >
                    <X aria-hidden="true" className="size-4" />
                  </button>
                )}
              </div>
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                {ROW_FIELDS.map((field) => {
                  const name = nameOf(row, field);
                  return (
                    <Field
                      key={field}
                      id={`students-${name}`}
                      label={t(`fields.${field}`)}
                      required={field === "first_name"}
                      error={form.errorFor(name)}
                    >
                      <Input
                        {...form.bind(name)}
                        maxLength={MAX_LENGTH[field] + 10}
                        dir={field === "student_number" ? "ltr" : undefined}
                        className={field === "student_number" ? "h-11 rtl:text-end" : "h-11"}
                      />
                    </Field>
                  );
                })}
              </div>
            </li>
          ))}
        </ol>

        <div className="flex flex-wrap items-center gap-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={addRow}
            disabled={rows.length >= maxRows}
          >
            <Plus aria-hidden="true" className="size-4" />
            {t("addMore")}
          </Button>
          {remaining !== null && (
            <span className="text-sm text-ink-soft">{t("remaining", { count: remaining })}</span>
          )}
        </div>

        <ErrorNote message={form.formError} />
        <div className="flex justify-end gap-2 border-t border-line pt-3">
          <Button type="button" variant="outline" size="sm" onClick={onClose}>
            {tCommon("cancel")}
          </Button>
          <Button type="submit" size="sm" loading={form.saving}>
            {form.saving ? tCommon("saving") : t("saveCount", { count })}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export function EditStudentDialog({
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
    initial: {
      first_name: student.first_name,
      last_name: student.last_name,
      father_name: student.father_name,
      student_number: student.student_number,
      parent_email: student.parent_email,
    },
    idPrefix: "student-",
    validators: {
      first_name: required(MAX_LENGTH.first_name),
      last_name: optional(MAX_LENGTH.last_name),
      father_name: optional(MAX_LENGTH.father_name),
      student_number: optional(MAX_LENGTH.student_number),
      parent_email: (value) => (value.trim() ? email(value) : null),
    },
    submit: async (values) => {
      await updateStudent(student.id, {
        first_name: values.first_name.trim(),
        last_name: values.last_name.trim(),
        father_name: values.father_name.trim(),
        student_number: values.student_number.trim(),
        parent_email: values.parent_email.trim(),
      });
    },
    onSuccess: onSaved,
    describeError: describe,
    describeFieldError: (name) => (name === "student_number" ? t("idTakenOne") : null),
  });

  return (
    <Modal open onClose={onClose} title={t("editTitle")} closeLabel={tCommon("close")}>
      <form onSubmit={form.handleSubmit} noValidate className="flex flex-col gap-3">
        <div className="grid gap-3 sm:grid-cols-2">
          {ROW_FIELDS.map((field) => (
            <Field
              key={field}
              id={`student-${field}`}
              label={t(`fields.${field}`)}
              required={field === "first_name"}
              error={form.errorFor(field)}
            >
              <Input
                {...form.bind(field)}
                dir={field === "student_number" ? "ltr" : undefined}
                className={field === "student_number" ? "rtl:text-end" : undefined}
              />
            </Field>
          ))}
        </div>
        <Field
          id="student-parent_email"
          label={t("parentEmail")}
          hint={t("parentEmailHint")}
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
