import { type ReactNode } from "react";
import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@manto/ui";

/**
 * Moldura comum das telas fora da sessão (login, primeiro acesso, esqueci minha senha,
 * redefinição). Centraliza o card, aplica a mesma entrada animada e respeita
 * `useReducedMotion()` (Princípio IX) — evita repetir esse wrapper em cinco telas.
 */
export function AuthCard({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  const reduceMotion = useReducedMotion();

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg p-4">
      <motion.div
        initial={reduceMotion ? false : { opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, ease: "easeOut" }}
        className="w-full max-w-sm"
      >
        <Card>
          <CardHeader>
            <CardTitle>{title}</CardTitle>
            {subtitle && <p className="text-sm text-muted">{subtitle}</p>}
          </CardHeader>
          <CardContent>{children}</CardContent>
        </Card>
        {footer && <div className="mt-4 text-center text-sm text-muted">{footer}</div>}
      </motion.div>
    </div>
  );
}

/** Link de navegação entre as telas de autenticação, com alvo de toque confortável. */
export function AuthLink({ to, children }: { to: string; children: ReactNode }) {
  return (
    <Link
      to={to}
      className="inline-flex min-h-[44px] items-center px-2 font-medium text-accent hover:underline"
    >
      {children}
    </Link>
  );
}
