import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { RequireTalentAuth } from "./components/RequireTalentAuth";
import { OnboardingGate } from "./components/OnboardingGate";
import { PortalShell } from "./components/PortalShell";
import { PortalLoginPage } from "./pages/PortalLoginPage";
import { PortalFirstAccessPage } from "./pages/PortalFirstAccessPage";
import { PortalForgotPasswordPage } from "./pages/PortalForgotPasswordPage";
import { PortalResetPasswordPage } from "./pages/PortalResetPasswordPage";
import { PortalTermsPage } from "./pages/PortalTermsPage";
import { PortalAgendaPage } from "./pages/PortalAgendaPage";
import { PortalConvitesPage } from "./pages/PortalConvitesPage";
import { PortalFigurinoPage } from "./pages/PortalFigurinoPage";
import { PortalFotosDocumentosPage } from "./pages/PortalFotosDocumentosPage";
import { PortalProfilePage } from "./pages/PortalProfilePage";
import { PortalHistoricoPage } from "./pages/PortalHistoricoPage";
import { PortalRatePage } from "./pages/PortalRatePage";

/**
 * Rotas do Portal do Artista.
 *
 * `basename` vem de `import.meta.env.BASE_URL` (o `base` do Vite): em produção o app é servido
 * sob `/portal/` pelo mesmo serviço estático dos outros bundles (`frontend/server.js`), e em dev
 * fica na raiz do dev server. Sem isso, um refresh em `/portal/agenda` não casaria com nenhuma
 * rota — o React Router veria o prefixo como parte do caminho.
 */
export function App() {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <Routes>
        {/* Fora da sessão */}
        <Route path="/login" element={<PortalLoginPage />} />
        <Route path="/first-access" element={<PortalFirstAccessPage />} />
        <Route path="/forgot-password" element={<PortalForgotPasswordPage />} />
        <Route path="/reset-password/:token" element={<PortalResetPasswordPage />} />

        {/* Autenticado — `OnboardingGate` segura a tela enquanto houver etapa de conta pendente */}
        <Route
          element={
            <RequireTalentAuth>
              <OnboardingGate>
                <PortalShell />
              </OnboardingGate>
            </RequireTalentAuth>
          }
        >
          <Route path="/" element={<Navigate to="/agenda" replace />} />
          <Route path="/agenda" element={<PortalAgendaPage />} />
          <Route path="/convites" element={<PortalConvitesPage />} />
          <Route path="/historico" element={<PortalHistoricoPage />} />
          <Route path="/perfil" element={<PortalProfilePage />} />
          <Route path="/fotos-documentos" element={<PortalFotosDocumentosPage />} />
          <Route path="/eventos/:eventId/figurino" element={<PortalFigurinoPage />} />
          <Route path="/eventos/:eventId/avaliar" element={<PortalRatePage />} />
          <Route path="/termos" element={<PortalTermsPage viewOnly />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
