"use client";

import { useState, type ChangeEvent, type FocusEvent, type FormEvent } from "react";
import { useTranslations } from "next-intl";
import { ApiError } from "@/lib/api";

export type ErrorKey = "required" | "email" | "phone" | "code" | "tooLong" | "invalid";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const SAUDI_MOBILE_PATTERN = /^(?:\+?966|0)?5[0-9]{8}$/;
const ARABIC_DIGITS = /[٠-٩۰-۹]/g;

/** Turns Arabic-Indic digits into 0-9, so Arabic keyboards work. */
export const toLatinDigits = (value: string) =>
  value.replace(ARABIC_DIGITS, (digit) => {
    const code = digit.charCodeAt(0);
    return String(code >= 0x06f0 ? code - 0x06f0 : code - 0x0660);
  });

/** Only digits, +, spaces and dashes can be typed. */
export const sanitizePhone = (value: string) => toLatinDigits(value).replace(/[^0-9+\s-]/g, "");
export const sanitizeCode = (value: string) => toLatinDigits(value).replace(/[^0-9]/g, "");

export const required = (max: number) => (value: string) => {
  if (!value.trim()) return "required";
  return value.length > max ? "tooLong" : null;
};
export const optional = (max: number) => (value: string) => (value.length > max ? "tooLong" : null);
export const email = (value: string) => {
  if (!value.trim()) return "required";
  return EMAIL_PATTERN.test(value.trim()) ? null : "email";
};
export const saudiMobile = (value: string) =>
  !value.trim() || SAUDI_MOBILE_PATTERN.test(value.replace(/[\s-]/g, "")) ? null : "phone";
export const sixDigitCode = (value: string) => {
  if (!value) return "required";
  return /^[0-9]{6}$/.test(value) ? null : "code";
};

type Options<F extends Record<string, string>> = {
  initial: F;
  validators: Partial<Record<keyof F, (value: string) => ErrorKey | null>>;
  sanitizers?: Partial<Record<keyof F, (value: string) => string>>;
  idPrefix?: string;
  submit: (values: F) => Promise<void>;
  onSuccess?: (values: F) => void;
  /** Returns the message for an error this form understands, such as a wrong password. */
  describeError?: (error: unknown) => string | null;
};

function bringIntoView(form: HTMLFormElement, name: string) {
  const field = form.querySelector<HTMLElement>(`[name="${name}"]`);
  if (!field) return;

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  field.scrollIntoView({ block: "center", behavior: reduced ? "auto" : "smooth" });
  field.focus({ preventScroll: true });
}

/**
 * Shared form behaviour: an error appears once a field has been visited and
 * disappears as soon as the value is valid. Submitting a form with errors
 * scrolls to the first one.
 */
export function useValidatedForm<F extends Record<string, string>>({
  initial,
  validators,
  sanitizers,
  idPrefix = "lead-",
  submit,
  onSuccess,
  describeError,
}: Options<F>) {
  const t = useTranslations("Leads.errors");

  const [values, setValues] = useState(initial);
  const [touched, setTouched] = useState<Partial<Record<keyof F, boolean>>>({});
  const [serverErrors, setServerErrors] = useState<Partial<Record<keyof F, boolean>>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function errorFor(name: keyof F) {
    if (!touched[name]) return undefined;
    const key = validators[name]?.(values[name]) ?? (serverErrors[name] ? "invalid" : null);
    return key ? t(key) : undefined;
  }

  function bind(name: keyof F & string) {
    const error = errorFor(name);
    const id = `${idPrefix}${name}`;
    return {
      id,
      name,
      value: values[name],
      "aria-required": validators[name]?.("") ? true : undefined,
      "aria-invalid": Boolean(error),
      "aria-describedby": error ? `${id}-error` : undefined,
      onChange: (
        event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>,
      ) => {
        const sanitize = sanitizers?.[name];
        const value = sanitize ? sanitize(event.target.value) : event.target.value;
        setValues((current) => ({ ...current, [name]: value }));
        setServerErrors((current) => ({ ...current, [name]: false }));
        setFormError(null);
      },
      onBlur: (event: FocusEvent<HTMLElement>) => {
        // Showing an error here would move the submit button from under the click.
        const next = event.relatedTarget;
        if (next instanceof HTMLButtonElement && next.type === "submit") return;
        setTouched((current) => ({ ...current, [name]: true }));
      },
    };
  }

  function reset(next: F = initial) {
    setValues(next);
    setTouched({});
    setServerErrors({});
    setFormError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    setFormError(null);

    const names = Object.keys(values) as (keyof F & string)[];
    setTouched(Object.fromEntries(names.map((name) => [name, true])) as Record<keyof F, boolean>);

    const firstInvalid = names.find((name) => validators[name]?.(values[name]));
    if (firstInvalid) {
      bringIntoView(form, firstInvalid);
      return;
    }

    setSaving(true);
    try {
      await submit(values);
      onSuccess?.(values);
    } catch (err) {
      const message = describeError?.(err);
      const invalid =
        err instanceof ApiError ? names.filter((name) => err.fields && name in err.fields) : [];

      if (message) {
        setFormError(message);
      } else if (err instanceof ApiError && err.status === 429) {
        setFormError(t("rateLimited"));
      } else if (invalid.length > 0) {
        setServerErrors(
          Object.fromEntries(invalid.map((name) => [name, true])) as Record<keyof F, boolean>,
        );
        bringIntoView(form, invalid[0]);
      } else {
        setFormError(t("generic"));
      }
    } finally {
      setSaving(false);
    }
  }

  return { values, bind, errorFor, formError, saving, handleSubmit, reset };
}
