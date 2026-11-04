import { Suspense } from "react";
import { setRequestLocale } from "next-intl/server";
import { SchoolsPanel } from "@/features/platform/components/schools-panel";

// Renders only after the sign-in check in the browser, so the server has nothing to validate.
export const instant = false;

export default async function PlatformSchoolsPage({
  params,
}: PageProps<"/[locale]/platform/schools">) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <Suspense>
      <SchoolsPanel />
    </Suspense>
  );
}
