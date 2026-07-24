import type { ReactNode } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@manto/ui";

/** Estilos e helpers compartilhados pelos 7 blocos do formulário de evento (feature 184). */

/** Base sem cor de borda — `FIELD`/`FIELD_ERROR` abaixo são mutuamente exclusivos (nunca os dois
 * juntos: duas classes de `border-color` na mesma string competem por especificidade igual, e a
 * que vier depois no stylesheet compilado do Tailwind vence — não necessariamente a que vier
 * depois na string de classe). */
const FIELD_BASE = "h-11 w-full rounded-md border bg-panel px-2 text-sm text-ink transition-colors";
export const FIELD = `${FIELD_BASE} border-line`;
export const FIELD_ERROR = `${FIELD_BASE} border-red border-2`;
export const LABEL = "mb-1 block text-sm text-muted";
export const HELP = "mt-1 text-xs text-muted";

export function fieldClass(hasError?: boolean): string {
  return hasError ? FIELD_ERROR : FIELD;
}

export function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return (
    <p className="mt-1 text-sm text-red" role="alert">
      {message}
    </p>
  );
}

export function BlockCard({
  title,
  id,
  children,
}: {
  title: string;
  id?: string;
  children: ReactNode;
}) {
  return (
    <Card id={id}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">{children}</CardContent>
    </Card>
  );
}
