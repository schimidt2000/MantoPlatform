# Feature Specification: Planilha de Pagamentos em React (Leitura)

**Feature Branch**: `159-financeiro-pagamentos-leitura`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Migrar a Planilha de Pagamentos (/financeiro/pagamentos) do Jinja para React, somente LEITURA — quarta e última fatia de leitura da US4 (Financeiro/Vendas), depois do Pipeline de Vendas (156), Dashboard Financeiro DRE (157) e Comissões (158). Escopo: tela lista os itens de pagamento do mês selecionado — cachês de talento (roles), salários (SalaryPayment, incluindo adiantamentos), comissões do período, gastos recorrentes — com status (pendente/pago/atrasado), valor, favorecido e tipo, e o total do mês. Reaproveitar 100% da lógica já existente em app/financeiro/routes.py (_pagamentos_query, _ensure_salary_payments, _build_payment_items, _build_bv_items, _build_commission_items, _build_recurring_items) sem duplicar regra de negócio — endpoint novo só monta os mesmos itens e serializa. Gate: require_financeiro (FINANCEIRO/SUPERADMIN), igual à view Jinja (pagamentos não tem recorte por vendedor como comissões). Ficam explicitamente fora desta fatia (fatias futuras da US4): marcar status de pagamento (set_payment_status), ações em massa (bulk_payment_action), adiantamento/exclusão de adiantamento de salário (salary_advance, salary_advance_delete) e exportação CSV (export_pagamentos) — toda escrita e a exportação ficam para uma fatia de escrita futura, seguindo o mesmo padrão de leitura-primeiro já usado em 145 (agenda) e 154 (talentos/figurino)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver a planilha de pagamentos do mês em React (Priority: P1)

Como usuário Financeiro/Superadmin, preciso ver, na tela React, todos os itens de pagamento de um
mês — cachês de talento, salários (com adiantamentos já descontados), repasses de BV, comissões
do ciclo e contas recorrentes — com favorecido, valor, status e totais, exatamente como vejo hoje
na planilha antiga.

**Why this priority**: é a tela que Financeiro usa para conferir tudo que precisa ser pago no mês
e organizar o fluxo de caixa; é 100% leitura (sem marcar status, sem ações em massa, sem
exportação), tornando-a a última fatia de leitura que resta na US4 depois do pipeline (156), do
dashboard (157) e de comissões (158).

**Independent Test**: abrir a tela de pagamentos em React para um mês qualquer, com um usuário
Financeiro, e conferir que a lista de itens (por tipo), os favorecidos, valores, status e os 5
totais (geral, pago, no banco, pendente, futuro) batem exatamente com os da tela antiga
(`/financeiro/pagamentos`) para o mesmo mês.

**Acceptance Scenarios**:

1. **Given** um usuário Financeiro ou Superadmin autenticado, **When** ele abre a tela de
   pagamentos em React sem escolher mês, **Then** vê todos os itens do mês corrente — cachês de
   talento dos eventos do mês, salários (semanal/quinzenal) já gerados para o mês, repasses de BV
   dos eventos do mês, comissões do ciclo do mês anterior (a pagar no dia 5) e contas recorrentes
   preenchidas do mês — ordenados por data.
2. **Given** o mesmo usuário, **When** ele troca o mês (seletor `YYYY-MM`), **Then** a lista e os
   totais são recalculados para o novo mês, com os mesmos valores da tela antiga para o mesmo mês
   (inclusive gerando os lançamentos de salário do mês se ainda não existirem, mesmo comportamento
   de `_ensure_salary_payments` hoje).
3. **Given** a tela carrega, **When** existem itens com status diferentes (`nao_pago`, `pago`,
   `no_banco`) e datas passadas/futuras, **Then** a resposta inclui os 5 totais do mês (valor
   total, total pago, total no banco, total pendente — não pago e não futuro —, total futuro — não
   pago e com data futura), calculados com a mesma regra de hoje.
4. **Given** um salário do mês tem um ou mais adiantamentos lançados, **When** o item aparece na
   lista, **Then** o valor mostrado é o líquido (bruto menos adiantamentos), com o valor bruto e a
   lista de adiantamentos (valor, data, comprovante) disponíveis para conferência — mesmos campos
   de hoje.
5. **Given** um repasse de BV não tem chave PIX cadastrada, **When** o item aparece na lista,
   **Then** ele é sinalizado como pendente de dados (`missing_data`), mesmo comportamento de hoje.
6. **Given** existem comissões pendentes de sincronização (eventos realizados que ainda não
   geraram a linha de comissão), **When** a tela carrega, **Then** a sincronização acontece antes
   da consulta (mesmo comportamento de `_resync_pending_commissions` hoje), sem exigir ação manual
   do usuário.
