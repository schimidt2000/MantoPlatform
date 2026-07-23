import { type ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { Skeleton } from "@manto/ui";
import { useCurrentTalent } from "../lib/portalAuth";

/** Guarda de rota: redireciona para /login quando não há sessão de talento válida. */
export function RequireTalentAuth({ children }: { children: ReactNode }) {
  const { data: talent, isLoading } = useCurrentTalent();

  if (isLoading) {
    return (
      <div className="mx-auto max-w-md space-y-4 p-4">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (!talent) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
