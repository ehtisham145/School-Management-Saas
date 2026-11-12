"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { ApiError } from "@/lib/api";
import { newPassword, repeats, useValidatedForm } from "@/lib/use-validated-form";
import { logout, me, setPassword } from "../api";
import { toActiveSession, type AuthenticatedResponse } from "../schemas";
import { useSession } from "../session-store";
import { markFreshLogin } from "../welcome";

type GateState =
  | { name: "loading" }
  | { name: "form"; username: string }
  | { name: "no-school"; schoolInactive: boolean }
  | { name: "failed" };

/**
 * The first sign-in of staff created without a password: after the email code
 * they land here and choose one. Anyone who already has a password, or isn't
 * signed in, is sent on.
 */
export function SetPasswordGate() {
  const t = useTranslations("Auth");
  const router = useRouter();
  const { setSession } = useSession();
  const [state, setState] = useState<GateState>({ name: "loading" });

  function continueToApp(response: AuthenticatedResponse) {
    if (response.is_platform_admin) {
      markFreshLogin();
      router.replace("/platform");
    } else if (response.memberships.length === 0) {
      void logout();
      setState({ name: "no-school", schoolInactive: response.school_inactive });
    } else {
      if (response.memberships.length === 1) setSession(toActiveSession(response.memberships[0]));
      markFreshLogin();
      router.replace("/dashboard");
    }
  }

  useEffect(() => {
    let cancelled = false;
    me()
      .then((result) => {
        if (cancelled) return;
        if (result.needs_password) {
          setState({ name: "form", username: result.username });
        } else {
          router.replace(result.is_platform_admin ? "/platform" : "/dashboard");
        }
      })
      .catch((err: { status?: number }) => {
        if (cancelled) return;
        if (err.status === 401 || err.status === 403) router.replace("/login");
        else setState({ name: "failed" });
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  switch (state.name) {
    case "loading":
      return <p className="text-sm text-ink-soft">{t("session.loading")}</p>;
    case "failed":
      return (
        <p role="alert" className="text-sm text-destructive">
          {t("session.loadFailed")}
        </p>
      );
    case "no-school":
      return (
        <p role="alert" className="text-sm text-destructive">
          {t(state.schoolInactive ? "schoolInactive" : "noSchool")}
        </p>
      );
    case "form":
      return <SetPasswordForm username={state.username} onDone={continueToApp} />;
  }
}

function SetPasswordForm({
  username,
  onDone,
}: {
  username: string;
  onDone: (response: AuthenticatedResponse) => void;
}) {
  const t = useTranslations("Auth.setPassword");
  const tLogin = useTranslations("Auth.login");
  const router = useRouter();

  const form = useValidatedForm({
    initial: { password: "", confirm: "" },
    validators: { password: newPassword, confirm: repeats("password") },
    validateWhileTyping: true,
    idPrefix: "set-",
    submit: async (values) => onDone(await setPassword(values.password)),
    describeError: (err) => {
      if (err instanceof ApiError && err.code === "password_already_set") {
        router.replace("/login");
        return t("errors.alreadySet");
      }
      return null;
    },
    describeFieldError: (name) => (name === "password" ? t("errors.weak") : null),
  });

  return (
    <form onSubmit={form.handleSubmit} noValidate className="flex flex-col gap-4">
      <div>
        <h1 className="text-[clamp(24px,2.4vw,30px)] text-navy-deep">{t("title")}</h1>
        <p className="mt-1.5 text-ink-soft">{t("description")}</p>
      </div>

      <Field id="set-username" label={t("usernameLabel")} hint={t("usernameHint")}>
        <Input id="set-username" value={username} readOnly dir="ltr" autoComplete="username" />
      </Field>

      <Field
        id="set-password"
        label={t("passwordLabel")}
        required
        hint={t("passwordHint")}
        error={form.errorFor("password")}
      >
        <PasswordInput
          {...form.bind("password")}
          autoComplete="new-password"
          showLabel={tLogin("showPassword")}
          hideLabel={tLogin("hidePassword")}
        />
      </Field>

      <Field id="set-confirm" label={t("confirmLabel")} required error={form.errorFor("confirm")}>
        <PasswordInput
          {...form.bind("confirm")}
          autoComplete="new-password"
          showLabel={tLogin("showPassword")}
          hideLabel={tLogin("hidePassword")}
        />
      </Field>

      {form.formError && (
        <p role="alert" className="text-sm text-destructive">
          {form.formError}
        </p>
      )}

      <Button type="submit" loading={form.saving}>
        {form.saving ? t("submitting") : t("submit")}
      </Button>
    </form>
  );
}
