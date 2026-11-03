"use client";

import dynamic from "next/dynamic";
import { useEffect, useState, type FormEvent } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { confirmTotp, setupTotp } from "../api";
import { CodeInput } from "./code-input";

// Only people setting up 2FA download the QR library.
const QRCodeSVG = dynamic(() => import("qrcode.react").then((module) => module.QRCodeSVG), {
  ssr: false,
});

type ErrorKey = "invalidCode" | "rateLimited" | "generic";

function toErrorKey(err: unknown): ErrorKey {
  if (err instanceof ApiError && err.status === 429) return "rateLimited";
  if (err instanceof ApiError && err.code === "invalid_token") return "invalidCode";
  return "generic";
}

function manualKeyFrom(otpauthUrl: string) {
  const secret = new URL(otpauthUrl).searchParams.get("secret") ?? "";
  return secret.match(/.{1,4}/g)?.join(" ") ?? secret;
}

export function TotpSetup({ onDone }: { onDone: () => void }) {
  const t = useTranslations("Auth.totpSetup");

  const [otpauthUrl, setOtpauthUrl] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<ErrorKey | null>(null);

  useEffect(() => {
    let cancelled = false;

    setupTotp()
      .then((result) => {
        if (!cancelled) setOtpauthUrl(result.otpauth_url);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.code === "already_enabled") {
          onDone();
        } else {
          setError(toErrorKey(err));
        }
      });

    return () => {
      cancelled = true;
    };
  }, [onDone]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await confirmTotp(code);
      onDone();
    } catch (err) {
      setError(toErrorKey(err));
      setCode("");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <div>
        <h2 className="text-base font-medium">{t("title")}</h2>
        <p className="text-sm text-muted-foreground">{t("description")}</p>
      </div>

      {otpauthUrl ? (
        <>
          <div className="flex justify-center rounded-lg bg-white p-3">
            <QRCodeSVG value={otpauthUrl} size={176} />
          </div>
          <div className="text-xs text-muted-foreground">
            <p>{t("manualKey")}</p>
            <code dir="ltr" className="mt-1 block font-mono break-all text-foreground">
              {manualKeyFrom(otpauthUrl)}
            </code>
          </div>
          <CodeInput id="totp-setup-code" label={t("codeLabel")} value={code} onChange={setCode} />
          <Button type="submit" disabled={isSubmitting}>
            {t("submit")}
          </Button>
        </>
      ) : (
        !error && <p className="text-sm text-muted-foreground">{t("loading")}</p>
      )}

      {error && (
        <p role="alert" className="text-sm text-destructive">
          {t(`errors.${error}`)}
        </p>
      )}
    </form>
  );
}
