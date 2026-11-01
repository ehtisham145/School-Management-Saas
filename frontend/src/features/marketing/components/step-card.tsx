import { Link } from "@/i18n/navigation";
import { Reveal } from "./reveal";

type StepCardProps = {
  href: string;
  number: string;
  title: string;
  description: string;
  delayMs?: number;
};

export function StepCard({ href, number, title, description, delayMs = 0 }: StepCardProps) {
  return (
    <Reveal delayMs={delayMs} className="h-full">
      <Link
        href={href}
        className="group flex h-full flex-col gap-3 border border-border bg-card p-7 transition-colors hover:bg-accent"
      >
        <span className="font-marketing-mono text-sm font-medium tracking-[0.06em] text-[var(--mk-accent-ink)]">
          {number}
        </span>
        <h3 className="font-display text-lg font-semibold text-card-foreground">{title}</h3>
        <p className="text-sm text-muted-foreground">{description}</p>
      </Link>
    </Reveal>
  );
}
