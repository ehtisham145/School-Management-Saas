import { setRequestLocale } from "next-intl/server";
import { MessagesPanel } from "@/features/teacher/components/messages-panel";
import { ClassesOnly } from "@/features/teacher/components/teacher-ui";

// Renders only after the sign-in check in the browser, so the server has nothing to validate.
export const instant = false;

export default async function Page({ params }: PageProps<"/[locale]/teacher/messages">) {
  const { locale } = await params;
  setRequestLocale(locale);

  // Part of the school plan (ADR-0027). An old link shows where to find it.
  return (
    <ClassesOnly>
      <MessagesPanel />
    </ClassesOnly>
  );
}
