import Image from "next/image";
import { ArrowLeft } from "lucide-react";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { LoginFlow } from "@/features/auth/components/login-flow";
import { LanguageMenu } from "@/features/marketing/components/language-menu";
import { Logo } from "@/features/marketing/components/logo";
import { Link } from "@/i18n/navigation";
import { pageMetadata } from "@/i18n/metadata";

export async function generateMetadata({ params }: PageProps<"/[locale]/login">) {
  const { locale } = await params;
  return pageMetadata(locale, "login", "/login");
}

export default async function LoginPage({ params }: PageProps<"/[locale]/login">) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("SignIn");

  return (
    <main className="group/signin grid flex-1 lg:grid-cols-2 lg:has-data-two-factor:grid-cols-1">
      <div className="flex flex-col px-4 py-6 sm:px-10 sm:py-8">
        <div className="flex items-center justify-between gap-3">
          <Link href="/" className="block shrink-0">
            <Logo priority />
          </Link>
          <LanguageMenu />
        </div>

        <div className="flex flex-1 items-center justify-center py-10">
          <div className="w-full max-w-[400px]">
            <div className="group-has-data-totp-setup/signin:hidden">
              <Link
                href="/"
                className="-ms-1 mb-6 inline-flex items-center gap-1.5 rounded-control py-1 ps-1 pe-2 text-sm font-semibold text-navy hover:bg-navy-soft lg:-ms-7"
              >
                <ArrowLeft aria-hidden="true" className="size-4 rtl:rotate-180" />
                {t("backHome")}
              </Link>
              <h1 className="text-[clamp(28px,3vw,36px)] text-navy-deep">{t("welcome")}</h1>
              <p className="mt-2 mb-7 text-ink-soft">{t("welcomeSub")}</p>
            </div>
            <LoginFlow />
          </div>
        </div>
      </div>

      <aside className="relative hidden flex-col justify-between overflow-hidden bg-navy-deep p-12 text-on-dark lg:flex lg:group-has-data-two-factor/signin:hidden">
        <div className="relative z-[1]">
          <h2 className="max-w-[16ch] text-[clamp(30px,3.2vw,44px)]">{t("headline")}</h2>
          <p className="mt-4 max-w-[40ch] text-on-dark-soft">{t("sub")}</p>
        </div>
        <Image
          src="/brand/sign-in.webp"
          width={1200}
          height={939}
          alt=""
          priority
          sizes="50vw"
          className="mx-auto mt-6 w-full max-w-[620px] mask-[radial-gradient(closest-side,black_72%,transparent_100%)]"
        />
      </aside>
    </main>
  );
}
