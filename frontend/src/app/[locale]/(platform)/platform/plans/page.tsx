import { setRequestLocale } from "next-intl/server";
import { PlansPanel } from "@/features/platform/components/plans-panel";

// Renders only after the sign-in check in the browser, so the server has nothing to validate.
export const instant = false;

export default async function PlatformPlansPage({ params }: PageProps<"/[locale]/platform/plans">) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <PlansPanel />;
}
