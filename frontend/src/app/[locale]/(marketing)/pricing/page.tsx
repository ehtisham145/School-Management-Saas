import { getTranslations, setRequestLocale } from "next-intl/server";
import { cn } from "cn";
import { HERO_IMAGES } from "@/features/marketing/hero-images";
import { DemoButton } from "@/features/leads/components/demo-dialog";
import type { Plan } from "@/features/leads/api";
import { CtaBox, PageHero, Section, SectionHeading } from "@/features/marketing/components/blocks";
import { PricingTabs } from "@/features/marketing/components/pricing-tabs";
import { Reveal } from "@/features/marketing/components/reveal";
import { pageMetadata } from "@/i18n/metadata";

type CardSpec = {
  plan: Plan;
  featured?: boolean;
  period?: "perYear" | "perMonth";
  cta: "bookDemo" | "talkToUs" | "requestAccess";
};

// Schools pay yearly, teachers monthly. The Custom plan has no list price.
const SCHOOL_PLANS: CardSpec[] = [
  { plan: "basic", period: "perYear", cta: "bookDemo" },
  { plan: "premium", period: "perYear", cta: "bookDemo", featured: true },
  { plan: "custom", cta: "talkToUs" },
];
const TEACHER_PLANS: CardSpec[] = [
  { plan: "teacher", period: "perMonth", cta: "requestAccess" },
  { plan: "teacher_pro", period: "perMonth", cta: "requestAccess", featured: true },
];

export async function generateMetadata({ params }: PageProps<"/[locale]/pricing">) {
  const { locale } = await params;
  return pageMetadata(locale, "pricing", "/pricing");
}

async function PlanCard({ spec, index }: { spec: CardSpec; index: number }) {
  const t = await getTranslations("Marketing.pricing");
  const { plan, featured = false, period, cta } = spec;
  const features = t.raw(`tiers.${plan}.features`) as string[];

  return (
    <Reveal delayMs={index * 110} className="h-full">
      <article
        className={cn(
          "relative flex h-full flex-col rounded-cta border p-8",
          featured
            ? "border-navy-deep bg-navy-deep text-on-dark shadow-soft"
            : "border-line bg-bg text-ink",
        )}
      >
        {featured && (
          <p className="absolute start-8 -top-3 rounded-full bg-orange px-3 py-1 text-xs font-bold text-on-orange">
            {t("popular")}
          </p>
        )}

        <h2 className={cn("text-[22px]", featured ? "text-on-dark" : "text-navy-deep")}>
          {t(`tiers.${plan}.name`)}
        </h2>
        <p className={cn("mt-1.5 text-[14.5px]", featured ? "text-on-dark-soft" : "text-ink-soft")}>
          {t(`tiers.${plan}.tagline`)}
        </p>

        <p className="mt-7 flex flex-wrap items-baseline gap-x-2">
          <bdi
            className={cn(
              "leading-tight font-bold tabular-nums",
              period ? "text-[38px]" : "text-[30px]",
              featured ? "text-on-dark" : "text-navy-deep",
            )}
          >
            {t(`tiers.${plan}.price`)}
          </bdi>
          {period && (
            <span className={cn("text-sm", featured ? "text-on-dark-soft" : "text-ink-soft")}>
              {t(period)}
            </span>
          )}
        </p>
        <p className={cn("mt-1 text-[13px]", featured ? "text-on-dark-soft" : "text-ink-soft")}>
          {t(`tiers.${plan}.billing`)}
        </p>

        <DemoButton plan={plan} variant={featured ? "orange" : "outline"} className="mt-7 w-full">
          {t(cta)}
        </DemoButton>

        <p
          className={cn(
            "mt-8 mb-4 border-t pt-6 text-[13px] font-bold",
            featured ? "border-on-dark-line text-on-dark" : "border-line text-navy-deep",
          )}
        >
          {t("includes")}
        </p>
        <ul className="flex flex-1 flex-col gap-3 text-[14.8px]">
          {features.map((feature) => (
            <li key={feature} className="flex items-start gap-3">
              <span
                aria-hidden="true"
                className="mt-[9px] size-1.5 shrink-0 rounded-full bg-orange"
              />
              <span className={featured ? "text-on-dark" : "text-ink"}>{feature}</span>
            </li>
          ))}
        </ul>
      </article>
    </Reveal>
  );
}

async function PlanGroup({
  intro,
  note,
  plans,
  className,
}: {
  intro: string;
  note: string;
  plans: CardSpec[];
  className: string;
}) {
  return (
    <>
      <p className="mx-auto max-w-[60ch] text-center text-[16.5px] text-ink-soft">{intro}</p>
      <div className={cn("mt-10 grid items-stretch gap-6", className)}>
        {plans.map((spec, index) => (
          <PlanCard key={spec.plan} spec={spec} index={index} />
        ))}
      </div>
      <p className="mx-auto mt-8 max-w-[70ch] text-center text-sm text-ink-soft">{note}</p>
    </>
  );
}

export default async function PricingPage({ params }: PageProps<"/[locale]/pricing">) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Marketing.pricing");

  const faq = t.raw("faq") as { q: string; a: string }[];

  return (
    <>
      <PageHero
        image={HERO_IMAGES.pricing}
        titleLead={t("hero.titleLead")}
        words={t.raw("hero.words") as string[]}
        locale={locale}
      />

      <Section>
        <PricingTabs
          label={t("tabs.label")}
          tabs={[
            {
              key: "schools",
              label: t("tabs.schools"),
              panel: (
                <PlanGroup
                  intro={t("schoolsIntro")}
                  note={t("schoolsNote")}
                  plans={SCHOOL_PLANS}
                  className="lg:grid-cols-3"
                />
              ),
            },
            {
              key: "teachers",
              label: t("tabs.teachers"),
              panel: (
                <PlanGroup
                  intro={t("teachersIntro")}
                  note={t("teachersNote")}
                  plans={TEACHER_PLANS}
                  className="mx-auto max-w-[860px] md:grid-cols-2"
                />
              ),
            },
          ]}
        />
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
