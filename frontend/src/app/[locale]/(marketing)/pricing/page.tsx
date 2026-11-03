import { getTranslations, setRequestLocale } from "next-intl/server";
import { cn } from "cn";
import { Badge } from "@/components/ui/badge";
import { DemoButton } from "@/features/leads/components/demo-dialog";
import {
  CheckItem,
  CtaBox,
  PageHero,
  Section,
  SectionHeading,
} from "@/features/marketing/components/blocks";
import { ExamsIcon, FeesIcon } from "@/features/marketing/components/icons";
import { Reveal } from "@/features/marketing/components/reveal";
import { pageMetadata } from "@/i18n/metadata";

const PLANS = ["basic", "premium", "advanced"] as const;

export async function generateMetadata({ params }: PageProps<"/[locale]/pricing">) {
  const { locale } = await params;
  return pageMetadata(locale, "pricing", "/pricing");
}

export default async function PricingPage({ params }: PageProps<"/[locale]/pricing">) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Marketing.pricing");

  const faq = t.raw("faq") as { q: string; a: string }[];

  return (
    <>
      <PageHero
        eyebrow={t("hero.eyebrow")}
        titleLead={t("hero.titleLead")}
        words={t.raw("hero.words") as string[]}
        lede={t("hero.lede")}
        locale={locale}
        media="illustration"
        chips={[
          { icon: FeesIcon, title: t("hero.chip1a"), sub: t("hero.chip1b") },
          { icon: ExamsIcon, title: t("hero.chip2a"), sub: t("hero.chip2b") },
        ]}
      />

      <Section>
        <div className="mb-8 flex justify-center">
          <Badge tone="warning">{t("sampleBadge")}</Badge>
        </div>
        <div className="grid items-stretch gap-[18px] lg:grid-cols-3">
          {PLANS.map((plan, index) => {
            const featured = plan === "premium";
            const features = t.raw(`tiers.${plan}.features`) as string[];
            return (
              <Reveal key={plan} delayMs={index * 110} className="h-full">
                <article
                  className={cn(
                    "relative flex h-full flex-col rounded-card border bg-bg p-7 transition-[transform,box-shadow] duration-200 hover:-translate-y-[3px] hover:shadow-soft",
                    featured ? "border-2 border-navy" : "border-line",
                  )}
                >
                  {featured && (
                    <Badge tone="orange" className="absolute end-5 top-5">
                      {t("popular")}
                    </Badge>
                  )}
                  <h2 className="text-xl text-navy-deep">{t(`tiers.${plan}.name`)}</h2>
                  <p className="mt-1.5 text-sm text-ink-soft">{t(`tiers.${plan}.tagline`)}</p>
                  <p className="mt-5 flex flex-wrap items-baseline gap-x-2 text-navy-deep">
                    <bdi className="text-[34px] leading-tight font-bold tabular-nums">
                      {t(`tiers.${plan}.price`)}
                    </bdi>
                    <span className="text-sm text-ink-soft">{t("perMonth")}</span>
                  </p>
                  <ul className="mt-6 mb-7 flex flex-1 flex-col gap-3 border-t border-line pt-6 text-[14.8px] text-ink">
                    {features.map((feature) => (
                      <CheckItem key={feature}>{feature}</CheckItem>
                    ))}
                  </ul>
                  <DemoButton
                    plan={plan}
                    variant={featured ? "default" : "outline"}
                    className="w-full"
                  >
                    {t("choose")}
                  </DemoButton>
                </article>
              </Reveal>
            );
          })}
        </div>
        <p className="mx-auto mt-7 max-w-[64ch] text-center text-sm text-ink-soft">{t("note")}</p>
      </Section>

      <Section tinted>
        <SectionHeading kicker={t("faqEyebrow")} title={t("faqTitle")} />
        <div className="grid gap-[18px] sm:grid-cols-2">
          {faq.map((item, index) => (
            <Reveal key={item.q} delayMs={(index % 2) * 90} className="h-full">
              <article className="h-full rounded-card border border-line bg-bg p-[26px]">
                <h3 className="text-[17px] text-ink">{item.q}</h3>
                <p className="mt-2 text-[14.8px] text-ink-soft">{item.a}</p>
              </article>
            </Reveal>
          ))}
        </div>
      </Section>

      <CtaBox title={t("cta.title")} description={t("cta.description")} button={t("cta.button")} />
    </>
  );
}
