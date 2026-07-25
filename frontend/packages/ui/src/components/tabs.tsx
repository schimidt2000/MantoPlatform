import { forwardRef, type ComponentPropsWithoutRef, type HTMLAttributes } from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { motion, useReducedMotion } from "framer-motion";
import { cn } from "../lib/cn";

/**
 * Alternador de abas do design system Manto (feature 187) — sobre `@radix-ui/react-tabs`
 * (navegação por teclado e ARIA "de fábrica"), mesma abordagem de primitivos headless já
 * aceita no projeto (ver `dialog.tsx`).
 */
const Tabs = TabsPrimitive.Root;

const TabsList = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(function TabsList(
  { className, ...props },
  ref,
) {
  return (
    <TabsPrimitive.List
      ref={ref}
      className={cn(
        "inline-flex items-center gap-1 rounded-md border border-line bg-surface-2 p-1",
        className,
      )}
      {...props}
    />
  );
});

type TabsTriggerProps = ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>;

const TabsTrigger = forwardRef<HTMLButtonElement, TabsTriggerProps>(function TabsTrigger(
  { className, ...props },
  ref,
) {
  return (
    <TabsPrimitive.Trigger
      ref={ref}
      className={cn(
        "rounded-md px-3 py-1.5 text-sm font-medium text-muted transition-colors",
        "data-[state=active]:bg-panel data-[state=active]:text-ink data-[state=active]:shadow-sm",
        "hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        className,
      )}
      {...props}
    />
  );
});

type TabsContentProps = ComponentPropsWithoutRef<typeof TabsPrimitive.Content>;

const TabsContent = forwardRef<HTMLDivElement, TabsContentProps>(function TabsContent(
  { className, children, ...props },
  ref,
) {
  const reduceMotion = useReducedMotion();
  return (
    <TabsPrimitive.Content ref={ref} className={cn("mt-4 focus-visible:outline-none", className)} {...props}>
      <motion.div
        initial={reduceMotion ? undefined : { opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.18, ease: "easeOut" }}
      >
        {children}
      </motion.div>
    </TabsPrimitive.Content>
  );
});

export { Tabs, TabsList, TabsTrigger, TabsContent };
