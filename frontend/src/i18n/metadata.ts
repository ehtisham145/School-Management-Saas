import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { routing } from "./routing";

type PageKey = "home" | "about" | "lms" | "pricing" | "contact" | "login";

export async function pageMetadata(locale: string, key: PageKey, path: string): Promise<Metadata> {
  const t = await getTranslations({ locale, namespace: "Marketing.meta" });

  return {
    title: t(`${key}.title`),
    description: t(`${key}.description`),
    alternates: {
      canonical: `/${locale}${path}`,
      languages: Object.fromEntries(routing.locales.map((code) => [code, `/${code}${path}`])),
    },
  };
}
