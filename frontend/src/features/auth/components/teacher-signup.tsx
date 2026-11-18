"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Link, useRouter } from "@/i18n/navigation";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { ApiError } from "@/lib/api";
import {
  email,
  newPassword,
  repeats,
  required,
  sanitizeCode,
  sixDigitCode,
  useValidatedForm,
} from "@/lib/use-validated-form";
import { requestTeacherSignup, verifyTeacherSignup } from "../api";
import { toActiveSession, type TeacherSignupDetails } from "../schemas";
import { useSession } from "../session-store";
import { markFreshLogin } from "../welcome";
import { CodeInput } from "./code-input";

const NAME_MAX_LENGTH = 120;
const RESEND_COOLDOWN_SECONDS = 30;

function DetailsStep({
  initial,
  onSent,
}: {
  initial: TeacherSignupDetails | null;
  onSent: (details: TeacherSignupDetails) => void;
}) {
  const t = useTranslations("Auth.teacherSignup");
  const tLogin = useTranslations("Auth.login");

  const form = useValidatedForm({
    initial: {
      full_name: initial?.full_name ?? "",
      email: initial?.email ?? "",
      password: initial?.password ?? "",
      confirm: initial?.password ?? "",
      accept_privacy: initial ? "yes" : "",
      website: "",
    },
    idPrefix: "signup-",
    validateWhileTyping: true,
    validators: {
      full_name: required(NAME_MAX_LENGTH),
      email,
      password: newPassword,
      confirm: repeats("password"),
      accept_privacy: (value) => (value ? null : "acceptPrivacy"),
    },
    submit: async (values) => {
      const details = {
        full_name: values.full_name.trim(),
        email: values.email.trim(),
        password: values.password,
        accept_privacy: true as const,
      };
      await requestTeacherSignup({ ...details, website: values.website });
      onSent(details);
    },
    describeError: (err) => {
      if (err instanceof ApiError && err.status === 429) return t("errors.rateLimited");
      if (err instanceof ApiError && err.status === 400) return null;
      return t("errors.generic");
    },
    describeFieldError: (name) => (name === "password" ? t("errors.weak") : null),
  });

  const acceptError = form.errorFor("accept_privacy");

  return (
    <form onSubmit={form.handleSubmit} noValidate className="flex flex-col gap-3">
      <Field
        id="signup-full_name"
        label={t("fullNameLabel")}
        required
        error={form.errorFor("full_name")}
      >
        <Input {...form.bind("full_name")} autoComplete="name" maxLength={NAME_MAX_LENGTH} />
      </Field>

      <Field id="signup-email" label={t("emailLabel")} required error={form.errorFor("email")}>
        <Input
          {...form.bind("email")}
          type="email"
          dir="ltr"
          autoComplete="email"
          className="rtl:text-end"
        />
      </Field>

      <Field
        id="signup-password"
        label={t("passwordLabel")}
        required
        hint={t("passwordHint")}
        error={form.errorFor("password")}
      >
        <PasswordInput
          {...form.bind("password")}
          autoComplete="new-password"
          showLabel={tLogin("showPassword")}
          hideLabel={tLogin("hidePassword")}
        />
      </Field>

      <Field
        id="signup-confirm"
        label={t("confirmLabel")}
        required
        error={form.errorFor("confirm")}
      >
        <PasswordInput
          {...form.bind("confirm")}
          autoComplete="new-password"
          showLabel={tLogin("showPassword")}
          hideLabel={tLogin("hidePassword")}
        />
      </Field>

      {/* Hidden from people. Bots fill it in, and their request is ignored. */}
      <div aria-hidden="true" className="hidden">
        <input {...form.bind("website")} type="text" tabIndex={-1} autoComplete="off" />
      </div>

      <div>
        <label className="flex items-start gap-2.5 text-sm text-ink">
          <input
            id="signup-accept_privacy"
            name="accept_privacy"
            type="checkbox"
            checked={Boolean(form.values.accept_privacy)}
            onChange={(event) => form.setValue("accept_privacy", event.target.checked ? "yes" : "")}
            aria-invalid={Boolean(acceptError)}
            aria-describedby={acceptError ? "signup-accept_privacy-error" : undefined}
            className="mt-0.5 size-4 shrink-0 accent-navy"
          />
          <span>
            {t.rich("accept", {
              link: (chunks) => (
                <Link
                  href="/privacy"
                  target="_blank"
                  className="font-semibold text-navy underline underline-offset-2"
                >
                  {chunks}
                </Link>
              ),
            })}
          </span>
        </label>
        {acceptError && (
          <p id="signup-accept_privacy-error" role="alert" className="mt-1 text-sm text-red-700">
            {acceptError}
          </p>
        )}
      </div>

      {form.formError && (
        <p role="alert" className="text-sm text-red-700">
          {form.formError}
        </p>
      )}

      <Button type="submit" loading={form.saving}>
        {form.saving ? t("submitting") : t("submit")}
      </Button>
    </form>
  );
}

