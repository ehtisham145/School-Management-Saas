import { setRequestLocale } from "next-intl/server";
import { PaperDesignPanel } from "@/features/teacher/components/paper-design-panel";

// Renders only after the sign-in check in the browser, so the server has nothing to validate.
export const instant = false;

export default async function Page({ params }: PageProps<"/[locale]/teacher/paper-design">) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <PaperDesignPanel />;
}
