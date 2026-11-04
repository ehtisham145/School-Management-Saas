import { Suspense } from "react";
import { setRequestLocale } from "next-intl/server";
import { NewSchoolPanel } from "@/features/platform/components/school-form";

// Renders only after the sign-in check in the browser, so the server has nothing to validate.
export const instant = false;

export default async function PlatformNewSchoolPage({
  params,
}: PageProps<"/[locale]/platform/schools/new">) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <Suspense>
      <NewSchoolPanel />
    </Suspense>
  );
}
