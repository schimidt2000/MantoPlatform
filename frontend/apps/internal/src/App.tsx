import { BrowserRouter, Navigate, Route, Routes, useParams } from "react-router-dom";
import { RequireAuth } from "./components/RequireAuth";
import { isRevendedorOnly, useCurrentUser } from "./lib/useAuth";
import { AppShell } from "./components/AppShell";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { AgendaPage } from "./pages/AgendaPage";
import { EventDetailPage } from "./pages/EventDetailPage";
import { EventCreatePage } from "./pages/EventCreatePage";
import { EventEditPage } from "./pages/EventEditPage";
import { EventosCancelamentosPage } from "./pages/EventosCancelamentosPage";
import { TalentsListPage } from "./pages/TalentsListPage";
import { TalentDetailPage } from "./pages/TalentDetailPage";
import { FigurinoListPage } from "./pages/FigurinoListPage";
import { FigurinoFormPage } from "./pages/FigurinoFormPage";
import { FigurinoProducaoListPage } from "./pages/FigurinoProducaoListPage";
import { FigurinoProducaoDetailPage } from "./pages/FigurinoProducaoDetailPage";
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
import { EducaMantoPackagesPage } from "./pages/EducaMantoPackagesPage";
import { EducaMantoPackageFormPage } from "./pages/EducaMantoPackageFormPage";
import { EducaMantoHistoricoPage } from "./pages/EducaMantoHistoricoPage";
import { GastosExtrasPage } from "./pages/GastosExtrasPage";
import { GastosRecorrentesPage } from "./pages/GastosRecorrentesPage";
import { OrcamentoCalculadoraPage } from "./pages/OrcamentoCalculadoraPage";
import { OrcamentoConfigPrecosPage } from "./pages/OrcamentoConfigPrecosPage";
import { OrcamentoHistoricoPage } from "./pages/OrcamentoHistoricoPage";
import { OrcamentoResultadoPage } from "./pages/OrcamentoResultadoPage";
import { AvaliacaoCastingPage } from "./pages/AvaliacaoCastingPage";
import { FormulariosAdminPage } from "./pages/FormulariosAdminPage";
import { Acervo3DPage } from "./pages/Acervo3DPage";
import { Fila3DPage } from "./pages/Fila3DPage";
import { MarketingPainelPage } from "./pages/MarketingPainelPage";
import { VirtuaisCampanhasPage } from "./pages/VirtuaisCampanhasPage";
import { VirtuaisCampanhaFormPage } from "./pages/VirtuaisCampanhaFormPage";
import { VirtuaisDevolucoesPage } from "./pages/VirtuaisDevolucoesPage";
import { FilaProducaoMidiaPage } from "./pages/FilaProducaoMidiaPage";
import { MarketingMetasPage } from "./pages/MarketingMetasPage";

/** Rota antiga `/talents/:id/edit` — redireciona para o modo edição unificado (feature 180). */
function TalentEditRedirect() {
  const { id } = useParams<{ id: string }>();
  return <Navigate to={`/talents/${id}?edit=1`} replace />;
}

/**
 * A Home não faz parte do perfil do Revendedor EducaManto (feature 078) — o servidor recusa os
 * dados dela. Além do destino pós-login, isto cobre quem chega em "/" por favorito ou clicando na
 * marca no topo: em vez de um painel vazio de erro, cai na Agenda.
 */
function HomeOuAgenda() {
  const { data, isLoading } = useCurrentUser();
  if (isLoading) return null;
  return isRevendedorOnly(data) ? <Navigate to="/agenda" replace /> : <DashboardPage />;
}

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
          <Route path="/" element={<HomeOuAgenda />} />
          <Route path="/agenda" element={<AgendaPage />} />
          <Route path="/events/new" element={<EventCreatePage />} />
          {/* Declarada ANTES de `/events/:id` — `:id` casaria com "cancelamentos". */}
          <Route path="/events/cancelamentos" element={<EventosCancelamentosPage />} />
          <Route path="/events/:id/edit" element={<EventEditPage />} />
          <Route path="/events/:id" element={<EventDetailPage />} />
          <Route path="/talents" element={<TalentsListPage />} />
          <Route path="/casting/avaliacoes" element={<AvaliacaoCastingPage />} />
          <Route path="/formularios" element={<FormulariosAdminPage />} />
          <Route path="/talents/:id" element={<TalentDetailPage />} />
          <Route path="/talents/:id/edit" element={<TalentEditRedirect />} />
          <Route path="/3d/acervo" element={<Acervo3DPage />} />
          <Route path="/3d/fila" element={<Fila3DPage />} />
          <Route path="/virtuais/campanhas" element={<VirtuaisCampanhasPage />} />
          <Route path="/virtuais/campanhas/:id" element={<VirtuaisCampanhaFormPage />} />
          <Route path="/virtuais/devolucoes" element={<VirtuaisDevolucoesPage />} />
          <Route path="/virtuais/producao" element={<FilaProducaoMidiaPage />} />
          <Route path="/marketing/painel" element={<MarketingPainelPage />} />
          <Route path="/marketing/metas" element={<MarketingMetasPage />} />
          <Route path="/figurinos" element={<FigurinoListPage />} />
          {/* Declaradas ANTES das dinâmicas: "/figurinos/producao/12" não pode cair em
              "/figurinos/:id/edit" (mesmo cuidado que "/events/cancelamentos" exigiu na 224). */}
          <Route path="/figurinos/producao" element={<FigurinoProducaoListPage />} />
          <Route path="/figurinos/producao/:id" element={<FigurinoProducaoDetailPage />} />
          {/* 225f — `/compras` teve item de menu próprio por um dia; virou aba da mesma tela.
              O redirect fica porque a rota já circulou em links e favoritos, e porque é ele que
              mantém "abrir direto nas compras" possível a partir de qualquer lugar. */}
          <Route path="/compras" element={<Navigate to="/figurinos/producao?tipo=compra" replace />} />
          <Route path="/figurinos/new" element={<FigurinoFormPage />} />
          <Route path="/figurinos/:id/edit" element={<FigurinoFormPage />} />
          <Route path="/vendas" element={<VendasPipelinePage />} />
          <Route path="/financeiro" element={<FinanceiroDashboardPage />} />
          <Route path="/financeiro/comissoes" element={<ComissoesPage />} />
          <Route path="/financeiro/pagamentos" element={<PagamentosPage />} />
          <Route path="/gastos" element={<GastosExtrasPage />} />
          <Route path="/gastos/recorrentes" element={<GastosRecorrentesPage />} />
          <Route path="/orcamento" element={<OrcamentoCalculadoraPage />} />
          <Route path="/orcamento/historico" element={<OrcamentoHistoricoPage />} />
          <Route path="/orcamento/configuracoes" element={<OrcamentoConfigPrecosPage />} />
          {/* Depois das rotas fixas: `/orcamento/:id` casaria "historico" e "configuracoes". */}
          <Route path="/orcamento/:id" element={<OrcamentoResultadoPage />} />
          <Route path="/educamanto" element={<EducaMantoCalculadoraPage />} />
          <Route path="/educamanto/pacotes" element={<EducaMantoPackagesPage />} />
          <Route path="/educamanto/pacotes/novo" element={<EducaMantoPackageFormPage />} />
          <Route path="/educamanto/pacotes/:id/editar" element={<EducaMantoPackageFormPage />} />
          <Route path="/educamanto/historico" element={<EducaMantoHistoricoPage />} />
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
