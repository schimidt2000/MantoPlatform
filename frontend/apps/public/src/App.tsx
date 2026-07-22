import { BrowserRouter, Route, Routes } from "react-router-dom";
import { CatalogGridPage } from "./pages/CatalogGridPage";
import { CategoriesPage } from "./pages/CategoriesPage";
import { CategoryDetailPage } from "./pages/CategoryDetailPage";
import { ProductDetailPage } from "./pages/ProductDetailPage";
import { WishlistPage } from "./pages/WishlistPage";
import { CadastroPage } from "./pages/CadastroPage";
import { CadastroSucessoPage } from "./pages/CadastroSucessoPage";
import { FormularioPage } from "./pages/FormularioPage";
import { FormularioEnviadoPage } from "./pages/FormularioEnviadoPage";
import { WishlistFloat } from "./components/WishlistFloat";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<CatalogGridPage />} />
        <Route path="/categorias" element={<CategoriesPage />} />
        <Route path="/categoria/:slug" element={<CategoryDetailPage />} />
        <Route path="/lista-desejos" element={<WishlistPage />} />
        <Route path="/cadastro" element={<CadastroPage />} />
        <Route path="/cadastro/enviado" element={<CadastroSucessoPage />} />
        <Route path="/f/pre-contrato" element={<FormularioPage formType="comum" />} />
        <Route path="/f/corporativo" element={<FormularioPage formType="corporativo" />} />
        <Route path="/f/:formType/enviado" element={<FormularioEnviadoPage />} />
        <Route path="/:slug" element={<ProductDetailPage />} />
      </Routes>
      <WishlistFloat />
    </BrowserRouter>
  );
}
