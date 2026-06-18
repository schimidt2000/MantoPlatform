# Feature Specification: Ensaios órfãos contam só a partir da data de início do sistema

**Feature Branch**: `060-ensaios-orfaos-data-inicio`

**Created**: 2026-06-18

**Status**: Draft

**Input**: User description: "Estão aparecendo diversos ensaios sem show órfãos. O grande problema é que a maioria é do passado. Isso também precisa começar a contar apenas após a data de início do sistema (configurado no painel de admin)."

## Contexto

A home mostra uma lista de **ensaios órfãos** — ensaios cujo show pai não existe mais na agenda
(feature 057) — para que possam ser cancelados. Hoje essa lista inclui **todas as datas,
inclusive passadas**, então aparecem muitos ensaios antigos (de shows cancelados há tempo) que
são apenas ruído.

O sistema já tem uma **"Data de início do sistema"** configurável no painel de admin
(`release_date`), usada para que as **demais tarefas da home** ignorem eventos anteriores a essa
data. Os ensaios órfãos são a exceção que ficou de fora desse filtro — e é isso que o cliente
quer corrigir: passar a contar/exibir órfãos **apenas a partir da data de início do sistema**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver só os ensaios órfãos relevantes (Priority: P1) 🎯 MVP

Como usuário do setor de ensaio (ou super admin), quero que a lista de ensaios órfãos na home
mostre apenas os que ocorrem a partir da data de início do sistema, para não ser inundado por
ensaios antigos de shows cancelados há muito tempo.

**Why this priority**: É o pedido central — remover o ruído de órfãos do passado.

**Independent Test**: Com a data de início configurada no admin, conferir que ensaios órfãos
anteriores a ela não aparecem na home, e que os a partir dela continuam aparecendo.

**Acceptance Scenarios**:

1. **Given** um ensaio órfão com data **anterior** à data de início do sistema, **When** a home
   é aberta, **Then** ele **não** aparece na lista de ensaios órfãos.
2. **Given** um ensaio órfão com data **igual ou posterior** à data de início, **When** a home é
   aberta, **Then** ele **aparece** na lista (e pode ser cancelado, como na feature 057).
3. **Given** a data de início **não** configurada, **When** a home é aberta, **Then** o corte usa
   a data de hoje — o mesmo critério já adotado pelas demais tarefas da home.

---

### Edge Cases

- **Data de início não configurada**: usar hoje como corte (igual ao restante da home).
- **Ensaio órfão exatamente na data de início**: incluído (o corte é "a partir de", inclusive).
- **Ensaios órfãos futuros**: continuam aparecendo normalmente.
- **Cancelamento (feature 057)**: segue funcionando para os órfãos exibidos.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A lista de ensaios órfãos da home MUST incluir **apenas** ensaios cuja data seja
  **igual ou posterior** à data de início do sistema configurada no admin.
- **FR-002**: Quando a data de início não estiver configurada, o sistema MUST usar a data de
  hoje como corte (mesmo fallback já usado pelas demais tarefas da home).
- **FR-003**: Ensaios órfãos com data **anterior** à data de início MUST **não** aparecer na
  lista.
- **FR-004**: O critério de corte MUST ser o **mesmo** já aplicado às demais tarefas da home
  (consistência: uma única data de início para tudo).
- **FR-005**: Os ensaios órfãos exibidos (a partir da data) MUST continuar podendo ser
  cancelados, sem regressão da feature 057.

### Key Entities

- **Ensaio órfão (existente)**: evento do tipo ENSAIO cujo show pai não existe mais. Esta
  feature não muda os dados; muda apenas **quais órfãos são exibidos** (a partir da data de
  início).
- **Data de início do sistema (existente)**: configuração de admin (`release_date`) que define o
  corte temporal das tarefas da home.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 ensaios órfãos anteriores à data de início aparecem na home.
- **SC-002**: 100% dos ensaios órfãos a partir da data de início continuam aparecendo e podendo
  ser cancelados.
- **SC-003**: O corte temporal dos órfãos coincide exatamente com o das demais tarefas da home.

## Assumptions

- "Data de início do sistema" = o campo `release_date` já existente no painel de admin.
- "Contar a partir de" é inclusivo (>= a data de início).
- O escopo é a **exibição** dos órfãos na home; não há exclusão/alteração de dados dos ensaios
  antigos (eles continuam no banco, apenas não poluem a lista).
- A feature reaproveita o mesmo corte (`release_date` → data de corte) já usado pelas outras
  tarefas da home, em vez de criar um novo parâmetro.
