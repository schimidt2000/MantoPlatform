import { type HTMLAttributes } from "react";
import { cn } from "../lib/cn";

/** Placeholder de carregamento (feedback de loading — Princípio V). */
function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("animate-pulse rounded-md bg-surface-2", className)} {...props} />;
}

export { Skeleton };
