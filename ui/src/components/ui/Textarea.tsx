import type { JSX, TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Textarea({
  className,
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement>): JSX.Element {
  return (
    <textarea
      className={cn(
        "min-h-16 rounded-md border border-border bg-background px-3 py-2 text-sm " +
          "focus-visible:outline-none focus-visible:ring-2 disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}
