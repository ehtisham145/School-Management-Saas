import { getTranslations, setRequestLocale } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "cn";
import { PageHero } from "@/features/marketing/components/page-hero";
import { Reveal } from "@/features/marketing/components/reveal";
import { CheckIcon } from "@/features/marketing/icons";

type Tier = {
  name: string;
  tagline: string;
  features: string[];
  cta: string;
  highlightLabel?: string;
};

type FaqItem = { q: string; a: string };

const TIER_KEYS = ["starter", "growth", "network"] as const;

export default async function PricingPage({ params }: PageProps<"/[locale]/pricing">) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Marketing.pricing");

  const words = t.raw("hero.words") as string[];
  const tiers = t.raw("tiers") as Record<(typeof TIER_KEYS)[number], Tier>;
  const faq = t.raw("faq") as FaqItem[];

  return (
    <>
      <PageHero
        eyebrow={t("hero.eyebrow")}
        titleLead={t("hero.titleLead")}
        words={words}
        lede={t("hero.lede")}
      />

      <section className="mx-auto max-w-6xl px-6 py-20 sm:py-24">
        <div className="grid gap-6 lg:grid-cols-3">
          {TIER_KEYS.map((key, index) => {
            const tier = tiers[key];
            const highlighted = Boolean(tier.highlightLabel);
            return (
              <Reveal key={key} delayMs={index * 100} className="h-full">
                <Link
                  href={{ pathname: "/contact", query: { plan: key } }}
                  className={cn(
                    "group flex h-full flex-col border bg-card p-8 transition-colors hover:bg-accent",
                    highlighted ? "border-primary" : "border-border",
                  )}
                >
                  {tier.highlightLabel && (
                    <span className="font-marketing-mono mb-4 inline-flex w-fit items-center bg-primary px-2.5 py-1 text-[0.68rem] font-medium tracking-[0.08em] text-primary-foreground uppercase">
                      {tier.highlightLabel}
                    </span>
                  )}
                  <h3 className="font-display text-xl font-semibold text-card-foreground">
                    {tier.name}
                  </h3>
                  <p className="mt-1.5 text-sm text-muted-foreground">{tier.tagline}</p>

                  <ul className="mt-6 flex flex-1 flex-col gap-3">
                    {tier.features.map((feature) => (
                      <li key={feature} className="flex items-start gap-2.5">
                        <CheckIcon className="mt-0.5 h-4 w-4 shrink-0 text-[var(--mk-teal)]" />
                        <span className="text-sm text-card-foreground">{feature}</span>
                      </li>
                    ))}
                  </ul>

                  <span
                    className={cn(
                      buttonVariants({ variant: highlighted ? "default" : "outline" }),
                      "mt-7 w-full",
                    )}
                  >
                    {tier.cta}
                  </span>
                </Link>
              </Reveal>
            );
          })}
        </div>
        <p className="font-marketing-mono mt-8 max-w-[60ch] text-xs text-[var(--mk-ink-faint)]">
          {t("note")}
        </p>
      </section>

      <section className="border-t border-border bg-muted">
        <div className="mx-auto max-w-4xl px-6 py-20 sm:py-24">
          <span className="font-marketing-mono inline-flex items-center gap-2 text-xs font-medium tracking-[0.14em] text-[var(--mk-accent-ink)] uppercase before:h-px before:w-[1.1em] before:bg-current">
            {t("faqEyebrow")}
          </span>
          <h2 className="font-display mt-3 text-3xl font-semibold text-balance text-foreground sm:text-4xl">
            {t("faqTitle")}
          </h2>

          <div className="mt-10 flex flex-col divide-y divide-border border-y border-border">
            {faq.map((item, index) => (
              <Reveal key={item.q} delayMs={(index % 4) * 80} className="py-6">
                <h3 className="font-display text-base font-semibold text-foreground">{item.q}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{item.a}</p>
              </Reveal>
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
