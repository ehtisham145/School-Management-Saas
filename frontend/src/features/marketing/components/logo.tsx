import Image from "next/image";
import { cn } from "cn";

const SOURCES = {
  // Navy text, for white and light backgrounds.
  color: "/brand/logo.webp",
  // White text, for navy-deep backgrounds (footer, sidebar).
  white: "/brand/logo-white.webp",
};

export function Logo({
  className,
  priority,
  variant = "color",
}: {
  className?: string;
  priority?: boolean;
  variant?: keyof typeof SOURCES;
}) {
  return (
    <Image
      src={SOURCES[variant]}
      width={534}
      height={120}
      alt="Lesson Lab"
      priority={priority}
      className={cn("h-[38px] w-auto sm:h-14", className)}
    />
  );
}
