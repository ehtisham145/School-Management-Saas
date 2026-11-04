import { WelcomeReveal } from "@/features/auth/components/welcome-reveal";
import { RequirePlatformAdmin } from "@/features/platform/components/require-platform-admin";

export default function PlatformLayout({ children }: LayoutProps<"/[locale]">) {
  return (
    <>
      <WelcomeReveal />
      <RequirePlatformAdmin>{children}</RequirePlatformAdmin>
    </>
  );
}
