import Image from "next/image";
import { cn } from "cn";

export function Logo({ className, priority }: { className?: string; priority?: boolean }) {
  return (
    <Image
      src="/brand/logo.png"
      width={586}
      height={190}
      alt="Lesson Lab"
      priority={priority}
      className={cn("h-[46px] w-auto sm:h-[60px]", className)}
    />
  );
}
