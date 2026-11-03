"use client";

import { Input } from "@/components/ui/input";

type CodeInputProps = {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
};

export function CodeInput({ id, label, value, onChange }: CodeInputProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      <Input
        id={id}
        name={id}
        dir="ltr"
        inputMode="numeric"
        autoComplete="one-time-code"
        pattern="[0-9]{6}"
        minLength={6}
        maxLength={6}
        required
        autoFocus
        className="text-center tracking-widest"
        value={value}
        onChange={(event) => onChange(event.target.value.replace(/\D/g, ""))}
      />
    </div>
  );
}
