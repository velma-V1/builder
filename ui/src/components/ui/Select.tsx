import type { JSX, SelectHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Select({
  className,
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>): JSX.Element {
  return (
    <select
      className={cn(
        "h-9 rounded-md border border-border bg-background px-3 text-sm " +
          "focus-visible:outline-none focus-visible:ring-2 disabled:opacity-50",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  );
}
