import type { ReactNode } from "react";
import { cn } from "cn";

type SectionHeadingProps = {
  eyebrow: string;
  title: ReactNode;
  description?: string;
  className?: string;
};

export function SectionHeading({ eyebrow, title, description, className }: SectionHeadingProps) {
  return (
    <div className={cn("max-w-[56ch]", className)}>
      <span className="font-marketing-mono inline-flex items-center gap-2 text-xs font-medium tracking-[0.14em] text-[var(--mk-accent-ink)] uppercase before:h-px before:w-[1.1em] before:bg-current">
        {eyebrow}
      </span>
      <h2 className="font-display mt-3 text-3xl font-semibold text-balance text-foreground sm:text-4xl">
        {title}
      </h2>
      {description && (
        <p className="mt-4 max-w-[60ch] text-base text-muted-foreground">{description}</p>
      )}
    </div>
  );
}
