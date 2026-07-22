# Feature Specification: Pipeline de Vendas em React (Leitura)

**Feature Branch**: `156-vendas-pipeline-leitura`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Encadear para a US4 (Vendas, Pagamentos e Reembolsos) da migração React (144). Escopo real levantado no código: o módulo Financeiro/Vendas tem 5 telas grandes (dashboard DRE, pipeline de vendas, planilha de pagamentos de salário com ações em massa, cadastro de funcionário/salário, comissões) — nenhuma migrada ainda. Seguindo o padrão de toda a migração (agenda começou pela leitura na 145, talentos/figurino começou pela leitura na 154), a primeira fatia da US4 é a tela mais estreita e independente: o Pipeline de Vendas (`/vendas/`) — listagem de eventos com venda, custo, lucro e comissão. Dashboard DRE, planilha de pagamentos e comissões ficam para fatias futuras da US4."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver o pipeline de vendas em React (Priority: P1)

Como usuário com acesso a Vendas (Comercial, Financeiro, Superadmin, ou o responsável
EducaManto configurado), preciso ver a lista de eventos com dados de venda, custo e comissão
na tela React — sem precisar abrir a tela antiga.

**Why this priority**: É a única tela deste conjunto que é puramente de leitura, sem ações em
massa nem cálculo de DRE — a fatia mais estreita e independente para abrir a US4, entregando
valor real (é a tela que Comercial usa no dia a dia para acompanhar vendas).

**Independent Test**: abrir a tela de pipeline em React e conferir que a lista de eventos
aparece com os mesmos valores (venda, custo, comissão, e lucro quando visível) da tela antiga,
para o mesmo usuário.

**Acceptance Scenarios**:

1. **Given** um usuário Comercial autenticado, **When** ele abre o pipeline de vendas em React,
   **Then** vê a lista de eventos (exceto ENSAIO) ordenada por data decrescente, com venda,
   custo e comissão de cada um.
2. **Given** um usuário Financeiro ou Superadmin, **When** ele abre a tela, **Then** vê também
   a coluna de lucro (venda − custo) — coluna que Comercial não vê.
3. **Given** um evento satélite de um grupo comercial, **When** a lista é montada, **Then** o
   satélite não aparece como linha própria — o evento principal do grupo mostra o nome do grupo
   e os custos consolidados (mesma regra de hoje).
4. **Given** o responsável EducaManto configurado (sem os papéis Comercial/Financeiro/
   Superadmin), **When** ele abre a tela, **Then** vê só os eventos cujo título começa com o
   prefixo EducaManto (mesma regra de hoje).
5. **Given** um usuário sem acesso a Vendas, **When** ele tenta abrir a tela ou chamar a API
   diretamente, **Then** o acesso é recusado (403).
6. **Given** a lista de eventos, **When** o usuário clica em "Ver" num evento, **Then** é levado
   para o detalhe do evento já migrado (tela React existente desde a 145).

---

### Edge Cases

- Evento sem venda registrada (`sale_value` vazio) → aparece na lista com venda/custo/comissão
  em branco (traço), não com erro nem "R$ 0,00" enganoso — mesmo comportamento de hoje.
- Nenhum evento no sistema (ou nenhum fora de ENSAIO) → tela mostra estado vazio amigável, não
  uma tabela quebrada.
- Evento com nota fiscal (`with_invoice`) → indicador visual de "NF" na linha (paridade com a
  tela antiga).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE expor a listagem do pipeline de vendas (todos os eventos exceto
  ENSAIO, ordenados por data decrescente) como endpoint JSON, reaproveitando exatamente o
  cálculo de custo e comissão já existente (sem duplicar a lógica).
- **FR-002**: O sistema DEVE restringir o acesso a essa listagem a usuários com papel Comercial,
  Financeiro ou Superadmin, ou ao responsável EducaManto configurado — mesma regra de hoje
  (`require_vendas`).
- **FR-003**: O sistema DEVE incluir a coluna de lucro na resposta somente quando o usuário
  autenticado for Financeiro ou Superadmin — paridade com a condicional hoje só no template.
- **FR-004**: Eventos satélites de um grupo comercial NÃO DEVEM aparecer como linha própria na
  listagem — o evento principal consolida os dados do grupo (mesma regra de `_group_cost`).
- **FR-005**: O responsável EducaManto configurado sem os papéis plenos DEVE ver apenas os
  eventos cujo título começa com o prefixo EducaManto — mesma regra de hoje.
- **FR-006**: A tela React DEVE mostrar, por evento: data do evento, título (ou nome do grupo +
  indicador "grupo"/"satélite"), local, data da venda, venda, custo, lucro (condicional),
  comissão, indicador de nota fiscal, e link para o detalhe do evento já migrado.
- **FR-007**: O comportamento da tela antiga (Jinja, `/vendas/`) DEVE permanecer idêntico ao de
  antes desta fatia — sem regressão.

### Key Entities

- **Evento (CalendarEvent)**: já existente; esta fatia só lê campos já existentes (venda, data
  de venda, tipo, indicador de nota fiscal, agrupamento comercial) — nenhum campo novo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário com acesso a Vendas consegue ver o pipeline completo (venda, custo,
  comissão, e lucro quando aplicável) inteiramente pela tela React, sem abrir a tela antiga.
- **SC-002**: Os valores mostrados em React são idênticos aos da tela antiga para o mesmo
  usuário e mesmos dados — verificado por paridade automatizada.
- **SC-003**: Usuário sem acesso a Vendas não consegue ver a listagem nem pela tela nem pela API
  (403 nos dois casos).

## Assumptions

- Esta fatia é só leitura — nenhuma ação de escrita (marcar comissão como paga, editar venda
  etc.) faz parte dela.
- Ficam explicitamente fora desta fatia (fatias futuras da US4): dashboard financeiro (DRE,
  KPIs, tendência mensal, auditoria — tela `/financeiro/`), planilha de pagamentos de salário
  com ações em massa e exportação (`/financeiro/pagamentos`), cadastro de funcionário/salário
  (`/financeiro/funcionarios`), e gestão de comissões (`/financeiro/comissoes`). Cada uma é
  grande e financeiramente sensível o suficiente para merecer seu próprio ciclo `/speckit-plan`,
  mesmo padrão adotado pela Agenda (145→153) e por Talentos/Figurino (154→155).
- Valores monetários exibidos em React usam `@manto/money` (formatBRL) como fonte única — nunca
  reimplementados no frontend.
