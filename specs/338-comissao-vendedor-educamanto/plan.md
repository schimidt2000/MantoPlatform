<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: Comissão do vendedor e lucro real no EducaManto

**Branch**: `338-comissao-vendedor-educamanto` | **Data**: 2026-11-06 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/338-comissao-vendedor-educamanto/spec.md`

## Resumo

A comissão do responsável EducaManto passa a sair do lucro real (venda − BV − cachês − gastos extras
aprovados − imposto da nota − comissão do vendedor), e a comissão do vendedor posta no preço pela
calculadora vira uma linha de comissão própria do vendedor do evento, a pagar no mês do evento,
proporcional ao retido no cancelado. Abordagem (`research.md`): uma coluna no evento guarda o valor; uma
coluna `source` separa duas trilhas em `commission_payments`, e a reconciliação da 306 trabalha numa trilha
por vez — nenhum chamador de hoje muda de comportamento fora do EducaManto.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite)
no frontend

**Dependências principais**: as de sempre; nenhuma nova.

**Armazenamento**: PostgreSQL. Verificação contra `manto_338` (cópia da produção de 06/11, `research.md`
R9), porque o `manto_local` está numa migration de outra branch.

**Verificação**: `specs/338-comissao-vendedor-educamanto/verify_338.py`; `npm run typecheck`; tela aberta.

**Plataforma-alvo**: web — app interno (desktop).

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**: o custo da base ganha uma consulta de gastos por evento EducaManto (poucos por mês);
`_resync_pending_commissions` continua um evento por vez.

**Restrições**: comissão paga nunca reescrita; nenhuma comissão comum muda de número (SC-003); campo novo
opcional no React; chave ausente no PATCH não mexe no valor.

**Escala/escopo**: 4 colunas (1 migration), 0 endpoint novo, 1 endpoint alterado, 3 serializações
alteradas, 3 telas tocadas (card Comercial, Comissões, Planilha).

## Constitution Check

| Princípio / seção | Como o plano cumpre |
|---|---|
| I. Reutilizar antes de criar | Reusa `_base_da_comissao`, `comissao_do_retido`, `reconciliar_comissao_do_cancelado` (parâmetro `fonte`), `filtro_devolucao`, `dias_vivos`, `_get_tax_rate`, `MoneyInput`/`formatBRL`. |
| II. Padrões de código | type hints, docstrings Google, constante em `app/constants.py`; `ruff check` nos tocados. |
| III. Camadas / API First | regra em `comissoes_ops.py`/`cancel_ops.py`/`event_ops.py` (puros); a view do `/comercial` só converte o corpo. |
| IV. Não quebrar o que funciona | migration aditiva; trilha principal = todas as linhas de hoje; o verify confere que uma comissão comum não muda (cenário 6 extra) e roda a reconciliação da 306 nos dois sentidos. |
| V. UI/UX com feedback | o campo entra no `VendaForm` (mesmo `useUpdateEventComercial`, erro no campo por `fields`). |
| VI. Esteira (Nível 1) | esteira completa; artefatos em `specs/338-…/`. |
| VII. Living Spec | spec escrita e esclarecida antes do código. |
| VIII. Verify antes do núcleo | `verify_338.py` na Fase 2 (Foundational), antes de `comissoes_ops`. |
| IX. Dinheiro BRL | `NUMERIC(12,2)`/`Decimal`; `MoneyInput` e `formatBRL` no React. |
| X. Mobile-first público | não toca superfície pública. |
| XI. Framer Motion | sem animação nova. |
| XII. Combobox / Maps | não se aplica. |
| XIII. RBAC declarado | `PATCH /comercial` mantém `_can_create_event`; o campo novo herda o gate; linha do `docs/01` §4.3 atualizada. |
| XIV. Config / efeito externo | sem env nova; alíquota é a de Configurações (`SiteSetting.tax_rate`). |
| XV. Texto por superfície | interno: rótulo "Comissão do vendedor", ajuda e erros no padrão (constituição XV); "Comissão" e "Gasto extra" do glossário. |
| Stack | migration à mão, `down_revision = d323b5a1c0e7`; sem Jinja novo. |
| Operação e Deploy | não toca `startCommand`; migration aditiva (sem ensaio destrutivo). Colide no merge com as migrations do CRM (325→335, sem push): quem mergear depois religa o `down_revision`. |

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/338-comissao-vendedor-educamanto/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/api.md
├── checklists/
├── tasks.md
└── verify_338.py
```

### Código

```text
migrations/versions/d338c5a9e2b1_comissao_vendedor_educamanto.py   # 4 colunas
app/models.py                     # CalendarEvent, CommissionPayment, EventCancellation
app/constants.py                  # ORIGEM_VENDEDOR_EDUCAMANTO
app/financeiro/comissoes_ops.py   # base nova, trilhas, sync do vendedor, alíquota, CommissionEntry.origem
app/financeiro/routes.py          # DRE (comissões), commission_lines.origem, reexporta a alíquota
app/financeiro/vendas_ops.py      # comissao_prevista
app/calendar/cancel_ops.py        # congelado do vendedor, alvos, prévia, reaplicar, recongelar, resumo, estorno
app/calendar/group_ops.py         # SATELLITE_FIELDS_CLEARED
app/calendar/event_ops.py         # validação e gravação do campo; 409 no cancelado
app/api/agenda_write.py           # corpo do /comercial
app/api/agenda_read.py            # venda.* e kpi.* novos
frontend/apps/internal/src/lib/{agenda,eventInline,financeiro}.ts
frontend/apps/internal/src/components/EventDetail/ComercialSection.tsx
frontend/apps/internal/src/pages/ComissoesPage.tsx
frontend/apps/internal/src/components/Pagamentos/PagamentoItemViews.tsx
```

**Decisão de estrutura**: a regra fica em `comissoes_ops.py` (núcleo da comissão) e o cancelado em
`cancel_ops.py`, onde já moram as duas metades; `routes.py` só ganha a soma da DRE e a reexportação.

## Rastreamento de complexidade

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| Duas linhas de comissão no mesmo evento | o dono pediu a comissão do vendedor como fonte própria, paga à pessoa | somar no responsável ou virar BV contraria o pedido e a Planilha (R1/R2) |
| Verify contra `manto_338`, não `manto_local` (Princípio VIII) | o `manto_local` está em `d334b2c4e6f8` (CRM, sem push) e parado em 20/10; refazê-lo apagaria o esquema das sessões do CRM | refazer o `manto_local` quebraria os verifies das worktrees 325–335; o `manto_338` é o mesmo espelho (dump de produção de 06/11, Postgres) |