7. **Given** um usuário sem papel Financeiro/Superadmin, **When** ele tenta abrir a tela ou chamar
   a API diretamente, **Then** o acesso é recusado (403).

---

### Edge Cases

- Mês sem nenhum item de pagamento → lista vazia com todos os totais em R$ 0,00, estado amigável,
  não erro.
- Mês em formato inválido no seletor (`month` fora de `YYYY-MM`) → mesmo fallback de hoje: usa o
  mês corrente.
- Item futuro (evento/vencimento ainda não ocorreu) com status `nao_pago` → entra no total futuro,
  não no total pendente, mesma regra de hoje.
- Gasto aprovado marcado como já pago na criação (`paid_at_creation=True`) → não aparece como item
  de pagamento, mesma regra de hoje.
- Conta recorrente com lançamento "registrado" (débito automático/assinatura, sem valor
  preenchido) → não aparece como item de pagamento, só as com status `a_pagar`/`pago`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE expor a lista combinada de itens de pagamento do mês selecionado —
  cachês de talento, salários, repasses de BV, comissões do ciclo e contas recorrentes — como
  endpoint JSON, reaproveitando exatamente a lógica já existente (`_pagamentos_query`,
  `_ensure_salary_payments`, `_build_payment_items`, `_build_bv_items`, `_build_commission_items`,
  `_build_recurring_items`, `_resync_pending_commissions`) sem duplicar nenhuma regra de negócio.
- **FR-002**: O sistema DEVE restringir o acesso a esse endpoint a usuários com papel Financeiro
  ou Superadmin — mesma regra de hoje (`require_financeiro`), sem recorte por vendedor (diferente
  de comissões).
- **FR-003**: O sistema DEVE aceitar o mesmo filtro de mês que a tela antiga aceita hoje via
  querystring (`month`, formato `YYYY-MM`), com o mesmo padrão (mês corrente) quando nenhum filtro
  é informado ou o valor é inválido.
- **FR-004**: A resposta DEVE incluir, para cada item: tipo (cachê/salário/BV/comissão/recorrente),
  data, favorecido, valor, chave PIX (quando houver) e status — mesmos campos exibidos hoje.
- **FR-005**: A resposta DEVE incluir, para itens de salário, o valor líquido (já descontados os
  adiantamentos), o valor bruto e a lista de adiantamentos (valor, data, comprovante) — mesmos
  campos de hoje.
- **FR-006**: A resposta DEVE sinalizar itens de BV sem chave PIX cadastrada como pendentes de
  dados (`missing_data`) — mesma regra de hoje.
- **FR-007**: A resposta DEVE incluir os 5 totais do mês (valor total, pago, no banco, pendente e
  futuro), calculados com a mesma regra de hoje.
- **FR-008**: O comportamento da tela antiga (Jinja, `/financeiro/pagamentos`) DEVE permanecer
  idêntico ao de antes desta fatia — sem regressão.

### Key Entities

- **Item de pagamento**: estrutura já existente (dicionário serializado por `_build_*_items`),
  não uma entidade de banco própria — representa um cachê (`EventRole`), salário
  (`SalaryPayment` + `SalaryAdvance`), repasse de BV (`EventAcrescimo`), comissão
  (`CommissionPayment`, agregada por vendedor/ciclo) ou conta recorrente
  (`RecurringExpenseEntry`); esta fatia só lê e serializa, nenhum campo novo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário Financeiro/Superadmin consegue conferir todos os itens de pagamento do
  mês (cachês, salários, BV, comissões, recorrentes) e os 5 totais inteiramente pela tela React,
  sem abrir a tela antiga.
- **SC-002**: Os valores mostrados em React são idênticos aos da tela antiga para o mesmo mês e
  mesmos dados — verificado por paridade automatizada.
- **SC-003**: Um usuário sem papel Financeiro/Superadmin não consegue ver a planilha de pagamentos
  nem pela tela nem pela API (403 nos dois casos).

## Assumptions

- Esta fatia é só leitura — marcar status de pagamento (`set_payment_status`), ações em massa
  (`bulk_payment_action`), lançar/excluir adiantamento de salário (`salary_advance`,
  `salary_advance_delete`) e exportação CSV (`export_pagamentos`) não fazem parte dela; essas
  ações continuam só na tela antiga até uma fatia de escrita futura.
- Com esta fatia, a US4 fica completa em leitura (pipeline, dashboard, comissões, pagamentos);
  toda escrita do módulo Financeiro/Vendas segue pendente para fatias futuras, mesmo padrão já
  usado no restante da migração (leitura primeiro, escrita depois).
- Valores monetários exibidos em React usam `@manto/money` (formatBRL) como fonte única — nunca
  reimplementados no frontend.
