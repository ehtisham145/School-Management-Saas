import type { ComponentProps } from "react";
import { cn } from "cn";

const TONES = {
  success: "bg-emerald-50 text-emerald-800",
  warning: "bg-amber-50 text-amber-800",
  danger: "bg-red-50 text-red-800",
  info: "bg-sky-50 text-sky-800",
  neutral: "bg-slate-100 text-slate-700",
  navy: "bg-navy-soft text-navy",
  orange: "bg-orange-soft text-orange-text",
} as const;

type BadgeProps = ComponentProps<"span"> & { tone?: keyof typeof TONES };

export function Badge({ tone = "neutral", className, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex w-fit items-center rounded-full px-2.5 py-0.5 text-xs font-bold",
        TONES[tone],
        className,
      )}
      {...props}
    />
  );
}
