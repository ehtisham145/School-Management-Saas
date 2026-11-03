import { RequirePlatformAdmin } from "@/features/platform/components/require-platform-admin";

export default function PlatformLayout({ children }: LayoutProps<"/[locale]">) {
  return <RequirePlatformAdmin>{children}</RequirePlatformAdmin>;
}
