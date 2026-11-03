import type { ReactNode } from "react";

type FieldProps = {
  id: string;
  label: string;
  required?: boolean;
  error?: string;
  hint?: string;
  children: ReactNode;
};

/** A label, its control, and the error shown under the field. */
export function Field({ id, label, required, error, hint, children }: FieldProps) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-semibold text-ink">
        {label}
        {required && (
          <span aria-hidden="true" className="ms-0.5 text-red-700">
            *
          </span>
        )}
      </label>
      {children}
      {hint && <p className="text-xs text-ink-soft">{hint}</p>}
      {error && (
        <p id={`${id}-error`} role="alert" className="text-sm text-red-700">
          {error}
        </p>
      )}
    </div>
  );
}
