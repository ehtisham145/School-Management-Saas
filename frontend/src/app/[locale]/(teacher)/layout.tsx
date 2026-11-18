import { TeacherApp } from "@/features/teacher/components/teacher-app";

export default function TeacherLayout({ children }: LayoutProps<"/[locale]">) {
  return <TeacherApp>{children}</TeacherApp>;
}
