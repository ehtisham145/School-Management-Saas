"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Table, TableCell, TableHead, TableHeaderCell, TableRow } from "@/components/ui/table";
import {
  arabicName,
  englishName,
  money,
  optionalWholeNumber,
  sanitizeDigits,
  sanitizeMoney,
  sanitizeSlug,
  slug,
  useValidatedForm,
} from "@/lib/use-validated-form";
import { createPlan, listPlans, updatePlan } from "../api";
import type { Plan } from "../schemas";
import { useLoad } from "../use-load";
import { LoadFeedback, localName, Money, Notice, PageHeader } from "./panel-ui";

const MAX_STUDENTS = 100_000;
const NAME_MAX = 100;
const CODE_MAX = 30;

function PlanDialog({
  plan,
  onClose,
  onSaved,
}: {
  plan: Plan | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const t = useTranslations("Platform.plans");
  const tCommon = useTranslations("Platform.common");
  const editing = plan !== null;

  const form = useValidatedForm({
    initial: {
      code: plan?.code ?? "",
      name_en: plan?.name_en ?? "",
      name_ar: plan?.name_ar ?? "",
      monthly_price: plan?.monthly_price ?? "",
      yearly_price: plan?.yearly_price ?? "",
      max_students: plan?.max_students?.toString() ?? "",
      is_active: plan === null || plan.is_active ? "true" : "false",
    },
    validators: {
      code: editing ? undefined : slug(CODE_MAX),
      name_en: englishName(NAME_MAX),
      name_ar: arabicName(NAME_MAX),
      monthly_price: money,
      yearly_price: money,
      max_students: optionalWholeNumber(1, MAX_STUDENTS, "students"),
    },
    sanitizers: {
      code: sanitizeSlug,
      monthly_price: sanitizeMoney,
      yearly_price: sanitizeMoney,
      max_students: sanitizeDigits,
    },
    rejectedInputErrors: {
      code: "slugCharacters",
      monthly_price: "moneyCharacters",
      yearly_price: "moneyCharacters",
      max_students: "digits",
    },
    validateWhileTyping: true,
    idPrefix: "plan-",
    submit: async (values) => {
      const body = {
        name_en: values.name_en.trim(),
        name_ar: values.name_ar.trim(),
        monthly_price: values.monthly_price,
        yearly_price: values.yearly_price,
        max_students: values.max_students ? Number(values.max_students) : null,
        is_active: values.is_active === "true",
      };
      if (plan) {
        await updatePlan(plan.id, body);
      } else {
        await createPlan({ ...body, code: values.code });
      }
    },
    onSuccess: onSaved,
  });

  return (
    <Modal
      open
      onClose={onClose}
      title={editing ? t("editTitle", { name: plan.name_en }) : t("newTitle")}
      description={t("formHint")}
      closeLabel={tCommon("close")}
    >
      <form onSubmit={form.handleSubmit} noValidate className="grid gap-3 sm:grid-cols-2">
        <Field
          id="plan-code"
          label={t("fields.code")}
          required={!editing}
          hint={editing ? t("fields.codeFixed") : t("fields.codeHint")}
          error={form.errorFor("code")}
        >
          <Input {...form.bind("code")} dir="ltr" disabled={editing} className="h-11" />
        </Field>
        <Field id="plan-is_active" label={t("fields.status")}>
          <Select {...form.bind("is_active")} className="h-11">
            <option value="true">{t("offered")}</option>
            <option value="false">{t("notOffered")}</option>
          </Select>
        </Field>
        <Field
          id="plan-name_en"
          label={t("fields.nameEn")}
          required
          error={form.errorFor("name_en")}
        >
          <Input {...form.bind("name_en")} dir="ltr" className="h-11" />
        </Field>
        <Field
          id="plan-name_ar"
          label={t("fields.nameAr")}
          required
          error={form.errorFor("name_ar")}
        >
          <Input {...form.bind("name_ar")} dir="rtl" className="h-11" />
        </Field>
        <Field
          id="plan-monthly_price"
          label={t("fields.monthlyPrice")}
          required
          error={form.errorFor("monthly_price")}
        >
          <Input {...form.bind("monthly_price")} inputMode="decimal" dir="ltr" className="h-11" />
        </Field>
        <Field
          id="plan-yearly_price"
          label={t("fields.yearlyPrice")}
          required
          error={form.errorFor("yearly_price")}
        >
          <Input {...form.bind("yearly_price")} inputMode="decimal" dir="ltr" className="h-11" />
        </Field>
        <Field
          id="plan-max_students"
          label={t("fields.maxStudents")}
          hint={t("fields.maxStudentsHint")}
          error={form.errorFor("max_students")}
        >
          <Input {...form.bind("max_students")} inputMode="numeric" dir="ltr" className="h-11" />
        </Field>

        {form.formError && (
          <p
            role="alert"
            className="rounded-control bg-red-50 p-3 text-sm text-red-800 sm:col-span-2"
          >
            {form.formError}
          </p>
        )}

        <div className="flex justify-end gap-2 sm:col-span-2">
          <Button type="button" variant="ghost" size="sm" onClick={onClose}>
            {tCommon("cancel")}
          </Button>
          <Button type="submit" size="sm" loading={form.saving}>
            {form.saving ? tCommon("saving") : tCommon("save")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export function PlansPanel() {
  const t = useTranslations("Platform.plans");
  const tCommon = useTranslations("Platform.common");
  const locale = useLocale();
  const plans = useLoad(listPlans, "plans");
  const [editing, setEditing] = useState<Plan | null | undefined>(undefined);
  const [savedNotice, setSavedNotice] = useState(false);

  function handleSaved() {
    setEditing(undefined);
    setSavedNotice(true);
    plans.reload();
  }

  return (
    <>
      <PageHeader
        title={t("title")}
        subtitle={t("subtitle")}
        action={
          <Button
            size="sm"
            onClick={() => {
              setSavedNotice(false);
              setEditing(null);
            }}
          >
            <Plus aria-hidden="true" />
            {t("new")}
          </Button>
        }
      />

      {savedNotice && <Notice tone="success">{t("saved")}</Notice>}

      <LoadFeedback state={plans.state} onRetry={plans.reload} />

      {plans.state.name === "ready" && plans.state.data.length === 0 && (
        <EmptyState title={t("empty")} description={t("emptyDescription")} />
      )}

      {plans.state.name === "ready" && plans.state.data.length > 0 && (
        <Table className="bg-bg">
          <TableHead>
            <TableRow>
              <TableHeaderCell>{t("columns.plan")}</TableHeaderCell>
              <TableHeaderCell>{t("columns.monthly")}</TableHeaderCell>
              <TableHeaderCell>{t("columns.yearly")}</TableHeaderCell>
              <TableHeaderCell>{t("columns.students")}</TableHeaderCell>
              <TableHeaderCell>{t("columns.subscriptions")}</TableHeaderCell>
              <TableHeaderCell>{t("columns.status")}</TableHeaderCell>
              <TableHeaderCell>{tCommon("actions")}</TableHeaderCell>
            </TableRow>
          </TableHead>
          <tbody>
            {plans.state.data.map((plan) => (
              <TableRow key={plan.id}>
                <TableCell>
                  <span className="block font-semibold text-ink">{localName(plan, locale)}</span>
                  <span className="block text-xs text-ink-soft" dir="ltr">
                    {plan.code}
                  </span>
                </TableCell>
                <TableCell>
                  <Money value={plan.monthly_price} locale={locale} />
                </TableCell>
                <TableCell>
                  <Money value={plan.yearly_price} locale={locale} />
                </TableCell>
                <TableCell>
                  {plan.max_students === null
                    ? t("unlimited")
                    : plan.max_students.toLocaleString(locale)}
                </TableCell>
                <TableCell>{plan.active_subscriptions.toLocaleString(locale)}</TableCell>
                <TableCell>
                  <Badge tone={plan.is_active ? "success" : "neutral"}>
                    {plan.is_active ? t("offered") : t("notOffered")}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setSavedNotice(false);
                      setEditing(plan);
                    }}
                  >
                    {tCommon("edit")}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </tbody>
        </Table>
      )}

      {editing !== undefined && (
        <PlanDialog
          key={editing?.id ?? "new"}
          plan={editing}
          onClose={() => setEditing(undefined)}
          onSaved={handleSaved}
        />
      )}
    </>
  );
}
