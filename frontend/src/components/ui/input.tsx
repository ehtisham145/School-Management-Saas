import * as React from "react";
import { Input as InputPrimitive } from "@base-ui/react/input";
import { cn } from "cn";

export const controlClasses =
  "w-full min-w-0 rounded-control border border-line bg-bg px-3.5 text-[15px] text-ink transition-[border-color] outline-none placeholder:text-ink-soft/70 hover:border-navy-line focus-visible:border-navy disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-red-600";

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <InputPrimitive
      type={type}
      data-slot="input"
      className={cn(controlClasses, "h-12", className)}
      {...props}
    />
  );
}

export { Input };
