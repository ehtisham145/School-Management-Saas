"use client";

import { useCallback, useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { Button } from "@/components/ui/button";
import { logout } from "../api";
import {
  toActiveSession,
  type AuthenticatedResponse,
  type LoginResponse,
  type Membership,
} from "../schemas";
import { useSession } from "../session-store";
import { EmailCodeForm } from "./email-code-form";
import { LoginForm } from "./login-form";
import { SchoolPicker } from "./school-picker";
import { TotpForm } from "./totp-form";
import { TotpSetup } from "./totp-setup";

type Step =
  | { name: "password" }
  | { name: "email-code" }
  | { name: "totp" }
  | { name: "totp-setup"; response: AuthenticatedResponse }
  | { name: "choose-school"; memberships: Membership[] }
  | { name: "no-school" };

export function LoginFlow() {
  const [resetKey, setResetKey] = useState(0);

  // Next.js keeps this page's state after navigating away (cacheComponents).
  // Start clean on return, so no old step or typed password comes back.
  useEffect(() => () => setResetKey((current) => current + 1), []);

  return <LoginSteps key={resetKey} />;
}

function LoginSteps() {
  const t = useTranslations("Auth");
  const locale = useLocale();
  const router = useRouter();
  const { setSession } = useSession();
  const [step, setStep] = useState<Step>({ name: "password" });

  const continueToApp = useCallback(
    ({ is_platform_admin, memberships }: AuthenticatedResponse) => {
      if (is_platform_admin) {
        router.push("/platform");
      } else if (memberships.length === 0) {
        void logout();
        setStep({ name: "no-school" });
      } else if (memberships.length === 1) {
        setSession(toActiveSession(memberships[0]));
        router.push("/dashboard");
      } else {
        setStep({ name: "choose-school", memberships });
      }
    },
    [router, setSession],
  );

  function handleAuthenticated(response: AuthenticatedResponse) {
    if (response.requires_2fa_setup) {
      setStep({ name: "totp-setup", response });
    } else {
      continueToApp(response);
    }
  }

  function handleResponse(response: LoginResponse) {
    if ("requires_2fa" in response) {
      setStep({ name: "totp" });
    } else {
      handleAuthenticated(response);
    }
  }

  const backToPassword = () => setStep({ name: "password" });

  switch (step.name) {
    case "password":
      return (
        <LoginForm
          onResponse={handleResponse}
          onUseEmailCode={() => setStep({ name: "email-code" })}
        />
      );
    case "email-code":
      return <EmailCodeForm onResponse={handleResponse} onBack={backToPassword} />;
    case "totp":
      return <TotpForm onAuthenticated={handleAuthenticated} onRestart={backToPassword} />;
    case "totp-setup":
      return <TotpSetupStep response={step.response} onDone={continueToApp} />;
    case "choose-school":
      return <SchoolPicker memberships={step.memberships} locale={locale} />;
    case "no-school":
      return (
        <div className="flex flex-col gap-3">
          <p role="alert" className="text-sm text-destructive">
            {t("noSchool")}
          </p>
          <Button type="button" variant="outline" onClick={backToPassword}>
            {t("totp.backToLogin")}
          </Button>
        </div>
      );
  }
}

function TotpSetupStep({
  response,
  onDone,
}: {
  response: AuthenticatedResponse;
  onDone: (response: AuthenticatedResponse) => void;
}) {
  const handleDone = useCallback(() => onDone(response), [onDone, response]);

  return <TotpSetup onDone={handleDone} />;
}
