"use client";

import { useState } from "react";
import { CircleCheck } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  email,
  optional,
  required,
  sanitizePhone,
  saudiMobile,
  useValidatedForm,
} from "@/lib/use-validated-form";
import { createDemoRequest, PLANS, type Plan } from "../api";
import { Honeypot } from "./honeypot";

type DemoFormProps = {
  plan?: Plan;
  onClose: () => void;
};

const COMPACT = "h-10";

export function DemoForm({ plan, onClose }: DemoFormProps) {
  const t = useTranslations("Leads");
  const tPlans = useTranslations("Marketing.pricing");
  const [sent, setSent] = useState<{ name: string; email: string } | null>(null);

  const form = useValidatedForm({
    initial: {
      name: "",
      school_name: "",
      email: "",
      phone: "",
      plan: plan ?? "",
      message: "",
      website: "",
    },
    validators: {
      name: required(120),
      school_name: required(200),
      email,
      phone: saudiMobile,
      message: optional(2000),
    },
    sanitizers: { phone: sanitizePhone },
    submit: async (values) => {
      await createDemoRequest({ ...values, plan: values.plan as Plan | "" });
    },
    onSuccess: (values) => setSent({ name: values.name, email: values.email }),
  });

  if (sent) {
    return (
      <div role="status" className="flex flex-col items-center gap-3 py-4 text-center">
        <CircleCheck aria-hidden="true" className="size-12 text-emerald-600" />
        <h3 className="text-lg text-navy-deep">{t("demo.successTitle")}</h3>
        <p className="text-sm text-ink-soft">
          {t.rich("demo.successBody", {
            name: () => <bdi>{sent.name}</bdi>,
            email: () => <bdi>{sent.email}</bdi>,
          })}
        </p>
        <Button variant="outline" className="mt-2" onClick={onClose}>
          {t("demo.close")}
        </Button>
      </div>
    );
  }

  return (
    <form onSubmit={form.handleSubmit} noValidate className="relative flex flex-col gap-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <Field id="lead-name" label={t("fields.name")} required error={form.errorFor("name")}>
          <Input
            {...form.bind("name")}
            autoComplete="name"
            placeholder={t("placeholders.name")}
            autoFocus
            className={COMPACT}
          />
        </Field>
        <Field
          id="lead-school_name"
          label={t("fields.school")}
          required
          error={form.errorFor("school_name")}
        >
          <Input
            {...form.bind("school_name")}
            autoComplete="organization"
            placeholder={t("placeholders.school")}
            className={COMPACT}
          />
        </Field>
        <Field id="lead-email" label={t("fields.email")} required error={form.errorFor("email")}>
          <Input
            {...form.bind("email")}
            type="email"
            dir="ltr"
            autoComplete="email"
            placeholder={t("placeholders.email")}
            className={`${COMPACT} rtl:text-end`}
          />
        </Field>
        <Field id="lead-phone" label={t("fields.phone")} error={form.errorFor("phone")}>
          <Input
            {...form.bind("phone")}
            type="tel"
            dir="ltr"
            inputMode="tel"
            autoComplete="tel"
            maxLength={20}
            placeholder={t("placeholders.phone")}
            className={`${COMPACT} rtl:text-end`}
          />
        </Field>
      </div>
      <Field id="lead-plan" label={t("fields.plan")}>
        <Select {...form.bind("plan")} className={COMPACT}>
          <option value="">{t("fields.planNone")}</option>
          {PLANS.map((option) => (
            <option key={option} value={option}>
              {tPlans(`tiers.${option}.name`)}
            </option>
          ))}
        </Select>
      </Field>
      <Field id="lead-message" label={t("fields.demoMessage")} error={form.errorFor("message")}>
        <Textarea {...form.bind("message")} rows={2} placeholder={t("placeholders.demoMessage")} />
      </Field>
      <Honeypot label={t("fields.website")} {...form.bind("website")} id="lead-website" />

      {form.formError && (
        <p role="alert" className="rounded-control bg-red-50 p-3 text-sm text-red-800">
          {form.formError}
        </p>
      )}

      <Button type="submit" size="sm" loading={form.saving} className="w-full">
        {form.saving ? t("demo.submitting") : t("demo.submit")}
      </Button>
    </form>
  );
}
