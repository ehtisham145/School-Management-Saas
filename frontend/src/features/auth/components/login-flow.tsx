"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { Button } from "@/components/ui/button";
import { logout } from "../api";
import { toActiveSession, type LoginResponse, type Membership } from "../schemas";
import { useSession } from "../session-store";
import { EmailCodeForm } from "./email-code-form";
import { LoginForm } from "./login-form";
import { SchoolPicker } from "./school-picker";
import { TotpForm } from "./totp-form";

type Step =
  | { name: "password" }
  | { name: "email-code" }
  | { name: "totp" }
  | { name: "choose-school"; memberships: Membership[] }
  | { name: "no-school" };

export function LoginFlow() {
  const t = useTranslations("Auth");
  const locale = useLocale();
  const router = useRouter();
  const { setSession } = useSession();
  const [step, setStep] = useState<Step>({ name: "password" });

  function handleAuthenticated(memberships: Membership[]) {
    if (memberships.length === 0) {
      void logout();
      setStep({ name: "no-school" });
    } else if (memberships.length === 1) {
      setSession(toActiveSession(memberships[0]));
      router.push("/dashboard");
    } else {
      setStep({ name: "choose-school", memberships });
    }
  }

  function handleResponse(response: LoginResponse) {
    if ("requires_2fa" in response) {
      setStep({ name: "totp" });
    } else {
      handleAuthenticated(response.memberships);
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
      return (
        <TotpForm
          onAuthenticated={(response) => handleAuthenticated(response.memberships)}
          onRestart={backToPassword}
        />
      );
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
