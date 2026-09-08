import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { createQueryClient } from "@manto/api-client";
import { App } from "./App";
import { ME_KEY } from "./lib/useAuth";
import "./index.css";

// Qualquer consulta que tome 401 significa que a sessão caiu. Zerar o usuário em cache manda a
// pessoa ao login em vez de deixá-la olhando "não foi possível carregar" numa casca logada —
// estado que o portal já não produzia (feature 294) mas que o ERP ainda produzia, e que custou
// várias rodadas de investigação em cima do servidor quando o cookie é que estava duplicado
// (feature 295). O `useCurrentUser` engole o 401 do próprio `/api/auth/me` e devolve `null`, então
// sem isto nenhuma tela do ERP tinha como saber que a sessão tinha morrido.
const queryClient = createQueryClient({
  aoPerderSessao: () => queryClient.setQueryData(ME_KEY, null),
});

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Elemento #root não encontrado no index.html");
}

createRoot(rootElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
