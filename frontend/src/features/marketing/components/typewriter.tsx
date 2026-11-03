"use client";

import { useEffect, useState } from "react";
import { cn } from "cn";

const TYPE_MS = 70;
const DELETE_MS = 35;
const HOLD_MS = 2200;
const GAP_MS = 300;

/** Splits by visible character, so Arabic marks stay with their letter. */
function toCharacters(word: string, locale: string) {
  return Array.from(new Intl.Segmenter(locale).segment(word), (part) => part.segment);
}

type TypewriterProps = {
  words: string[];
  locale: string;
  className?: string;
};

/**
 * Every word sits invisibly in the same grid cell, so the space for the longest
 * one is reserved and the page never jumps while typing. The server renders the
 * first word in full for search engines and for people who prefer less motion.
 */
export function Typewriter({ words, locale, className }: TypewriterProps) {
  const [wordIndex, setWordIndex] = useState(0);
  const [length, setLength] = useState<number | null>(null);
  const [deleting, setDeleting] = useState(true);

  const characters = toCharacters(words[wordIndex], locale);
  const shown = length ?? characters.length;

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let delay: number;
    let next: () => void;

    if (deleting) {
      if (shown === characters.length && length === null) {
        delay = HOLD_MS;
        next = () => setLength(characters.length - 1);
      } else if (shown > 0) {
        delay = DELETE_MS;
        next = () => setLength(shown - 1);
      } else {
        delay = GAP_MS;
        next = () => {
          setWordIndex((wordIndex + 1) % words.length);
          setDeleting(false);
        };
      }
    } else if (shown < characters.length) {
      delay = TYPE_MS;
      next = () => setLength(shown + 1);
    } else {
      delay = HOLD_MS;
      next = () => {
        setDeleting(true);
        setLength(characters.length - 1);
      };
    }

    const timer = window.setTimeout(next, delay);
    return () => window.clearTimeout(timer);
  }, [characters.length, deleting, length, shown, wordIndex, words.length]);

  return (
    <span className={cn("grid max-w-full", className)}>
      <span className="sr-only">{words[0]}</span>
      {words.map((word) => (
        <span key={word} aria-hidden="true" className="invisible col-start-1 row-start-1">
          {word}
        </span>
      ))}
      <span aria-hidden="true" className="col-start-1 row-start-1">
        {characters.slice(0, shown).join("")}
        <span className="ms-0.5 inline-block h-[0.85em] w-[3px] translate-y-[0.08em] animate-[caret_1s_steps(1)_infinite] bg-current" />
      </span>
    </span>
  );
}
