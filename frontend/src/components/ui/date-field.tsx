"use client";

import { useRef, type ComponentProps } from "react";
import { CalendarDays } from "lucide-react";
import { cn } from "cn";
import { dayDateToIso, isoToDayDate } from "@/lib/use-validated-form";
import { Input } from "./input";

type DateFieldProps = Omit<ComponentProps<"input">, "value" | "type"> & {
  /** The date as DD/MM/YYYY, exactly as the teacher sees it. */
  value: string;
  /** Called with a DD/MM/YYYY date picked from the calendar. */
  onPick: (value: string) => void;
  calendarLabel: string;
  /** Latest date the calendar offers, as YYYY-MM-DD. */
  max?: string;
};

/**
 * A date that can be typed as DD/MM/YYYY or picked from the calendar.
 * Pass the form's bind() props with a maskDayDate sanitizer, so typing is shaped as you go.
 */
export function DateField({
  value,
  onPick,
  calendarLabel,
  max,
  className,
  disabled,
  ...props
}: DateFieldProps) {
  const picker = useRef<HTMLInputElement>(null);

  function openCalendar() {
    const input = picker.current;
    if (!input) return;
    input.value = dayDateToIso(value) ?? "";
    try {
      input.showPicker();
    } catch {
      // Older browsers have no showPicker; a click opens the calendar there.
      input.click();
    }
  }

  return (
    <div className="relative">
      <Input
        {...props}
        type="text"
        value={value}
        disabled={disabled}
        inputMode="numeric"
        autoComplete="off"
        placeholder="DD/MM/YYYY"
        maxLength={10}
        dir="ltr"
        className={cn("pe-12 rtl:text-end", className)}
      />
      <button
        type="button"
        aria-label={calendarLabel}
        disabled={disabled}
        onClick={openCalendar}
        className="absolute inset-y-0 end-0 flex w-11 cursor-pointer items-center justify-center rounded-e-control text-ink-soft hover:text-navy disabled:cursor-not-allowed disabled:opacity-50"
      >
        <CalendarDays aria-hidden="true" className="size-5" />
      </button>
      <input
        ref={picker}
        type="date"
        tabIndex={-1}
        aria-hidden="true"
        max={max}
        onChange={(event) => event.target.value && onPick(isoToDayDate(event.target.value))}
        className="pointer-events-none absolute end-0 bottom-0 size-px opacity-0"
      />
    </div>
  );
}
