"use client";

import { useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { cn } from "cn";

type Tab = { key: string; label: string; panel: ReactNode };

/**
 * A two-way switch between plan groups. Both panels are rendered on the
 * server, so search engines and people without JavaScript see every plan;
 * only the visible one changes.
 */
export function PricingTabs({ label, tabs }: { label: string; tabs: Tab[] }) {
  const [active, setActive] = useState(0);
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);
  const baseId = useId();

  function select(index: number) {
    setActive(index);
    buttons.current[index]?.focus();
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const rtl = getComputedStyle(event.currentTarget).direction === "rtl";
    const forward = rtl ? "ArrowLeft" : "ArrowRight";
    const back = rtl ? "ArrowRight" : "ArrowLeft";
    if (event.key === forward) select((active + 1) % tabs.length);
    else if (event.key === back) select((active - 1 + tabs.length) % tabs.length);
    else if (event.key === "Home") select(0);
    else if (event.key === "End") select(tabs.length - 1);
    else return;
    event.preventDefault();
  }

  return (
    <div>
      <div
        role="tablist"
        aria-label={label}
        onKeyDown={onKeyDown}
        className="mx-auto flex w-fit rounded-full border border-line bg-bg p-1"
      >
        {tabs.map((tab, index) => (
          <button
            key={tab.key}
            ref={(node) => {
              buttons.current[index] = node;
            }}
            type="button"
            role="tab"
            id={`${baseId}-tab-${tab.key}`}
            aria-selected={active === index}
            aria-controls={`${baseId}-panel-${tab.key}`}
            tabIndex={active === index ? 0 : -1}
            onClick={() => setActive(index)}
            className={cn(
              "rounded-full px-5 py-2.5 text-[15px] font-semibold transition-colors sm:px-7",
              active === index ? "bg-navy-deep text-on-dark" : "text-ink-soft hover:text-navy",
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {tabs.map((tab, index) => (
        <div
          key={tab.key}
          role="tabpanel"
          id={`${baseId}-panel-${tab.key}`}
          aria-labelledby={`${baseId}-tab-${tab.key}`}
          hidden={active !== index}
          className="mt-10"
        >
          {tab.panel}
        </div>
      ))}
    </div>
  );
}
