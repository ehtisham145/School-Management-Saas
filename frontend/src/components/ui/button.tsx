import { Button as ButtonPrimitive } from "@base-ui/react/button";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "cn";
import { Spinner } from "./spinner";

const buttonVariants = cva(
  "group/button inline-flex shrink-0 cursor-pointer items-center justify-center rounded-btn border-[1.5px] text-[15px] font-bold transition-[transform,background-color,border-color] select-none hover:not-disabled:-translate-y-px disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default: "border-transparent bg-navy text-on-dark hover:bg-navy-hover",
        orange: "border-transparent bg-orange text-on-orange hover:bg-orange-hover",
        outline: "border-navy-line bg-bg text-navy hover:border-navy hover:bg-navy-soft",
        secondary: "border-transparent bg-navy-soft text-navy hover:bg-navy-line",
        ghost: "border-transparent text-navy hover:bg-navy-soft",
        destructive: "border-transparent bg-red-600 text-on-dark hover:bg-red-700",
        link: "border-transparent text-navy underline-offset-4 hover:underline",
      },
      size: {
        default: "min-h-12 gap-2 px-[22px]",
        lg: "min-h-12 gap-2 px-[22px]",
        sm: "min-h-[42px] gap-1.5 rounded-control px-4 text-sm",
        icon: "size-[42px] rounded-control",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

type ButtonProps = ButtonPrimitive.Props &
  VariantProps<typeof buttonVariants> & {
    /** Disables the button and shows a spinner while saving. */
    loading?: boolean;
  };

function Button({
  className,
  variant = "default",
  size = "default",
  loading = false,
  disabled,
  children,
  ...props
}: ButtonProps) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Spinner />}
      {children}
    </ButtonPrimitive>
  );
}

export { Button, buttonVariants };
