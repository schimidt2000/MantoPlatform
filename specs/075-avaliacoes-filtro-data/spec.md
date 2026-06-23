# Feature Specification: Alternar filtro de avaliações entre data do evento e data da avaliação

**Feature Branch**: `075-avaliacoes-filtro-data`

**Created**: 2026-06-23

**Status**: Draft

**Input**: "Quero esse botão de poder mudar para data de avaliação." (na página de Avaliações, o
filtro de período hoje considera a data do evento; o cliente quer poder alternar para a data em que
a avaliação foi feita.)

## Contexto

Na página de Avaliações, o filtro de período (30 dias / 3 meses / 12 meses / personalizado)
considera a **data do evento** (`start_at`). O cliente quer um **botão para alternar** o critério
para a **data da avaliação** (quando a nota foi enviada). Assim, "últimos 30 dias" pode significar
"eventos realizados nos últimos 30 dias" **ou** "avaliações recebidas nos últimos 30 dias".

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Alternar o critério de data do filtro (Priority: P1) 🎯 MVP

Como usuário da página de Avaliações, quero alternar entre **"data do evento"** e **"data da
avaliação"**, para analisar tanto o desempenho dos eventos do período quanto o que foi avaliado
no período.

**Independent Test**: Numa avaliação enviada hoje sobre um show de 3 meses atrás, escolher "data da
avaliação" + "últimos 30 dias" faz essa avaliação **aparecer**; em "data do evento" + "30 dias"
ela **não** aparece.

**Acceptance Scenarios**:

1. **Given** a página de avaliações, **When** o critério está em **"data do evento"** (padrão),
   **Then** o período filtra pela data de realização do evento (comportamento atual).
2. **Given** o critério em **"data da avaliação"**, **When** aplico um período, **Then** filtra
   pela data em que a avaliação foi enviada.
3. **Given** que troco o critério, **When** a página recarrega, **Then** o período, a categoria e os
   demais filtros são **mantidos**; só o critério de data muda.
4. **Given** todos os números/listas (médias, comentários, ranking, seletor de eventos), **When** o
   critério está em "data da avaliação", **Then** todos respeitam o mesmo critério, de forma
   consistente.

### Edge Cases

- **Visão por evento**: o período não se aplica (o evento já é o recorte) → o botão fica oculto/sem
  efeito, como o período já faz hoje.
- **Avaliação sem data de envio**: não entra em nenhum período no modo "data da avaliação".
- O rótulo do recorte deixa claro qual critério está ativo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A página de avaliações MUST oferecer um **botão/alternador** entre "data do evento"
  (padrão) e "data da avaliação".
- **FR-002**: O critério selecionado MUST ser aplicado **a todo o recorte** do período: KPIs,
  distribuição, médias por categoria, comentários, pontos de atenção, ranking/tendência e o seletor
  de eventos.
- **FR-003**: O padrão MUST permanecer **"data do evento"** (sem regressão do comportamento atual).
- **FR-004**: Alternar o critério MUST **preservar** os demais filtros (período, categoria, datas
  personalizadas).
- **FR-005**: O rótulo do recorte MUST indicar quando o filtro está por **data da avaliação**.

### Key Entities

- **Avaliação (existente)**: tem data de envio (quando foi feita) e referência ao evento (que tem a
  data de realização). O filtro passa a poder usar uma ou outra.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: É possível alternar o critério e os resultados mudam conforme esperado (caso do show
  antigo avaliado hoje).
- **SC-002**: Em "data do evento", os números são idênticos ao comportamento atual (sem regressão).
- **SC-003**: Trocar o critério mantém os demais filtros ativos.

## Assumptions

- Dois critérios: "data do evento" (padrão) e "data da avaliação" (data de envio da nota).
- Mudança de interface + filtro; sem novo dado, sem migration.
