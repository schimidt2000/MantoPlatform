# Quickstart — Agenda/Eventos leitura (145, US1)

Reaproveita a estrutura da Fundação (feature 144). Nada de novo no monorepo — só novas telas
em `apps/internal` e novos endpoints de leitura no Flask.

## Rodar em desenvolvimento

```powershell
# Backend (Flask API) contra manto_local
.\scripts\db\run-local.ps1

# Frontend (dentro de frontend/)
npm run dev:internal   # proxy /api -> Flask; abre em http://localhost:5173
```

Novas rotas no app: `/agenda` e `/events/:id` (sob login), acessíveis a partir do dashboard.

## Verificação desta fatia

- **Backend (o que importa)**: `scripts/db/verify_145_agenda_read.py` (gitignored) — test
  client contra `manto_local`, requests fora de `app_context`:
  - `GET /api/agenda?ym=...` retorna os mesmos ids de evento que `_build_events_from_db`.
  - `GET /api/events/<id>` como **superadmin**: contém blocos financeiros; totais (custo,
    comissão, recebido, reembolso pendente) batem com o cálculo da view Jinja.
  - `GET /api/events/<id>` como **casting sem financeiro**: NÃO contém nenhum campo de
    venda/pagamento/reembolso/comissão.
  - 404 para evento inexistente; 401 sem sessão.
- **Frontend**: `npx tsc --noEmit` e `npm run build` em `apps/internal` sem erros; conferência
  manual (com o usuário) em viewport mobile — a equipe usa muito a agenda no celular.

## Paridade (critério de aceite)

Abrir o mesmo evento em `beta` (React) e em `app.` (Jinja) com o mesmo usuário e conferir que as
seções e os valores exibidos são os mesmos, respeitando as permissões do papel.
