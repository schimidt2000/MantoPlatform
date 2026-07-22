# Feature Specification: Dashboard Financeiro (DRE) em React (Leitura)

**Feature Branch**: `157-financeiro-dashboard-dre-leitura`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Migrar o Dashboard DRE (`/financeiro/`) do módulo Financeiro para React — leitura. Equivalente ao que a 156 foi para o pipeline de vendas: a view Jinja em app/financeiro/routes.py:387 (dashboard()) é 100% leitura (GET only), consolida DRE gerencial (realizado/projetado/total), KPIs (ticket médio, ratio custo-talento, break-even, Fator R), a receber de clientes, pagamentos pendentes/realizados a talentos, receita por tipo de evento, top vendedores, tendência mensal (6 meses), auditoria de eventos sem receita, tabela de eventos do período com status financeiro, recebimentos previstos, notas fiscais a emitir e custo de nota por mês de emissão. Migrar para um endpoint JSON novo reaproveitando 100% da lógica pura já existente sem duplicar nada — só serialização. Frontend com os mesmos filtros de período (este_mes/30d/mes_anterior/custom). A view Jinja continua existindo em paralelo. Gate: require_financeiro (FINANCEIRO/SUPERADMIN). Fica de fora: qualquer mutação e as fatias futuras (Planilha de Pagamentos, Funcionário/Salário, Comissões)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver o dashboard financeiro (DRE) em React (Priority: P1)

Como usuário Financeiro ou Superadmin, preciso ver o painel gerencial do período (DRE
realizado/projetado/total, KPIs, tabela de eventos, pendências de recebimento e notas fiscais)
na tela React — sem precisar abrir a tela antiga.

**Why this priority**: É o painel que Financeiro consulta todos os dias para acompanhar o
resultado do período; é 100% leitura (nenhuma ação em massa nem edição), tornando-o a próxima
fatia mais estreita e independente da US4 depois do pipeline de vendas (156).

**Independent Test**: abrir o dashboard em React para um período qualquer e conferir que todos
os números (DRE, KPIs, painéis laterais, tabela de eventos) batem com os da tela antiga, para o
mesmo usuário e mesmo período.

**Acceptance Scenarios**:

1. **Given** um usuário Financeiro ou Superadmin autenticado, **When** ele abre o dashboard em
   React sem escolher período, **Then** vê o DRE do mês corrente (realizado, projetado e total),
   com receita bruta/líquida, CPV, lucro bruto e custo fixo (pessoal + comissões).
2. **Given** o mesmo usuário, **When** ele troca o filtro de período entre "Este mês", "Últimos
   30 dias", "Mês anterior" e um intervalo personalizado (datas custom), **Then** o DRE, os KPIs
   e a tabela de eventos são recalculados para o novo período, com os mesmos valores da tela
   antiga para o mesmo intervalo.
3. **Given** o DRE do período, **When** a tela carrega os KPIs, **Then** vê ticket médio, ratio
   custo-talento, termômetro de break-even (com indicador visual de atingido/não atingido) e
   alerta do Fator R (com indicador de "protegido" quando a folha atinge o limiar configurado).
4. **Given** o período selecionado, **When** a tela monta os painéis laterais, **Then** vê receita
   por tipo de evento (ordenada da maior para a menor), os top 5 vendedores por receita (com
   lucro de cada um), e a tendência dos últimos 6 meses (receita, custo, lucro, margem, nº de
   eventos por mês).
5. **Given** eventos com venda registrada mas sem recebimento completo, **When** a tela monta a
   tabela de eventos do período, **Then** cada linha mostra o status financeiro correto
   (permuta, sem_valor, pago_total, parcial, pendente) e o lucro/comissão de cada evento; eventos
   satélites de um grupo comercial não aparecem como linha própria (mesma regra de hoje).
6. **Given** o período, **When** a tela monta os painéis de pendência, **Then** vê a lista de
   recebimentos previstos (parcelas a vencer no período), a lista de notas fiscais a emitir (não
   filtrada por período) e o custo total de notas emitidas no período (pela data de emissão).
7. **Given** eventos com venda zerada e sem flag de cortesia/permuta, **When** a tela monta a
   auditoria, **Then** esses eventos aparecem destacados como pendência de revisão.
8. **Given** um usuário sem papel Financeiro/Superadmin, **When** ele tenta abrir a tela ou
   chamar a API diretamente, **Then** o acesso é recusado (403).

---

### Edge Cases

- Período sem nenhum evento → DRE zerado e painéis com estado vazio amigável, não erro.
- Break-even sem custo fixo no período (custo fixo = 0) → indicador não marca "atingido" por
  divisão por zero; mesma regra de proteção já usada em `_pct`/`breakeven_atingido` hoje.
- Fator R sem receita bruta no período (receita = 0) → não marca "protegido" (mesma proteção de
  hoje).
