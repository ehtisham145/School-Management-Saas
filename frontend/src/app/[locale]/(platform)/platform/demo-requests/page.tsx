import { setRequestLocale } from "next-intl/server";
import { DemoRequestsPanel } from "@/features/platform/components/demo-requests-panel";

// Renders only after the sign-in check in the browser, so the server has nothing to validate.
export const instant = false;

export default async function PlatformDemoRequestsPage({
  params,
}: PageProps<"/[locale]/platform/demo-requests">) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <DemoRequestsPanel />;
}
