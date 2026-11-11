"use client";

import { useEffect, useState, type ReactNode } from "react";
import {
  BarChart3,
  CalendarCheck,
  CreditCard,
  FileText,
  History,
  LayoutDashboard,
  Menu,
  School,
  Tags,
  X,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "cn";
import { Link, usePathname } from "@/i18n/navigation";
import type { MeResponse } from "@/features/auth/schemas";
import { LanguageMenu } from "@/features/marketing/components/language-menu";
import { Logo } from "@/features/marketing/components/logo";
import { ProfileMenu } from "./profile-menu";

const NAV_ITEMS = [
  { href: "/platform", labelKey: "dashboard", icon: LayoutDashboard },
  { href: "/platform/demo-requests", labelKey: "demoRequests", icon: CalendarCheck },
  { href: "/platform/schools", labelKey: "schools", icon: School },
  { href: "/platform/subscriptions", labelKey: "subscriptions", icon: CreditCard },
  { href: "/platform/quotations", labelKey: "quotations", icon: FileText },
  { href: "/platform/plans", labelKey: "plans", icon: Tags },
  { href: "/platform/usage", labelKey: "usage", icon: BarChart3 },
  { href: "/platform/audit-log", labelKey: "auditLog", icon: History },
] as const;

function isCurrent(pathname: string, href: string) {
  return href === "/platform" ? pathname === href : pathname.startsWith(href);
}

export function PlatformShell({ user, children }: { user: MeResponse; children: ReactNode }) {
  const t = useTranslations("Platform.nav");
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!menuOpen) return;

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setMenuOpen(false);
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [menuOpen]);

  return (
    <div className="flex min-h-dvh flex-1 bg-bg-tint">
      {menuOpen && (
        <div
          aria-hidden="true"
          onClick={() => setMenuOpen(false)}
          className="fixed inset-0 z-40 bg-navy-deep/60 lg:hidden"
        />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 start-0 z-50 flex w-64 flex-col bg-navy-deep text-on-dark transition-transform lg:sticky lg:top-0 lg:h-dvh lg:shrink-0 lg:translate-x-0",
          menuOpen
            ? "translate-x-0"
            : "max-lg:invisible max-lg:-translate-x-full max-lg:rtl:translate-x-full",
        )}
      >
        <div className="flex items-center justify-between gap-2 p-4">
          <Link
            href="/platform"
            onClick={() => setMenuOpen(false)}
            className="rounded-control bg-bg px-3 py-2"
          >
            <Logo className="h-7 sm:h-7" />
          </Link>
          <button
            type="button"
            aria-label={t("close")}
            onClick={() => setMenuOpen(false)}
            className="flex size-9 cursor-pointer items-center justify-center rounded-control text-on-dark-soft hover:bg-on-dark-line hover:text-on-dark lg:hidden"
          >
            <X aria-hidden="true" className="size-5" />
          </button>
        </div>

        <nav aria-label={t("label")} className="flex-1 overflow-y-auto px-3 py-2">
          <ul className="flex flex-col gap-1">
            {NAV_ITEMS.map(({ href, labelKey, icon: Icon }) => {
              const current = isCurrent(pathname, href);
              return (
                <li key={href}>
                  <Link
                    href={href}
                    aria-current={current ? "page" : undefined}
                    onClick={() => setMenuOpen(false)}
                    className={cn(
                      "flex min-h-11 items-center gap-3 rounded-control border-s-[3px] px-3 text-sm font-semibold transition-colors",
                      current
                        ? "border-orange bg-on-dark-line text-on-dark"
                        : "border-transparent text-on-dark-soft hover:bg-on-dark-line hover:text-on-dark",
                    )}
                  >
                    <Icon aria-hidden="true" className="size-[18px] shrink-0" />
                    {t(labelKey)}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-3 border-b border-line bg-bg px-4 sm:px-6">
          <button
            type="button"
            aria-label={t("open")}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen(true)}
            className="flex size-[42px] cursor-pointer items-center justify-center rounded-control border border-line text-navy hover:bg-navy-soft lg:hidden"
          >
            <Menu aria-hidden="true" className="size-5" />
          </button>
          <div className="ms-auto flex items-center gap-2">
            <LanguageMenu />
            <ProfileMenu user={user} />
          </div>
        </header>
        <main className="mx-auto flex w-full max-w-[1240px] flex-1 flex-col gap-5 p-4 sm:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
