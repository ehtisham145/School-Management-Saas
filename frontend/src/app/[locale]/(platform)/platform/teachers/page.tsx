import { setRequestLocale } from "next-intl/server";
import { TeachersPanel } from "@/features/platform/components/teachers-panel";

// Renders only after the sign-in check in the browser, so the server has nothing to validate.
export const instant = false;

export default async function PlatformTeachersPage({
  params,
}: PageProps<"/[locale]/platform/teachers">) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <TeachersPanel />;
}
