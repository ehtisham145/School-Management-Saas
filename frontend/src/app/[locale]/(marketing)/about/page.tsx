import { getTranslations, setRequestLocale } from "next-intl/server";
import { HERO_IMAGES } from "@/features/marketing/hero-images";
import {
  CtaBox,
  FeatureCard,
  PageHero,
  Section,
  SectionHeading,
} from "@/features/marketing/components/blocks";
import {
  AdminIcon,
  AttendanceIcon,
  BilingualIcon,
  LocationIcon,
} from "@/features/marketing/components/icons";
import { Reveal } from "@/features/marketing/components/reveal";
import { pageMetadata } from "@/i18n/metadata";

const VALUE_ICONS = [BilingualIcon, AttendanceIcon, LocationIcon, AdminIcon];

export async function generateMetadata({ params }: PageProps<"/[locale]/about">) {
  const { locale } = await params;
  return pageMetadata(locale, "about", "/about");
}

export default async function AboutPage({ params }: PageProps<"/[locale]/about">) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Marketing.about");

  const paragraphs = t.raw("story.paragraphs") as string[];
  const values = t.raw("values.items") as { title: string; description: string }[];

  return (
    <>
      <PageHero
        image={HERO_IMAGES.about}
        titleLead={t("hero.titleLead")}
        words={t.raw("hero.words") as string[]}
        locale={locale}
      />

      <Section>
        <SectionHeading kicker={t("story.eyebrow")} title={t("story.title")} />
        <Reveal className="flex max-w-[68ch] flex-col gap-5 text-[16.5px] text-ink-soft">
          {paragraphs.map((paragraph) => (
            <p key={paragraph}>{paragraph}</p>
          ))}
        </Reveal>
      </Section>

      <Section tinted>
        <SectionHeading kicker={t("values.eyebrow")} title={t("values.title")} />
        <div className="grid gap-[18px] sm:grid-cols-2">
          {values.map((value, index) => (
            <FeatureCard
              key={value.title}
              icon={VALUE_ICONS[index]}
              index={index}
              title={value.title}
              description={value.description}
            />
          ))}
        </div>
      </Section>

      <CtaBox title={t("cta.title")} description={t("cta.description")} button={t("cta.button")} />
    </>
  );
}
