"use client";

import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { LoadFeedback, PageHeader } from "@/features/platform/components/panel-ui";
import { useLoad } from "@/features/platform/use-load";
import { required, requiredChoice, useValidatedForm } from "@/lib/use-validated-form";
import { listClasses, listMessages, sendMessage } from "../api";
import {
  ErrorNote,
  Panel,
  UpgradeLink,
  useFormatDate,
  useTeacherError,
  useWorkspace,
} from "./teacher-ui";

function MessageForm({ onSent }: { onSent: () => void }) {
  const t = useTranslations("Teacher.messages");
  const describe = useTeacherError();
  const classes = useLoad(listClasses, "message-classes");
  const form = useValidatedForm({
    initial: { classroom: "", subject: "", body: "" },
    idPrefix: "message-",
    validators: { classroom: requiredChoice, subject: required(150), body: required(3000) },
    submit: async (values) => {
      await sendMessage({ ...values, classroom: Number(values.classroom) });
      form.reset();
    },
    onSuccess: onSent,
    describeError: describe,
    describeFieldError: (name) => (name === "classroom" ? t("noParents") : null),
  });

  return (
    <Panel title={t("new")}>
      <form onSubmit={form.handleSubmit} noValidate className="flex flex-col gap-3">
        <div className="grid gap-3 sm:grid-cols-2">
          <Field
            id="message-classroom"
            label={t("classroom")}
            required
            error={form.errorFor("classroom")}
          >
            <Select {...form.bind("classroom")} className="h-11">
              <option value="">{t("chooseClass")}</option>
              {classes.state.name === "ready" &&
                classes.state.data.map((classroom) => (
                  <option key={classroom.id} value={classroom.id}>
                    {classroom.name}
                  </option>
                ))}
            </Select>
          </Field>
          <Field
            id="message-subject"
            label={t("subject")}
            required
            error={form.errorFor("subject")}
          >
            <Input {...form.bind("subject")} />
          </Field>
        </div>
        <Field id="message-body" label={t("body")} required error={form.errorFor("body")}>
          <Textarea {...form.bind("body")} rows={5} />
        </Field>
        <ErrorNote message={form.formError} />
        <div>
          <Button type="submit" size="sm" loading={form.saving}>
            {form.saving ? t("sending") : t("send")}
          </Button>
        </div>
      </form>
    </Panel>
  );
}

export function MessagesPanel() {
  const t = useTranslations("Teacher.messages");
  const formatDate = useFormatDate();
  const { workspace } = useWorkspace();
  const { state, reload } = useLoad(listMessages, "messages");
  const isPro = workspace.limits.pro_features;

  return (
    <>
      <PageHeader title={t("title")} subtitle={t("subtitle")} />

      {!isPro && (
        <Panel>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-ink">{t("proOnly")}</p>
            <UpgradeLink />
          </div>
        </Panel>
      )}
      {isPro && !workspace.access.read_only && <MessageForm onSent={reload} />}

      <Panel title={t("sent")}>
        <LoadFeedback state={state} onRetry={reload} />
        {state.name === "ready" && state.data.count === 0 && (
          <EmptyState title={t("emptyTitle")} description={t("emptyHint")} />
        )}
        {state.name === "ready" && state.data.count > 0 && (
          <ul className="divide-y divide-line">
            {state.data.results.map((message) => (
              <li key={message.id} className="py-3">
                <p className="text-sm font-semibold text-ink">{message.subject}</p>
                <p className="mt-0.5 text-xs text-ink-soft">
                  {message.classroom_name} · {formatDate(message.created_at)} ·{" "}
                  {t("recipients", { count: message.recipient_count })}
                </p>
                <p className="mt-1.5 text-sm whitespace-pre-line text-ink-soft">{message.body}</p>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </>
  );
}
