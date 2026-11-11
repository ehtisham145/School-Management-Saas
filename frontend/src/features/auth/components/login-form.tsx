"use client";

import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { ApiError } from "@/lib/api";
import { required, useValidatedForm } from "@/lib/use-validated-form";
import { login } from "../api";
import type { AuthenticatedResponse } from "../schemas";

type LoginFormProps = {
  onResponse: (response: AuthenticatedResponse) => void;
  onUseEmailCode: () => void;
};

export function LoginForm({ onResponse, onUseEmailCode }: LoginFormProps) {
  const t = useTranslations("Auth.login");

  const form = useValidatedForm({
    initial: { username: "", password: "" },
    idPrefix: "",
    validators: { username: required(150), password: required(4096) },
    submit: async (values) => onResponse(await login(values)),
    describeError: (err) => {
      if (err instanceof ApiError && err.status === 429) return t("errors.rateLimited");
      if (err instanceof ApiError && err.code === "invalid_credentials") {
        return t("errors.invalidCredentials");
      }
      return t("errors.generic");
    },
  });

  return (
    <form onSubmit={form.handleSubmit} noValidate className="flex flex-col gap-3">
      <Field id="username" label={t("usernameLabel")} required error={form.errorFor("username")}>
        <Input
          {...form.bind("username")}
          autoComplete="username"
          placeholder={t("usernamePlaceholder")}
        />
      </Field>

      <Field id="password" label={t("passwordLabel")} required error={form.errorFor("password")}>
        <PasswordInput
          {...form.bind("password")}
          autoComplete="current-password"
          placeholder={t("passwordPlaceholder")}
          showLabel={t("showPassword")}
          hideLabel={t("hidePassword")}
        />
      </Field>

      {form.formError && (
        <p role="alert" className="text-sm text-red-700">
          {form.formError}
        </p>
      )}

      <Button type="submit" loading={form.saving}>
        {form.saving ? t("submitting") : t("submit")}
      </Button>

      <Button type="button" variant="ghost" onClick={onUseEmailCode}>
        {t("useEmailCode")}
      </Button>
    </form>
  );
}
