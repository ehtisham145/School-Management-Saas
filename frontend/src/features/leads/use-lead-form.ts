"use client";

import { useState, type ChangeEvent, type FormEvent } from "react";
import { useTranslations } from "next-intl";
import { ApiError } from "@/lib/api";

export type ErrorKey = "required" | "email" | "phone" | "tooLong" | "invalid";
type Validators<F> = Partial<Record<keyof F, (value: string) => ErrorKey | null>>;

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_PATTERN = /^\+?[0-9][0-9\s-]{5,28}$/;

export const required = (max: number) => (value: string) => {
  if (!value.trim()) return "required";
  return value.length > max ? "tooLong" : null;
};
export const optional = (max: number) => (value: string) => (value.length > max ? "tooLong" : null);
export const email = (value: string) => {
  if (!value.trim()) return "required";
  return EMAIL_PATTERN.test(value.trim()) ? null : "email";
};
export const phone = (value: string) =>
  !value.trim() || PHONE_PATTERN.test(value.trim()) ? null : "phone";

type UseLeadFormOptions<F extends Record<string, string>> = {
  initial: F;
  validators: Validators<F>;
  submit: (values: F) => Promise<void>;
  onSuccess: (values: F) => void;
};

/** Shared state for the public forms: live validation, saving and server errors. */
export function useLeadForm<F extends Record<string, string>>({
  initial,
  validators,
  submit,
  onSuccess,
}: UseLeadFormOptions<F>) {
  const t = useTranslations("Leads.errors");

  const [values, setValues] = useState(initial);
  const [touched, setTouched] = useState<Partial<Record<keyof F, boolean>>>({});
  const [serverErrors, setServerErrors] = useState<Partial<Record<keyof F, boolean>>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function errorKeyFor(name: keyof F): ErrorKey | null {
    return validators[name]?.(values[name]) ?? (serverErrors[name] ? "invalid" : null);
  }

  function errorFor(name: keyof F) {
    const key = touched[name] ? errorKeyFor(name) : null;
    return key ? t(key) : undefined;
  }

  function bind(name: keyof F & string) {
    const error = errorFor(name);
    return {
      id: `lead-${name}`,
      name,
      value: values[name],
      "aria-invalid": Boolean(error),
      "aria-describedby": error ? `lead-${name}-error` : undefined,
      onChange: (
        event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>,
      ) => {
        setValues((current) => ({ ...current, [name]: event.target.value }));
        setServerErrors((current) => ({ ...current, [name]: false }));
      },
      onBlur: () => setTouched((current) => ({ ...current, [name]: true })),
    };
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    const names = Object.keys(values) as (keyof F)[];
    setTouched(Object.fromEntries(names.map((name) => [name, true])) as Record<keyof F, boolean>);

    const firstInvalid = names.find((name) => validators[name]?.(values[name]));
    if (firstInvalid) {
      event.currentTarget.querySelector<HTMLElement>(`[name="${String(firstInvalid)}"]`)?.focus();
      return;
    }

    setSaving(true);
    try {
      await submit(values);
      onSuccess(values);
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setFormError(t("rateLimited"));
      } else if (err instanceof ApiError && err.fields && Object.keys(err.fields).length > 0) {
        setServerErrors(
          Object.fromEntries(Object.keys(err.fields).map((name) => [name, true])) as Partial<
            Record<keyof F, boolean>
          >,
        );
      } else {
        setFormError(t("generic"));
      }
    } finally {
      setSaving(false);
    }
  }

  return { values, bind, errorFor, formError, saving, handleSubmit };
}
