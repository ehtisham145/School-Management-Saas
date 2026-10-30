import { getTranslations, setRequestLocale } from "next-intl/server";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Link } from "@/i18n/navigation";

export default async function HomePage({ params }: PageProps<"/[locale]">) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Home");
  const otherLocale = locale === "ar" ? "en" : "ar";

  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 p-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold">{t("title")}</h1>
        <p className="mt-2 text-lg text-muted-foreground">{t("subtitle")}</p>
      </div>

      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>{t("demoTitle")}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <Input placeholder={t("emailPlaceholder")} />
          <Button>{t("submit")}</Button>
        </CardContent>
      </Card>

      <Link href="/" locale={otherLocale} className="text-sm underline">
        {t("switchLanguage")}
      </Link>
    </main>
  );
}
