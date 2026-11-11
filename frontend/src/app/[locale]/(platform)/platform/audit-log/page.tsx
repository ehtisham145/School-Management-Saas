import { setRequestLocale } from "next-intl/server";
import { AuditLogPanel } from "@/features/platform/components/audit-log-panel";

// Renders only after the sign-in check in the browser, so the server has nothing to validate.
export const instant = false;

export default async function PlatformAuditLogPage({
  params,
}: PageProps<"/[locale]/platform/audit-log">) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <AuditLogPanel />;
}
