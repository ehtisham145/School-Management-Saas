import { setRequestLocale } from "next-intl/server";
import { DashboardView } from "@/features/auth/components/dashboard-view";

// Renders only after the sign-in check in the browser, so the server has nothing to validate.
export const instant = false;

export default async function DashboardPage({ params }: PageProps<"/[locale]/dashboard">) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <DashboardView />;
}
