import * as React from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "cn";
import { controlClasses } from "./input";

export function Select({ className, children, ...props }: React.ComponentProps<"select">) {
  return (
    <div className="relative">
      <select
        data-slot="select"
        className={cn(controlClasses, "h-12 appearance-none pe-10", className)}
        {...props}
      >
        {children}
      </select>
      <ChevronDown
        aria-hidden="true"
        className="pointer-events-none absolute end-3.5 top-1/2 size-4 -translate-y-1/2 text-ink-soft"
      />
    </div>
  );
}
