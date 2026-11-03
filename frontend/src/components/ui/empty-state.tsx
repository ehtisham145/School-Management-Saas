import type { ReactNode } from "react";

type EmptyStateProps = {
  title: string;
  description?: string;
  action?: ReactNode;
};

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-card border border-dashed border-line px-6 py-12 text-center">
      <p className="font-bold text-navy-deep">{title}</p>
      {description && <p className="max-w-[46ch] text-sm text-ink-soft">{description}</p>}
      {action}
    </div>
  );
}
