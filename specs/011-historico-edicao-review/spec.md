# Feature Specification: Indicar edição e ver histórico de uma avaliação

**Feature Branch**: `011-historico-edicao-review`

**Created**: 2026-05-30

**Status**: Draft

**Input**: User description: "No local onde vejo as reviews das pessoas, mostrar que já foi
editada e ver o histórico de edição."

## Contexto

Desde a feature 010, o talento pode editar sua avaliação de eventos nos últimos 30 dias. Hoje a
edição **sobrescreve** a avaliação — não há registro de que foi editada nem das versões
anteriores. Quem vê as avaliações (equipe, na página do talento) não sabe se uma nota foi
alterada. O usuário quer (1) um **indicador "editada"** e (2) **ver o histórico de edições** de
uma avaliação.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Saber que uma avaliação foi editada (Priority: P1)

Na página do talento (onde a equipe vê as avaliações feitas por ele), uma avaliação que foi
editada após o envio inicial mostra um indicador "editada", com a data da última edição.

**Why this priority**: É o sinal mínimo para a equipe saber que aquela nota mudou desde o envio.

**Independent Test**: Editar uma avaliação e confirmar que, na página do talento, aquela
avaliação passa a exibir "editada" com a data.

**Acceptance Scenarios**:

1. **Given** uma avaliação que nunca foi editada, **When** a equipe vê a página do talento,
   **Then** ela aparece sem o indicador de edição.
2. **Given** uma avaliação editada ao menos uma vez, **When** a equipe vê a página do talento,
   **Then** ela mostra "editada" e a data da última edição.

---

### User Story 2 - Ver o histórico de edições de uma avaliação (Priority: P1)

A partir da avaliação na página do talento, a equipe consegue abrir o **histórico de edições**:
a lista de versões anteriores (nota geral, comentário e sub-avaliações), cada uma com a data em
que foi substituída.

**Why this priority**: É o pedido central — ver o que mudou ao longo do tempo.

**Independent Test**: Editar uma avaliação duas vezes e confirmar que o histórico mostra as
versões anteriores, com datas, além da versão atual.

**Acceptance Scenarios**:

1. **Given** uma avaliação editada 2 vezes, **When** a equipe abre o histórico de edições,
   **Then** vê a versão atual e as 2 versões anteriores, cada uma com nota, comentário,
   sub-avaliações e a data correspondente.
2. **Given** uma avaliação nunca editada, **When** a equipe a vê, **Then** não há histórico a
   exibir (ou o histórico mostra apenas a versão atual, sem versões anteriores).

---

### Edge Cases

- **Avaliações anteriores a esta funcionalidade**: não têm versões anteriores registradas;
  aparecem sem histórico até serem editadas novamente.
- **Edição que não muda nada**: se o conteúdo não mudou, não precisa registrar uma nova versão.
- **Sub-avaliações**: o histórico inclui o conjunto de sub-avaliações de cada versão (não só a
  nota geral).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Uma avaliação editada após o envio inicial MUST exibir um indicador "editada" com
  a data da última edição, no local onde a equipe vê as avaliações do talento.
- **FR-002**: O sistema MUST preservar as versões anteriores de uma avaliação ao editá-la
  (a partir da ativação desta funcionalidade).
- **FR-003**: Cada versão preservada MUST incluir a nota geral, o comentário e as
  sub-avaliações daquele momento, com a data em que deixou de ser a versão vigente.
- **FR-004**: A equipe MUST conseguir abrir o histórico de edições de uma avaliação e ver as
  versões anteriores junto com a versão atual.
- **FR-005**: Avaliações nunca editadas NÃO MUST exibir o indicador "editada" nem versões
  anteriores.
- **FR-006**: Uma edição que não altera o conteúdo NÃO MUST gerar uma nova versão.
- **FR-007**: O registro de versões NÃO MUST alterar o comportamento de edição existente para o
  talento (continua simples no portal).

### Key Entities *(include if feature involves data)*

- **Avaliação de evento** (já existe): ganha a noção de "última edição".
- **Versão de avaliação** (nova): uma fotografia de uma avaliação num momento — nota geral,
  comentário e sub-avaliações — guardada quando a avaliação é substituída por uma edição.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das avaliações editadas após a ativação exibem o indicador "editada".
- **SC-002**: O histórico de uma avaliação editað N vezes mostra N versões anteriores + a atual.
- **SC-003**: 0 avaliações nunca editadas exibem indicador de edição.
- **SC-004**: A experiência de edição do talento no portal permanece igual (sem etapas novas).

## Assumptions

- "Local onde vejo as reviews" = a página do talento (visão da equipe) onde aparecem as
  avaliações feitas por ele.
- O histórico passa a ser registrado a partir da ativação desta funcionalidade; não há como
  recriar versões anteriores a isso (não eram guardadas).
- Uma "versão" cobre a avaliação geral + as sub-avaliações daquele momento.
- O histórico é informativo para a equipe; o talento continua editando normalmente no portal.
