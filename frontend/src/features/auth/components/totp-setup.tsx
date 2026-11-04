"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { ArrowLeft, Check, ChevronDown, Copy, ShieldCheck } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "cn";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { sanitizeCode, sixDigitCode, useValidatedForm } from "@/lib/use-validated-form";
import { confirmTotp, setupTotp } from "../api";
import { CodeInput } from "./code-input";

const QR_SIZE = 176;

const QrPlaceholder = () => (
  <div
    aria-hidden="true"
    className="animate-pulse rounded-control bg-navy-soft"
    style={{ width: QR_SIZE, height: QR_SIZE }}
  />
);

// Only people setting up 2FA download the QR library.
const QRCodeSVG = dynamic(() => import("qrcode.react").then((module) => module.QRCodeSVG), {
  ssr: false,
  loading: QrPlaceholder,
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
  const [attempt, setAttempt] = useState(0);
  const [step, setStep] = useState<"scan" | "verify">("scan");
  const [cameBack, setCameBack] = useState(false);

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
  }, [onDone, attempt]);

  function retry() {
    setLoadError(null);
    setAttempt((current) => current + 1);
  }

  return (
    <div className="flex flex-col gap-5">
      <p className="flex items-center gap-2 text-sm font-semibold text-navy">
        <ShieldCheck aria-hidden="true" className="size-4 shrink-0" />
        {t("title")}
      </p>

      <Stepper current={step} />

      {step === "scan" ? (
        <ScanStep
          otpauthUrl={otpauthUrl}
          loadError={loadError}
          focusContinue={cameBack}
          onRetry={retry}
          onContinue={() => setStep("verify")}
        />
      ) : (
        <VerifyStep
          onDone={onDone}
          onBack={() => {
            setCameBack(true);
            setStep("scan");
          }}
        />
      )}
    </div>
  );
}

function Stepper({ current }: { current: "scan" | "verify" }) {
  const t = useTranslations("Auth.totpSetup");
  const onVerify = current === "verify";

  return (
    <ol aria-label={t("stepsLabel")} className="flex items-center gap-2">
      <StepItem number={1} active={!onVerify} done={onVerify} label={t("stepScan")} />
      <li aria-hidden="true" className={cn("h-px flex-1", onVerify ? "bg-navy" : "bg-line")} />
      <StepItem number={2} active={onVerify} done={false} label={t("stepVerify")} />
    </ol>
  );
}

function StepItem({
  number,
  active,
  done,
  label,
}: {
  number: number;
  active: boolean;
  done: boolean;
  label: string;
}) {
  const t = useTranslations("Auth.totpSetup");

  return (
    <li aria-current={active ? "step" : undefined} className="flex items-center gap-2">
      <span
        className={cn(
          "grid size-7 shrink-0 place-items-center rounded-full text-xs font-bold",
          active && "bg-orange text-on-orange",
          done && "bg-navy text-on-dark",
          !active && !done && "bg-navy-soft text-ink-soft",
        )}
      >
        {done ? <Check aria-hidden="true" className="size-4" /> : number}
      </span>
      <span className={cn("text-sm font-semibold", active ? "text-navy-deep" : "text-ink-soft")}>
        {label}
        {done && <span className="sr-only"> ({t("stepDone")})</span>}
      </span>
    </li>
  );
}

function StepHeading({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <h1 className="text-2xl text-navy-deep">{title}</h1>
      <p className="mt-1.5 text-sm text-ink-soft">{children}</p>
    </div>
  );
}

function ScanStep({
  otpauthUrl,
  loadError,
  focusContinue,
  onRetry,
  onContinue,
}: {
  otpauthUrl: string | null;
  loadError: ErrorKey | null;
  focusContinue: boolean;
  onRetry: () => void;
  onContinue: () => void;
}) {
  const t = useTranslations("Auth.totpSetup");

  return (
    <div className="flex flex-col gap-5">
      <StepHeading title={t("scanTitle")}>{t("scanDescription")}</StepHeading>

      {loadError ? (
        <div className="flex flex-col gap-3">
          <p role="alert" className="text-sm text-red-700">
            {t(`errors.${loadError}`)}
          </p>
          <Button type="button" variant="outline" onClick={onRetry}>
            {t("retry")}
          </Button>
        </div>
      ) : (
        <>
          <QrFrame otpauthUrl={otpauthUrl} />
          {otpauthUrl && (
            <>
              <ManualKey otpauthUrl={otpauthUrl} />
              <Button type="button" autoFocus={focusContinue} onClick={onContinue}>
                {t("scanned")}
              </Button>
            </>
          )}
        </>
      )}
    </div>
  );
}

