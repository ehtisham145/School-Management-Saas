"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import { useLocale, useTranslations } from "next-intl";
import { cn } from "cn";
import { me } from "../api";
import type { MeResponse } from "../schemas";
import { consumeFreshLogin, resolveWelcomeMode, type WelcomeMode } from "../welcome";

const ENTER_MS = 40;
const HOLD_MS = 1500;
const HOLD_REPEAT_MS = 1050;
const OPEN_DELAY_MS = 180;
const UNMOUNT_MS = 950;
const UNMOUNT_FAST_MS = 500;
const SLIVER_COUNT = 18;
const SLIVER_COLORS = ["var(--on-dark)", "var(--orange)", "var(--on-dark-soft)"];

type Phase = "closed" | "in" | "leaving" | "open";
type Welcome = { mode: WelcomeMode; firstName: string; subtitle?: string };

function greetingKey(mode: WelcomeMode) {
  if (mode === "repeat") return "welcomeBack";
  const hour = new Date().getHours();
  if (hour < 12) return "goodMorning";
  return hour < 17 ? "goodAfternoon" : "goodEvening";
}

function toWelcome(user: MeResponse, locale: string): Welcome {
  const school = user.memberships.find(
    (membership) => membership.membership_id === user.active_membership_id,
  )?.school;

  return {
    // The API exposes no user id here, and usernames are unique.
    mode: resolveWelcomeMode(user.username),
    firstName: user.full_name.trim().split(/\s+/)[0] ?? "",
    subtitle: school && (locale === "ar" ? school.name_ar : school.name_en),
  };
}

function Slivers() {
  return (
    <div aria-hidden="true">
      {Array.from({ length: SLIVER_COUNT }, (_, i) => {
        const angle = (i / SLIVER_COUNT) * Math.PI * 2 + (i % 3) * 0.4;
        const radius = 22 + ((i * 7) % 20);
        return (
          <i
            key={i}
            className="wr-sliver"
            style={
              {
                "--c": SLIVER_COLORS[i % 3],
                "--h": `${10 + ((i * 5) % 10)}px`,
                "--r": `${(i * 47) % 360}deg`,
                "--x": `calc(-50% + ${Math.cos(angle) * radius}vw)`,
                "--y": `calc(-50% + ${Math.sin(angle) * radius * 0.7}vh)`,
                "--d": `${1.4 + (i % 4) * 0.15}s`,
              } as CSSProperties
            }
          />
        );
      })}
    </div>
  );
}

/** Mounted in each signed-in layout, outside its guard, so it covers the guard's own screens. */
export function WelcomeReveal() {
  const t = useTranslations("Welcome");
  const locale = useLocale();

  const [visible, setVisible] = useState(false);
  const [welcome, setWelcome] = useState<Welcome | null>(null);
  const [phase, setPhase] = useState<Phase>("closed");
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  const clearTimers = useCallback(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  }, []);

  const finish = useCallback(
    (fast: boolean) => {
      clearTimers();
      setPhase("leaving");
      timers.current.push(
        setTimeout(() => setPhase("open"), fast ? 0 : OPEN_DELAY_MS),
        setTimeout(
          () => {
            setVisible(false);
            setWelcome(null);
          },
          fast ? UNMOUNT_FAST_MS : UNMOUNT_MS,
        ),
      );
    },
    [clearTimers],
  );

  // A layout effect, so the panels are in place before the signed-in page first paints.
  useLayoutEffect(() => {
    if (consumeFreshLogin()) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- sessionStorage exists only in the browser
      setVisible(true);
    }
  }, []);

  useEffect(() => {
    if (!visible) return;
    let cancelled = false;

    me()
      .then((user) => {
        if (!cancelled) setWelcome(toWelcome(user, locale));
      })
      .catch(() => {
        // The guard behind the panels deals with the error, so only get out of its way.
        if (!cancelled) finish(true);
      });

    return () => {
      cancelled = true;
    };
  }, [visible, locale, finish]);

  useEffect(() => {
    if (!welcome) return;

    timers.current.push(
      setTimeout(() => setPhase("in"), ENTER_MS),
      setTimeout(() => finish(false), welcome.mode === "repeat" ? HOLD_REPEAT_MS : HOLD_MS),
    );

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") finish(true);
    }
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      clearTimers();
    };
  }, [welcome, finish, clearTimers]);

  if (!visible) return null;

  const leaving = phase === "leaving" || phase === "open";
  const greeting = welcome ? t(greetingKey(welcome.mode)) : "";

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "wr",
        phase !== "closed" && "wr-in",
        leaving && "wr-leaving",
        phase === "open" && "wr-open",
      )}
    >
      <div className="wr-panel wr-start" />
      <div className="wr-panel wr-end" />
      {welcome && (
        <>
          <div className="wr-stage">
            <div className="wr-logo">
              {/* The logo's navy text needs a light background, as in the sidebar. */}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/brand/logo.webp" alt="Lesson Lab" />
            </div>
            <div className="wr-rule" />
            <p className="wr-hello">
              {welcome.firstName ? t("withName", { greeting, name: welcome.firstName }) : greeting}
            </p>
            {welcome.subtitle && (
              <p className="wr-company">
                <bdi>{welcome.subtitle}</bdi>
              </p>
            )}
          </div>
          <button type="button" className="wr-skip" onClick={() => finish(true)}>
            {t("skip")}
          </button>
          {welcome.mode === "milestone" && phase === "open" && <Slivers />}
        </>
      )}
    </div>
  );
}
