import { request, type FullConfig } from "@playwright/test";

/**
 * Login único via `POST /api/auth/login` (cookie de sessão HttpOnly) antes da suíte inteira,
 * reaproveitado por todos os specs via `storageState` (feature 180 — ver quickstart.md).
 *
 * Requer um usuário CASTING ou SUPERADMIN já existente em `manto_local`, informado via
 * `E2E_USER_EMAIL`/`E2E_USER_PASSWORD` (não criamos usuário aqui — evita duplicar a lógica de
 * bootstrap de conta fora do fluxo real da aplicação).
 */
export default async function globalSetup(config: FullConfig): Promise<void> {
  const baseURL = config.projects[0]?.use?.baseURL ?? "http://localhost:5173";
  const email = process.env.E2E_USER_EMAIL;
  const password = process.env.E2E_USER_PASSWORD;

  if (!email || !password) {
    throw new Error(
      "E2E_USER_EMAIL e E2E_USER_PASSWORD são obrigatórios para rodar os testes Playwright — " +
        "use um usuário CASTING/SUPERADMIN já existente em manto_local.",
    );
  }

  const context = await request.newContext({ baseURL });
  const response = await context.post("/api/auth/login", {
    data: { email, password },
  });
  if (!response.ok()) {
    throw new Error(`Login e2e falhou (${response.status()}) — confirme as credenciais de teste.`);
  }
  await context.storageState({ path: "e2e/.auth/state.json" });
  await context.dispose();
}
