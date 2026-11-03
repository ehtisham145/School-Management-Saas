"use client";

import type { ComponentProps } from "react";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";

type CodeInputProps = ComponentProps<typeof Input> & {
  id: string;
  label: string;
  error?: string;
};

export function CodeInput({ id, label, error, ...props }: CodeInputProps) {
  return (
    <Field id={id} label={label} required error={error}>
      <Input
        id={id}
        dir="ltr"
        inputMode="numeric"
        autoComplete="one-time-code"
        maxLength={6}
        autoFocus
        className="text-center tracking-widest"
        {...props}
      />
    </Field>
  );
}
