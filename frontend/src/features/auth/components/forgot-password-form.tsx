"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { ApiError } from "@/lib/api";
import {
  email,
  newPassword,
  repeats,
  sanitizeCode,
  sixDigitCode,
  useValidatedForm,
} from "@/lib/use-validated-form";
import { confirmPasswordReset, requestPasswordReset } from "../api";
import type { AuthenticatedResponse } from "../schemas";
import { CodeInput } from "./code-input";

type ForgotPasswordFormProps = {
  onResponse: (response: AuthenticatedResponse) => void;
  onBack: () => void;
};

function EmailStep({ onSent, onBack }: { onSent: (address: string) => void; onBack: () => void }) {
  const t = useTranslations("Auth.forgotPassword");
  const tAuth = useTranslations("Auth");

  const form = useValidatedForm({
    initial: { email: "" },
    idPrefix: "",
    validators: { email },
    submit: async (values) => {
      await requestPasswordReset(values.email.trim());
    },
    onSuccess: (values) => onSent(values.email.trim()),
    describeError: (err) => {
      if (err instanceof ApiError && err.status === 429) return t("errors.rateLimited");
      return t("errors.generic");
    },
  });

  return (
    <form onSubmit={form.handleSubmit} noValidate className="flex flex-col gap-3">
      <Field id="email" label={t("emailLabel")} required error={form.errorFor("email")}>
        <Input
          {...form.bind("email")}
          type="email"
          dir="ltr"
          autoComplete="email"
          className="rtl:text-end"
        />
      </Field>

      {form.formError && (
        <p role="alert" className="text-sm text-red-700">
          {form.formError}
        </p>
      )}

      <Button type="submit" loading={form.saving}>
        {t("sendCode")}
      </Button>
      <Button type="button" variant="ghost" onClick={onBack}>
        {tAuth("backToLogin")}
      </Button>
    </form>
  );
}

const RESEND_COOLDOWN_SECONDS = 30;

function ResetStep({
  address,
  onResponse,
  onChangeEmail,
}: {
  address: string;
  onResponse: (response: AuthenticatedResponse) => void;
  onChangeEmail: () => void;
}) {
  const t = useTranslations("Auth.forgotPassword");
  const tLogin = useTranslations("Auth.login");
  const [step, setStep] = useState<"code" | "password">("code");
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
      await requestPasswordReset(address);
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
    initial: { code: "", password: "", confirm: "" },
    idPrefix: "reset-",
    validateWhileTyping: true,
    validators: { code: sixDigitCode, password: newPassword, confirm: repeats("password") },
    sanitizers: { code: sanitizeCode },
    submit: async (values) =>
      onResponse(
        await confirmPasswordReset({
          email: address,
          code: values.code,
          password: values.password,
        }),
      ),
    describeError: (err) => {
      if (err instanceof ApiError && err.status === 429) return t("errors.rateLimited");
      if (err instanceof ApiError && err.status === 401) {
        // The code turned out wrong or expired: go back where it can be fixed.
        setStep("code");
        return t("errors.invalidCode");
      }
      // A 400 here is a weak password: let it surface inline under that field instead.
      if (err instanceof ApiError && err.status === 400) return null;
      return t("errors.generic");
    },
    describeFieldError: (name) => (name === "password" ? t("errors.weak") : null),
  });

  function handleContinue() {
    // Re-applying the same value marks the field touched, so an empty/short
    // code shows its error now instead of only after a submit attempt.
    form.setValue("code", form.values.code);
    if (sixDigitCode(form.values.code) === null) setStep("password");
  }

  return (
    <form onSubmit={form.handleSubmit} noValidate className="flex flex-col gap-3">
      {step === "code" ? (
        <>
          <p className="text-sm text-ink-soft">
            {t.rich("codeSent", { email: () => <bdi>{address}</bdi> })}
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

          <Button type="button" onClick={handleContinue}>
            {t("continue")}
          </Button>
        </>
      ) : (
        <>
          <Field
            id="reset-password"
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
            id="reset-confirm"
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

          {form.formError && (
            <p role="alert" className="text-sm text-red-700">
              {form.formError}
            </p>
          )}

          <Button type="submit" loading={form.saving}>
            {form.saving ? t("submitting") : t("submit")}
          </Button>
        </>
      )}
      <Button type="button" variant="ghost" onClick={onChangeEmail}>
        {t("changeEmail")}
      </Button>
    </form>
  );
}

export function ForgotPasswordForm({ onResponse, onBack }: ForgotPasswordFormProps) {
  const [address, setAddress] = useState<string | null>(null);

  if (address === null) {
    return <EmailStep onSent={setAddress} onBack={onBack} />;
  }

  return (
    <ResetStep address={address} onResponse={onResponse} onChangeEmail={() => setAddress(null)} />
  );
}
