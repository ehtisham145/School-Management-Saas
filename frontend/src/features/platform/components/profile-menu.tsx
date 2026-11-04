"use client";

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { ChevronDown, LogOut, UserRound } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "cn";
import { Link } from "@/i18n/navigation";
import type { MeResponse } from "@/features/auth/schemas";
import { useLogout } from "@/features/auth/use-logout";

const ITEM_CLASSES =
  "flex w-full cursor-pointer items-center gap-2.5 rounded-lg px-3 py-2.5 text-start text-sm font-medium hover:bg-navy-soft disabled:cursor-not-allowed disabled:opacity-50";

export function initialsOf(user: MeResponse) {
  const words = (user.full_name || user.username).trim().split(/\s+/);
  return words
    .slice(0, 2)
    .map((word) => word.charAt(0).toUpperCase())
    .join("");
}

export function ProfileMenu({ user }: { user: MeResponse }) {
  const t = useTranslations("Platform");
  const { handleLogout, isLoggingOut } = useLogout();

  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    menuRef.current?.querySelector<HTMLElement>('[role="menuitem"]')?.focus();

    function handlePointerDown(event: PointerEvent) {
      const target = event.target as Node;
      if (!menuRef.current?.contains(target) && !buttonRef.current?.contains(target)) {
        setOpen(false);
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [open]);

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      setOpen(false);
      buttonRef.current?.focus();
    } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const items = [
        ...(menuRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? []),
      ];
      const step = event.key === "ArrowDown" ? 1 : -1;
      const current = items.indexOf(document.activeElement as HTMLElement);
      items[(current + step + items.length) % items.length]?.focus();
    } else if (event.key === "Tab") {
      setOpen(false);
    }
  }

  return (
    <div className="relative">
      <button
        ref={buttonRef}
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={t("profileMenu.label")}
        onClick={() => setOpen((value) => !value)}
        className="inline-flex h-[42px] cursor-pointer items-center gap-2 rounded-control border border-line bg-bg ps-1.5 pe-2 text-sm font-semibold text-ink hover:bg-bg-tint"
      >
        <span
          aria-hidden="true"
          className="flex size-[30px] items-center justify-center rounded-full bg-navy text-xs font-bold text-on-dark"
        >
          {initialsOf(user)}
        </span>
        <bdi className="hidden max-w-[140px] truncate sm:inline">
          {user.full_name || user.username}
        </bdi>
        <ChevronDown
          aria-hidden="true"
          className={cn("size-[13px] transition-transform", open && "rotate-180")}
        />
      </button>

      {open && (
        <div
          ref={menuRef}
          role="menu"
          aria-label={t("profileMenu.label")}
          onKeyDown={handleKeyDown}
          className="absolute end-0 top-[calc(100%+8px)] z-50 w-60 rounded-btn border border-line bg-bg p-1.5 text-ink shadow-soft"
        >
          <div className="border-b border-line px-3 py-2.5">
            <span className="block truncate text-sm font-bold text-navy-deep">
              <bdi>{user.full_name || user.username}</bdi>
            </span>
            {user.email && (
              <span className="block truncate text-xs text-ink-soft">
                <bdi>{user.email}</bdi>
              </span>
            )}
          </div>
          <div className="pt-1.5">
            <Link
              href="/platform/profile"
              role="menuitem"
              onClick={() => setOpen(false)}
              className={ITEM_CLASSES}
            >
              <UserRound aria-hidden="true" className="size-4 text-navy" />
              {t("profileMenu.profile")}
            </Link>
            <button
              type="button"
              role="menuitem"
              disabled={isLoggingOut}
              onClick={handleLogout}
              className={ITEM_CLASSES}
            >
              <LogOut aria-hidden="true" className="size-4 text-navy" />
              {isLoggingOut ? t("loggingOut") : t("logout")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
