import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { RequireTalentAuth } from "./components/RequireTalentAuth";
import { PortalShell } from "./components/PortalShell";
import { PortalLoginPage } from "./pages/PortalLoginPage";
import { PortalAgendaPage } from "./pages/PortalAgendaPage";
import { PortalConvitesPage } from "./pages/PortalConvitesPage";
import { PortalFigurinoPage } from "./pages/PortalFigurinoPage";
import { PortalFotosDocumentosPage } from "./pages/PortalFotosDocumentosPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<PortalLoginPage />} />
        <Route
          element={
            <RequireTalentAuth>
              <PortalShell />
            </RequireTalentAuth>
          }
        >
          <Route path="/" element={<Navigate to="/agenda" replace />} />
          <Route path="/agenda" element={<PortalAgendaPage />} />
          <Route path="/convites" element={<PortalConvitesPage />} />
          <Route path="/eventos/:eventId/figurino" element={<PortalFigurinoPage />} />
          <Route path="/fotos-documentos" element={<PortalFotosDocumentosPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
