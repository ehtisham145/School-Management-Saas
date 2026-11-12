"use client";

import { useState, type ChangeEvent, type FocusEvent, type FormEvent } from "react";
import { useTranslations } from "next-intl";
import { ApiError } from "@/lib/api";

export type ErrorKey =
  | "required"
  | "email"
  | "phone"
  | "code"
  | "tooLong"
  | "invalid"
  | "digits"
  | "phoneCharacters"
  | "slugCharacters"
  | "saudiPhone"
  | "registrationNumber"
  | "students"
  | "englishName"
  | "arabicName"
  | "slug"
  | "money"
  | "moneyCharacters"
  | "percent"
  | "quantity"
  | "date"
  | "pastDate"
  | "choose"
  | "passwordShort"
  | "passwordNumeric"
  | "passwordMismatch"
  | "sameEmail";

/** Gets the field value, and every value of the form for checks that compare fields. */
type Validator = (value: string, all: Record<string, string>) => ErrorKey | null;

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const SAUDI_MOBILE_PATTERN = /^(?:\+?966|0)?5[0-9]{8}$/;
const SAUDI_PHONE_PATTERN = /^(?:\+?966|0)?[15][0-9]{8}$/;
const SLUG_PATTERN = /^[a-z0-9_-]+$/;
const ARABIC_LETTER = /[؀-ۿ]/;
const LATIN_LETTER = /[A-Za-z]/;
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
export const sanitizeDigits = sanitizeCode;
/** Letters and numbers in any language, spaces, - and /. */
export const sanitizeRegistrationNumber = (value: string) =>
  toLatinDigits(value).replace(/[^\p{L}\p{N} /-]/gu, "");
export const sanitizeSlug = (value: string) => value.toLowerCase().replace(/[^a-z0-9_-]/g, "");

export const required = (max: number) => (value: string) => {
  if (!value.trim()) return "required";
  return value.length > max ? "tooLong" : null;
};
/** Runs after the required check, so an empty field always says "required". */
const requiredAnd =
  (check: (trimmed: string) => ErrorKey | null): Validator =>
  (value) => {
    const trimmed = value.trim();
    return trimmed ? check(trimmed) : "required";
  };
const compactPhone = (value: string) => value.replace(/[\s-]/g, "");

export const requiredMobile = requiredAnd((value) =>
  SAUDI_MOBILE_PATTERN.test(compactPhone(value)) ? null : "phone",
);
export const optionalPhone = (value: string) =>
  !value.trim() || SAUDI_PHONE_PATTERN.test(compactPhone(value)) ? null : "saudiPhone";
export const slug = (max: number) =>
  requiredAnd((value) => {
    if (value.length > max) return "tooLong";
    return SLUG_PATTERN.test(value) ? null : "slug";
  });
export const optionalSlug = (max: number) => (value: string) => {
  if (!value.trim()) return null;
  if (value.length > max) return "tooLong";
  return SLUG_PATTERN.test(value) ? null : "slug";
};
export const englishName = (max: number) =>
  requiredAnd((value) => {
    if (value.length > max) return "tooLong";
    return LATIN_LETTER.test(value) && !ARABIC_LETTER.test(value) ? null : "englishName";
  });
export const arabicName = (max: number) =>
  requiredAnd((value) => {
    if (value.length > max) return "tooLong";
    return ARABIC_LETTER.test(value) ? null : "arabicName";
  });
export const optionalArabicName = (max: number) => (value: string) => {
  if (!value.trim()) return null;
  if (value.length > max) return "tooLong";
  return ARABIC_LETTER.test(value) ? null : "arabicName";
};
export const optionalRegistrationNumber = (max: number) => (value: string) => {
  if (!value.trim()) return null;
  if (value.length > max) return "tooLong";
  return /[\p{L}\p{N}]/u.test(value) ? null : "registrationNumber";
};
export const wholeNumberInRange = (min: number, max: number, error: ErrorKey) =>
  requiredAnd((value) => {
    const number = Number(value);
    return number >= min && number <= max ? null : error;
  });
export const optional = (max: number) => (value: string) => (value.length > max ? "tooLong" : null);

/** Riyals with up to 2 decimals, below a billion. Matches the API's money fields. */
const MONEY_PATTERN = /^\d{1,9}(\.\d{1,2})?$/;
const PERCENT_PATTERN = /^\d{1,3}(\.\d{1,2})?$/;
const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

/** Digits and one decimal point, so an amount can be typed with an Arabic keyboard too. */
export const sanitizeMoney = (value: string) =>
  toLatinDigits(value)
    .replace(/[٫،,]/g, ".")
    .replace(/[^0-9.]/g, "")
    .replace(/(\..*)\./g, "$1");

export const money = requiredAnd((value) => (MONEY_PATTERN.test(value) ? null : "money"));
export const optionalMoney = (value: string) =>
  !value.trim() || MONEY_PATTERN.test(value.trim()) ? null : "money";
