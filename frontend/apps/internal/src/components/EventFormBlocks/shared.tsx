import type { ReactNode } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@manto/ui";
import type { AlertaFormulario } from "../../lib/formulariosAdmin";

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

/** Selo "do formulário" (feature 298): o valor veio do que a cliente escreveu — confira. */
export function SeloDoFormulario() {
  return (
    <span className="ml-1.5 inline-block rounded-full bg-accent-soft px-1.5 py-0.5 align-middle text-[11px] font-medium text-accent-dark">
      do formulário
    </span>
  );
}

/** A marca "do formulário" de um campo, quando ele veio do formulário (feature 298). */
export function DoFormulario({
  campo,
  doFormulario,
}: {
  campo: string;
  doFormulario?: ReadonlySet<string>;
}) {
  return doFormulario?.has(campo) ? <SeloDoFormulario /> : null;
}

/**
 * Os alertas do formulário para um campo (feature 298): por que o valor não entrou (ou pede
 * conferência) e o que a cliente escreveu. A explicação vem pronta do servidor.
 */
export function AlertasDoCampo({
  campo,
  alertas,
}: {
  campo: string;
  alertas?: readonly AlertaFormulario[];
}) {
  const doCampo = (alertas ?? []).filter((a) => a.campo === campo);
  if (doCampo.length === 0) return null;
  return (
    <div className="mt-1 space-y-1">
      {doCampo.map((a, i) => (
        <p key={`${a.motivo}-${i}`} className="rounded bg-gold-50 px-2 py-1 text-xs text-ink">
          ⚠ {a.mensagem ?? "Confira este campo."}
          {a.texto_da_cliente && (
            <>
              {" "}
              A cliente escreveu: <span className="font-medium">“{a.texto_da_cliente}”</span>
            </>
          )}
        </p>
      ))}
    </div>
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