const CORNERS = [
  "start-0 top-0 rounded-ss-lg border-s-[3px] border-t-[3px]",
  "end-0 top-0 rounded-se-lg border-e-[3px] border-t-[3px]",
  "start-0 bottom-0 rounded-es-lg border-s-[3px] border-b-[3px]",
  "end-0 bottom-0 rounded-ee-lg border-e-[3px] border-b-[3px]",
];

function QrFrame({ otpauthUrl }: { otpauthUrl: string | null }) {
  const t = useTranslations("Auth.totpSetup");

  return (
    <div className="flex justify-center rounded-lg border border-line bg-bg-tint py-5">
      <div
        role={otpauthUrl ? "img" : "status"}
        aria-label={otpauthUrl ? t("qrLabel") : t("loading")}
        className="relative rounded-lg bg-bg p-4"
      >
        {CORNERS.map((corner) => (
          <span
            key={corner}
            aria-hidden="true"
            className={cn("absolute size-6 border-navy", corner)}
          />
        ))}
        {/* The QR code stays black on white: phone cameras read that most reliably. */}
        {otpauthUrl ? <QRCodeSVG value={otpauthUrl} size={QR_SIZE} /> : <QrPlaceholder />}
      </div>
    </div>
  );
}

function ManualKey({ otpauthUrl }: { otpauthUrl: string }) {
  const t = useTranslations("Auth.totpSetup");
  const [copied, setCopied] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const manualKey = manualKeyFrom(otpauthUrl);

  useEffect(() => () => clearTimeout(timer.current), []);

  async function copy() {
    try {
      await navigator.clipboard.writeText(manualKey.replaceAll(" ", ""));
    } catch {
      return; // The key stays on screen, so it can still be selected by hand.
    }
    setCopied(true);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setCopied(false), 2000);
  }

  return (
    <details className="group rounded-control border border-line">
      <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-2 rounded-control px-3.5 text-sm font-semibold text-navy hover:bg-navy-soft [&::-webkit-details-marker]:hidden">
        {t("manualToggle")}
        <ChevronDown
          aria-hidden="true"
          className="size-4 shrink-0 transition-transform group-open:rotate-180"
        />
      </summary>
      <div className="flex flex-col gap-2 border-t border-line p-3.5">
        <p className="text-xs text-ink-soft">{t("manualHelp")}</p>
        <code
          dir="ltr"
          className="rounded-control bg-bg-tint px-3 py-2 font-mono text-sm text-ink select-all"
        >
          {manualKey}
        </code>
        <Button type="button" variant="outline" size="sm" onClick={copy}>
          {copied ? <Check aria-hidden="true" /> : <Copy aria-hidden="true" />}
          <span aria-live="polite">{copied ? t("copied") : t("copy")}</span>
        </Button>
      </div>
    </details>
  );
}

function VerifyStep({ onDone, onBack }: { onDone: () => void; onBack: () => void }) {
  const t = useTranslations("Auth.totpSetup");

  const form = useValidatedForm({
    initial: { code: "" },
    idPrefix: "totp-setup-",
    validators: { code: sixDigitCode },
    sanitizers: { code: sanitizeCode },
    submit: async (values) => confirmTotp(values.code),
    onSuccess: onDone,
    describeError: (err) =>
      err instanceof ApiError && err.code === "totp_wait"
        ? t("errors.wait", { seconds: err.retryAfter ?? 1 })
        : t(`errors.${toErrorKey(err)}`),
  });

  return (
    <form onSubmit={form.handleSubmit} noValidate className="flex flex-col gap-5">
      <StepHeading title={t("verifyTitle")}>{t("verifyDescription")}</StepHeading>

      <CodeInput
        {...form.bind("code")}
        label={t("codeLabel")}
        error={form.errorFor("code")}
        className="h-14 text-center font-mono text-2xl tracking-[0.35em]"
      />

      {form.formError && (
        <p role="alert" className="text-sm text-red-700">
          {form.formError}
        </p>
      )}

      <div className="flex flex-col gap-2">
        <Button type="submit" loading={form.saving}>
          {t("submit")}
        </Button>
        <Button type="button" variant="ghost" disabled={form.saving} onClick={onBack}>
          <ArrowLeft aria-hidden="true" className="rtl:rotate-180" />
          {t("back")}
        </Button>
      </div>
    </form>
  );
}
