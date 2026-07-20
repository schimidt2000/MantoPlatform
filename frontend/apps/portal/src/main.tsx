import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Elemento #root não encontrado");
}

// Placeholder — a migração do Portal do Artista acontece na User Story 3.
createRoot(rootElement).render(
  <StrictMode>
    <main style={{ fontFamily: "system-ui", padding: "2rem" }}>
      <h1>Portal do Artista</h1>
      <p>Em construção (User Story 3 da migração).</p>
    </main>
  </StrictMode>,
);
