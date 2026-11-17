import type { ComponentProps } from "react";
import { cn } from "cn";

/** The mobile companion to `Table`: one card per row, visible only below `sm`. */
export function CardList({ className, ...props }: ComponentProps<"ul">) {
  return <ul className={cn("flex flex-col gap-3 sm:hidden", className)} {...props} />;
}

export function CardListItem({ className, ...props }: ComponentProps<"li">) {
  return (
    <li
      className={cn("flex flex-col gap-3 rounded-card border border-line bg-bg p-4", className)}
      {...props}
    />
  );
}

/** The card's top line: a title (name, number...) with an optional badge/status beside it. */
export function CardListHeader({ className, ...props }: ComponentProps<"div">) {
  return <div className={cn("flex items-start justify-between gap-3", className)} {...props} />;
}

/** A label/value grid for the card's secondary fields, two per row from `sm` phones up. */
export function CardListFields({ className, ...props }: ComponentProps<"dl">) {
  return <dl className={cn("grid grid-cols-2 gap-3", className)} {...props} />;
}
