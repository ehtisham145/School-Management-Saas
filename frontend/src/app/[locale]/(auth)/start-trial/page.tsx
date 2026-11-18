import { ArrowLeft } from "lucide-react";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { TeacherSignup } from "@/features/auth/components/teacher-signup";
import { LanguageMenu } from "@/features/marketing/components/language-menu";
import { Logo } from "@/features/marketing/components/logo";
import { Link } from "@/i18n/navigation";
import { pageMetadata } from "@/i18n/metadata";

export async function generateMetadata({ params }: PageProps<"/[locale]/start-trial">) {
  const { locale } = await params;
  return pageMetadata(locale, "startTrial", "/start-trial");
}

/** The same plain layout as the sign-in page: the offer beside the sign-up card. */
export default async function StartTrialPage({ params }: PageProps<"/[locale]/start-trial">) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Auth.teacherSignup");
  const tFooter = await getTranslations("Marketing.footer");
  const points = t.raw("points") as string[];

  return (
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

      <div className="page-wrap grid flex-1 content-center items-center gap-10 py-10 lg:grid-cols-[1fr_minmax(0,460px)] lg:gap-20">
        <div className="text-center lg:text-start">
          <Link href="/" className="inline-block">
            <Logo priority className="h-12 sm:h-16" />
          </Link>
          <p className="mx-auto mt-6 max-w-[18ch] text-[clamp(26px,3.2vw,40px)] leading-tight font-semibold text-navy-deep lg:mx-0">
            {t("headline")}
          </p>
          <p className="mx-auto mt-3 max-w-[42ch] text-[17px] text-ink-soft lg:mx-0">{t("sub")}</p>
          <ul className="mt-6 hidden flex-col gap-2.5 text-[15px] text-ink lg:flex">
            {points.map((point) => (
              <li key={point} className="flex items-center gap-3">
                <span aria-hidden="true" className="size-1.5 shrink-0 rounded-full bg-orange" />
                {point}
              </li>
            ))}
          </ul>
        </div>

        <div className="mx-auto w-full max-w-[460px]">
          <div className="rounded-card border border-line bg-bg p-6 shadow-soft sm:p-8">
            <h1 className="text-[clamp(24px,2.4vw,30px)] text-navy-deep">{t("title")}</h1>
            <p className="mt-1.5 mb-6 text-ink-soft">{t("subtitle")}</p>
            <TeacherSignup />
          </div>

          <p className="mt-6 text-center text-[15px] text-ink-soft">
            {t("haveAccount")}{" "}
            <Link href="/login" className="font-semibold text-navy hover:underline">
              {t("signIn")}
            </Link>
          </p>
        </div>
      </div>

      <footer className="page-wrap flex flex-wrap justify-center gap-x-5 gap-y-1 py-6 text-sm text-ink-soft">
        <Link href="/privacy" className="hover:text-navy hover:underline">
          {tFooter("privacy")}
        </Link>
      </footer>
    </main>
  );
}
