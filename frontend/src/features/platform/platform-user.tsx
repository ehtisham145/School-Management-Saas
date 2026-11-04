"use client";

import { createContext, useContext, type ReactNode } from "react";
import type { MeResponse } from "@/features/auth/schemas";

const PlatformUserContext = createContext<MeResponse | null>(null);

export function PlatformUserProvider({
  user,
  children,
}: {
  user: MeResponse;
  children: ReactNode;
}) {
  return <PlatformUserContext.Provider value={user}>{children}</PlatformUserContext.Provider>;
}

export function usePlatformUser() {
  const user = useContext(PlatformUserContext);
  if (!user) throw new Error("usePlatformUser needs RequirePlatformAdmin above it.");
  return user;
}
