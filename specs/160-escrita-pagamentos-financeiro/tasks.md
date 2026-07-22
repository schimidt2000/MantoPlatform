# Tasks: Escrita da Planilha de Pagamentos em React (160)

**Input**: Design documents from `specs/160-escrita-pagamentos-financeiro/`
**Prerequisites**: plan.md, spec.md, data-model.md,
contracts/financeiro-pagamentos-escrita-endpoints.md, quickstart.md

**Tests**: verificação é o script de paridade
`scripts/db/verify_160_escrita_pagamentos_financeiro.py` contra `manto_local`, gerado na Phase de
Polish.

**Organização**: 4 user stories (US1 marcar status, US2 ação em massa, US3 adiantamento, US4
export CSV), nessa ordem de prioridade.

## Phase 1: Setup

- [ ] T001 Confirmar `manto_local` (Postgres) atualizado (`python -m flask db heads`) — sem
      migration nova nesta fatia.

## Phase 2: Foundational

- [ ] T002 Criar `app/api/financeiro_write.py` (NOVO): imports/estrutura base (`api_bp`,
      `_has_role`/gate reaproveitado de `app/api/financeiro_read.py`, ou reimplementado igual —
      mesma paridade `_has_role(FINANCEIRO, SUPERADMIN)`), sem rotas ainda — só o esqueleto que as
      próximas tasks preenchem.
- [ ] T003 [P] Adicionar `apiFetchBlob(path, options)` em
      `frontend/packages/api-client/src/client.ts`: mesma assinatura de `apiFetch`, mas devolve
      `Blob` em vez de `.json()`; exportar em `frontend/packages/api-client/src/index.ts`.

## Phase 3: User Story 1 — Marcar status de um item de pagamento (P1)

**Goal**: usuário Financeiro/Superadmin marca o status de qualquer item (cachê, salário, gasto,
BV, comissão) direto na tela React, sem sair dela.

**Independent Test**: na tela de pagamentos, marcar um item de cada tipo como pago/não pago (e
tentar "no banco" num tipo que não aceita) e conferir o resultado na tela e no banco
(`manto_local`).

- [ ] T004 [US1] Implementar `POST /api/financeiro/pagamentos/set-status` em
      `app/api/financeiro_write.py`: body JSON `{item_type, item_id, status}`; reaproveita a mesma
      árvore de decisão de `set_payment_status` (`app/financeiro/routes.py:1177`) — commission
      (parse `"sellerId:YYYY-MM"`, `_bulk_set_commission_period`-like loop já existente inline),
      recurring, salary, expense, bv, cache — com os mesmos modelos e `audit(...)`. 200
      `{"status": effective_status}`; 400 `{"error": {"message": "..."}}` se `item_id`/`status`
      inválido ou item não encontrado.
- [ ] T005 [P] [US1] Criar `useSetPaymentStatus()` em
      `frontend/apps/internal/src/lib/financeiro.ts`: `useMutation` que chama o endpoint T004;
      `onSuccess` invalida `["financeiro-pagamentos", month]`.
- [ ] T006 [US1] Em `frontend/apps/internal/src/pages/PagamentosPage.tsx`, trocar o badge de status
      estático de `PagamentoRow` por um `<select>` (opções conforme `status_labels`, restrito a
      `pago`/`nao_pago` para `recurring`/`commission`) chamando `useSetPaymentStatus`; loading
      local (disabled) durante o envio; erro em toast/inline amigável (Princípio V).

**Checkpoint**: US1 completa e testável isoladamente — marcar status individual funciona ponta a
ponta.

---

## Phase 4: User Story 2 — Ações em massa sobre itens selecionados (P2)

**Goal**: usuário seleciona vários itens (cachê/salário/gasto/comissão) de uma vez e aplica uma
ação (status ou excluir) em lote.

**Independent Test**: selecionar itens de tipos diferentes, aplicar "marcar como pago" e depois
"excluir" (numa seleção sem gasto/comissão) e conferir os resultados e as mensagens de itens
ignorados.

- [ ] T007 [US2] Implementar `POST /api/financeiro/pagamentos/bulk-action` em
      `app/api/financeiro_write.py`: body JSON `{action, role_ids[], salary_ids[], expense_ids[],
      commission_ids[], month}`; reaproveita `_bulk_set_commission_period` (já existe em
      `app/financeiro/routes.py:1380`) e a mesma lógica de `bulk_payment_action`
      (`app/financeiro/routes.py:1412`) — delete só cachê/salário (gastos/comissões viram
      `skipped`), status ignora `no_banco` em comissão. 200 `{"changed": N, "skipped": [string,
      ...]}`.
- [ ] T008 [P] [US2] Criar `useBulkPaymentAction()` em
      `frontend/apps/internal/src/lib/financeiro.ts`: `useMutation` para o endpoint T007;
      `onSuccess` invalida `["financeiro-pagamentos", month]` e limpa a seleção.
