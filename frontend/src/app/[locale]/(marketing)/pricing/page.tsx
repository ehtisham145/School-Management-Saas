import { getTranslations, setRequestLocale } from "next-intl/server";
import { Check } from "lucide-react";
import { cn } from "cn";
import { DemoButton } from "@/features/leads/components/demo-dialog";
import { CtaBox, PageHero, Section, SectionHeading } from "@/features/marketing/components/blocks";
import { GroupIcon, PremiumIcon, SchoolIcon } from "@/features/marketing/components/icons";
import { Reveal } from "@/features/marketing/components/reveal";
import { pageMetadata } from "@/i18n/metadata";

const PLANS = ["basic", "premium", "advanced"] as const;
const PLAN_ICONS = { basic: SchoolIcon, premium: PremiumIcon, advanced: GroupIcon };

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
        image="/images/pricing.jpg"
        titleLead={t("hero.titleLead")}
        words={t.raw("hero.words") as string[]}
        locale={locale}
      />

      <Section>
        <div className="grid items-stretch gap-6 pt-4 lg:grid-cols-3 lg:gap-5">
          {PLANS.map((plan, index) => {
            const featured = plan === "premium";
            const features = t.raw(`tiers.${plan}.features`) as string[];
            const PlanIcon = PLAN_ICONS[plan];
            return (
              <Reveal key={plan} delayMs={index * 110} className="h-full">
                <article
                  className={cn(
                    "relative isolate flex h-full flex-col overflow-hidden rounded-cta border p-8 transition-[transform,box-shadow] duration-300 hover:-translate-y-1.5 hover:shadow-soft",
                    featured
                      ? "border-navy-deep bg-navy-deep text-on-dark shadow-soft lg:-my-3 lg:py-11"
                      : "border-line bg-bg text-ink",
                  )}
                >
                  {/* A soft glow behind the top of the card. */}
                  <span
                    aria-hidden="true"
                    className={cn(
                      "pointer-events-none absolute -end-16 -top-20 -z-10 size-56 rounded-full blur-3xl",
                      featured ? "bg-orange opacity-30" : "bg-navy-soft opacity-80",
                    )}
                  />

                  <div className="flex items-start justify-between gap-3">
                    <span
                      className={cn(
                        "grid size-12 place-items-center rounded-tile",
                        featured ? "bg-orange text-on-orange" : "bg-navy-soft text-navy",
                      )}
                    >
                      <PlanIcon aria-hidden="true" className="size-6" />
                    </span>
                    {featured && (
                      <span className="rounded-full bg-orange px-3 py-1 text-xs font-bold text-on-orange">
                        {t("popular")}
                      </span>
                    )}
                  </div>

                  <h2
                    className={cn("mt-5 text-[22px]", featured ? "text-on-dark" : "text-navy-deep")}
                  >
                    {t(`tiers.${plan}.name`)}
                  </h2>
                  <p
                    className={cn(
                      "mt-1.5 text-sm",
                      featured ? "text-on-dark-soft" : "text-ink-soft",
                    )}
                  >
                    {t(`tiers.${plan}.tagline`)}
                  </p>

                  <p className="mt-6 flex flex-wrap items-baseline gap-x-2">
                    <bdi
                      className={cn(
                        "text-[40px] leading-tight font-bold tabular-nums",
                        featured ? "text-on-dark" : "text-navy-deep",
                      )}
                    >
                      {t(`tiers.${plan}.price`)}
                    </bdi>
                    <span
                      className={cn("text-sm", featured ? "text-on-dark-soft" : "text-ink-soft")}
                    >
                      {t("perMonth")}
                    </span>
                  </p>

                  <p
                    className={cn(
                      "mt-6 mb-4 border-t pt-6 text-[13px] font-bold",
                      featured ? "border-on-dark-line text-on-dark" : "border-line text-navy-deep",
                    )}
                  >
                    {t("includes")}
                  </p>
                  <ul className="mb-8 flex flex-1 flex-col gap-3.5 text-[14.8px]">
                    {features.map((feature) => (
                      <li key={feature} className="flex items-start gap-3">
                        <span
                          aria-hidden="true"
                          className={cn(
                            "mt-px grid size-5 shrink-0 place-items-center rounded-full",
                            featured ? "bg-orange text-on-orange" : "bg-navy-soft text-navy",
                          )}
                        >
                          <Check className="size-3" strokeWidth={3} />
                        </span>
                        <span className={featured ? "text-on-dark" : "text-ink"}>{feature}</span>
                      </li>
                    ))}
                  </ul>

                  <DemoButton
                    plan={plan}
                    variant={featured ? "orange" : "outline"}
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
