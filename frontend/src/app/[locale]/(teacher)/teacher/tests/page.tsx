import { setRequestLocale } from "next-intl/server";
import { TestsPanel } from "@/features/teacher/components/tests-panel";

// Renders only after the sign-in check in the browser, so the server has nothing to validate.
export const instant = false;

export default async function Page({ params }: PageProps<"/[locale]/teacher/tests">) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <TestsPanel />;
}
