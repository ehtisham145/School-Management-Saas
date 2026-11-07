import { getTranslations, setRequestLocale } from "next-intl/server";
import { CheckItem } from "@/features/marketing/components/blocks";
import { pageMetadata } from "@/i18n/metadata";

type PolicySection = { title: string; paragraphs?: string[]; items?: string[] };

export async function generateMetadata({ params }: PageProps<"/[locale]/privacy">) {
  const { locale } = await params;
  return pageMetadata(locale, "privacy", "/privacy");
}

export default async function PrivacyPage({ params }: PageProps<"/[locale]/privacy">) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Marketing.privacy");

  const sections = t.raw("sections") as PolicySection[];

  return (
    <>
      <section className="border-b border-line bg-bg-tint">
        <div className="page-wrap py-[clamp(40px,5vw,72px)]">
          <span className="inline-flex items-center gap-2 rounded-full bg-orange-soft px-[13px] py-1.5 text-[13px] font-bold text-orange-text">
            <i aria-hidden="true" className="size-[7px] rounded-full bg-orange" />
            {t("eyebrow")}
          </span>
          <h1 className="mt-5 text-[clamp(34px,4.2vw,54px)] text-navy-deep">{t("title")}</h1>
          <p className="mt-[18px] max-w-[62ch] text-[clamp(16px,1.35vw,18px)] text-ink-soft">
            {t("lede")}
          </p>
          <p className="mt-4 text-[13.5px] font-bold text-ink-soft">{t("updated")}</p>
        </div>
      </section>

      <section className="py-[clamp(48px,6vw,80px)]">
        <div className="page-wrap">
          <article className="flex max-w-[72ch] flex-col gap-10 text-[16px] text-ink-soft">
            {sections.map((section) => (
              <section key={section.title}>
                <h2 className="mb-3 text-[clamp(20px,2vw,24px)] text-navy-deep">{section.title}</h2>
                {section.items && (
                  <ul className="mb-3 grid gap-2.5">
                    {section.items.map((item) => (
                      <CheckItem key={item}>{item}</CheckItem>
                    ))}
                  </ul>
                )}
                <div className="flex flex-col gap-3">
                  {section.paragraphs?.map((paragraph) => (
                    <p key={paragraph}>{paragraph}</p>
                  ))}
                </div>
              </section>
            ))}
          </article>
        </div>
      </section>
    </>
  );
}
