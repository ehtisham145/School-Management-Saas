"use client";

import { useEffect, useState } from "react";

type TypewriterProps = {
  words: string[];
  className?: string;
};

const TYPE_SPEED = 55;
const DELETE_SPEED = 28;
const PAUSE_MS = 1500;
const NEXT_WORD_DELAY = 250;

export function Typewriter({ words, className }: TypewriterProps) {
  const [text, setText] = useState(words[0] ?? "");

  useEffect(() => {
    if (words.length === 0) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      // Initial state already shows words[0]; nothing to animate.
      return;
    }

    let wordIndex = 0;
    let charIndex = 0;
    let deleting = false;
    let timeoutId: ReturnType<typeof setTimeout>;

    function tick() {
      const word = words[wordIndex];
      if (!deleting) {
        charIndex++;
        setText(word.slice(0, charIndex));
        if (charIndex === word.length) {
          deleting = true;
          timeoutId = setTimeout(tick, PAUSE_MS);
          return;
        }
        timeoutId = setTimeout(tick, TYPE_SPEED);
      } else {
        charIndex--;
        setText(word.slice(0, charIndex));
        if (charIndex === 0) {
          deleting = false;
          wordIndex = (wordIndex + 1) % words.length;
          timeoutId = setTimeout(tick, NEXT_WORD_DELAY);
          return;
        }
        timeoutId = setTimeout(tick, DELETE_SPEED);
      }
    }

    timeoutId = setTimeout(tick, TYPE_SPEED);
    return () => clearTimeout(timeoutId);
  }, [words]);

  return (
    <span className={className}>
      <span aria-hidden className="font-marketing-mono font-medium">
        {text}
      </span>
      <span
        aria-hidden
        className="ms-0.5 inline-block h-[0.9em] w-[2px] translate-y-[0.1em] bg-current align-middle motion-safe:animate-[marketing-caret_1s_step-end_infinite]"
      />
      <span className="sr-only">{words.join(", ")}</span>
    </span>
  );
}
