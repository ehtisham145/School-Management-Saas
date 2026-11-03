import type { ComponentProps } from "react";
import { cn } from "cn";

/** Wide tables scroll inside this container, never the whole page. */
export function Table({ className, ...props }: ComponentProps<"table">) {
  return (
    <div className="overflow-x-auto rounded-card border border-line">
      <table className={cn("w-full text-sm tabular-nums", className)} {...props} />
    </div>
  );
}

export function TableHead({ className, ...props }: ComponentProps<"thead">) {
  return <thead className={cn("bg-bg-tint text-ink-soft", className)} {...props} />;
}

export function TableRow({ className, ...props }: ComponentProps<"tr">) {
  return <tr className={cn("border-t border-line first:border-t-0", className)} {...props} />;
}

export function TableHeaderCell({ className, ...props }: ComponentProps<"th">) {
  return <th className={cn("p-3 text-start font-semibold", className)} {...props} />;
}

export function TableCell({ className, ...props }: ComponentProps<"td">) {
  return <td className={cn("p-3", className)} {...props} />;
}
