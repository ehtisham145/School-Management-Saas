import { setRequestLocale } from "next-intl/server";
import { SubscriptionsPanel } from "@/features/platform/components/subscriptions-panel";

// Renders only after the sign-in check in the browser, so the server has nothing to validate.
export const instant = false;

export default async function PlatformSubscriptionsPage({
  params,
}: PageProps<"/[locale]/platform/subscriptions">) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <SubscriptionsPanel />;
}
