// Structure-only placeholder — not installed, not run in this repository state.
import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>): JSX.Element {
  return (
    <div
      className={cn("rounded-lg border border-border bg-background p-md shadow-sm", className)}
      {...props}
    />
  );
}
