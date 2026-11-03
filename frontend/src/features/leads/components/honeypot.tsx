/** Hidden from people. Bots that fill it are ignored by the backend. */
export function Honeypot({ label, ...props }: { label: string } & React.ComponentProps<"input">) {
  return (
    <div aria-hidden="true" className="absolute -start-[9999px] size-px overflow-hidden">
      <label>
        {label}
        <input type="text" tabIndex={-1} autoComplete="off" {...props} />
      </label>
    </div>
  );
}
