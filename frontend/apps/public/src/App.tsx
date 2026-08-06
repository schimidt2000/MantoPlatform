import { BrowserRouter, Route, Routes } from "react-router-dom";
import { CatalogGridPage } from "./pages/CatalogGridPage";
import { CategoriesPage } from "./pages/CategoriesPage";
import { CategoryDetailPage } from "./pages/CategoryDetailPage";
import { ProductDetailPage } from "./pages/ProductDetailPage";
import { WishlistPage } from "./pages/WishlistPage";
import { CadastroPage } from "./pages/CadastroPage";
import { CadastroSucessoPage } from "./pages/CadastroSucessoPage";
import { CadastroConfirmarPage } from "./pages/CadastroConfirmarPage";
import { FormularioPage } from "./pages/FormularioPage";
import { FormularioEnviadoPage } from "./pages/FormularioEnviadoPage";
import { AvaliarPage } from "./pages/AvaliarPage";
import { CampanhaVirtualPage } from "./pages/CampanhaVirtualPage";
import { PedidoVirtualPage } from "./pages/PedidoVirtualPage";
import { WishlistFloat } from "./components/WishlistFloat";

// Prefixo de rota condicional ao build de produção (feature 186, US6) — mesmo app servido sob
// `/catalogo/*` no mesmo serviço Railway do app interno (ver `frontend/server.js`); em dev
// continua em `/`, mesmo comportamento de sempre.
const BASENAME = import.meta.env.PROD ? "/catalogo" : undefined;

export function App() {
  return (
    <BrowserRouter basename={BASENAME}>
      <Routes>
        <Route path="/" element={<CatalogGridPage />} />
        <Route path="/categorias" element={<CategoriesPage />} />
        <Route path="/categoria/:slug" element={<CategoryDetailPage />} />
        <Route path="/lista-desejos" element={<WishlistPage />} />
        <Route path="/cadastro" element={<CadastroPage />} />
        <Route path="/cadastro/enviado" element={<CadastroSucessoPage />} />
        <Route path="/cadastro/confirmar/:token" element={<CadastroConfirmarPage />} />
        <Route path="/f/pre-contrato" element={<FormularioPage formType="comum" />} />
        <Route path="/f/corporativo" element={<FormularioPage formType="corporativo" />} />
        <Route path="/f/:formType/enviado" element={<FormularioEnviadoPage />} />
        <Route path="/avaliar/:token" element={<AvaliarPage />} />
        {/* Loja de Interações Virtuais (feature 205). Declaradas antes do catch-all `/:slug`
            por clareza — são de dois segmentos, então não colidem com ele de qualquer forma. */}
        <Route path="/v/:slug" element={<CampanhaVirtualPage />} />
        <Route path="/v/pedido/:token" element={<PedidoVirtualPage />} />
        <Route path="/:slug" element={<ProductDetailPage />} />
      </Routes>
      <WishlistFloat />
    </BrowserRouter>
  );
}
