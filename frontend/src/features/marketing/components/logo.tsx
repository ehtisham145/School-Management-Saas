import Image from "next/image";
import { cn } from "cn";

export function Logo({ className, priority }: { className?: string; priority?: boolean }) {
  return (
    <Image
      src="/brand/logo.webp"
      width={515}
      height={120}
      alt="Lesson Lab"
      priority={priority}
      className={cn("h-[38px] w-auto sm:h-14", className)}
    />
  );
}
