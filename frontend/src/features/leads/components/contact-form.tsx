"use client";

import { useState } from "react";
import { CircleCheck } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { email, optional, required, useValidatedForm } from "@/lib/use-validated-form";
import { createContactMessage } from "../api";
import { Honeypot } from "./honeypot";

function ContactFields({ onSent }: { onSent: (sent: { name: string; email: string }) => void }) {
  const t = useTranslations("Leads");

  const form = useValidatedForm({
    initial: { name: "", school_name: "", email: "", message: "", website: "" },
    validators: {
      name: required(120),
      school_name: optional(200),
      email,
      message: required(2000),
    },
    submit: async (values) => {
      await createContactMessage(values);
    },
    onSuccess: (values) => onSent({ name: values.name, email: values.email }),
  });

  return (
    <form onSubmit={form.handleSubmit} noValidate className="relative flex flex-col gap-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field id="lead-name" label={t("fields.name")} required error={form.errorFor("name")}>
          <Input {...form.bind("name")} autoComplete="name" placeholder={t("placeholders.name")} />
        </Field>
        <Field
          id="lead-school_name"
          label={t("fields.schoolOptional")}
          error={form.errorFor("school_name")}
        >
          <Input
            {...form.bind("school_name")}
            autoComplete="organization"
            placeholder={t("placeholders.school")}
          />
        </Field>
      </div>
      <Field id="lead-email" label={t("fields.email")} required error={form.errorFor("email")}>
        <Input
          {...form.bind("email")}
          type="email"
          dir="ltr"
          autoComplete="email"
          placeholder={t("placeholders.email")}
          className="rtl:text-end"
        />
      </Field>
      <Field
        id="lead-message"
        label={t("fields.message")}
        required
        error={form.errorFor("message")}
      >
        <Textarea {...form.bind("message")} rows={5} placeholder={t("placeholders.message")} />
      </Field>
      <Honeypot label={t("fields.website")} {...form.bind("website")} id="lead-website" />

      {form.formError && (
        <p role="alert" className="rounded-control bg-red-50 p-3 text-sm text-red-800">
          {form.formError}
        </p>
      )}

      <Button type="submit" loading={form.saving} className="w-full sm:w-fit">
        {form.saving ? t("contact.submitting") : t("contact.submit")}
      </Button>
    </form>
  );
}

export function ContactForm() {
  const t = useTranslations("Leads.contact");
  const [sent, setSent] = useState<{ name: string; email: string } | null>(null);

  if (sent) {
    return (
      <div role="status" className="flex flex-col items-center gap-3 py-8 text-center">
        <CircleCheck aria-hidden="true" className="size-12 text-emerald-600" />
        <h3 className="text-lg text-navy-deep">{t("successTitle")}</h3>
        <p className="text-sm text-ink-soft">
          {t.rich("successBody", {
            name: () => <bdi>{sent.name}</bdi>,
            email: () => <bdi>{sent.email}</bdi>,
          })}
        </p>
        <Button variant="outline" className="mt-2" onClick={() => setSent(null)}>
          {t("another")}
        </Button>
      </div>
    );
  }

  return <ContactFields onSent={setSent} />;
}
