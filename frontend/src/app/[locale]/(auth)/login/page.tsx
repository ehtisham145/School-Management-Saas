import { ArrowLeft } from "lucide-react";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { LoginFlow } from "@/features/auth/components/login-flow";
import { DemoButton, DemoDialogProvider } from "@/features/leads/components/demo-dialog";
import { LanguageMenu } from "@/features/marketing/components/language-menu";
import { Logo } from "@/features/marketing/components/logo";
import { Link } from "@/i18n/navigation";
import { pageMetadata } from "@/i18n/metadata";

export async function generateMetadata({ params }: PageProps<"/[locale]/login">) {
  const { locale } = await params;
  return pageMetadata(locale, "login", "/login");
}

/** Brand on one side, the sign-in card on the other, on a plain tinted page. */
export default async function LoginPage({ params }: PageProps<"/[locale]/login">) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("SignIn");
  const tFooter = await getTranslations("Marketing.footer");

  return (
    <DemoDialogProvider>
      <main className="flex flex-1 flex-col bg-bg-tint">
        <div className="page-wrap flex items-center justify-between gap-3 pt-5">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-sm font-semibold text-ink-soft hover:text-navy"
          >
            <ArrowLeft aria-hidden="true" className="size-4 rtl:rotate-180" />
            {t("backHome")}
          </Link>
          <LanguageMenu />
        </div>

        <div className="page-wrap grid flex-1 content-center items-center gap-10 py-10 lg:grid-cols-[1fr_minmax(0,420px)] lg:gap-20">
          <div className="text-center lg:text-start">
            <Link href="/" className="inline-block">
              <Logo priority className="h-12 sm:h-16" />
            </Link>
            <div>
              <p className="mx-auto mt-6 max-w-[18ch] text-[clamp(26px,3.2vw,40px)] leading-tight font-semibold text-navy-deep lg:mx-0">
                {t("headline")}
              </p>
              <p className="mx-auto mt-3 max-w-[40ch] text-[17px] text-ink-soft lg:mx-0">
                {t("sub")}
              </p>
            </div>
          </div>

          <div className="mx-auto w-full max-w-[420px]">
            <div className="rounded-card border border-line bg-bg p-6 shadow-soft sm:p-8">
              <h1 className="text-[clamp(24px,2.4vw,30px)] text-navy-deep">{t("welcome")}</h1>
              <p className="mt-1.5 mb-6 text-ink-soft">{t("welcomeSub")}</p>
              <LoginFlow />
            </div>

            <div className="mt-6 flex flex-wrap items-center justify-center gap-x-3 gap-y-2 text-[15px] text-ink-soft">
              <span>{t("newSchool")}</span>
              <DemoButton variant="outline" size="sm">
                {t("bookDemo")}
              </DemoButton>
            </div>
          </div>
        </div>

        <footer className="page-wrap flex flex-wrap justify-center gap-x-5 gap-y-1 py-6 text-sm text-ink-soft">
          <Link href="/" className="hover:text-navy hover:underline">
            {t("backHome")}
          </Link>
          <Link href="/privacy" className="hover:text-navy hover:underline">
            {tFooter("privacy")}
          </Link>
        </footer>
      </main>
    </DemoDialogProvider>
  );
}
