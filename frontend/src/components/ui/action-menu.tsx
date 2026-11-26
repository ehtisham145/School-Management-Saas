"use client";

import type { ReactNode } from "react";
import { Menu } from "@base-ui/react/menu";
import { Ellipsis } from "lucide-react";
import { cn } from "cn";

export type ActionMenuItem = {
  label: string;
  icon?: ReactNode;
  onSelect: () => void;
  disabled?: boolean;
  tone?: "default" | "danger";
};

/**
 * A "⋯" button that opens a short list of actions. Used on phones in place of a row of
 * buttons. Base UI handles focus, arrow keys, Escape and closing on outside click.
 */
export function ActionMenu({
  label,
  items,
  className,
}: {
  /** Read by screen readers, for example "More for question 3". */
  label: string;
  items: ActionMenuItem[];
  className?: string;
}) {
  return (
    <Menu.Root>
      <Menu.Trigger
        aria-label={label}
        className={cn(
          "flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-control border border-line bg-bg text-navy hover:bg-navy-soft data-[popup-open]:bg-navy-soft",
          className,
        )}
      >
        <Ellipsis aria-hidden="true" className="size-5" />
      </Menu.Trigger>
      <Menu.Portal>
        <Menu.Positioner sideOffset={6} align="end" className="z-50">
          <Menu.Popup className="min-w-48 rounded-control border border-line bg-bg p-1 text-ink shadow-soft outline-none">
            {items.map((item) => (
              <Menu.Item
                key={item.label}
                disabled={item.disabled}
                onClick={item.onSelect}
                className={cn(
                  "flex min-h-11 cursor-pointer items-center gap-2.5 rounded-control px-3 text-sm font-semibold outline-none select-none data-[disabled]:cursor-not-allowed data-[disabled]:opacity-40 data-[highlighted]:bg-navy-soft",
                  item.tone === "danger" ? "text-red-700" : "text-navy",
                )}
              >
                {item.icon}
                {item.label}
              </Menu.Item>
            ))}
          </Menu.Popup>
        </Menu.Positioner>
      </Menu.Portal>
    </Menu.Root>
  );
}
