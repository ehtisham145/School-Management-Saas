/** Set when a sign-in finishes, and consumed once by WelcomeReveal. */
const WELCOME_FLAG = "ll_welcome";

function storage(kind: "local" | "session") {
  try {
    return kind === "local" ? window.localStorage : window.sessionStorage;
  } catch {
    return null;
  }
}

export function markFreshLogin() {
  try {
    storage("session")?.setItem(WELCOME_FLAG, "1");
  } catch {
    // Storage is blocked or full: the sign-in continues without the welcome.
  }
}

/** True only once after each sign-in, so refreshing or navigating never replays it. */
export function consumeFreshLogin() {
  try {
    const session = storage("session");
    if (session?.getItem(WELCOME_FLAG) !== "1") return false;
    session.removeItem(WELCOME_FLAG);
    return true;
  } catch {
    return false;
  }
}

export type WelcomeMode = "milestone" | "first" | "repeat";

const localDay = () => {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
};

/** Works out which welcome this user gets on this device, and records the visit. */
export function resolveWelcomeMode(userKey: string): WelcomeMode {
  const seenKey = `ll_welcome_seen_${userKey}`;
  const dayKey = `ll_welcome_day_${userKey}`;
  let seen: string | null = null;
  let lastDay: string | null = null;

  try {
    const local = storage("local");
    seen = local?.getItem(seenKey) ?? null;
    lastDay = local?.getItem(dayKey) ?? null;
    local?.setItem(seenKey, "1");
    local?.setItem(dayKey, localDay());
  } catch {
    // Storage is blocked or full: the welcome still plays.
  }

  if (!seen) return "milestone";
  return lastDay === localDay() ? "repeat" : "first";
}
