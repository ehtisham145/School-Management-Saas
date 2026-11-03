"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { sanitizeCode, sixDigitCode, useValidatedForm } from "@/lib/use-validated-form";
import { confirmTotpReset, requestTotpReset, verifyTotp } from "../api";
import type { AuthenticatedResponse } from "../schemas";
import { CodeInput } from "./code-input";

type ErrorKey = "invalidCode" | "expired" | "noEmail" | "rateLimited" | "generic";

type TotpFormProps = {
  onAuthenticated: (response: AuthenticatedResponse) => void;
  onRestart: () => void;
};

function toErrorKey(err: unknown): ErrorKey {
  if (!(err instanceof ApiError)) return "generic";
  if (err.status === 429) return "rateLimited";
  if (err.code === "invalid_token") return "invalidCode";
  if (err.code === "no_pending_login") return "expired";
  if (err.code === "no_email") return "noEmail";
  return "generic";
}

export function TotpForm({ onAuthenticated, onRestart }: TotpFormProps) {
  const t = useTranslations("Auth.totp");

  const [isReset, setIsReset] = useState(false);
  const [requesting, setRequesting] = useState(false);
  const [resetError, setResetError] = useState<ErrorKey | null>(null);

  const form = useValidatedForm({
    initial: { code: "" },
    idPrefix: "totp-",
    validators: { code: sixDigitCode },
    sanitizers: { code: sanitizeCode },
    submit: async (values) => {
      const verify = isReset ? confirmTotpReset : verifyTotp;
      onAuthenticated(await verify(values.code));
    },
    describeError: (err) => t(`errors.${toErrorKey(err)}`),
  });

  async function startReset() {
    setResetError(null);
    setRequesting(true);
    try {
      await requestTotpReset();
      setIsReset(true);
      form.reset();
    } catch (err) {
      setResetError(toErrorKey(err));
    } finally {
      setRequesting(false);
    }
  }

  const message = form.formError ?? (resetError ? t(`errors.${resetError}`) : null);

  return (
    <form onSubmit={form.handleSubmit} noValidate className="flex flex-col gap-3">
      <p className="text-sm text-ink-soft">{isReset ? t("resetDescription") : t("description")}</p>

      <CodeInput
        {...form.bind("code")}
        label={isReset ? t("resetCodeLabel") : t("codeLabel")}
        error={form.errorFor("code")}
      />

      {message && (
        <p role="alert" className="text-sm text-red-700">
          {message}
        </p>
      )}

      <Button type="submit" loading={form.saving}>
        {t("verify")}
      </Button>

      {!isReset && (
        <Button type="button" variant="ghost" loading={requesting} onClick={startReset}>
          {t("lostDevice")}
        </Button>
      )}

      <Button type="button" variant="ghost" onClick={onRestart}>
        {t("backToLogin")}
      </Button>
    </form>
  );
}
