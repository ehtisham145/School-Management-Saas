import { setRequestLocale } from "next-intl/server";
import { DashboardPanel } from "@/features/platform/components/dashboard-panel";

// Renders only after the sign-in check in the browser, so the server has nothing to validate.
export const instant = false;

export default async function PlatformDashboardPage({ params }: PageProps<"/[locale]/platform">) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <DashboardPanel />;
}