function CodeStep({
  details,
  onChangeDetails,
}: {
  details: TeacherSignupDetails;
  onChangeDetails: () => void;
}) {
  const t = useTranslations("Auth.teacherSignup");
  const router = useRouter();
  const { setSession } = useSession();
  const [cooldown, setCooldown] = useState(RESEND_COOLDOWN_SECONDS);
  const [resending, setResending] = useState(false);
  const [resendNotice, setResendNotice] = useState<string | null>(null);

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = window.setTimeout(() => setCooldown((current) => current - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [cooldown]);

  async function handleResend() {
    setResending(true);
    setResendNotice(null);
    try {
      await requestTeacherSignup(details);
      setResendNotice(t("codeResent"));
      setCooldown(RESEND_COOLDOWN_SECONDS);
    } catch (err) {
      setResendNotice(
        err instanceof ApiError && err.status === 429
          ? t("errors.rateLimited")
          : t("errors.generic"),
      );
    } finally {
      setResending(false);
    }
  }

  const form = useValidatedForm({
    initial: { code: "" },
    idPrefix: "signup-",
    validateWhileTyping: true,
    validators: { code: sixDigitCode },
    sanitizers: { code: sanitizeCode },
    rejectedInputErrors: { code: "digits" },
    submit: async (values) => {
      const response = await verifyTeacherSignup({ ...details, code: values.code });
      if (response.memberships.length > 0) setSession(toActiveSession(response.memberships[0]));
      markFreshLogin();
      router.push("/teacher");
    },
    describeError: (err) => {
      if (err instanceof ApiError && err.status === 429) return t("errors.rateLimited");
      if (err instanceof ApiError && err.status === 401) return t("errors.invalidCode");
      return t("errors.generic");
    },
  });

  return (
    <form onSubmit={form.handleSubmit} noValidate className="flex flex-col gap-3">
      <h2 className="text-lg text-navy-deep">{t("codeTitle")}</h2>
      <p className="text-sm text-ink-soft">
        {t.rich("codeSent", { email: () => <bdi>{details.email}</bdi> })}
      </p>

      <CodeInput {...form.bind("code")} label={t("codeLabel")} error={form.errorFor("code")} />

      <div className="flex items-center justify-between gap-3">
        {resendNotice ? <p className="text-sm text-ink-soft">{resendNotice}</p> : <span />}
        <Button
          type="button"
          variant="ghost"
          size="sm"
          loading={resending}
          disabled={cooldown > 0}
          onClick={handleResend}
        >
          {cooldown > 0 ? t("resendIn", { seconds: cooldown }) : t("resend")}
        </Button>
      </div>

      {form.formError && (
        <p role="alert" className="text-sm text-red-700">
          {form.formError}
        </p>
      )}

      <Button type="submit" loading={form.saving}>
        {form.saving ? t("verifying") : t("verify")}
      </Button>
      <Button type="button" variant="ghost" onClick={onChangeDetails}>
        {t("changeDetails")}
      </Button>
    </form>
  );
}

function SignupSteps() {
  const [details, setDetails] = useState<TeacherSignupDetails | null>(null);
  const [codeSent, setCodeSent] = useState(false);

  if (details && codeSent) {
    return <CodeStep details={details} onChangeDetails={() => setCodeSent(false)} />;
  }

  return (
    <DetailsStep
      initial={details}
      onSent={(sent) => {
        setDetails(sent);
        setCodeSent(true);
      }}
    />
  );
}

export function TeacherSignup() {
  const [resetKey, setResetKey] = useState(0);

  // Next.js keeps this page's state after navigating away (cacheComponents).
  // Start clean on return, so a typed password doesn't come back.
  useEffect(() => () => setResetKey((current) => current + 1), []);

  return <SignupSteps key={resetKey} />;
}
