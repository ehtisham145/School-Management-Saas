import { WelcomeReveal } from "@/features/auth/components/welcome-reveal";
import { TeacherApp } from "@/features/teacher/components/teacher-app";

export default function TeacherLayout({ children }: LayoutProps<"/[locale]">) {
  return (
    <>
      {/* Outside the app, so the welcome also covers its loading screen. */}
      <WelcomeReveal />
      <TeacherApp>{children}</TeacherApp>
    </>
  );
}
