"use client";

import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";

type RevealProps = {
  children: ReactNode;
  className?: string;
  delayMs?: number;
};

const EASING = "cubic-bezier(0.22, 1, 0.36, 1)";
const DURATION = "1.2s";
const HIDDEN: CSSProperties = { opacity: 0, translate: "0 36px", scale: "0.98" };

/**
 * Slides content into place as it scrolls into view, and again whenever the
 * visitor scrolls back up past it and returns. If scripts are off, the
 * `.reveal` rule in the marketing layout keeps the content visible.
 */
export function Reveal({ children, className, delayMs = 0 }: RevealProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      const frame = requestAnimationFrame(() => setVisible(true));
      return () => cancelAnimationFrame(frame);
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
        } else if (entry.boundingClientRect.top > 0) {
          setVisible(false);
        }
      },
      { threshold: 0.1, rootMargin: "0px 0px -40px 0px" },
    );
    observer.observe(node);

    return () => {
      observer.disconnect();
      // Next.js keeps visited pages alive, so start over when the page returns.
      setVisible(false);
    };
  }, []);

  const style: CSSProperties = visible
    ? {
        transition: `opacity ${DURATION} ${EASING} ${delayMs}ms, translate ${DURATION} ${EASING} ${delayMs}ms, scale ${DURATION} ${EASING} ${delayMs}ms`,
      }
    : HIDDEN;

  return (
    <div
      ref={ref}
      className={["reveal", visible && "is-visible", className].filter(Boolean).join(" ")}
      style={style}
    >
      {children}
    </div>
  );
}
