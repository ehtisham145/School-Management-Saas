"use client";

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { Check, ChevronDown, Globe } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { cn } from "cn";
import { usePathname, useRouter } from "@/i18n/navigation";

const LANGUAGES = [
  { code: "en", name: "English" },
  { code: "ar", name: "العربية" },
] as const;

export function LanguageMenu() {
  const t = useTranslations("Marketing.lang");
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();

  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLUListElement>(null);

  useEffect(() => {
    if (!open) return;

    menuRef.current?.querySelector<HTMLButtonElement>('[aria-checked="true"]')?.focus();

    function handlePointerDown(event: PointerEvent) {
      const target = event.target as Node;
      if (!menuRef.current?.contains(target) && !buttonRef.current?.contains(target)) {
        setOpen(false);
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [open]);

  function close() {
    setOpen(false);
    buttonRef.current?.focus();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLUListElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      close();
    } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const items = [...(menuRef.current?.querySelectorAll("button") ?? [])];
      const step = event.key === "ArrowDown" ? 1 : -1;
      const current = items.indexOf(document.activeElement as HTMLButtonElement);
      items[(current + step + items.length) % items.length]?.focus();
    } else if (event.key === "Tab") {
      setOpen(false);
    }
  }

  function choose(code: (typeof LANGUAGES)[number]["code"]) {
    close();
    if (code !== locale) {
      const { search, hash } = window.location;
      router.replace(`${pathname}${search}${hash}`, { locale: code });
    }
  }

  const current = LANGUAGES.find((language) => language.code === locale) ?? LANGUAGES[0];

  return (
    <div className="relative">
      <button
        ref={buttonRef}
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={t("label")}
        onClick={() => setOpen((value) => !value)}
        className="inline-flex h-[42px] cursor-pointer items-center gap-[7px] rounded-control border border-line bg-bg px-[9px] text-sm font-semibold text-ink hover:bg-bg-tint sm:px-3"
      >
        <Globe aria-hidden="true" className="size-[17px]" />
        <span>{current.name}</span>
        <ChevronDown
          aria-hidden="true"
          className={cn("size-[13px] transition-transform", open && "rotate-180")}
        />
      </button>

      {open && (
        <ul
          ref={menuRef}
          role="menu"
          aria-label={t("label")}
          onKeyDown={handleKeyDown}
          className="absolute end-0 top-[calc(100%+8px)] z-50 min-w-[172px] rounded-btn border border-line bg-bg p-1.5 text-ink shadow-soft"
        >
          {LANGUAGES.map((language) => {
            const selected = language.code === locale;
            return (
              <li key={language.code} role="none">
                <button
                  type="button"
                  role="menuitemradio"
                  aria-checked={selected}
                  lang={language.code}
                  onClick={() => choose(language.code)}
                  className={cn(
                    "flex w-full cursor-pointer items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-start text-[14.5px] hover:bg-navy-soft",
                    selected ? "font-bold text-navy" : "font-medium",
                  )}
                >
                  {language.name}
                  <Check
                    aria-hidden="true"
                    className={cn("size-4 text-orange-text", !selected && "invisible")}
                  />
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
