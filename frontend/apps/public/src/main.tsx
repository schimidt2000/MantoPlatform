import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Elemento #root não encontrado");
}

// Placeholder — catálogo público e demais superfícies anônimas são a User Story 5.
createRoot(rootElement).render(
  <StrictMode>
    <main style={{ fontFamily: "system-ui", padding: "2rem" }}>
      <h1>Manto Produções</h1>
      <p>Em construção (User Story 5 da migração).</p>
    </main>
  </StrictMode>,
);
