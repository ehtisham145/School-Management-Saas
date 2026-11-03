import { setRequestLocale } from "next-intl/server";
import { SchoolsPanel } from "@/features/platform/components/schools-panel";

export default async function PlatformPage({ params }: PageProps<"/[locale]/platform">) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <SchoolsPanel />;
}
