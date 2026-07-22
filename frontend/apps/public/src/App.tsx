import { BrowserRouter, Route, Routes } from "react-router-dom";
import { CatalogGridPage } from "./pages/CatalogGridPage";
import { CategoriesPage } from "./pages/CategoriesPage";
import { CategoryDetailPage } from "./pages/CategoryDetailPage";
import { ProductDetailPage } from "./pages/ProductDetailPage";
import { WishlistPage } from "./pages/WishlistPage";
import { WishlistFloat } from "./components/WishlistFloat";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<CatalogGridPage />} />
        <Route path="/categorias" element={<CategoriesPage />} />
        <Route path="/categoria/:slug" element={<CategoryDetailPage />} />
        <Route path="/lista-desejos" element={<WishlistPage />} />
        <Route path="/:slug" element={<ProductDetailPage />} />
      </Routes>
      <WishlistFloat />
    </BrowserRouter>
  );
}
