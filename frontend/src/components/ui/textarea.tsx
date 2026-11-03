import * as React from "react";
import { cn } from "cn";
import { controlClasses } from "./input";

export function Textarea({ className, rows = 4, ...props }: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      rows={rows}
      className={cn(controlClasses, "resize-y py-3", className)}
      {...props}
    />
  );
}
