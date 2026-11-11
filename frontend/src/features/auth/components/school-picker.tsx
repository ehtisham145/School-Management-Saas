"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { switchSchool } from "../api";
import type { Membership } from "../schemas";
import { useSession } from "../session-store";

type SchoolPickerErrorKey = "notFound" | "generic";

type SchoolPickerProps = {
  memberships: Membership[];
  locale: string;
  onSelected?: () => void;
};

export function SchoolPicker({ memberships, locale, onSelected }: SchoolPickerProps) {
  const t = useTranslations("Auth.schoolPicker");
  const tRoles = useTranslations("Roles");
  const router = useRouter();
  const { setSession } = useSession();

  const [pendingId, setPendingId] = useState<number | null>(null);
  const [error, setError] = useState<SchoolPickerErrorKey | null>(null);

  async function handleSelect(membershipId: number) {
    setError(null);
    setPendingId(membershipId);

    try {
      const result = await switchSchool({ membership_id: membershipId });
      setSession({
        membershipId: result.membership_id,
        role: result.role,
        school: result.school,
      });
      onSelected?.();
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError && err.code === "not_found" ? "notFound" : "generic");
      setPendingId(null);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div>
        <h2 className="text-base font-medium">{t("title")}</h2>
        <p className="text-sm text-muted-foreground">{t("description")}</p>
      </div>

      <ul className="flex flex-col gap-2">
        {memberships.map((membership) => {
          const schoolName =
            locale === "ar"
              ? membership.school.name_ar || membership.school.name_en
              : membership.school.name_en;

          return (
            <li key={membership.membership_id}>
              <Button
                type="button"
                variant="outline"
                className="h-auto w-full justify-start py-2"
                disabled={pendingId !== null}
                onClick={() => handleSelect(membership.membership_id)}
              >
                <span className="flex flex-col items-start">
                  <span>{schoolName}</span>
                  <span className="text-xs text-muted-foreground">{tRoles(membership.role)}</span>
                </span>
              </Button>
            </li>
          );
        })}
      </ul>

      {error && (
        <p role="alert" className="text-sm text-destructive">
          {t(`errors.${error}`)}
        </p>
      )}
    </div>
  );
}
