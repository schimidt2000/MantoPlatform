# Quickstart — Fundação (144, User Story 1)

## Estrutura de diretórios nova

```text
Manto_Platform/
├── app/                        # Flask (existente) — passa a servir só /api/*
├── frontend/
│   ├── package.json            # npm workspaces root
│   ├── apps/
│   │   ├── internal/           # SPA staff (admin/agenda/financeiro/...) — US1 começa aqui
│   │   ├── portal/             # SPA Portal do Artista (US3+)
│   │   └── public/             # SPA anônima (catálogo/cadastro/formulários/feedback) (US5+)
│   └── packages/
│       ├── ui/                 # shadcn/ui configurado + tema Tailwind base
│       ├── api-client/         # fetch wrapper tipado + hooks TanStack Query
│       └── money/              # <MoneyInput> + hook de formatação BRL (fonte única, FR-012)
```

`apps/portal` e `apps/public` são criados como scaffolding vazio nesta fatia (só o essencial
para o workspace resolver), sem telas reais — o conteúdo delas é escopo de US3/US5.

## Rodar em desenvolvimento

```powershell
# Backend (Flask API) — igual hoje, contra manto_local
.\scripts\db\run-local.ps1

# Frontend (novo terminal, dentro de frontend/)
npm install
npm run dev --workspace=apps/internal
```

`vite.config.ts` de `apps/internal` proxya `/api/*` para `http://localhost:5000` (porta do
Flask) — ver `research.md` §2. Cookie de sessão funciona em dev sem CORS relaxado por causa
do proxy.

## Verificação funcional desta fatia

- Backend: script Python (`scripts/db/verify_144_auth_dashboard.py`, gitignored, mesmo
  padrão das features anteriores) usando o test client do Flask contra `manto_local`,
  chamando `/api/auth/login`, `/api/auth/me`, `/api/dashboard`, `/api/auth/logout` — sucesso,
  credenciais inválidas, acesso sem sessão (401), e RBAC condicionando os campos do
  dashboard por papel.
- Frontend: `npx tsc --noEmit` e `npm run build` sem erros em `apps/internal` (novo portão de
  qualidade da constituição 2.0.0); conferência manual no browser do fluxo login → dashboard,
  incluindo estados de loading/erro/sucesso e a transição Framer Motion no botão de login.
