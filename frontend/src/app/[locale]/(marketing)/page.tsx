import { getTranslations, setRequestLocale } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "cn";
import { Typewriter } from "@/features/marketing/components/typewriter";
import { Reveal } from "@/features/marketing/components/reveal";
import { FeatureCard } from "@/features/marketing/components/feature-card";
import { StepCard } from "@/features/marketing/components/step-card";
import { SectionHeading } from "@/features/marketing/components/section-heading";
import { RecordCardStack } from "@/features/marketing/components/record-card-stack";
import {
  AttendanceIcon,
  ExamsIcon,
  FeesIcon,
  TimetableIcon,
  MessagesIcon,
  BilingualIcon,
} from "@/features/marketing/icons";

const FEATURE_ICONS = [AttendanceIcon, ExamsIcon, FeesIcon, TimetableIcon, MessagesIcon, BilingualIcon];
const FEATURE_ANCHORS = [
  "/features#attendance",
  "/features#exams",
  "/features#fees",
  "/features#timetable",
  "/features#messages",
  "/features#bilingual",
];

type FeatureItem = { title: string; description: string };
type StepItem = { title: string; description: string };

export default async function HomePage({ params }: PageProps<"/[locale]">) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Marketing.home");

  const words = t.raw("hero.words") as string[];
  const chips = t.raw("trust.chips") as string[];
  const featureItems = t.raw("features.items") as FeatureItem[];
  const steps = t.raw("how.steps") as StepItem[];

  return (
    <>
      <section className="relative overflow-hidden border-b border-border">
        <div className="mx-auto grid max-w-6xl gap-12 px-6 py-20 sm:py-28 lg:grid-cols-[1.08fr_0.92fr] lg:items-center">
          <div>
            <span className="inline-flex items-center gap-2 font-marketing-mono text-xs font-medium tracking-[0.14em] text-[var(--mk-accent-ink)] uppercase before:h-px before:w-[1.1em] before:bg-current">
              {t("hero.eyebrow")}
            </span>
            <h1 className="mt-4 text-balance font-display text-4xl leading-[1.08] font-semibold text-foreground sm:text-6xl">
              {t("hero.titleLead")}
              <br />
              <Typewriter words={words} className="text-primary" />
            </h1>
            <p className="mt-6 max-w-[46ch] text-lg text-muted-foreground">{t("hero.lede")}</p>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/contact" className={buttonVariants({ size: "lg" })}>
                {t("hero.ctaPrimary")}
              </Link>
              <Link href="/features" className={buttonVariants({ variant: "outline", size: "lg" })}>
                {t("hero.ctaSecondary")}
              </Link>
            </div>

            <div className="mt-10 flex flex-wrap gap-8 border-t border-border pt-7">
              <div>
                <b className="font-marketing-mono text-xl text-foreground">{t("hero.statAr")}</b>
                <p className="mt-1 text-xs text-[var(--mk-ink-faint)]">{t("hero.statArLabel")}</p>
              </div>
              <div>
                <b className="font-marketing-mono text-xl text-foreground">{t("hero.statHijri")}</b>
                <p className="mt-1 text-xs text-[var(--mk-ink-faint)]">{t("hero.statHijriLabel")}</p>
              </div>
              <div>
                <b className="font-marketing-mono text-xl text-foreground">{t("hero.statRoles")}</b>
                <p className="mt-1 text-xs text-[var(--mk-ink-faint)]">{t("hero.statRolesLabel")}</p>
              </div>
            </div>
          </div>

          <RecordCardStack
            timetableLabel={t("heroCards.timetableLabel")}
            timetableValue={t("heroCards.timetableValue")}
            feesLabel={t("heroCards.feesLabel")}
            feesValue={t("heroCards.feesValue")}
            attendanceLabel={t("heroCards.attendanceLabel")}
            attendanceValue={t("heroCards.attendanceValue")}
          />
        </div>
      </section>

      <div className="border-b border-border bg-muted">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-10 gap-y-4 px-6 py-7">
          <p className="max-w-[30ch] font-display text-base text-muted-foreground">{t("trust.lead")}</p>
          <ul className="flex flex-wrap gap-2.5">
            {chips.map((chip) => (
              <li
                key={chip}
                className="border border-[var(--mk-line-strong)] bg-card px-3.5 py-1.5 font-marketing-mono text-xs text-muted-foreground"
              >
                {chip}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <section className="mx-auto max-w-6xl px-6 py-20 sm:py-28">
        <SectionHeading
          eyebrow={t("features.eyebrow")}
          title={t("features.title")}
          className="mb-12"
        />
        <div className="grid gap-px overflow-hidden border border-border bg-border sm:grid-cols-2 lg:grid-cols-3">
          {featureItems.map((item, index) => (
            <FeatureCard
              key={item.title}
              href={FEATURE_ANCHORS[index]}
              icon={FEATURE_ICONS[index]}
              title={item.title}
              description={item.description}
              delayMs={(index % 3) * 90}
            />
          ))}
        </div>
      </section>

      <section className="border-t border-border bg-muted">
        <div className="mx-auto max-w-6xl px-6 py-20 sm:py-28">
          <SectionHeading eyebrow={t("how.eyebrow")} title={t("how.title")} className="mb-12" />
          <div className="grid gap-px overflow-hidden border border-border bg-border sm:grid-cols-3">
            {steps.map((step, index) => (
              <StepCard
                key={step.title}
                href="/contact"
                number={String(index + 1).padStart(2, "0")}
                title={step.title}
                description={step.description}
                delayMs={index * 90}
              />
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-20 sm:py-28">
        <Reveal>
          <div className="border border-border bg-card p-8 sm:p-14">
            <blockquote className="max-w-[46ch] text-balance font-display text-xl font-medium text-foreground sm:text-2xl">
              &ldquo;{t("quote.text")}&rdquo;
            </blockquote>
            <div className="mt-6 flex items-center gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--mk-teal-soft)] font-display text-sm font-bold text-[var(--mk-teal)]">
                P
              </span>
              <cite className="text-sm text-muted-foreground not-italic">{t("quote.attribution")}</cite>
            </div>
            <p className="mt-5 font-marketing-mono text-xs text-[var(--mk-ink-faint)]">
              {t("quote.sampleNote")}
            </p>
          </div>
        </Reveal>
      </section>

      <section className="bg-[var(--mk-band-bg)] text-[var(--mk-band-text)]">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-8 px-6 py-16 sm:py-20">
          <div>
            <h2 className="max-w-[18ch] text-balance font-display text-3xl font-semibold text-[var(--mk-band-text)] sm:text-4xl">
              {t("cta.title")}
            </h2>
            <p className="mt-3 max-w-[42ch] text-[var(--mk-band-text)] opacity-80">
              {t("cta.description")}
            </p>
          </div>
          <Link href="/contact" className={cn(buttonVariants({ size: "lg" }))}>
            {t("cta.button")}
          </Link>
        </div>
      </section>
    </>
  );
}
