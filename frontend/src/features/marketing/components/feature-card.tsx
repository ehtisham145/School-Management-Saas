import type { ComponentType, SVGProps } from "react";
import { Link } from "@/i18n/navigation";
import { Reveal } from "./reveal";
import { ArrowIcon } from "../icons";

type FeatureCardProps = {
  href: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  title: string;
  description: string;
  delayMs?: number;
};

export function FeatureCard({ href, icon: Icon, title, description, delayMs = 0 }: FeatureCardProps) {
  return (
    <Reveal delayMs={delayMs} className="h-full">
      <Link
        href={href}
        className="group relative flex h-full flex-col gap-3 border border-border bg-card p-7 transition-colors hover:bg-accent focus-visible:bg-accent"
      >
        <span className="flex h-11 w-11 items-center justify-center rounded-[var(--radius)] border border-[var(--mk-line-strong)] text-muted-foreground transition-colors group-hover:border-primary group-hover:text-primary">
          <Icon className="h-[22px] w-[22px]" />
        </span>
        <h3 className="font-display text-lg font-semibold text-card-foreground">{title}</h3>
        <p className="max-w-[34ch] text-sm text-muted-foreground">{description}</p>
        <ArrowIcon className="absolute top-7 end-7 h-4 w-4 text-[var(--mk-ink-faint)] opacity-0 transition-all group-hover:translate-x-[3px] group-hover:-translate-y-[3px] group-hover:opacity-100 rtl:group-hover:-translate-x-[3px] rtl:group-hover:translate-y-[-3px]" />
      </Link>
    </Reveal>
  );
}
