"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { sanitizeCode, sixDigitCode, useValidatedForm } from "@/lib/use-validated-form";
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
  const [loadError, setLoadError] = useState<ErrorKey | null>(null);

  const form = useValidatedForm({
    initial: { code: "" },
    idPrefix: "totp-setup-",
    validators: { code: sixDigitCode },
    sanitizers: { code: sanitizeCode },
    submit: async (values) => confirmTotp(values.code),
    onSuccess: onDone,
    describeError: (err) => t(`errors.${toErrorKey(err)}`),
  });

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
          setLoadError(toErrorKey(err));
        }
      });

    return () => {
      cancelled = true;
    };
  }, [onDone]);

  return (
    <form onSubmit={form.handleSubmit} noValidate className="flex flex-col gap-3">
      <div>
        <h2 className="text-base text-navy-deep">{t("title")}</h2>
        <p className="text-sm text-ink-soft">{t("description")}</p>
      </div>

      {otpauthUrl ? (
        <>
          <div className="flex min-h-[200px] items-center justify-center rounded-lg bg-bg p-3">
            <QRCodeSVG value={otpauthUrl} size={176} />
          </div>
          <div className="text-xs text-ink-soft">
            <p>{t("manualKey")}</p>
            <code dir="ltr" className="mt-1 block font-mono break-all text-ink">
              {manualKeyFrom(otpauthUrl)}
            </code>
          </div>
          <CodeInput {...form.bind("code")} label={t("codeLabel")} error={form.errorFor("code")} />
          <Button type="submit" loading={form.saving}>
            {t("submit")}
          </Button>
        </>
      ) : (
        !loadError && <p className="text-sm text-ink-soft">{t("loading")}</p>
      )}

      {(form.formError || loadError) && (
        <p role="alert" className="text-sm text-red-700">
          {form.formError ?? t(`errors.${loadError ?? "generic"}`)}
        </p>
      )}
    </form>
  );
}
