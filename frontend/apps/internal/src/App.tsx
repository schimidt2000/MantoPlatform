import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { RequireAuth } from "./components/RequireAuth";
import { AppShell } from "./components/AppShell";
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
import { EducaMantoCalculadoraPage } from "./pages/EducaMantoCalculadoraPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        {/* Layout route (feature 173): todas as rotas autenticadas dentro do shell. */}
        <Route
          element={
            <RequireAuth>
              <AppShell />
            </RequireAuth>
          }
        >
          <Route path="/" element={<DashboardPage />} />
          <Route path="/agenda" element={<AgendaPage />} />
          <Route path="/events/new" element={<EventCreatePage />} />
          <Route path="/events/:id" element={<EventDetailPage />} />
          <Route path="/talents" element={<TalentsListPage />} />
          <Route path="/talents/:id" element={<TalentDetailPage />} />
          <Route path="/talents/:id/edit" element={<TalentEditPage />} />
          <Route path="/figurinos" element={<FigurinoListPage />} />
          <Route path="/figurinos/new" element={<FigurinoFormPage />} />
          <Route path="/figurinos/:id/edit" element={<FigurinoFormPage />} />
          <Route path="/vendas" element={<VendasPipelinePage />} />
          <Route path="/financeiro" element={<FinanceiroDashboardPage />} />
          <Route path="/financeiro/comissoes" element={<ComissoesPage />} />
          <Route path="/financeiro/pagamentos" element={<PagamentosPage />} />
          <Route path="/educamanto" element={<EducaMantoCalculadoraPage />} />
          <Route path="/clientes" element={<ClientsListPage />} />
          <Route path="/clientes/avaliacoes" element={<ClientFeedbackPage />} />
          <Route path="/clientes/:id" element={<ClientDetailPage />} />
          <Route path="/rh" element={<RhDashboardPage />} />
          <Route path="/admin/usuarios" element={<AdminUsersListPage />} />
          <Route path="/admin/usuarios/novo" element={<AdminUserCreatePage />} />
          <Route path="/admin/usuarios/:id" element={<AdminUserEditPage />} />
          <Route path="/admin/configuracoes" element={<AdminSettingsPage />} />
          <Route path="/admin/logs" element={<AdminLogsPage />} />
          <Route path="/admin/desempenho" element={<AdminDesempenhoPage />} />
          <Route path="/admin/sync" element={<AdminSyncPage />} />
          <Route path="/admin/anuncio-portal" element={<AdminPortalAnnouncementPage />} />
          <Route path="/admin/migrar-arquivos" element={<AdminMigrarArquivosPage />} />
          <Route path="/admin/importar-catalogo" element={<AdminImportarCatalogoPage />} />
          <Route path="/admin/catalogo" element={<AdminCatalogoListPage />} />
          <Route path="/admin/catalogo/novo" element={<AdminCatalogoFormPage />} />
          <Route path="/admin/catalogo/:id/editar" element={<AdminCatalogoFormPage />} />
          <Route path="/revisao" element={<RevisaoListPage />} />
          <Route path="/revisao/novo" element={<RevisaoSpaceCreatePage />} />
          <Route path="/revisao/:id" element={<RevisaoSpacePage />} />
          <Route path="/revisao/:spaceId/asset/:assetId" element={<RevisaoAssetPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
