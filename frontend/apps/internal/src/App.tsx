import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { RequireAuth } from "./components/RequireAuth";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { AgendaPage } from "./pages/AgendaPage";
import { EventDetailPage } from "./pages/EventDetailPage";
import { EventCreatePage } from "./pages/EventCreatePage";
import { TalentsListPage } from "./pages/TalentsListPage";
import { TalentDetailPage } from "./pages/TalentDetailPage";
import { TalentEditPage } from "./pages/TalentEditPage";
import { FigurinoListPage } from "./pages/FigurinoListPage";
import { FigurinoFormPage } from "./pages/FigurinoFormPage";
import { VendasPipelinePage } from "./pages/VendasPipelinePage";
import { FinanceiroDashboardPage } from "./pages/FinanceiroDashboardPage";
import { ComissoesPage } from "./pages/ComissoesPage";
import { PagamentosPage } from "./pages/PagamentosPage";
import { ClientsListPage } from "./pages/ClientsListPage";
import { ClientDetailPage } from "./pages/ClientDetailPage";
import { ClientFeedbackPage } from "./pages/ClientFeedbackPage";
import { RhDashboardPage } from "./pages/RhDashboardPage";
import { AdminUsersListPage } from "./pages/AdminUsersListPage";
import { AdminUserCreatePage } from "./pages/AdminUserCreatePage";
import { AdminUserEditPage } from "./pages/AdminUserEditPage";
import { AdminSettingsPage } from "./pages/AdminSettingsPage";
import { AdminLogsPage } from "./pages/AdminLogsPage";
import { AdminDesempenhoPage } from "./pages/AdminDesempenhoPage";
import { AdminSyncPage } from "./pages/AdminSyncPage";
import { AdminPortalAnnouncementPage } from "./pages/AdminPortalAnnouncementPage";
import { AdminMigrarArquivosPage } from "./pages/AdminMigrarArquivosPage";
import { AdminImportarCatalogoPage } from "./pages/AdminImportarCatalogoPage";
import { AdminCatalogoListPage } from "./pages/AdminCatalogoListPage";
import { AdminCatalogoFormPage } from "./pages/AdminCatalogoFormPage";
import { RevisaoListPage } from "./pages/RevisaoListPage";
import { RevisaoSpaceCreatePage } from "./pages/RevisaoSpaceCreatePage";
import { RevisaoSpacePage } from "./pages/RevisaoSpacePage";
import { RevisaoAssetPage } from "./pages/RevisaoAssetPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <DashboardPage />
            </RequireAuth>
          }
        />
        <Route
          path="/agenda"
          element={
            <RequireAuth>
              <AgendaPage />
            </RequireAuth>
          }
        />
        <Route
          path="/events/new"
          element={
            <RequireAuth>
              <EventCreatePage />
            </RequireAuth>
          }
        />
        <Route
          path="/events/:id"
          element={
            <RequireAuth>
              <EventDetailPage />
            </RequireAuth>
          }
        />
        <Route
          path="/talents"
          element={
            <RequireAuth>
              <TalentsListPage />
            </RequireAuth>
          }
        />
        <Route
          path="/talents/:id"
          element={
            <RequireAuth>
              <TalentDetailPage />
            </RequireAuth>
          }
        />
        <Route
          path="/talents/:id/edit"
          element={
            <RequireAuth>
              <TalentEditPage />
            </RequireAuth>
          }
        />
        <Route
          path="/figurinos"
          element={
            <RequireAuth>
              <FigurinoListPage />
            </RequireAuth>
          }
        />
        <Route
          path="/figurinos/new"
          element={
            <RequireAuth>
              <FigurinoFormPage />
            </RequireAuth>
          }
        />
        <Route
          path="/figurinos/:id/edit"
          element={
            <RequireAuth>
              <FigurinoFormPage />
            </RequireAuth>
          }
        />
        <Route
          path="/vendas"
          element={
            <RequireAuth>
              <VendasPipelinePage />
            </RequireAuth>
          }
        />
        <Route
          path="/financeiro"
          element={
            <RequireAuth>
              <FinanceiroDashboardPage />
            </RequireAuth>
          }
        />
        <Route
          path="/financeiro/comissoes"
          element={
            <RequireAuth>
              <ComissoesPage />
            </RequireAuth>
          }
        />
        <Route
          path="/financeiro/pagamentos"
          element={
            <RequireAuth>
              <PagamentosPage />
            </RequireAuth>
          }
        />
        <Route
          path="/clientes"
          element={
            <RequireAuth>
              <ClientsListPage />
            </RequireAuth>
          }
        />
        <Route
          path="/clientes/avaliacoes"
          element={
            <RequireAuth>
              <ClientFeedbackPage />
            </RequireAuth>
          }
        />
        <Route
          path="/clientes/:id"
          element={
            <RequireAuth>
              <ClientDetailPage />
            </RequireAuth>
          }
        />
        <Route
          path="/rh"
          element={
            <RequireAuth>
              <RhDashboardPage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/usuarios"
          element={
            <RequireAuth>
              <AdminUsersListPage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/usuarios/novo"
          element={
            <RequireAuth>
              <AdminUserCreatePage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/usuarios/:id"
          element={
            <RequireAuth>
              <AdminUserEditPage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/configuracoes"
          element={
            <RequireAuth>
              <AdminSettingsPage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/logs"
          element={
            <RequireAuth>
              <AdminLogsPage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/desempenho"
          element={
            <RequireAuth>
              <AdminDesempenhoPage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/sync"
          element={
            <RequireAuth>
              <AdminSyncPage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/anuncio-portal"
          element={
            <RequireAuth>
              <AdminPortalAnnouncementPage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/migrar-arquivos"
          element={
            <RequireAuth>
              <AdminMigrarArquivosPage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/importar-catalogo"
          element={
            <RequireAuth>
              <AdminImportarCatalogoPage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/catalogo"
          element={
            <RequireAuth>
              <AdminCatalogoListPage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/catalogo/novo"
          element={
            <RequireAuth>
              <AdminCatalogoFormPage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/catalogo/:id/editar"
          element={
            <RequireAuth>
              <AdminCatalogoFormPage />
            </RequireAuth>
          }
        />
        <Route
          path="/revisao"
          element={
            <RequireAuth>
              <RevisaoListPage />
            </RequireAuth>
          }
        />
        <Route
          path="/revisao/novo"
          element={
            <RequireAuth>
              <RevisaoSpaceCreatePage />
            </RequireAuth>
          }
        />
        <Route
          path="/revisao/:id"
          element={
            <RequireAuth>
              <RevisaoSpacePage />
            </RequireAuth>
          }
        />
        <Route
          path="/revisao/:spaceId/asset/:assetId"
          element={
            <RequireAuth>
              <RevisaoAssetPage />
            </RequireAuth>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
