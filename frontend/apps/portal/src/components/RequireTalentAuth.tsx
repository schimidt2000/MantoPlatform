import { type ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { Skeleton } from "@manto/ui";
import { comDestino } from "../lib/destino";
import { useCurrentTalent } from "../lib/portalAuth";

/** Guarda de rota: redireciona para /login quando não há sessão de talento válida. */
export function RequireTalentAuth({ children }: { children: ReactNode }) {
  const { data: talent, isLoading } = useCurrentTalent();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="mx-auto max-w-md space-y-4 p-4">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (!talent) {
    // Guarda para onde a pessoa QUERIA ir: quem chega pelo link do e-mail de reenvio de fotos
    // precisa voltar a `/fotos-documentos` depois de entrar, e não à agenda.
    return <Navigate to={comDestino("/login", location.pathname)} replace />;
  }

  return <>{children}</>;
}