export const percent = requiredAnd((value) =>
  PERCENT_PATTERN.test(value) && Number(value) <= 100 ? null : "percent",
);
export const optionalWholeNumber =
  (min: number, max: number, error: ErrorKey) => (value: string) => {
    if (!value.trim()) return null;
    const number = Number(value);
    return Number.isInteger(number) && number >= min && number <= max ? null : error;
  };
export const requiredChoice = (value: string) => (value ? null : "choose");
export const requiredDate = requiredAnd((value) => (DATE_PATTERN.test(value) ? null : "date"));
/** Today in Saudi Arabia, as the API compares dates there. */
export const todayInRiyadh = () =>
  new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Riyadh" }).format(new Date());
export const dateFromToday = requiredAnd((value) => {
  if (!DATE_PATTERN.test(value)) return "date";
  return value < todayInRiyadh() ? "pastDate" : null;
});
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

/** Matches the server's minimum; the server also rejects common passwords. */
export const PASSWORD_MIN_LENGTH = 10;
export const newPassword = (value: string) => {
  if (!value) return "required";
  if (value.length < PASSWORD_MIN_LENGTH) return "passwordShort";
  if (/^[0-9]+$/.test(value)) return "passwordNumeric";
  return value.length > 128 ? "tooLong" : null;
};
/** The value must repeat another field, such as a password confirmation. */
export const repeats =
  (field: string): Validator =>
  (value, all) => {
    if (!value) return "required";
    return value === all[field] ? null : "passwordMismatch";
  };
/** An email that must not be the same as the one in another field. */
export const emailOtherThan =
  (field: string): Validator =>
  (value, all) => {
    const error = email(value);
    if (error) return error;
    const other = all[field]?.trim().toLowerCase();
    return other && other === value.trim().toLowerCase() ? "sameEmail" : null;
  };

type Options<F extends Record<string, string>> = {
  initial: F;
  validators: Partial<Record<keyof F, Validator>>;
  sanitizers?: Partial<Record<keyof F, (value: string) => string>>;
  /** The warning to show at once when a sanitizer removes a typed character. */
  rejectedInputErrors?: Partial<Record<keyof F, ErrorKey>>;
  /** Checks a field from the first keystroke, instead of waiting until it loses focus. */
  validateWhileTyping?: boolean;
  idPrefix?: string;
  submit: (values: F) => Promise<void>;
  onSuccess?: (values: F) => void;
  /** Returns the message for an error this form understands, such as a wrong password. */
  describeError?: (error: unknown) => string | null;
  /** Returns the message for a server error on one field, in place of the general one. */
  describeFieldError?: (name: keyof F) => string | null;
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
  rejectedInputErrors,
  validateWhileTyping = false,
  idPrefix = "lead-",
  submit,
  onSuccess,
  describeError,
  describeFieldError,
}: Options<F>) {
  const t = useTranslations("Leads.errors");

  const [values, setValues] = useState(initial);
  const [touched, setTouched] = useState<Partial<Record<keyof F, boolean>>>({});
  const [rejected, setRejected] = useState<Partial<Record<keyof F, boolean>>>({});
  const [serverErrors, setServerErrors] = useState<Partial<Record<keyof F, boolean>>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function errorFor(name: keyof F) {
    const rejectedKey: ErrorKey | undefined = rejected[name]
      ? rejectedInputErrors?.[name]
      : undefined;
    if (rejectedKey) return t(rejectedKey);
    if (!touched[name]) return undefined;

    const key: ErrorKey | null | undefined = validators[name]?.(values[name], values);
    if (key) return t(key);
    if (!serverErrors[name]) return undefined;
    return describeFieldError?.(name) ?? t("invalid");
  }

  function setValue(name: keyof F & string, value: string) {
    setValues((current) => ({ ...current, [name]: value }));
    setServerErrors((current) => ({ ...current, [name]: false }));
    setFormError(null);
    if (validateWhileTyping) setTouched((current) => ({ ...current, [name]: true }));
  }

  function bind(name: keyof F & string) {
    const error = errorFor(name);
    const id = `${idPrefix}${name}`;
    return {
      id,
      name,
      value: values[name],
      "aria-required": validators[name]?.("", values) ? true : undefined,
      "aria-invalid": Boolean(error),
      "aria-describedby": error ? `${id}-error` : undefined,
      onChange: (
        event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>,
      ) => {
        const typed = event.target.value;
        const sanitize = sanitizers?.[name];
        const value = sanitize ? sanitize(typed) : typed;
        // Compares lengths, because a sanitizer may also convert what it keeps.
        setRejected((current) => ({ ...current, [name]: value.length < typed.length }));
        setValue(name, value);
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
    setRejected({});
    setServerErrors({});
    setFormError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    setFormError(null);
    setRejected({});

    const names = Object.keys(values) as (keyof F & string)[];
    setTouched(Object.fromEntries(names.map((name) => [name, true])) as Record<keyof F, boolean>);

    const firstInvalid = names.find((name) => validators[name]?.(values[name], values));
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

  return { values, bind, setValue, errorFor, formError, saving, handleSubmit, reset };
}
