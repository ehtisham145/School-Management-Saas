"use client";

import type { ReactNode } from "react";
import { usePathname } from "@/i18n/navigation";

export function PageTransition({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div key={pathname} className="motion-safe:animate-[marketing-page-in_0.45s_ease-out]">
      {children}
    </div>
  );
}
