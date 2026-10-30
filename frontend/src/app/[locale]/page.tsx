import { getTranslations, setRequestLocale } from "next-intl/server";
import { Link } from "@/i18n/navigation";

export default async function HomePage({ params }: PageProps<"/[locale]">) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Home");
  const otherLocale = locale === "ar" ? "en" : "ar";

  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 p-8 text-center">
      <h1 className="text-4xl font-bold">{t("title")}</h1>
      <p className="text-lg opacity-70">{t("subtitle")}</p>
      <Link href="/" locale={otherLocale} className="rounded-lg border px-4 py-2">
        {t("switchLanguage")}
      </Link>
    </main>
  );
}
