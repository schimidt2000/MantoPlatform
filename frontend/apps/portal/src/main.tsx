import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { createQueryClient } from "@manto/api-client";
import { App } from "./App";
import { ME_KEY } from "./lib/portalAuth";
import "./index.css";

// Qualquer consulta que tome 401 significa que a sessão caiu. Zerar o talento em cache faz o
// `RequireTalentAuth` levar a pessoa ao login guardando o destino — em vez de deixá-la numa tela
// com o cabeçalho logado e o conteúdo dizendo "não foi possível carregar", que era o estado
// impossível de diagnosticar.
const queryClient = createQueryClient({
  aoPerderSessao: () => queryClient.setQueryData(ME_KEY, null),
});

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Elemento #root não encontrado");
}

createRoot(rootElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
