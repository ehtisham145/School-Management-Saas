import { RequireSession } from "@/features/auth/components/require-session";

export default function AppLayout({ children }: LayoutProps<"/[locale]">) {
  return <RequireSession>{children}</RequireSession>;
}
