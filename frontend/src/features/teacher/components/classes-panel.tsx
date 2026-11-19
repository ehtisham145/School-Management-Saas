"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowRight, Check, Clock, MoreHorizontal, Plus } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "cn";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { LoadFeedback, PageHeader } from "@/features/platform/components/panel-ui";
import { useLoad } from "@/features/platform/use-load";
import { optional, required, useValidatedForm } from "@/lib/use-validated-form";
import { createClass, deleteClass, listClasses, updateClass } from "../api";
import type { Classroom } from "../schemas";
import { ClassDetail } from "./class-detail";
import { StudentProfile } from "./student-profile";
import { ConfirmDelete, ErrorNote, FormButtons, useTeacherError, useWorkspace } from "./teacher-ui";

function ClassDialog({
  classroom,
  onClose,
  onSaved,
}: {
  classroom: Classroom | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const t = useTranslations("Teacher.classes");
  const tCommon = useTranslations("Teacher.common");
  const describe = useTeacherError();
  const form = useValidatedForm({
    initial: {
      name: classroom?.name ?? "",
      subject: classroom?.subject ?? "",
      grade: classroom?.grade ?? "",
    },
    idPrefix: "class-",
    validators: { name: required(100), subject: optional(100), grade: optional(50) },
    submit: async (values) => {
      if (classroom) await updateClass(classroom.id, values);
      else await createClass(values);
    },
    onSuccess: onSaved,
    describeError: describe,
    describeFieldError: (name) => (name === "name" ? t("nameSubjectTaken") : null),
  });

  return (
    <Modal
      open
      onClose={onClose}
      title={classroom ? t("editTitle") : t("newTitle")}
      closeLabel={tCommon("close")}
    >
      <form onSubmit={form.handleSubmit} noValidate className="flex flex-col gap-3">
        <Field id="class-name" label={t("name")} required error={form.errorFor("name")}>
          <Input {...form.bind("name")} placeholder={t("nameExample")} />
        </Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field id="class-subject" label={t("subject")} error={form.errorFor("subject")}>
            <Input {...form.bind("subject")} />
          </Field>
          <Field id="class-grade" label={t("grade")} error={form.errorFor("grade")}>
            <Input {...form.bind("grade")} />
          </Field>
        </div>
        <ErrorNote message={form.formError} />
        <FormButtons saving={form.saving} onCancel={onClose} />
      </form>
    </Modal>
  );
}

/** "#12" opens class 12, and "#12/s/40" opens student 40 of that class. */
function readHash() {
  const [classPart, kind, studentPart] = window.location.hash.slice(1).split("/");
  return {
    classId: Number(classPart) || null,
    studentId: kind === "s" ? Number(studentPart) || null : null,
  };
}

/** A short badge for the class, such as "5A" for "Grade 5A". */
function classBadge(name: string) {
  const words = name.trim().split(/\s+/);
  const numbered = words.find((word) => /\d/.test(word));
  return (numbered ?? words.map((word) => word[0]).join("")).slice(0, 3).toUpperCase();
}

function CardMenu({
  label,
  onEdit,
  onDelete,
}: {
  label: string;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const tCommon = useTranslations("Teacher.common");
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent | KeyboardEvent) => {
      if (
        event instanceof KeyboardEvent
          ? event.key === "Escape"
          : !box.current?.contains(event.target as Node)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);

  const item =
    "block w-full cursor-pointer rounded-md px-3 py-2 text-start text-sm font-semibold hover:bg-navy-soft";
  return (
    <div ref={box} className="relative z-10">
      <button
        type="button"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className="flex size-9 cursor-pointer items-center justify-center rounded-control text-ink-soft hover:bg-navy-soft hover:text-navy"
      >
        <MoreHorizontal aria-hidden="true" className="size-5" />
      </button>
      {open && (
        <div
          role="menu"
          className="absolute end-0 top-10 w-36 rounded-control border border-line bg-bg p-1 shadow-soft"
        >
          <button
            type="button"
            role="menuitem"
            className={cn(item, "text-ink")}
            onClick={() => {
              setOpen(false);
              onEdit();
            }}
          >
            {tCommon("edit")}
          </button>
          <button
            type="button"
            role="menuitem"
            className={cn(item, "text-red-700 hover:bg-red-50")}
            onClick={() => {
              setOpen(false);
              onDelete();
            }}
          >
            {tCommon("delete")}
          </button>
        </div>
      )}
    </div>
  );
}

function ClassCard({
  classroom,
  readOnly,
  onEdit,
  onDelete,
}: {
  classroom: Classroom;
  readOnly: boolean;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const t = useTranslations("Teacher.classes");
  const taken = classroom.attendance_taken_today;
  const details = [classroom.subject, classroom.grade].filter(Boolean).join(" · ");

  return (
    <li className="group relative flex flex-col overflow-hidden rounded-card border border-line bg-bg transition-[border-color,box-shadow,transform] duration-200 hover:-translate-y-0.5 hover:border-navy-line hover:shadow-soft">
      <div aria-hidden="true" className="h-1.5 bg-linear-to-r from-navy to-navy-hover" />
      <div className="flex flex-1 flex-col gap-4 p-4">
        <div className="flex items-start gap-3">
          <span
            aria-hidden="true"
            className="flex size-12 shrink-0 items-center justify-center rounded-tile bg-navy-soft text-base font-bold text-navy"
          >
            {classBadge(classroom.name)}
          </span>
          <div className="min-w-0 flex-1">
            <a
              href={`#${classroom.id}`}
              className="block truncate text-[17px] font-semibold text-navy-deep outline-none after:absolute after:inset-0 after:rounded-card focus-visible:after:ring-2 focus-visible:after:ring-navy"
            >
              {classroom.name}
            </a>
            <p className="mt-0.5 truncate text-sm text-ink-soft">{details || t("noDetails")}</p>
          </div>
          {!readOnly && (
            <CardMenu
              label={t("menu", { name: classroom.name })}
              onEdit={onEdit}
              onDelete={onDelete}
            />
          )}
        </div>

        <dl className="grid grid-cols-2 gap-2">
          <div className="rounded-control bg-bg-tint px-3 py-2">
            <dt className="text-xs text-ink-soft">{t("students")}</dt>
            <dd className="text-xl font-bold text-navy-deep tabular-nums">
              {classroom.student_count}
            </dd>
          </div>
          <div className="rounded-control bg-bg-tint px-3 py-2">
            <dt className="text-xs text-ink-soft">{t("tests")}</dt>
            <dd className="text-xl font-bold text-navy-deep tabular-nums">
              {classroom.assessment_count}
            </dd>
          </div>
        </dl>

        <div className="mt-auto flex flex-wrap items-center justify-between gap-2">
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold",
              taken ? "bg-emerald-50 text-emerald-800" : "bg-orange-soft text-orange-text",
            )}
          >
            {taken ? (
              <Check aria-hidden="true" className="size-3.5" />
            ) : (
              <Clock aria-hidden="true" className="size-3.5" />
            )}
            {taken ? t("attendanceTaken") : t("attendanceWaiting")}
          </span>
          <span
            aria-hidden="true"
            className="inline-flex items-center gap-1 text-sm font-semibold text-navy"
          >
            {t("openClass")}
            <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5 rtl:rotate-180 rtl:group-hover:-translate-x-0.5" />
          </span>
        </div>
      </div>
    </li>
  );
}

export function ClassesPanel() {
  const t = useTranslations("Teacher.classes");
  const { workspace, reload: reloadWorkspace } = useWorkspace();
  const { state, reload } = useLoad(listClasses, "classes");
  const [dialog, setDialog] = useState<Classroom | "new" | null>(null);
  const [removing, setRemoving] = useState<Classroom | null>(null);
  const [opened, setOpened] = useState<ReturnType<typeof readHash>>({
    classId: null,
    studentId: null,
  });
  const readOnly = workspace.access.read_only;

  // The open class lives in the address, so a refresh or the back button keeps it.
  useEffect(() => {
    const sync = () => {
      setOpened(readHash());
      window.scrollTo({ top: 0 });
    };
    sync();
    window.addEventListener("hashchange", sync);
    return () => window.removeEventListener("hashchange", sync);
  }, []);

  function refresh() {
    setDialog(null);
    reload();
    reloadWorkspace();
  }

  if (opened.classId !== null && opened.studentId !== null) {
    return <StudentProfile classId={opened.classId} studentId={opened.studentId} />;
  }

  if (opened.classId !== null) {
    return (
      <ClassDetail
        classId={opened.classId}
        onBack={() => {
          window.location.hash = "";
          reload();
        }}
      />
    );
  }

  return (
    <>
      <PageHeader
        title={t("title")}
        subtitle={t("subtitle")}
        action={
          !readOnly && (
            <Button size="sm" onClick={() => setDialog("new")}>
              <Plus aria-hidden="true" className="size-4" />
              {t("new")}
            </Button>
          )
        }
      />

      <LoadFeedback state={state} onRetry={reload} />

      {state.name === "ready" && state.data.length === 0 && (
        <EmptyState title={t("emptyTitle")} description={t("emptyHint")} />
      )}

      {state.name === "ready" && state.data.length > 0 && (
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {state.data.map((classroom) => (
            <ClassCard
              key={classroom.id}
              classroom={classroom}
              readOnly={readOnly}
              onEdit={() => setDialog(classroom)}
              onDelete={() => setRemoving(classroom)}
            />
          ))}
        </ul>
      )}

      {dialog && (
        <ClassDialog
          classroom={dialog === "new" ? null : dialog}
          onClose={() => setDialog(null)}
          onSaved={refresh}
        />
      )}
      {removing && (
        <ConfirmDelete
          title={t("deleteTitle", { name: removing.name })}
          body={t("deleteBody")}
          onConfirm={async () => {
            await deleteClass(removing.id);
            refresh();
          }}
          onClose={() => setRemoving(null)}
        />
      )}
    </>
  );
}