- Evento em grupo comercial (líder + satélites) → custo consolidado aparece só na linha do líder,
  satélites não geram linha própria (mesma regra de `_group_cost`/`is_satellite`).
- Filtro de período customizado com datas inválidas ou invertidas → mesma validação/fallback já
  aplicado hoje em `_resolve_period`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE expor o dashboard financeiro completo (DRE realizado/projetado/
  total, KPIs, painéis laterais, tendência mensal, auditoria, tabela de eventos do período,
  recebimentos previstos, notas fiscais) como endpoint JSON, reaproveitando exatamente os
  cálculos já existentes (`_resolve_period`, `_compute_drg`, `_salary_cost`, `_group_cost`,
  `_event_cost`, `_event_commission`, `_get_commission_rate`, `_is_permuta`, `_pct`,
  `_get_fator_r_threshold`, `_get_tax_rate`) sem duplicar nenhuma regra de negócio.
- **FR-002**: O sistema DEVE restringir o acesso a esse endpoint a usuários com papel Financeiro
  ou Superadmin — mesma regra de hoje (`require_financeiro`).
- **FR-003**: O sistema DEVE aceitar os mesmos filtros de período que a tela antiga aceita hoje
  via querystring (este mês, últimos 30 dias, mês anterior, e intervalo customizado por datas),
  com o mesmo período padrão (mês corrente) quando nenhum filtro é informado.
- **FR-004**: A resposta DEVE incluir as três visões do DRE gerencial (realizado, projetado,
  total) com os mesmos componentes usados hoje (receita bruta, receita líquida, CPV, lucro
  bruto, pessoal, comissões, gastos extras, gastos recorrentes).
- **FR-005**: A resposta DEVE incluir os KPIs do período: ticket médio, ratio custo-talento,
  termômetro de break-even (percentual e se foi atingido) e alerta do Fator R (percentual,
  limiar configurado e se está protegido).
- **FR-006**: A resposta DEVE incluir os painéis de: valor a receber de clientes, pagamentos
  pendentes e realizados a talentos, receita por tipo de evento, top 5 vendedores por receita (com
  lucro), tendência dos últimos 6 meses, e auditoria de eventos com receita zerada sem cortesia/
  permuta.
- **FR-007**: A resposta DEVE incluir a tabela de eventos do período (excluindo satélites), com
  custo, lucro, comissão, taxa de comissão aplicada, indicador de projetado/realizado, e status
  financeiro (permuta, sem_valor, pago_total, parcial, pendente) por evento — mesma regra de hoje.
- **FR-008**: A resposta DEVE incluir recebimentos previstos (parcelas a vencer no período, ainda
  não recebidas), notas fiscais a emitir (independente do período) e custo de notas emitidas no
  período (por data de emissão) — mesma regra de hoje.
- **FR-009**: O comportamento da tela antiga (Jinja, `/financeiro/`) DEVE permanecer idêntico ao
  de antes desta fatia — sem regressão.

### Key Entities

- **Evento (CalendarEvent)**, **Pagamento de evento (EventPayment)**, **Parcela (EventInstallment)**,
  **Nota fiscal (EventInvoice)**, **Gasto especial (SpecialExpense)**, **Lançamento recorrente
  (RecurringExpenseEntry)**: todos já existentes; esta fatia só lê campos e agregações já
  existentes — nenhuma entidade ou campo novo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário Financeiro/Superadmin consegue acompanhar o resultado do período
  (DRE, KPIs, pendências) inteiramente pela tela React, sem abrir a tela antiga.
- **SC-002**: Os valores mostrados em React são idênticos aos da tela antiga para o mesmo
  usuário, mesmo período e mesmos dados — verificado por paridade automatizada.
- **SC-003**: Usuário sem papel Financeiro/Superadmin não consegue ver o dashboard nem pela tela
  nem pela API (403 nos dois casos).

## Assumptions

- Esta fatia é só leitura — nenhuma ação de escrita (marcar nota como emitida, registrar
  pagamento, ajustar comissão etc.) faz parte dela; essas ações continuam só na tela antiga.
- Ficam explicitamente fora desta fatia (fatias futuras da US4, mesmo padrão de 156): planilha de
  pagamentos de salário com ações em massa e exportação (`/financeiro/pagamentos`), cadastro de
  funcionário/salário (`/financeiro/funcionarios`), e gestão de comissões
  (`/financeiro/comissoes`). Cada uma é grande e financeiramente sensível o suficiente para seu
  próprio ciclo `/speckit-plan`.
- Valores monetários exibidos em React usam `@manto/money` (formatBRL) como fonte única — nunca
  reimplementados no frontend.
- A ação "emitir nota fiscal" (`POST /financeiro/nf/<id>/emitir`) não faz parte desta fatia de
  leitura — a lista de notas a emitir é só informativa aqui.
