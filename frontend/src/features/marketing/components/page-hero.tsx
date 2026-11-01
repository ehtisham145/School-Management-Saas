import type { ReactNode } from "react";
import { Typewriter } from "./typewriter";

type PageHeroProps = {
  eyebrow: string;
  titleLead: string;
  words: string[];
  lede: string;
  children?: ReactNode;
};

export function PageHero({ eyebrow, titleLead, words, lede, children }: PageHeroProps) {
  return (
    <section className="border-b border-border">
      <div className="mx-auto max-w-4xl px-6 py-20 sm:py-28">
        <span className="inline-flex items-center gap-2 font-marketing-mono text-xs font-medium tracking-[0.14em] text-[var(--mk-accent-ink)] uppercase before:h-px before:w-[1.1em] before:bg-current">
          {eyebrow}
        </span>
        <h1 className="mt-4 text-balance font-display text-4xl leading-[1.12] font-semibold text-foreground sm:text-5xl">
          {titleLead}
          <br />
          <Typewriter words={words} className="text-primary" />
        </h1>
        <p className="mt-6 max-w-[55ch] text-lg text-muted-foreground">{lede}</p>
        {children && <div className="mt-8 flex flex-wrap gap-3">{children}</div>}
      </div>
    </section>
  );
}
