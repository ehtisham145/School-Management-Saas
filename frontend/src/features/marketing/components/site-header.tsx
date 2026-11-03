"use client";

import { useState } from "react";
import { Menu } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "cn";
import { Link, usePathname } from "@/i18n/navigation";
import { DemoButton } from "@/features/leads/components/demo-dialog";
import { LanguageMenu } from "./language-menu";
import { Logo } from "./logo";

const NAV_ITEMS = [
  { href: "/", key: "home" },
  { href: "/about", key: "about" },
  { href: "/lms", key: "lms" },
  { href: "/pricing", key: "pricing" },
  { href: "/contact", key: "contact" },
] as const;

export function SiteHeader() {
  const t = useTranslations("Marketing.nav");
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);

  const closeMenu = () => setMenuOpen(false);

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-bg">
      <div className="page-wrap relative flex h-16 items-center justify-between gap-2 sm:h-[76px] sm:gap-4">
        <Link href="/" onClick={closeMenu} className="block shrink-0">
          <Logo priority />
        </Link>

        <nav
          id="site-nav"
          aria-label={t("main")}
          className={cn(
            "gap-7 text-[14.5px] font-semibold text-ink-soft lg:flex",
            menuOpen
              ? "absolute inset-x-0 top-full flex flex-col gap-0.5 border-b border-line bg-bg px-4 py-3 shadow-soft sm:px-6 lg:static lg:flex-row lg:gap-7 lg:border-0 lg:p-0 lg:shadow-none"
              : "hidden",
          )}
        >
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={closeMenu}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "border-b-2 py-2.5 transition-colors hover:text-navy lg:py-1.5",
                  "border-transparent",
                  active && "text-navy lg:border-orange",
                )}
              >
                {t(item.key)}
              </Link>
            );
          })}
          <Link
            href="/login"
            onClick={closeMenu}
            className="py-2.5 text-navy transition-colors sm:hidden"
          >
            {t("signIn")}
          </Link>
        </nav>

        <div className="flex items-center gap-2">
          <LanguageMenu />
          <Link
            href="/login"
            className="hidden rounded-control px-3 py-[9px] text-[14.5px] font-semibold text-navy hover:bg-navy-soft sm:block"
          >
            {t("signIn")}
          </Link>
          <DemoButton size="sm" className="hidden sm:inline-flex">
            {t("cta")}
          </DemoButton>
          <button
            type="button"
            aria-expanded={menuOpen}
            aria-controls="site-nav"
            aria-label={menuOpen ? t("closeMenu") : t("menu")}
            onClick={() => setMenuOpen((value) => !value)}
            className="flex size-[42px] cursor-pointer items-center justify-center rounded-control border border-line bg-bg text-ink lg:hidden"
          >
            <Menu aria-hidden="true" className="size-5" />
          </button>
        </div>
      </div>
    </header>
  );
}
