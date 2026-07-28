import { type ReactNode } from "react";
import { useCurrentTalent } from "../lib/portalAuth";
import { PortalChangePasswordPage } from "../pages/PortalChangePasswordPage";
import { PortalTermsPage } from "../pages/PortalTermsPage";

/**
 * Trava de onboarding: enquanto o talento tiver etapa de conta pendente, é ela que ocupa a tela.
 *
 * Serve a etapa no lugar do app em vez de redirecionar para uma rota — assim não existe URL de
 * onboarding que alguém possa pular digitando na barra de endereço, e o gate continua valendo em
 * qualquer rota profunda (deep link para `/agenda` com senha pendente cai aqui também).
 *
 * A ordem vem de `pending_steps` do backend (`portal_account_ops.pending_account_steps`) — fonte
 * única, para o front não reimplementar a regra de qual etapa vem primeiro.
 */
export function OnboardingGate({ children }: { children: ReactNode }) {
  const { data: talent } = useCurrentTalent();

  const nextStep = talent?.pending_steps?.[0];

  if (nextStep === "change_password") {
    return <PortalChangePasswordPage />;
  }

  if (nextStep === "accept_terms") {
    return <PortalTermsPage />;
  }

  return <>{children}</>;
}
