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
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