- [ ] T009 [US2] Em `PagamentosPage.tsx`: checkbox por linha + estado de seleção (por
      `type`+`id`); barra de ação em massa fixa quando há ≥1 selecionado (contagem, botões "marcar
      como pago"/"não pago"/"excluir"); exibir `skipped` retornado como aviso; desabilitar a barra
      quando a seleção está vazia.

**Checkpoint**: US2 completa e testável isoladamente (não depende de US3/US4; pode reaproveitar o
`<select>` de status da US1 para os itens individuais).

---

## Phase 5: User Story 3 — Registrar e excluir adiantamento de salário (P3)

**Goal**: usuário registra um adiantamento (valor + comprovante) para um lançamento de salário, e
remove um adiantamento existente.

**Independent Test**: registrar um adiantamento válido (conferir valor líquido atualizado),
tentar um inválido em cada uma das 3 formas de rejeição, e excluir um adiantamento registrado.

- [ ] T010 [US3] Implementar `POST /api/financeiro/pagamentos/salary/<int:sp_id>/advance` em
      `app/api/financeiro_write.py`: recebe multipart (`amount`, `advance_date` opcional,
      `advance_proof`); reaproveita exatamente a validação/gravação de `salary_advance`
      (`app/financeiro/routes.py:1288`) — `parse_brl`, soma ≤ salário, comprovante obrigatório
      ≤10MB, mesmo caminho `UPLOAD_PAYMENTS`. 200 `{"id", "amount", "date", "proof"}`; 400
      `{"error": {"message": "..."}}` traduzindo cada mensagem de `flash` de hoje; 404 se
      `sp_id` não existe.
- [ ] T011 [US3] Implementar `POST /api/financeiro/pagamentos/salary/advance/<int:adv_id>/delete`
      em `app/api/financeiro_write.py`: reaproveita `salary_advance_delete`
      (`app/financeiro/routes.py:1351`, remove arquivo + registro). 204; 404 se não existe.
- [ ] T012 [P] [US3] Criar `useAddSalaryAdvance()`/`useDeleteSalaryAdvance()` em
      `frontend/apps/internal/src/lib/financeiro.ts`: primeira usa `FormData` (multipart) contra
      T010; segunda contra T011. Ambas invalidam `["financeiro-pagamentos", month]` no sucesso.
- [ ] T013 [US3] Em `PagamentosPage.tsx`, dentro do `<details>` de adiantamentos de um item
      `salary` (já existe da 159): formulário (valor com `Input` monetário `@manto/money`, data
      opcional, arquivo) chamando `useAddSalaryAdvance`; botão de excluir por adiantamento listado
      chamando `useDeleteSalaryAdvance`; mensagens de erro do backend exibidas inline; loading
      desabilita o formulário durante o envio.

**Checkpoint**: US3 completa e testável isoladamente.

---

## Phase 6: User Story 4 — Exportar CSV dos pagamentos do mês (P4)

**Goal**: usuário baixa um CSV dos cachês do mês selecionado.

**Independent Test**: exportar um mês com cachês (conferir colunas/linhas) e um mês vazio
(conferir só cabeçalho, sem erro).

- [ ] T014 [US4] Implementar `GET /api/financeiro/pagamentos/export` em
      `app/api/financeiro_write.py`: reaproveita `_pagamentos_query(month)` e monta o mesmo CSV de
      `export_pagamentos` (`app/financeiro/routes.py:1501`, mesmas 7 colunas); resposta
      `text/csv; charset=utf-8` + `Content-Disposition: attachment; filename=pagamentos_{month}.csv`
      — única rota desta fatia fora do envelope JSON padrão (documentado no contrato).
- [ ] T015 [US4] Em `PagamentosPage.tsx`, botão "Exportar CSV" no cabeçalho (ao lado do seletor de
      mês): usa `apiFetchBlob` (T003) contra o endpoint T014, monta `URL.createObjectURL` + `<a
      download="pagamentos_{month}.csv">` sintético, revoga a URL depois; loading no botão durante
      o download (Princípio V).

**Checkpoint**: US4 completa — com ela, todas as 4 ações de escrita da 159 estão migradas.

---

## Phase 7: Polish & Verificação

- [ ] T016 Criar `scripts/db/verify_160_escrita_pagamentos_financeiro.py` (gitignored): test
      client Flask contra `manto_local`, requests fora de `app_context` — cobre: set-status para
      cada `item_type` (inclusive rejeição de status inválido por tipo e item inexistente);
      bulk-action (status + delete, inclusive itens ignorados de gasto/comissão e `no_banco` em
      comissão); salary advance (criação válida, as 4 rejeições, exclusão com remoção do arquivo);
      export CSV (cabeçalhos de resposta e conteúdo, mês vazio); gate 403 em todas as rotas para
      papel fora de Financeiro/Superadmin. Compara efeito no banco com o resultado das rotas Jinja
      equivalentes para a mesma entrada (paridade).
- [ ] T017 Rodar `ruff check app/` nos arquivos tocados.
- [ ] T018 Rodar `npx tsc --noEmit` e `npm run build` em `frontend/apps/internal`.
- [ ] T019 Conferência mobile (320–430px) das novas ações (checkbox + barra de ação em massa,
      formulário de adiantamento, botão de exportar) — Princípio VIII.
- [ ] T020 Atualizar `docs/changelog.html` com entrada em linguagem simples (entrada 160) e
      republicar no artifact já existente (mesmo link).

## Dependencies

Setup (Phase 1) → Foundational (Phase 2) → US1 (Phase 3) → US2 (Phase 4) → US3 (Phase 5) → US4
(Phase 6) → Polish (Phase 7).

US2 reaproveita visualmente o `<select>` de status da US1 (mesma linha), por isso vem depois; US3 e
US4 são independentes entre si e de US1/US2 — poderiam ser implementadas em paralelo se necessário,
mas seguem em ordem de prioridade da spec. Dentro de cada story: endpoint API → hook de mutação
(`[P]` quando não depende de outro arquivo tocado na mesma story) → UI.

## Implementation Strategy

MVP = US1 (marcar status individual — a ação mais usada). US2→US4 incrementam sobre a mesma tela,
cada uma independentemente testável e "shippable". Com esta fatia completa, a US4
(Financeiro/Vendas) fica com leitura e escrita 100% em React nas 4 telas migradas (pipeline, DRE,
comissões, pagamentos).
