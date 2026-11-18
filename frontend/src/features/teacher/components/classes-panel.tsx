"use client";

import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button, buttonVariants } from "@/components/ui/button";
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
    describeFieldError: (name) => (name === "name" ? t("nameTaken") : null),
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

const classIdFromHash = () => Number(window.location.hash.slice(1)) || null;

export function ClassesPanel() {
  const t = useTranslations("Teacher.classes");
  const tCommon = useTranslations("Teacher.common");
  const { workspace, reload: reloadWorkspace } = useWorkspace();
  const { state, reload } = useLoad(listClasses, "classes");
  const [dialog, setDialog] = useState<Classroom | "new" | null>(null);
  const [removing, setRemoving] = useState<Classroom | null>(null);
  const [openId, setOpenId] = useState<number | null>(null);
  const readOnly = workspace.access.read_only;

  // The open class lives in the address, so a refresh or the back button keeps it.
  useEffect(() => {
    const sync = () => setOpenId(classIdFromHash());
    sync();
    window.addEventListener("hashchange", sync);
    return () => window.removeEventListener("hashchange", sync);
  }, []);

  function refresh() {
    setDialog(null);
    reload();
    reloadWorkspace();
  }

  if (openId !== null) {
    return (
      <ClassDetail
        classId={openId}
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
            <li key={classroom.id} className="rounded-card border border-line bg-bg p-4">
              <a
                href={`#${classroom.id}`}
                className="text-[17px] font-semibold text-navy-deep hover:underline"
              >
                {classroom.name}
              </a>
              <p className="mt-1 text-sm text-ink-soft">
                {[classroom.subject, classroom.grade].filter(Boolean).join(" · ") || " "}
              </p>
              <p className="mt-2 text-sm text-ink">
                {t("studentCount", { count: classroom.student_count })}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <a href={`#${classroom.id}`} className={buttonVariants({ size: "sm" })}>
                  {t("open")}
                </a>
                {!readOnly && (
                  <>
                    <Button variant="outline" size="sm" onClick={() => setDialog(classroom)}>
                      {tCommon("edit")}
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => setRemoving(classroom)}>
                      {tCommon("delete")}
                    </Button>
                  </>
                )}
              </div>
            </li>
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
