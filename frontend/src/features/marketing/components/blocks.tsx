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

/**
 * Full-width photo with only the page heading over it. The heading is light
 * text with a dark shadow, so it reads on any part of the photo without a
 * wash over the image.
 */
export function PhotoHero({
  image,
  alt = "",
  children,
}: {
  image: string;
  alt?: string;
  children: ReactNode;
}) {
  return (
    <section className="relative flex min-h-[clamp(360px,48vw,620px)] items-start overflow-hidden bg-navy-deep">
      <Image
        src={image}
        alt={alt}
        fill
        priority
        sizes="100vw"
        className="object-cover object-center"
      />
      <div className="page-wrap relative z-[1] pt-[clamp(40px,7vw,104px)] pb-12">
        <h1 className="hero-on-photo max-w-[min(100%,680px)] text-[clamp(34px,4.5vw,58px)] text-on-dark">
          {children}
        </h1>
      </div>
    </section>
  );
}

export function PageHero({
  image,
  titleLead,
  words,
  locale,
}: {
  image: string;
  titleLead: string;
  words: string[];
  locale: string;
}) {
  return (
    <PhotoHero image={image}>
      {titleLead} <Typewriter words={words} locale={locale} onPhoto className="text-orange" />
    </PhotoHero>
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
