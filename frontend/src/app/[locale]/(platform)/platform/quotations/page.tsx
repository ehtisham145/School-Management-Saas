import { Suspense } from "react";
import { setRequestLocale } from "next-intl/server";
import { QuotationsPanel } from "@/features/platform/components/quotations-panel";

// Renders only after the sign-in check in the browser, so the server has nothing to validate.
export const instant = false;

export default async function PlatformQuotationsPage({
  params,
}: PageProps<"/[locale]/platform/quotations">) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <Suspense>
      <QuotationsPanel />
    </Suspense>
  );
}
