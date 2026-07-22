# Implementation Plan: Escrita da Planilha de Pagamentos em React (160)

**Branch**: `160-escrita-pagamentos-financeiro` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/160-escrita-pagamentos-financeiro/spec.md`

## Summary

Quinta fatia da US4 (Financeiro/Vendas) e primeira de ESCRITA do módulo — fecha a paridade da
Planilha de Pagamentos (159, só leitura). Migra as quatro ações de escrita que ficaram
explicitamente fora da 159: marcar status de um item (`set_payment_status`), ação em massa
(`bulk_payment_action`), adiantamento de salário — registrar e excluir (`salary_advance`/
`salary_advance_delete`) — e exportação CSV (`export_pagamentos`). Endpoints novos em
`app/api/financeiro_write.py` (arquivo novo, mesma convenção `_read.py`/`_write.py` já usada em
agenda/talentos/figurino) chamam exatamente as mesmas funções e regras já existentes em
`app/financeiro/routes.py` — sem duplicar lógica de negócio, só adaptar entrada (JSON/multipart em
vez de form/redirect) e saída (JSON em vez de redirect/flash). `PagamentosPage.tsx` (159) ganha as
ações; nenhuma tela nova.

## Technical Context

Igual à 144-159: Python/Flask + React (Vite/TS/TanStack Query `useMutation`). Sem dependência nova.
Primeiro caso de download binário (CSV) na migração — define o padrão `apiFetchBlob` em
`@manto/api-client`, reaproveitável pelas fatias futuras de PDF (orçamento, EducaManto).
Verificação com test client Flask contra `manto_local`, requests fora de `app_context`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I (reutilizar)**: zero regra de negócio nova. `set_payment_status`/`bulk_payment_action`/
  `salary_advance`/`salary_advance_delete`/a query de `export_pagamentos` são chamadas/replicadas
  campo a campo dos helpers hoje em `app/financeiro/routes.py` — os endpoints novos só trocam a
  camada de entrada/saída (form+redirect → JSON/multipart+resposta), mesma exceção "core-in-routes"
  já usada em 156-159 (sem extrair `_ops` novo só para esta fatia, os helpers já são multi-uso
  dentro do blueprint).
- **II (padrões de código)**: endpoints novos em `app/api/financeiro_write.py` (arquivo NOVO — só
  hoje o financeiro tinha `_read.py`), type hints/docstring; erros amplos sempre logados.
- **III (API first)**: 5 endpoints novos, 100% JSON (exceto o corpo de `advance` que é multipart na
  requisição, resposta ainda JSON) e 1 endpoint de export que devolve CSV puro (`text/csv`) — as
  rotas Jinja antigas (`/financeiro/pagamentos/set-status`, `/bulk-action`, `/salary/<id>/advance`,
  `/salary/advance/<id>/delete`, `/export`) continuam existindo em paralelo, sem mudança de
  comportamento (FR não regressivo, mesmo padrão strangler-fig de toda a migração).
- **IV (não quebrar)**: paridade verificada contra `manto_local` — mesmo efeito no banco (status,
  adiantamento criado/removido, itens excluídos) entre a rota Jinja e a rota API, para a mesma
  entrada.
- **V (feedback)**: todo botão de ação usa `useMutation` do TanStack Query — estado de
  loading/disabled durante o envio, mensagem de erro amigável em falha, e a lista/])totais
  recarregam (via `invalidateQueries`) após sucesso, sem reload de página inteira (FR-010/FR-011).
- **VII (monetário)**: valor do adiantamento entra como string BRL (`Input` com `@manto/money`,
  igual a todo formulário monetário já migrado) e é convertido no backend com `parse_brl`, mesma
  função que a rota Jinja já usa — nenhum cálculo novo no frontend.
- **VIII (mobile-first)**: seleção múltipla (checkbox por linha) e barra de ação em massa cabem em
  largura de coluna única <768px; formulário de adiantamento é modal/collapse, não precisa de
  espaço lateral.
- **IX (movimento)**: sem transição nova além do padrão de loading do TanStack Query já usado nas
  fatias anteriores.

Sem violação nova.

## Project Structure

### Documentation (this feature)

```text
specs/160-escrita-pagamentos-financeiro/
├── plan.md
├── data-model.md
├── quickstart.md
├── contracts/financeiro-pagamentos-escrita-endpoints.md
└── tasks.md
```

### Source Code (repository root)

```text
app/api/financeiro_write.py          # NOVO — 5 endpoints de escrita/export de pagamentos
frontend/apps/internal/src/
├── lib/financeiro.ts                # + useMutation hooks (setPaymentStatus, bulkAction,
│                                     #   addSalaryAdvance, deleteSalaryAdvance) + useExportCsv
├── pages/PagamentosPage.tsx          # + checkboxes/seleção, seletor de status por item, barra
│                                     #   de ação em massa, formulário de adiantamento, botão CSV
frontend/packages/api-client/src/client.ts  # + apiFetchBlob (download binário, 1ª vez na migração)
scripts/db/verify_160_escrita_pagamentos_financeiro.py  # NOVO: paridade Jinja×API + RBAC 403
```

**Structure Decision**: núcleo permanece 100% em `app/financeiro/routes.py` (mesma exceção
"core-in-routes" de 156-159); `app/api/financeiro_write.py` é o único arquivo novo no backend,
agrupando as 5 rotas desta fatia (paralelo a `agenda_write.py`/`talents_write.py`/
`figurino_write.py`, já existentes para outras US). `apiFetchBlob` fica no `api-client`
compartilhado (não só neste app) porque será reaproveitado pelas fatias futuras de PDF.

## Design Decisions

1. **`POST /api/financeiro/pagamentos/set-status`** (gate `_has_role(FINANCEIRO, SUPERADMIN)`,
   igual à 159): body JSON `{item_type, item_id, status}` — chama a mesma árvore de decisão de
   `set_payment_status` (commission/recurring/salary/expense/bv/cache), reaproveitando os mesmos
   modelos e `audit(...)`. Sucesso: `{"status": effective_status}` (200). Item/status inválido:
   `{"error": {"message": "..."}}` (400) — nenhuma alteração no banco.
2. **`POST /api/financeiro/pagamentos/bulk-action`**: body JSON `{action, role_ids[], salary_ids[],
   expense_ids[], commission_ids[], month}` — reaproveita `_bulk_set_commission_period` e a mesma
   lógica de `bulk_payment_action` (delete só cachê/salário; gastos/comissões ignorados com aviso
   quando a ação é delete; comissões ignoradas quando a ação é `no_banco`). Resposta:
   `{"changed": N, "skipped": ["<mensagem>", ...]}` (200) — sem `flash`, o frontend renderiza
   `skipped` como toast/aviso.
3. **`POST /api/financeiro/pagamentos/salary/<id>/advance`** (multipart, convenção da 153/155):
   campos de formulário `amount` (string BRL), `advance_date` (opcional, `YYYY-MM-DD`), arquivo
   `advance_proof` — mesma validação de `salary_advance` (soma não pode passar do salário,
   comprovante obrigatório, limite 10 MB), mesmo caminho de armazenamento
   (`UPLOAD_PAYMENTS`/`/uploads/payments/`). Sucesso: `{"id", "amount", "date", "proof"}` do
   adiantamento criado (200). Erro de validação: 400 com `message` explicando o motivo (mesmo texto
   das mensagens `flash` de hoje, sem duplicar a regra — só traduz `flash`→corpo JSON).
4. **`POST /api/financeiro/pagamentos/salary/advance/<id>/delete`**: JSON vazio — reaproveita
   `salary_advance_delete` (remove arquivo do comprovante do disco + registro). Sucesso: `204`.
5. **`GET /api/financeiro/pagamentos/export`**: reaproveita `_pagamentos_query(month)` e o mesmo
   loop de `export_pagamentos` (mesmas 7 colunas, mesmo `Content-Disposition`) — é a única rota
   desta fatia que não devolve o envelope JSON padrão (retorna `text/csv` puro), documentado como
   exceção explícita no contrato, igual à rota Jinja hoje.
6. **`apiFetchBlob` (novo, `@manto/api-client`)**: variante de `apiFetch` que devolve `Blob` em vez
   de fazer `.json()` — usada só pelo botão de exportar CSV desta fatia; o componente monta
   `URL.createObjectURL(blob)` + `<a download>` sintético e revoga a URL depois do clique (padrão
   descrito na spec/US4, Princípio V — feedback do clique via estado de loading do `useMutation`
   que envolve o fetch do blob).
7. **Frontend — sem tela nova**: `PagamentosPage.tsx` ganha: (a) checkbox por linha + barra de ação
   em massa fixa quando há seleção; (b) `<select>` de status por item (chama `setPaymentStatus`,
   com loading local no item durante o envio); (c) formulário de adiantamento embutido na linha
   expandida de salário (reaproveita o `<details>` de adiantamentos já existente da 159); (d) botão
   "Exportar CSV" no cabeçalho, ao lado do seletor de mês. Toda mutação usa `invalidateQueries(["
   financeiro-pagamentos", month])` no `onSuccess` — sem patch manual de estado local.

## Complexity Tracking

Nenhuma violação nova.
