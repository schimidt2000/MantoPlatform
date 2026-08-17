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
import { VitrineVirtualPage } from "./pages/VitrineVirtualPage";
import { WishlistFloat } from "./components/WishlistFloat";

// Prefixo de rota condicional ao build de produção (feature 186, US6) — mesmo app servido sob
// `/catalogo/*` no mesmo serviço Railway do app interno (ver `frontend/server.js`); em dev
// continua em `/`, mesmo comportamento de sempre.
const CATALOGO_BASENAME = import.meta.env.PROD ? "/catalogo" : undefined;

/**
 * O cadastro público de talento mora na RAIZ do domínio (`/cadastro`), fora do `/catalogo`.
 *
 * `/catalogo/cadastro` é um endereço que não faz sentido para quem recebe o link: `/catalogo` é a
 * vitrine de personagens, não o lugar onde uma artista se inscreve. `/cadastro` também é o que já
 * está impresso e em circulação — era o formulário Jinja, agora aposentado.
 *
 * Os dois endereços saem deste mesmo bundle; o que muda é o `basename` do roteador, escolhido
 * pela URL que o navegador abriu. `/catalogo/cadastro/*` CONTINUA funcionando de propósito: os
 * e-mails de confirmação já enviados apontam para lá e o token não expira nunca
 * (`app/cadastro/verify_ops.py`).
 */
function isCadastroSurface(pathname: string): boolean {
  return pathname === "/cadastro" || pathname.startsWith("/cadastro/");
}

export function App() {
  const cadastroSurface = isCadastroSurface(window.location.pathname);

  return (
    <BrowserRouter basename={cadastroSurface ? undefined : CATALOGO_BASENAME}>
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
            por clareza — são de dois segmentos, então não colidem com ele de qualquer forma.
            `/v` sozinho é a home da loja (224e): é para onde `alo.mantoproducoes.com.br` manda
            quem digita só o domínio. */}
        <Route path="/v" element={<VitrineVirtualPage />} />
        <Route path="/v/:slug" element={<CampanhaVirtualPage />} />
        <Route path="/v/pedido/:token" element={<PedidoVirtualPage />} />
        <Route path="/:slug" element={<ProductDetailPage />} />
      </Routes>
      {/* A lista de desejos é da vitrine. Servida de `/cadastro`, sem o basename `/catalogo`, ela
          apontaria para `/lista-desejos` na raiz do domínio — que é o bundle do ERP interno. */}
      {!cadastroSurface && <WishlistFloat />}
    </BrowserRouter>
  );
}
