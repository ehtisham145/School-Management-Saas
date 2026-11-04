import { RequireSession } from "@/features/auth/components/require-session";
import { WelcomeReveal } from "@/features/auth/components/welcome-reveal";

export default function AppLayout({ children }: LayoutProps<"/[locale]">) {
  return (
    <>
      <WelcomeReveal />
      <RequireSession>{children}</RequireSession>
    </>
  );
}
