"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { email, sanitizeCode, sixDigitCode, useValidatedForm } from "@/lib/use-validated-form";
import { requestEmailOtp, verifyEmailOtp } from "../api";
import type { LoginResponse } from "../schemas";
import { CodeInput } from "./code-input";

type EmailCodeFormProps = {
  onResponse: (response: LoginResponse) => void;
  onBack: () => void;
};

function useDescribeError() {
  const t = useTranslations("Auth.emailCode");

  return (err: unknown) => {
    if (err instanceof ApiError && err.status === 429) return t("errors.rateLimited");
    if (err instanceof ApiError && err.status === 401) return t("errors.invalidCode");
    return t("errors.generic");
  };
}

function EmailStep({ onSent, onBack }: { onSent: (address: string) => void; onBack: () => void }) {
  const t = useTranslations("Auth.emailCode");
  const describeError = useDescribeError();

  const form = useValidatedForm({
    initial: { email: "" },
    idPrefix: "",
    validators: { email },
    submit: async (values) => {
      await requestEmailOtp(values.email.trim());
    },
    onSuccess: (values) => onSent(values.email.trim()),
    describeError,
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
        {t("usePassword")}
      </Button>
    </form>
  );
}

function CodeStep({
  address,
  onResponse,
  onChangeEmail,
}: {
  address: string;
  onResponse: (response: LoginResponse) => void;
  onChangeEmail: () => void;
}) {
  const t = useTranslations("Auth.emailCode");
  const describeError = useDescribeError();

  const form = useValidatedForm({
    initial: { code: "" },
    idPrefix: "email-",
    validators: { code: sixDigitCode },
    sanitizers: { code: sanitizeCode },
    submit: async (values) => onResponse(await verifyEmailOtp(address, values.code)),
    describeError,
  });

  return (
    <form onSubmit={form.handleSubmit} noValidate className="flex flex-col gap-3">
      <p className="text-sm text-ink-soft">
        {t.rich("codeSent", { email: () => <bdi>{address}</bdi> })}
      </p>
      <CodeInput {...form.bind("code")} label={t("codeLabel")} error={form.errorFor("code")} />

      {form.formError && (
        <p role="alert" className="text-sm text-red-700">
          {form.formError}
        </p>
      )}

      <Button type="submit" loading={form.saving}>
        {t("verify")}
      </Button>
      <Button type="button" variant="ghost" onClick={onChangeEmail}>
        {t("changeEmail")}
      </Button>
    </form>
  );
}

export function EmailCodeForm({ onResponse, onBack }: EmailCodeFormProps) {
  const [address, setAddress] = useState<string | null>(null);

  if (address === null) {
    return <EmailStep onSent={setAddress} onBack={onBack} />;
  }

  return (
    <CodeStep address={address} onResponse={onResponse} onChangeEmail={() => setAddress(null)} />
  );
}
