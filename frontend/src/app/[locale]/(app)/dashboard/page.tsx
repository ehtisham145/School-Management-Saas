import { setRequestLocale } from "next-intl/server";
import { DashboardView } from "@/features/auth/components/dashboard-view";

export default async function DashboardPage({ params }: PageProps<"/[locale]/dashboard">) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <DashboardView />;
}
