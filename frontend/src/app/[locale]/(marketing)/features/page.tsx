import type { ComponentType, SVGProps } from "react";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { buttonVariants } from "@/components/ui/button";
import { PageHero } from "@/features/marketing/components/page-hero";
import { SectionHeading } from "@/features/marketing/components/section-heading";
import { FeatureCard } from "@/features/marketing/components/feature-card";
import { Reveal } from "@/features/marketing/components/reveal";
import {
  AttendanceIcon,
  ExamsIcon,
  FeesIcon,
  TimetableIcon,
  MessagesIcon,
  BilingualIcon,
  CheckIcon,
} from "@/features/marketing/icons";

type Group = {
  tag: string;
  blurb: string;
  title: string;
  description: string;
  bullets: string[];
};

const GROUPS = [
  { key: "attendance", icon: AttendanceIcon },
  { key: "exams", icon: ExamsIcon },
  { key: "fees", icon: FeesIcon },
  { key: "timetable", icon: TimetableIcon },
  { key: "messages", icon: MessagesIcon },
  { key: "bilingual", icon: BilingualIcon },
] as const satisfies ReadonlyArray<{ key: string; icon: ComponentType<SVGProps<SVGSVGElement>> }>;

export default async function FeaturesPage({ params }: PageProps<"/[locale]/features">) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Marketing.features");

  const words = t.raw("hero.words") as string[];
  const groups = t.raw("groups") as Record<string, Group>;

  return (
    <>
      <PageHero
        eyebrow={t("hero.eyebrow")}
        titleLead={t("hero.titleLead")}
        words={words}
        lede={t("hero.lede")}
      />

      <section className="mx-auto max-w-6xl px-6 py-20 sm:py-24">
        <SectionHeading eyebrow={t("gridEyebrow")} title={t("gridTitle")} className="mb-12" />
        <div className="grid gap-px overflow-hidden border border-border bg-border sm:grid-cols-2 lg:grid-cols-3">
          {GROUPS.map(({ key, icon }, index) => {
            const group = groups[key];
            return (
              <FeatureCard
                key={key}
                href={`#${key}`}
                icon={icon}
                title={group.tag}
                description={group.blurb}
                delayMs={(index % 3) * 90}
              />
            );
          })}
        </div>
      </section>

      {GROUPS.map(({ key, icon: Icon }, index) => {
        const group = groups[key];
        const alt = index % 2 === 1;
        return (
          <section
            key={key}
            id={key}
            className={`scroll-mt-20 border-t border-border ${alt ? "bg-muted" : ""}`}
          >
            <div className="mx-auto grid max-w-6xl gap-10 px-6 py-16 sm:py-20 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
              <Reveal className={alt ? "lg:order-2" : undefined}>
                <span className="flex h-12 w-12 items-center justify-center rounded-[var(--radius)] border border-[var(--mk-line-strong)] bg-card text-primary">
                  <Icon className="h-6 w-6" />
                </span>
                <span className="font-marketing-mono mt-5 block text-xs font-medium tracking-[0.12em] text-[var(--mk-accent-ink)] uppercase">
                  {group.tag}
                </span>
                <h2 className="font-display mt-2 max-w-[20ch] text-2xl font-semibold text-balance text-foreground sm:text-3xl">
                  {group.title}
                </h2>
                <p className="mt-4 max-w-[48ch] text-muted-foreground">{group.description}</p>
              </Reveal>

              <Reveal delayMs={120} className={alt ? "lg:order-1" : undefined}>
                <ul className="flex flex-col gap-4 border border-border bg-card p-7">
                  {group.bullets.map((bullet) => (
                    <li key={bullet} className="flex items-start gap-3">
                      <CheckIcon className="mt-0.5 h-5 w-5 shrink-0 text-[var(--mk-teal)]" />
                      <span className="text-sm text-card-foreground">{bullet}</span>
                    </li>
                  ))}
                </ul>
              </Reveal>
            </div>
          </section>
        );
      })}

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
