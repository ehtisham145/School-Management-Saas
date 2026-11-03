"use client";

import { useState, type FormEvent } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
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

  const [code, setCode] = useState("");
  const [isReset, setIsReset] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<ErrorKey | null>(null);

  async function submit(action: () => Promise<void>) {
    setError(null);
    setIsSubmitting(true);

    try {
      await action();
    } catch (err) {
      setError(toErrorKey(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const verify = isReset ? confirmTotpReset : verifyTotp;
    void submit(async () => onAuthenticated(await verify(code)));
  }

  function startReset() {
    void submit(async () => {
      await requestTotpReset();
      setIsReset(true);
      setCode("");
    });
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">
        {isReset ? t("resetDescription") : t("description")}
      </p>

      <CodeInput
        id="totp-code"
        label={isReset ? t("resetCodeLabel") : t("codeLabel")}
        value={code}
        onChange={setCode}
      />

      {error && (
        <p role="alert" className="text-sm text-destructive">
          {t(`errors.${error}`)}
        </p>
      )}

      <Button type="submit" disabled={isSubmitting}>
        {t("verify")}
      </Button>

      {!isReset && (
        <Button type="button" variant="ghost" disabled={isSubmitting} onClick={startReset}>
          {t("lostDevice")}
        </Button>
      )}

      <Button type="button" variant="ghost" onClick={onRestart}>
        {t("backToLogin")}
      </Button>
    </form>
  );
}
