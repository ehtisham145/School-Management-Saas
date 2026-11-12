"use client";

import { useCallback, useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { Button } from "@/components/ui/button";
import { logout } from "../api";
import { toActiveSession, type AuthenticatedResponse, type Membership } from "../schemas";
import { useSession } from "../session-store";
import { markFreshLogin } from "../welcome";
import { EmailCodeForm } from "./email-code-form";
import { LoginForm } from "./login-form";
import { SchoolPicker } from "./school-picker";

type Step =
  | { name: "password" }
  | { name: "email-code" }
  | { name: "choose-school"; memberships: Membership[] }
  | { name: "no-school"; schoolInactive: boolean };

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
    ({
      needs_password,
      is_platform_admin,
      memberships,
      school_inactive,
    }: AuthenticatedResponse) => {
      if (needs_password) {
        // First sign-in by email code: choose a password before anything else.
        router.push("/set-password");
      } else if (is_platform_admin) {
        markFreshLogin();
        router.push("/platform");
      } else if (memberships.length === 0) {
        void logout();
        setStep({ name: "no-school", schoolInactive: school_inactive });
      } else if (memberships.length === 1) {
        setSession(toActiveSession(memberships[0]));
        markFreshLogin();
        router.push("/dashboard");
      } else {
        setStep({ name: "choose-school", memberships });
      }
    },
    [router, setSession],
  );

  const backToPassword = () => setStep({ name: "password" });

  switch (step.name) {
    case "password":
      return (
        <LoginForm
          onResponse={continueToApp}
          onUseEmailCode={() => setStep({ name: "email-code" })}
        />
      );
    case "email-code":
      return <EmailCodeForm onResponse={continueToApp} onBack={backToPassword} />;
    case "choose-school":
      return (
        <SchoolPicker memberships={step.memberships} locale={locale} onSelected={markFreshLogin} />
      );
    case "no-school":
      return (
        <div className="flex flex-col gap-3">
          <p role="alert" className="text-sm text-destructive">
            {t(step.schoolInactive ? "schoolInactive" : "noSchool")}
          </p>
          <Button type="button" variant="outline" onClick={backToPassword}>
            {t("backToLogin")}
          </Button>
        </div>
      );
  }
}
