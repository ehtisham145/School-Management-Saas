"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import type { ActiveSession } from "./schemas";

type SessionContextValue = {
  session: ActiveSession | null;
  setSession: (session: ActiveSession) => void;
  clearSession: () => void;
};

const SessionContext = createContext<SessionContextValue | null>(null);

// In-memory copy of the server session: set on login/switch-school, and
// restored from GET /api/auth/me/ by RequireSession after a page refresh.
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
