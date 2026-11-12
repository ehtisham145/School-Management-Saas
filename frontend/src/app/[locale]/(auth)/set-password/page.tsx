import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { SetPasswordGate } from "@/features/auth/components/set-password";
import { LanguageMenu } from "@/features/marketing/components/language-menu";
import { Logo } from "@/features/marketing/components/logo";
import { Link } from "@/i18n/navigation";

export async function generateMetadata({
  params,
}: PageProps<"/[locale]/set-password">): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "Auth.setPassword" });
  return { title: t("title"), robots: { index: false } };
}

/** Same plain look as the sign-in page, with only the card. */
export default async function SetPasswordPage({ params }: PageProps<"/[locale]/set-password">) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <main className="flex flex-1 flex-col bg-bg-tint">
      <div className="page-wrap flex justify-end pt-5">
        <LanguageMenu />
      </div>
      <div className="page-wrap flex flex-1 flex-col items-center justify-center py-10">
        <Link href="/" className="inline-block">
          <Logo priority className="h-12 sm:h-14" />
        </Link>
        <div className="mt-8 w-full max-w-[420px] rounded-card border border-line bg-bg p-6 shadow-soft sm:p-8">
          <SetPasswordGate />
        </div>
      </div>
    </main>
  );
}
