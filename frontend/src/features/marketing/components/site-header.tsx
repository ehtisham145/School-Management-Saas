"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { cn } from "cn";
import { Link, usePathname } from "@/i18n/navigation";
import { buttonVariants } from "@/components/ui/button";
import { BrandMark } from "../icons";

const NAV_ITEMS = [
  { href: "/" as const, key: "home" },
  { href: "/features" as const, key: "features" },
  { href: "/pricing" as const, key: "pricing" },
  { href: "/about" as const, key: "about" },
  { href: "/contact" as const, key: "contact" },
];

export function SiteHeader() {
  const t = useTranslations("Marketing.nav");
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/90 backdrop-blur-sm">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
        <Link
          href="/"
          onClick={() => setOpen(false)}
          className="flex items-center gap-2 font-display text-xl font-bold text-foreground"
        >
          <BrandMark className="h-7 w-7 text-primary" />
          {t("brand")}
        </Link>

        <nav className="hidden items-center gap-8 md:flex">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "border-b pb-1 text-sm font-medium text-muted-foreground transition-colors hover:border-primary hover:text-foreground",
                  active ? "border-primary text-foreground" : "border-transparent",
                )}
              >
                {t(item.key)}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-2">
          <Link
            href="/login"
            className="hidden text-sm font-medium text-muted-foreground hover:text-foreground sm:inline-flex"
          >
            {t("signIn")}
          </Link>
          <Link href="/contact" className={cn(buttonVariants(), "hidden sm:inline-flex")}>
            {t("cta")}
          </Link>
          <button
            type="button"
            className="flex flex-col gap-1.5 p-2 md:hidden"
            aria-label={t("toggleMenu")}
            aria-expanded={open}
            onClick={() => setOpen((value) => !value)}
          >
            <span className="block h-0.5 w-5 bg-foreground" />
            <span className="block h-0.5 w-5 bg-foreground" />
          </button>
        </div>
      </div>

      {open && (
        <nav className="flex flex-col gap-1 border-t border-border bg-background px-6 pb-4 md:hidden">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setOpen(false)}
              className="py-2.5 text-sm font-medium text-foreground"
            >
              {t(item.key)}
            </Link>
          ))}
          <Link href="/login" onClick={() => setOpen(false)} className="py-2.5 text-sm font-medium text-foreground">
            {t("signIn")}
          </Link>
          <Link
            href="/contact"
            onClick={() => setOpen(false)}
            className={cn(buttonVariants(), "mt-2")}
          >
            {t("cta")}
          </Link>
        </nav>
      )}
    </header>
  );
}
