# Quickstart: Migração das últimas ferramentas Jinja para React

## Rodar localmente

```powershell
# Backend, apontando para manto_local (Postgres) — nunca o SQLite vazio
.\scripts\db\run-local.ps1

# Frontend (staff)
cd frontend; npm run dev:internal
```

Acessar as 7 telas novas no app React: Gastos Extras, Calculadora de Orçamento, Gastos
Recorrentes, Orçamentos (histórico), Configuração de Preços, Avaliação de Casting e Formulários
(Comercial) — todas agora com rota interna real (`navigation.tsx` não abre mais nenhuma em outra
aba).

## Verificação funcional (obrigatória antes do merge)

Um script por domínio, test client Flask contra `manto_local`, requests fora de
`app.app_context()`, cobrindo sucesso/erro/RBAC:

1. **Gastos** (`gastos_read.py`/`gastos_write.py`): criar gasto como usuário comum (201);
   aprovar/rejeitar como SUPERADMIN (200) e como não-SUPERADMIN (403); dupla
   aprovação/rejeição (409); vincular a evento; CRUD completo de recorrente + parcelas
   (preencher/pagar/pular/reabrir/excluir) como FINANCEIRO (200) e como COMERCIAL (403).
2. **Orçamento — calculadora** (`orcamento_read.py`/`orcamento_write.py`): `POST /calcular` com
   os mesmos parâmetros de um caso conhecido da tela clássica, conferindo que o resultado bate
   valor a valor; `POST /salvar` gera registro em `OrcamentoHistory`.
3. **Orçamento — config de preços**: `GET`/`POST /settings` como SUPERADMIN (200) e como
   COMERCIAL (403); alterar um valor e confirmar que o próximo `POST /calcular` reflete a mudança
   (FR-011); adicionar/remover item especial.
4. **Orçamento — histórico/PDF**: listar, ver detalhe de um registro atual e de um registro
   legado (pré-snapshot) — ambos exibindo os mesmos campos que a tela clássica; baixar PDF e
   conferir que o conteúdo bate com `gerar_orcamento_pdf` chamado direto; enviar e-mail (mock do
   serviço de e-mail); excluir.
5. **Avaliação de Casting** (`ratings_read.py`/`ratings_write.py`): filtros por evento/categoria/
   período batendo com a tela clássica; distribuição de notas por categoria; modo anônimo ligado
   omite autor para não-SUPERADMIN e mantém visível para SUPERADMIN; toggle do modo anônimo
   restrito a SUPERADMIN (403 para os demais).
6. **Formulários — staff** (`formularios_admin_read.py`/`formularios_admin_write.py`): busca,
   associar/desassociar cliente, vincular/desvincular evento (conferir `event_link_locked=true`
   após a ação manual); excluir resposta restrito a SUPERADMIN; editor de campos — criar/editar/
   mover/excluir campo comum (200) e tentativa de excluir/renomear campo `is_system` (400/403).
7. **Paridade**: as 7 rotas Jinja legadas (`/gastos/`, `/gastos/recorrentes`, `/orcamento/`,
   `/orcamento/settings`, `/orcamento/historico`, `/talents/avaliacoes`, `/formularios/`)
   continuam respondendo sem regressão (agora delegando aos `*_ops.py` novos).

## Frontend

```powershell
cd frontend/apps/internal
npx tsc --noEmit
npm run build
```

Conferir manualmente em `npm run dev:internal`, por tela: fluxo completo (criar/aprovar/calcular/
filtrar conforme o caso), loading/erro/sucesso em toda ação, confirmação antes de ação destrutiva,
e que **nenhum item de menu das 7 áreas abre mais fora da SPA** (checar `navigation.tsx`
renderizado, não só o código-fonte). Viewport desktop (painel interno) e mobile por consistência.
