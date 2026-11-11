import { Suspense } from "react";
import { setRequestLocale } from "next-intl/server";
import { QuotationFormPanel } from "@/features/platform/components/quotation-form";

// Renders only after the sign-in check in the browser, so the server has nothing to validate.
export const instant = false;

export default async function PlatformNewQuotationPage({
  params,
}: PageProps<"/[locale]/platform/quotations/new">) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <Suspense>
      <QuotationFormPanel />
    </Suspense>
  );
}
