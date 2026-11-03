"use client";

import { useState, type FormEvent } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { requestEmailOtp, verifyEmailOtp } from "../api";
import type { LoginResponse } from "../schemas";
import { CodeInput } from "./code-input";

type ErrorKey = "invalidCode" | "rateLimited" | "generic";

type EmailCodeFormProps = {
  onResponse: (response: LoginResponse) => void;
  onBack: () => void;
};

export function EmailCodeForm({ onResponse, onBack }: EmailCodeFormProps) {
  const t = useTranslations("Auth.emailCode");

  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [codeSent, setCodeSent] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<ErrorKey | null>(null);

  async function submit(action: () => Promise<void>) {
    setError(null);
    setIsSubmitting(true);

    try {
      await action();
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setError("rateLimited");
      } else if (err instanceof ApiError && err.status === 401) {
        setError("invalidCode");
      } else {
        setError("generic");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (codeSent) {
      void submit(async () => onResponse(await verifyEmailOtp(email, code)));
    } else {
      void submit(async () => {
        await requestEmailOtp(email);
        setCodeSent(true);
      });
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      {codeSent ? (
        <>
          <p className="text-sm text-muted-foreground">{t("codeSent", { email })}</p>
          <CodeInput id="email-code" label={t("codeLabel")} value={code} onChange={setCode} />
        </>
      ) : (
        <div className="flex flex-col gap-1.5">
          <label htmlFor="email" className="text-sm font-medium">
            {t("emailLabel")}
          </label>
          <Input
            id="email"
            name="email"
            type="email"
            dir="ltr"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>
      )}

      {error && (
        <p role="alert" className="text-sm text-destructive">
          {t(`errors.${error}`)}
        </p>
      )}

      <Button type="submit" disabled={isSubmitting}>
        {codeSent ? t("verify") : t("sendCode")}
      </Button>

      <Button
        type="button"
        variant="ghost"
        onClick={() => {
          if (codeSent) {
            setCodeSent(false);
            setCode("");
            setError(null);
          } else {
            onBack();
          }
        }}
      >
        {codeSent ? t("changeEmail") : t("usePassword")}
      </Button>
    </form>
  );
}
