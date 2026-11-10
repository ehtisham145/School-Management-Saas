import { getTranslations, setRequestLocale } from "next-intl/server";
import {
  CheckItem,
  CtaBox,
  IconTile,
  PageHero,
  Section,
  SectionHeading,
} from "@/features/marketing/components/blocks";
import {
  AttendanceIcon,
  BilingualIcon,
  ExamsIcon,
  FeesIcon,
  MessagesIcon,
  TimetableIcon,
} from "@/features/marketing/components/icons";
import { Reveal } from "@/features/marketing/components/reveal";
import { pageMetadata } from "@/i18n/metadata";

const GROUPS = [
  { key: "attendance", icon: AttendanceIcon },
  { key: "exams", icon: ExamsIcon },
  { key: "fees", icon: FeesIcon },
  { key: "timetable", icon: TimetableIcon },
  { key: "messages", icon: MessagesIcon },
  { key: "bilingual", icon: BilingualIcon },
] as const;

export async function generateMetadata({ params }: PageProps<"/[locale]/lms">) {
  const { locale } = await params;
  return pageMetadata(locale, "lms", "/lms");
}

export default async function LmsPage({ params }: PageProps<"/[locale]/lms">) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Marketing.lms");

  return (
    <>
      <PageHero
        image="/images/lms.jpg"
        titleLead={t("hero.titleLead")}
        words={t.raw("hero.words") as string[]}
        locale={locale}
      />

      <Section>
        <SectionHeading kicker={t("gridEyebrow")} title={t("gridTitle")} />
        <div className="grid gap-[18px] sm:grid-cols-2 lg:grid-cols-3">
          {GROUPS.map(({ key, icon }, index) => (
            <Reveal key={key} delayMs={(index % 3) * 90} className="h-full">
              <a
                href={`#${key}`}
                className="block h-full rounded-card border border-line bg-bg p-[26px] transition-[transform,box-shadow,border-color] duration-200 hover:-translate-y-[3px] hover:border-navy-line hover:shadow-soft"
              >
                <IconTile icon={icon} index={index} />
                <h3 className="mt-4 text-[18.5px] text-ink">{t(`groups.${key}.tag`)}</h3>
                <p className="mt-2 text-[14.8px] text-ink-soft">{t(`groups.${key}.blurb`)}</p>
              </a>
            </Reveal>
          ))}
        </div>
      </Section>

      {GROUPS.map(({ key, icon }, index) => {
        const bullets = t.raw(`groups.${key}.bullets`) as string[];
        return (
          <section
            key={key}
            id={key}
            className={index % 2 === 0 ? "border-t border-line bg-bg-tint" : "border-t border-line"}
          >
            <div className="page-wrap grid gap-8 py-[clamp(48px,6vw,80px)] lg:grid-cols-2 lg:items-center lg:gap-12">
              <Reveal>
                <IconTile icon={icon} index={index} />
                <p className="mt-5 text-[13.5px] font-bold text-orange-text">
                  {t(`groups.${key}.tag`)}
                </p>
                <h2 className="mt-2 max-w-[22ch] text-[clamp(24px,2.6vw,32px)] text-navy-deep">
                  {t(`groups.${key}.title`)}
                </h2>
                <p className="mt-3.5 max-w-[52ch] text-ink-soft">
                  {t(`groups.${key}.description`)}
                </p>
              </Reveal>
              <Reveal delayMs={120}>
                <ul className="flex flex-col gap-4 rounded-card border border-line bg-bg p-[26px] text-[14.8px] text-ink">
                  {bullets.map((bullet) => (
                    <CheckItem key={bullet}>{bullet}</CheckItem>
                  ))}
                </ul>
              </Reveal>
            </div>
          </section>
        );
      })}

      <CtaBox title={t("cta.title")} description={t("cta.description")} button={t("cta.button")} />
    </>
  );
}
