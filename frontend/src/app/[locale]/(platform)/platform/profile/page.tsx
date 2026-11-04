import { setRequestLocale } from "next-intl/server";
import { ProfilePanel } from "@/features/platform/components/profile-panel";

// Renders only after the sign-in check in the browser, so the server has nothing to validate.
export const instant = false;

export default async function PlatformProfilePage({
  params,
}: PageProps<"/[locale]/platform/profile">) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <ProfilePanel />;
}
