import { getTranslations, setRequestLocale } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { buttonVariants } from "@/components/ui/button";
import { PageHero } from "@/features/marketing/components/page-hero";
import { SectionHeading } from "@/features/marketing/components/section-heading";
import { FeatureCard } from "@/features/marketing/components/feature-card";
import { Reveal } from "@/features/marketing/components/reveal";
import { BilingualIcon, CalendarIcon, LocationIcon, RolesIcon } from "@/features/marketing/icons";

type ValueItem = { title: string; description: string; href: string };

const VALUE_ICONS = [BilingualIcon, CalendarIcon, LocationIcon, RolesIcon];

export default async function AboutPage({ params }: PageProps<"/[locale]/about">) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Marketing.about");

  const words = t.raw("hero.words") as string[];
  const paragraphs = t.raw("story.paragraphs") as string[];
  const values = t.raw("values.items") as ValueItem[];

  return (
    <>
      <PageHero
        eyebrow={t("hero.eyebrow")}
        titleLead={t("hero.titleLead")}
        words={words}
        lede={t("hero.lede")}
      />

      <section className="mx-auto max-w-4xl px-6 py-20 sm:py-24">
        <Reveal>
          <span className="font-marketing-mono inline-flex items-center gap-2 text-xs font-medium tracking-[0.14em] text-[var(--mk-accent-ink)] uppercase before:h-px before:w-[1.1em] before:bg-current">
            {t("story.eyebrow")}
          </span>
          <h2 className="font-display mt-3 text-3xl font-semibold text-balance text-foreground sm:text-4xl">
            {t("story.title")}
          </h2>
          <div className="mt-6 flex flex-col gap-5">
            {paragraphs.map((paragraph) => (
              <p
                key={paragraph}
                className="max-w-[65ch] text-base leading-relaxed text-muted-foreground"
              >
                {paragraph}
              </p>
            ))}
          </div>
        </Reveal>
      </section>

      <section className="border-t border-border bg-muted">
        <div className="mx-auto max-w-6xl px-6 py-20 sm:py-24">
          <SectionHeading
            eyebrow={t("values.eyebrow")}
            title={t("values.title")}
            className="mb-12"
          />
          <div className="grid gap-px overflow-hidden border border-border bg-border sm:grid-cols-2">
            {values.map((value, index) => (
              <FeatureCard
                key={value.title}
                href={value.href}
                icon={VALUE_ICONS[index]}
                title={value.title}
                description={value.description}
                delayMs={(index % 2) * 90}
              />
            ))}
          </div>
        </div>
      </section>

      <section className="bg-[var(--mk-band-bg)] text-[var(--mk-band-text)]">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-8 px-6 py-16 sm:py-20">
          <div>
            <h2 className="font-display max-w-[20ch] text-3xl font-semibold text-balance text-[var(--mk-band-text)] sm:text-4xl">
              {t("cta.title")}
            </h2>
            <p className="mt-3 max-w-[42ch] text-[var(--mk-band-text)] opacity-80">
              {t("cta.description")}
            </p>
          </div>
          <Link href="/contact" className={buttonVariants({ size: "lg" })}>
            {t("cta.button")}
          </Link>
        </div>
      </section>
    </>
  );
}
