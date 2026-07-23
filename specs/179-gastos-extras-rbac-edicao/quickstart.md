# Quickstart: Gastos Extras — RBAC, edição, "Aprovado com edições"

## Rodar localmente

```powershell
# Backend, apontado para a cópia local de produção (Postgres) — nunca SQLite
.\scripts\db\run-local.ps1

# Frontend (outro terminal)
cd frontend
npm run dev:internal
```

Acesse `http://localhost:5173/gastos` (ou porta configurada pelo Vite) autenticado como:
- Um usuário sem papel `SUPERADMIN`/`FINANCEIRO` → deve ver só "Meus Gastos", sem KPIs.
- Um usuário com papel `FINANCEIRO` (ou `SUPERADMIN`) → deve ver os 4 KPIs + tabela completa +
  ações completas.

## Aplicar a migration nova

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim()
python -m flask db upgrade
python -m flask db heads   # confirma que ficou no head novo
```

## Roteiro de verificação manual (mínimo antes de "pronto")

1. Colaborador comum registra um gasto pelo modal "+ Novo gasto" (com nota fiscal) → aparece
   como "Pendente" só para ele.
2. Financeiro abre a tela → vê os 4 KPIs e o gasto acima na tabela global.
3. Financeiro clica "Aprovar" (sem editar) → vira "Aprovado" simples.
4. Financeiro edita outro gasto pendente (corrige o valor) e usa "Salvar e Aprovar" → vira
   "Aprovado c/ edições", visível com esse rótulo tanto para o financeiro quanto para o autor.
5. Financeiro edita um gasto já "Aprovado" (corrige a categoria) → vira "Aprovado c/ edições".
6. Financeiro tenta editar um gasto "Rejeitado" sem marcar "Salvar e Aprovar" → bloqueado (409).
7. Conferir que a tela Jinja legada (`/gastos` fora do painel Beta, se ainda acessível) continua
   idêntica ao comportamento anterior — nenhuma mudança visível nela.
8. Conferir no app real que o total do DRE/planilha de pagamentos do período inclui os gastos
   "aprovado c/ edições" corretamente (mesma soma de antes da mudança).
9. Testar o modal em viewport mobile (320–430px) — sem rolagem horizontal, campos utilizáveis.
