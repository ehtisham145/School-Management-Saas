import { getTranslations, setRequestLocale } from "next-intl/server";
import {
  CtaBox,
  FeatureCard,
  IconTile,
  PhotoHero,
  Section,
  SectionHeading,
} from "@/features/marketing/components/blocks";
import {
  AdminIcon,
  AttendanceIcon,
  BilingualIcon,
  ExamsIcon,
  FeesIcon,
  MessagesIcon,
  ParentIcon,
  PrincipalIcon,
  StudentIcon,
  TeacherIcon,
  TimetableIcon,
} from "@/features/marketing/components/icons";
import { Reveal } from "@/features/marketing/components/reveal";
import { Typewriter } from "@/features/marketing/components/typewriter";
import { pageMetadata } from "@/i18n/metadata";

const FEATURES = [
  { icon: AttendanceIcon, title: "att", description: "attD" },
  { icon: ExamsIcon, title: "exam", description: "examD" },
  { icon: FeesIcon, title: "fee", description: "feeD" },
  { icon: TimetableIcon, title: "time", description: "timeD" },
  { icon: MessagesIcon, title: "msg", description: "msgD" },
  { icon: BilingualIcon, title: "lang", description: "langD" },
] as const;

const ROLES = [
  { icon: AdminIcon, title: "admin", description: "adminD" },
  { icon: PrincipalIcon, title: "principal", description: "principalD" },
  { icon: TeacherIcon, title: "teacher", description: "teacherD" },
  { icon: StudentIcon, title: "student", description: "studentD" },
  { icon: ParentIcon, title: "parent", description: "parentD" },
] as const;

const STRIP = [
  { key: "a", className: "ps-0 sm:ps-0" },
  { key: "b", className: "border-s" },
  { key: "c", className: "border-t ps-0 sm:ps-0 lg:border-s lg:border-t-0 lg:ps-[22px]" },
  { key: "d", className: "border-s border-t lg:border-t-0" },
] as const;
const STEPS = ["s1", "s2", "s3"] as const;

export async function generateMetadata({ params }: PageProps<"/[locale]">) {
  const { locale } = await params;
  return pageMetadata(locale, "home", "");
}

export default async function HomePage({ params }: PageProps<"/[locale]">) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Marketing.home");

  return (
    <>
      <PhotoHero image="/images/home.jpg" alt={t("hero.alt")}>
        <Typewriter
          words={t.raw("hero.words") as string[]}
          highlights={t.raw("hero.highlights") as string[]}
          locale={locale}
          onPhoto
        />
      </PhotoHero>

      <section aria-label={t("hero.eyebrow")} className="bg-navy-deep text-on-dark">
        <div className="page-wrap grid grid-cols-2 lg:grid-cols-4">
          {STRIP.map(({ key, className }) => (
            <div
              key={key}
              className={`border-on-dark-line px-3.5 py-[18px] sm:px-[22px] sm:py-6 ${className}`}
            >
              <b className="block text-[17px] font-bold">{t(`strip.${key}1`)}</b>
              <span className="text-[13.5px] text-on-dark-soft">{t(`strip.${key}2`)}</span>
            </div>
          ))}
        </div>
      </section>

      <Section id="features">
        <SectionHeading
          kicker={t("features.kicker")}
          title={t("features.title")}
          description={t("features.sub")}
        />
        <div className="grid gap-[18px] sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature, index) => (
            <FeatureCard
              key={feature.title}
              icon={feature.icon}
              index={index}
              title={t(`f.${feature.title}`)}
              description={t(`f.${feature.description}`)}
            />
          ))}
        </div>
      </Section>

      <Section tinted>
        <SectionHeading kicker={t("roles.kicker")} title={t("roles.title")} />
        <div className="grid grid-cols-2 gap-3.5 sm:grid-cols-3 lg:grid-cols-5">
          {ROLES.map((role, index) => (
            <Reveal
              key={role.title}
              delayMs={index * 80}
              className="h-full last:col-span-2 sm:last:col-span-1"
            >
              <article className="h-full rounded-[14px] border border-line bg-bg px-[18px] py-[22px]">
                <IconTile icon={role.icon} index={index} />
                <h3 className="mt-3 text-base text-ink">{t(`r.${role.title}`)}</h3>
                <p className="mt-1.5 text-[13.5px] text-ink-soft">{t(`r.${role.description}`)}</p>
              </article>
            </Reveal>
          ))}
        </div>
      </Section>

      <Section id="how">
        <SectionHeading kicker={t("how.kicker")} title={t("how.title")} />
        <ol className="grid gap-[18px] sm:grid-cols-2 lg:grid-cols-3">
          {STEPS.map((step, index) => (
            <li key={step}>
              <Reveal delayMs={index * 110} className="border-t-[3px] border-navy pt-[22px]">
                <span className="grid size-[38px] place-items-center rounded-full bg-orange font-bold text-on-orange tabular-nums">
                  {index + 1}
                </span>
                <h3 className="mt-4 text-[18.5px] text-ink">{t(`how.${step}`)}</h3>
                <p className="mt-2 text-[14.8px] text-ink-soft">{t(`how.${step}d`)}</p>
              </Reveal>
            </li>
          ))}
        </ol>
      </Section>

      <CtaBox title={t("cta.title")} description={t("cta.sub")} button={t("cta.btn")} />
    </>
  );
}
