"use client";

import { useState, type FormEvent } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { login } from "../api";
import type { LoginResponse } from "../schemas";

type LoginErrorKey = "invalidCredentials" | "rateLimited" | "generic";

type LoginFormProps = {
  onResponse: (response: LoginResponse) => void;
  onUseEmailCode: () => void;
};

export function LoginForm({ onResponse, onUseEmailCode }: LoginFormProps) {
  const t = useTranslations("Auth.login");

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<LoginErrorKey | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      onResponse(await login({ username, password }));
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setError("rateLimited");
      } else if (err instanceof ApiError && err.code === "invalid_credentials") {
        setError("invalidCredentials");
      } else {
        setError("generic");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <div className="flex flex-col gap-1.5">
        <label htmlFor="username" className="text-sm font-medium">
          {t("usernameLabel")}
        </label>
        <Input
          id="username"
          name="username"
          autoComplete="username"
          required
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          placeholder={t("usernamePlaceholder")}
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="password" className="text-sm font-medium">
          {t("passwordLabel")}
        </label>
        <Input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder={t("passwordPlaceholder")}
        />
      </div>

      {error && (
        <p role="alert" className="text-sm text-destructive">
          {t(`errors.${error}`)}
        </p>
      )}

      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? t("submitting") : t("submit")}
      </Button>

      <Button type="button" variant="ghost" onClick={onUseEmailCode}>
        {t("useEmailCode")}
      </Button>
    </form>
  );
}
