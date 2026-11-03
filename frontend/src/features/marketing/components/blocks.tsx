import Image from "next/image";
import type { ComponentType, ReactNode } from "react";
import { Check } from "lucide-react";
import { cn } from "cn";
import { DemoButton } from "@/features/leads/components/demo-dialog";
import { Reveal } from "./reveal";
import { Typewriter } from "./typewriter";

type Icon = ComponentType<{ className?: string; "aria-hidden"?: boolean }>;

export function SectionHeading({
  kicker,
  title,
  description,
}: {
  kicker: string;
  title: string;
  description?: string;
}) {
  return (
    <Reveal className="mb-11 max-w-[640px]">
      <p className="mb-2.5 text-[13.5px] font-bold text-orange-text">{kicker}</p>
      <h2 className="text-[clamp(28px,3.4vw,42px)] text-navy-deep">{title}</h2>
      {description && <p className="mt-3 text-[16.5px] text-ink-soft">{description}</p>}
    </Reveal>
  );
}

export function Section({
  id,
  tinted,
  children,
}: {
  id?: string;
  tinted?: boolean;
  children: ReactNode;
}) {
  return (
    <section id={id} className={cn("py-[clamp(64px,8vw,104px)]", tinted && "bg-bg-tint")}>
      <div className="page-wrap">{children}</div>
    </section>
  );
}

/** Icon tiles alternate between navy and orange, as in the demo. */
export function IconTile({ icon: IconComponent, index = 0 }: { icon: Icon; index?: number }) {
  return (
    <span
      className={cn(
        "grid size-[46px] place-items-center rounded-tile",
        index % 2 === 0 ? "bg-navy-soft text-navy" : "bg-orange-soft text-orange-text",
      )}
    >
      <IconComponent aria-hidden className="size-[23px]" />
    </span>
  );
}

export function FeatureCard({
  icon,
  index,
  title,
  description,
}: {
  icon: Icon;
  index: number;
  title: string;
  description: string;
}) {
  return (
    <Reveal delayMs={(index % 3) * 90} className="h-full">
      <article className="h-full rounded-card border border-line bg-bg p-[26px] transition-[transform,box-shadow,border-color] duration-200 hover:-translate-y-[3px] hover:border-navy-line hover:shadow-soft">
        <IconTile icon={icon} index={index} />
        <h3 className="mt-4 text-[18.5px] text-ink">{title}</h3>
        <p className="mt-2 text-[14.8px] text-ink-soft">{description}</p>
      </article>
    </Reveal>
  );
}

export function CheckItem({ children }: { children: ReactNode }) {
  return (
    <li className="flex items-start gap-2.5">
      <Check aria-hidden="true" className="mt-[3px] size-[18px] shrink-0 text-orange-text" />
      <span>{children}</span>
    </li>
  );
}

export type HeroChip = { icon: Icon; title: string; sub: string };

export function StatusChip({
  chip,
  tone,
  className,
}: {
  chip: HeroChip;
  tone: "navy" | "orange";
  className?: string;
}) {
  const IconComponent = chip.icon;
  return (
    <div
      aria-hidden="true"
      className={cn(
        "absolute z-[1] flex animate-float items-center gap-[7px] rounded-[11px] bg-bg px-2.5 py-[7px] text-ink shadow-chip sm:gap-2.5 sm:rounded-[14px] sm:px-3.5 sm:py-2.5",
        className,
      )}
    >
      <span
        className={cn(
          "grid size-[26px] shrink-0 place-items-center rounded-lg sm:size-[34px] sm:rounded-control",
          tone === "navy" ? "bg-navy-soft text-navy" : "bg-orange-soft text-orange-text",
        )}
      >
        <IconComponent className="size-3.5 sm:size-[18px]" />
      </span>
      <div>
        <b className="block text-xs font-bold whitespace-nowrap sm:text-sm">{chip.title}</b>
        <span className="block text-[10.5px] whitespace-nowrap text-ink-soft sm:text-xs">
          {chip.sub}
        </span>
      </div>
    </div>
  );
}

export function PageHero({
  eyebrow,
  titleLead,
  words,
  lede,
  locale,
  media,
  chips,
}: {
  eyebrow: string;
  titleLead: string;
  words: string[];
  lede: string;
  locale: string;
  media: "photo" | "illustration";
  chips: [HeroChip, HeroChip];
}) {
  return (
    <section className="border-b border-line bg-bg-tint">
      <div className="page-wrap grid items-center gap-10 py-[clamp(40px,5vw,72px)] lg:grid-cols-[1.05fr_0.95fr] lg:gap-14">
        <div className="min-w-0">
          <span className="inline-flex items-center gap-2 rounded-full bg-orange-soft px-[13px] py-1.5 text-[13px] font-bold text-orange-text">
            <i aria-hidden="true" className="size-[7px] rounded-full bg-orange" />
            {eyebrow}
          </span>
          <h1 className="mt-5 text-[clamp(34px,4.2vw,54px)] text-navy-deep">
            {titleLead} <Typewriter words={words} locale={locale} className="text-orange-text" />
          </h1>
          <p className="mt-[18px] max-w-[56ch] text-[clamp(16px,1.35vw,18px)] text-ink-soft">
            {lede}
          </p>
        </div>

        <div className="relative mx-auto w-full max-w-[560px] lg:max-w-none">
          <div
            className={cn(
              "relative aspect-[4/3] overflow-hidden rounded-cta",
              media === "illustration" && "bg-navy-deep",
            )}
          >
            {media === "photo" ? (
              <Image
                src="/brand/hero.jpg"
                alt=""
                fill
                priority
                sizes="(max-width: 1040px) 560px, 45vw"
                className="object-cover object-[80%_center]"
              />
            ) : (
              <Image
                src="/brand/sign-in.webp"
                alt=""
                fill
                priority
                sizes="(max-width: 1040px) 560px, 45vw"
                className="mask-[radial-gradient(closest-side,black_72%,transparent_100%)] object-contain p-4"
              />
            )}
          </div>
          <StatusChip chip={chips[0]} tone="navy" className="start-3 top-4 sm:-start-3 sm:top-6" />
          <StatusChip
            chip={chips[1]}
            tone="orange"
            className="end-3 bottom-4 [animation-delay:-3s] sm:-end-3 sm:bottom-6"
          />
        </div>
      </div>
    </section>
  );
}

function CtaFrame({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <section className="py-[clamp(64px,8vw,104px)]">
      <div className="page-wrap">
        <Reveal>
          <div className="flex flex-wrap items-center justify-between gap-6 rounded-cta bg-navy-deep p-[clamp(30px,5vw,54px)] text-on-dark">
            <div className="min-w-0 flex-[1_1_320px]">
              <h2 className="max-w-[20ch] text-[clamp(26px,3vw,38px)]">{title}</h2>
              <p className="mt-2.5 max-w-[46ch] text-on-dark-soft">{description}</p>
            </div>
            {children}
          </div>
        </Reveal>
      </div>
    </section>
  );
}

export function CtaBox({
  title,
  description,
  button,
}: {
  title: string;
  description: string;
  button: string;
}) {
  return (
    <CtaFrame title={title} description={description}>
      <DemoButton variant="orange" className="w-full sm:w-auto">
        {button}
      </DemoButton>
    </CtaFrame>
  );
}

export function CtaLinkBox({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <CtaFrame title={title} description={description}>
      {children}
    </CtaFrame>
  );
}
