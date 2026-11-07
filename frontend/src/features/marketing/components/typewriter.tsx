"use client";

import { useEffect, useState } from "react";
import { cn } from "cn";

const TYPE_MS = 95;
const DELETE_MS = 45;
const HOLD_MS = 2800;
const GAP_MS = 450;

/** Splits by visible character, so Arabic marks stay with their letter. */
function toCharacters(word: string, locale: string) {
  return Array.from(new Intl.Segmenter(locale).segment(word), (part) => part.segment);
}

type TypewriterProps = {
  words: string[];
  /** The part of each word shown in the accent color. */
  highlights?: string[];
  locale: string;
  className?: string;
};

/**
 * Every word sits invisibly in the same grid cell, so the space for the longest
 * one is reserved and the page never jumps while typing. The server renders the
 * first word in full for search engines and for people who prefer less motion.
 */
export function Typewriter({ words, highlights, locale, className }: TypewriterProps) {
  const [wordIndex, setWordIndex] = useState(0);
  const [length, setLength] = useState<number | null>(null);
  const [deleting, setDeleting] = useState(true);

  const word = words[wordIndex];
  const characters = toCharacters(word, locale);
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

  const typed = characters.slice(0, shown).join("");
  const highlight = highlights?.[wordIndex];
  const start = highlight ? word.indexOf(highlight) : -1;

  return (
    <span className={cn("grid max-w-full", className)}>
      <span className="sr-only">{words[0]}</span>
      {words.map((item) => (
        <span key={item} aria-hidden="true" className="invisible col-start-1 row-start-1">
          {item}
        </span>
      ))}
      <span aria-hidden="true" className="col-start-1 row-start-1">
        {start < 0 ? (
          typed
        ) : (
          <>
            {typed.slice(0, start)}
            <span className="text-orange-text">{typed.slice(start)}</span>
          </>
        )}
        <span className="ms-0.5 inline-block h-[0.85em] w-[3px] translate-y-[0.08em] animate-[caret_1s_steps(1)_infinite] bg-orange-text" />
      </span>
    </span>
  );
}
