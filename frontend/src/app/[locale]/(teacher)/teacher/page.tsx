import { setRequestLocale } from "next-intl/server";
import { OverviewPanel } from "@/features/teacher/components/overview-panel";

// Renders only after the sign-in check in the browser, so the server has nothing to validate.
export const instant = false;

export default async function Page({ params }: PageProps<"/[locale]/teacher">) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <OverviewPanel />;
}
