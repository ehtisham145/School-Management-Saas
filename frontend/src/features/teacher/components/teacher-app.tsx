"use client";

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  BookOpenText,
  ClipboardCheck,
  CreditCard,
  House,
  LogOut,
  Mail,
  Menu,
  Palette,
  Presentation,
  UsersRound,
  X,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "cn";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import { Button } from "@/components/ui/button";
import { me } from "@/features/auth/api";
import { useLogout } from "@/features/auth/use-logout";
import { LanguageMenu } from "@/features/marketing/components/language-menu";
import { Logo } from "@/features/marketing/components/logo";
import { getWorkspace } from "../api";
import type { Workspace } from "../schemas";
import { UpgradeLink, WorkspaceProvider } from "./teacher-ui";

// `classes` items show only when the workspace has classes; they belong to the school plan.
const NAV_ITEMS = [
  { href: "/teacher", labelKey: "overview", icon: House, classes: false },
  { href: "/teacher/lessons", labelKey: "lessons", icon: BookOpenText, classes: false },
  { href: "/teacher/presentations", labelKey: "presentations", icon: Presentation, classes: false },
  { href: "/teacher/tests", labelKey: "tests", icon: ClipboardCheck, classes: false },
  // In the side menu only: the phone's bottom bar keeps five items.
  {
    href: "/teacher/paper-design",
    labelKey: "paperDesign",
    icon: Palette,
    classes: false,
    phone: false,
  },
  { href: "/teacher/classes", labelKey: "classes", icon: UsersRound, classes: true },
  { href: "/teacher/messages", labelKey: "messages", icon: Mail, classes: true },
  { href: "/teacher/plan", labelKey: "plan", icon: CreditCard, classes: false },
] as const;

function navItems(workspace: Workspace | null) {
  return NAV_ITEMS.filter((item) => !item.classes || workspace?.features.classes);
}

/** On phones the menu sits at the bottom, in reach of a thumb. Five items at most. */
function BottomBar({ items, pathname }: { items: ReturnType<typeof navItems>; pathname: string }) {
  const t = useTranslations("Teacher.nav");
  return (
    <nav
      aria-label={t("label")}
      className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-bg pb-[env(safe-area-inset-bottom)] lg:hidden"
    >
      <ul className="flex">
        {items
          .filter((item) => !item.classes && !("phone" in item && item.phone === false))
          .map(({ href, labelKey, icon: Icon }) => {
            const current = isCurrent(pathname, href);
            return (
              <li key={href} className="min-w-0 flex-1">
                <Link
                  href={href}
                  aria-current={current ? "page" : undefined}
                  className={cn(
                    "flex min-h-16 flex-col items-center justify-center gap-1 px-1 text-[11px] font-semibold",
                    current ? "text-orange-text" : "text-ink-soft",
                  )}
                >
                  <Icon aria-hidden="true" className="size-5 shrink-0" />
                  <span className="w-full truncate text-center">{t(`short.${labelKey}`)}</span>
                </Link>
              </li>
            );
          })}
      </ul>
    </nav>
  );
}

function isCurrent(pathname: string, href: string) {
  return href === "/teacher" ? pathname === href : pathname.startsWith(href);
}

function PlanBanner({
  tier,
  readOnly,
  daysLeft,
}: {
  tier: string;
  readOnly: boolean;
  daysLeft: number | null;
}) {
  const t = useTranslations("Teacher.banner");

  if (readOnly) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-3 bg-red-50 px-4 py-3 text-sm font-semibold text-red-800 sm:px-6">
        <span>{t("readOnly")}</span>
        <UpgradeLink />
      </div>
    );
  }
  if (tier === "trial" && daysLeft !== null) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-3 bg-orange-soft px-4 py-3 text-sm font-semibold text-orange-text sm:px-6">
        <span>{t("trial", { days: daysLeft })}</span>
        <UpgradeLink />
      </div>
    );
  }
  return null;
}

function TeacherShell({ children }: { children: ReactNode }) {
  const t = useTranslations("Teacher.nav");
  const tCommon = useTranslations("Teacher.common");
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const { handleLogout, isLoggingOut } = useLogout();
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const reload = useCallback(() => setAttempt((current) => current + 1), []);

  // The page stays on screen while the counts refresh, so open tabs and forms aren't lost.
  useEffect(() => {
    const controller = new AbortController();
    getWorkspace(controller.signal)
      .then((data) => {
        setWorkspace(data);
        setFailed(false);
      })
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      });
    return () => controller.abort();
  }, [attempt]);

  const value = useMemo(() => (workspace ? { workspace, reload } : null), [workspace, reload]);
  const items = navItems(workspace);

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
            href="/teacher"
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
            {items.map(({ href, labelKey, icon: Icon }) => {
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

        <div className="border-t border-on-dark-line px-3 py-2">
          <button
            type="button"
            disabled={isLoggingOut}
            onClick={handleLogout}
            className="flex min-h-11 w-full cursor-pointer items-center gap-3 rounded-control px-3 text-sm font-semibold text-on-dark-soft transition-colors hover:bg-on-dark-line hover:text-on-dark disabled:cursor-not-allowed disabled:opacity-50"
          >
            <LogOut aria-hidden="true" className="size-[18px] shrink-0" />
            {t("logout")}
          </button>
        </div>
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
          <div className="ms-auto flex items-center gap-3">
            {value && (
              <span className="hidden text-sm font-semibold text-ink sm:inline">
                {value.workspace.teacher_name}
              </span>
            )}
            <LanguageMenu />
          </div>
        </header>

        {value && (
          <PlanBanner
            tier={value.workspace.access.tier}
            readOnly={value.workspace.access.read_only}
            daysLeft={value.workspace.access.days_left}
          />
        )}

        {/* Room at the bottom on phones, so the bottom bar never covers the page. */}
        <main className="mx-auto flex w-full max-w-[1120px] flex-1 flex-col gap-5 p-4 pb-24 sm:p-6 sm:pb-24 lg:pb-6">
          {value ? (
            <WorkspaceProvider value={value}>{children}</WorkspaceProvider>
          ) : !failed ? (
            <p role="status" className="py-10 text-sm text-ink-soft">
              {tCommon("loading")}
            </p>
          ) : (
            <div className="flex flex-col items-start gap-3 py-6">
              <p role="alert" className="text-sm text-red-700">
                {tCommon("loadFailed")}
              </p>
              <Button variant="outline" size="sm" onClick={reload}>
                {tCommon("retry")}
              </Button>
            </div>
          )}
        </main>
      </div>
      <BottomBar items={items} pathname={pathname} />
    </div>
  );
}

/** Only an individual teacher gets this app. Everyone else goes back to their own area. */
export function TeacherApp({ children }: { children: ReactNode }) {
  const tCommon = useTranslations("Teacher.common");
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    me()
      .then((result) => {
        if (cancelled) return;
        if (result.is_platform_admin) router.replace("/platform");
        else if (result.memberships.some((item) => item.school.kind === "individual")) {
          setAllowed(true);
        } else router.replace("/dashboard");
      })
      .catch(() => {
        if (!cancelled) router.replace("/login");
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  if (!allowed) {
    return (
      <main className="flex flex-1 items-center justify-center p-8">
        <p className="text-sm text-ink-soft">{tCommon("loading")}</p>
      </main>
    );
  }
  return <TeacherShell>{children}</TeacherShell>;
}
