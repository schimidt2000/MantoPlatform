# Quickstart: EducaManto — Pacotes e Conteúdos em React

## Rodar localmente

```powershell
# Backend, apontando para manto_local (Postgres) — nunca o SQLite vazio
.\scripts\db\run-local.ps1

# Frontend (staff)
cd frontend; npm run dev:internal
```

Acessar `/educamanto` (calculadora), `/educamanto/pacotes` (gestão) e
`/educamanto/historico` no app React.

## Verificação funcional (obrigatória antes do merge)

Script com test client Flask contra `manto_local`, requests fora de `app.app_context()`,
cobrindo por papel (SUPERADMIN, COMERCIAL, ENSAIO, REVENDEDOR_EDUCAMANTO, e um papel sem
acesso):

1. `GET /api/educamanto/packages` — 200 para todos os papéis com acesso, dados batendo com o
   Jinja legado (`/educamanto/`).
2. `POST /api/educamanto/packages` — 201 para SUPERADMIN, 403 para COMERCIAL/ENSAIO.
3. `PATCH /api/educamanto/packages/<id>` — 200, itens substituídos corretamente.
4. `POST /api/educamanto/packages/<id>/duplicate` — 201, cópia com itens idênticos.
5. `DELETE /api/educamanto/packages/<id>` — 204, pacote e itens removidos (cascade).
6. `POST /api/educamanto/orcamento/gerar` — 200 com PDF válido + registro criado em
   `EducaMantoQuote`; 400 sem pacote/dias.
7. `GET /api/educamanto/orcamento/<id>/pdf` — 200, valores batem com o snapshot congelado mesmo
   após editar/excluir o pacote original.
8. `GET /api/educamanto/historico` — filtros de texto/período funcionando; `users`/`user_name`
   presentes só para SUPERADMIN.
9. Paridade: as mesmas ações via rota Jinja legada (`/educamanto/packages/create` etc.)
   continuam funcionando sem regressão.

## Frontend

```powershell
cd frontend/apps/internal
npx tsc --noEmit
npm run build
```

Conferir manualmente em `npm run dev:internal`: criar/editar/duplicar/excluir pacote, gerar
orçamento (download do PDF), abrir histórico e reabrir um PDF antigo — em viewport desktop e
mobile.
