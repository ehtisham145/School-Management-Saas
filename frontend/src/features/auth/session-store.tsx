"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import type { ActiveSession } from "./schemas";

type SessionContextValue = {
  session: ActiveSession | null;
  setSession: (session: ActiveSession) => void;
  clearSession: () => void;
};

const SessionContext = createContext<SessionContextValue | null>(null);

// In-memory only: set on login/switch-school, read by the placeholder
// dashboard. A hard refresh on /dashboard loses it and redirects to /login,
// which is correct for now since there's no "who am I" endpoint yet to
// rehydrate from the session cookie.
export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<ActiveSession | null>(null);

  const clearSession = useCallback(() => setSession(null), []);

  const value = useMemo(() => ({ session, setSession, clearSession }), [session, clearSession]);

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error("useSession must be used within a SessionProvider");
  }
  return context;
}
