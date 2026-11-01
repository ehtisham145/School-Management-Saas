import { AttendanceIcon } from "../icons";

type RecordCardStackProps = {
  timetableLabel: string;
  timetableValue: string;
  feesLabel: string;
  feesValue: string;
  attendanceLabel: string;
  attendanceValue: string;
};

export function RecordCardStack({
  timetableLabel,
  timetableValue,
  feesLabel,
  feesValue,
  attendanceLabel,
  attendanceValue,
}: RecordCardStackProps) {
  return (
    <div className="relative h-[320px] sm:h-[380px]" aria-hidden="true">
      <div className="absolute start-[2%] top-[4%] w-[240px] -rotate-6 border border-[var(--mk-line-strong)] bg-card p-5 shadow-lg shadow-black/5">
        <span className="font-marketing-mono text-[0.68rem] tracking-[0.08em] text-[var(--mk-ink-faint)] uppercase">
          {timetableLabel}
        </span>
        <p className="mt-1 font-display text-base font-semibold text-card-foreground">
          {timetableValue}
        </p>
        <div className="mt-3 flex flex-col gap-1.5">
          <span className="block h-1.5 w-[85%] bg-muted" />
          <span className="block h-1.5 w-[60%] bg-muted" />
          <span className="block h-1.5 w-[72%] bg-muted" />
        </div>
      </div>

      <div className="absolute end-[0%] top-[16%] w-[240px] rotate-3 border border-[var(--mk-line-strong)] bg-card p-5 shadow-lg shadow-black/5">
        <span className="font-marketing-mono text-[0.68rem] tracking-[0.08em] text-[var(--mk-ink-faint)] uppercase">
          {feesLabel}
        </span>
        <p className="mt-1 font-display text-base font-semibold text-card-foreground">{feesValue}</p>
        <div className="mt-3 flex flex-col gap-1.5">
          <span className="block h-1.5 w-[88%] bg-muted" />
          <span className="block h-1.5 w-[55%] bg-muted" />
          <span className="block h-1.5 w-[70%] bg-muted" />
        </div>
      </div>

      <div className="absolute start-[12%] top-[42%] w-[250px] -rotate-2 border border-primary bg-card p-5 shadow-xl shadow-black/10">
        <div className="flex items-center justify-between">
          <span className="font-marketing-mono text-[0.68rem] tracking-[0.08em] text-[var(--mk-accent-ink)] uppercase">
            {attendanceLabel}
          </span>
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[var(--mk-teal-soft)] text-[var(--mk-teal)]">
            <AttendanceIcon className="h-3.5 w-3.5" strokeWidth={2} />
          </span>
        </div>
        <p className="mt-1 font-display text-base font-semibold text-card-foreground">
          {attendanceValue}
        </p>
        <div className="mt-3 flex flex-col gap-1.5">
          <span className="block h-1.5 w-[90%] bg-muted" />
          <span className="block h-1.5 w-[65%] bg-muted" />
          <span className="block h-1.5 w-[76%] bg-muted" />
        </div>
      </div>
    </div>
  );
}
