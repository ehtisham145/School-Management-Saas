"use client";

import { useState, type FormEvent } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { createSchool } from "../api";
import type { CreateSchoolRequest, PlatformSchool } from "../schemas";

const EMPTY_FORM: CreateSchoolRequest = { name_en: "", name_ar: "", code: "", admin_email: "" };

type FieldErrors = Partial<Record<keyof CreateSchoolRequest, string>>;

function toFieldErrors(fields: Record<string, unknown> = {}): FieldErrors {
  const errors: FieldErrors = {};
  for (const name of Object.keys(EMPTY_FORM) as (keyof CreateSchoolRequest)[]) {
    const messages = fields[name];
    if (Array.isArray(messages) && messages.length > 0) {
      errors[name] = String(messages[0]);
    } else if (typeof messages === "string") {
      errors[name] = messages;
    }
  }
  return errors;
}

type SchoolFormProps = {
  onCreated: (school: PlatformSchool) => void;
  onCancel: () => void;
};

export function SchoolForm({ onCreated, onCancel }: SchoolFormProps) {
  const t = useTranslations("Platform.form");

  const [form, setForm] = useState(EMPTY_FORM);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [hasGenericError, setHasGenericError] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFieldErrors({});
    setHasGenericError(false);
    setIsSubmitting(true);

    try {
      onCreated(await createSchool(form));
    } catch (err) {
      const errors = err instanceof ApiError ? toFieldErrors(err.fields) : {};
      setFieldErrors(errors);
      setHasGenericError(Object.keys(errors).length === 0);
    } finally {
      setIsSubmitting(false);
    }
  }

  function field(name: keyof CreateSchoolRequest, label: string, hint?: string) {
    const error = fieldErrors[name];
    const isEmail = name === "admin_email";
    const isLatin = isEmail || name === "code" || name === "name_en";

    return (
      <div className="flex flex-col gap-1.5">
        <label htmlFor={name} className="text-sm font-medium">
          {label}
        </label>
        <Input
          id={name}
          name={name}
          type={isEmail ? "email" : "text"}
          dir={isLatin ? "ltr" : "rtl"}
          required
          maxLength={name === "code" ? 30 : 200}
          aria-invalid={Boolean(error)}
          value={form[name]}
          onChange={(event) => setForm((current) => ({ ...current, [name]: event.target.value }))}
        />
        {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">{t("description")}</p>

      {field("name_en", t("nameEn"))}
      {field("name_ar", t("nameAr"))}
      {field("code", t("code"), t("codeHint"))}
      {field("admin_email", t("adminEmail"))}

      {hasGenericError && (
        <p role="alert" className="text-sm text-destructive">
          {t("errors.generic")}
        </p>
      )}

      <div className="flex gap-2">
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? t("submitting") : t("submit")}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel}>
          {t("cancel")}
        </Button>
      </div>
    </form>
  );
}
