import { setRequestLocale } from "next-intl/server";
import { UsagePanel } from "@/features/platform/components/usage-panel";

// Renders only after the sign-in check in the browser, so the server has nothing to validate.
export const instant = false;

export default async function PlatformUsagePage({ params }: PageProps<"/[locale]/platform/usage">) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <UsagePanel />;
}
