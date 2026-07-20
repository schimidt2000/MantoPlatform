import { type ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { Skeleton } from "@manto/ui";
import { useCurrentUser } from "../lib/useAuth";

/** Guarda de rota: redireciona para /login quando não há sessão válida. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { data: user, isLoading } = useCurrentUser();

  if (isLoading) {
    return (
      <div className="mx-auto max-w-2xl space-y-4 p-6">
        <Skeleton className="h-8 w-1/3" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
