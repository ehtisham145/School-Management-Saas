"use client";

import { useState } from "react";
import { cn } from "cn";

type MarqueeItem = { title: string; desc: string };

function Phrase({ title, desc }: MarqueeItem) {
  return (
    <span className="text-[14.5px] font-semibold whitespace-nowrap">
      {title} <span className="font-normal opacity-70">— {desc}</span>
    </span>
  );
}

function MarqueeRow({
  items,
  reverse,
  tone,
}: {
  items: MarqueeItem[];
  reverse?: boolean;
  tone: "navy" | "cream";
}) {
  const separator = tone === "navy" ? "✦" : "·";

  return (
    <div
      className={cn(
        "marquee-row overflow-hidden py-3.5",
        tone === "navy" ? "bg-navy-deep text-on-dark" : "bg-navy-soft text-navy",
      )}
    >
      <div
        className={cn("marquee-track flex w-max items-center", reverse && "marquee-track--reverse")}
      >
        {[0, 1].map((copy) => (
          <div
            key={copy}
            aria-hidden={copy === 1 || undefined}
            className={cn("flex items-center", copy === 1 && "motion-reduce:hidden")}
          >
            {items.map((item) => (
              <span key={item.title} className="flex items-center">
                <Phrase {...item} />
                <span aria-hidden="true" className="mx-5 text-[15px] text-orange-text">
                  {separator}
                </span>
              </span>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export function MarqueeStrip({
  row1,
  row2,
  eyebrow,
}: {
  row1: MarqueeItem[];
  row2: MarqueeItem[];
  eyebrow: string;
}) {
  const [isSlow, setIsSlow] = useState(false);

  return (
    <section aria-label={eyebrow} className="overflow-hidden py-10 sm:py-14">
      <div
        className={cn(
          "marquee-group relative -mx-[6vw] w-[112vw] -rotate-[1.4deg] shadow-[0_18px_40px_-10px_rgb(15_29_49_/_45%)]",
          isSlow && "is-slow",
        )}
        onClick={() => setIsSlow((current) => !current)}
      >
        <MarqueeRow items={row1} tone="navy" />
        <div className="h-[2px] bg-orange" />
        <MarqueeRow items={row2} reverse tone="cream" />
      </div>
    </section>
  );
}
