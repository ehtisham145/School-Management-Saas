"use client";

import { useState, type FormEvent } from "react";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { login } from "../api";
import type { Membership } from "../schemas";
import { useSession } from "../session-store";
import { SchoolPicker } from "./school-picker";

type LoginErrorKey = "invalidCredentials" | "rateLimited" | "generic";

export function LoginForm() {
  const t = useTranslations("Auth.login");
  const router = useRouter();
  const locale = useLocale();
  const { setSession } = useSession();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<LoginErrorKey | null>(null);
  const [memberships, setMemberships] = useState<Membership[] | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const response = await login({ username, password });

      if (response.memberships.length === 1) {
        const membership = response.memberships[0];
        setSession({
          membershipId: membership.membership_id,
          role: membership.role,
          school: membership.school,
        });
        router.push("/dashboard");
        return;
      }

      setMemberships(response.memberships);
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

  if (memberships) {
    return <SchoolPicker memberships={memberships} locale={locale} />;
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
    </form>
  );
}
