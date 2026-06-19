# Feature Specification: Vincular um ensaio existente a um evento pai

**Feature Branch**: `063-vincular-ensaio-pai`

**Created**: 2026-06-19

**Status**: Draft

**Input**: User description: "Preciso que dê para vincular um ensaio já existente na agenda a um novo evento pai."

## Contexto

Um ensaio é um evento do tipo ENSAIO vinculado a um show (evento pai). Hoje o vínculo só é
definido no momento em que o ensaio é criado a partir de um show. Quando um ensaio fica **órfão**
(o show foi removido/cancelado da agenda) ou foi criado solto, **não há como vinculá-lo a um
show** — a página do ensaio apenas informa "Este ensaio não está vinculado a nenhum show na
agenda" (ver feature 062), sem ação para corrigir.

O cliente precisa poder **vincular um ensaio já existente a um evento pai** — escolhendo o show
na própria página do ensaio. Isso vale tanto para ensaios órfãos quanto para trocar o pai de um
ensaio que já tem vínculo.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Vincular um ensaio órfão a um show (Priority: P1) 🎯 MVP

Como equipe de ensaio, quero, na página de um ensaio órfão, escolher um show da agenda e
vinculá-lo, para que o ensaio deixe de ficar solto e volte a aparecer junto do show.

**Why this priority**: É o pedido central e resolve o caso real do print (ensaio órfão sem como
religar).

**Independent Test**: Abrir um ensaio órfão, escolher um show na lista e confirmar; o ensaio
passa a mostrar esse show como origem e aparece entre os ensaios do show.

**Acceptance Scenarios**:

1. **Given** um ensaio órfão, **When** a equipe escolhe um show e confirma o vínculo, **Then** o
   ensaio passa a ter aquele show como **evento pai** (mostrado em "Show de origem" com link).
2. **Given** o ensaio recém-vinculado, **When** o show é aberto, **Then** o ensaio aparece na
   lista de ensaios daquele show.
3. **Given** a lista de shows para escolher, **When** exibida, **Then** permite **buscar** pelo
   nome para achar o show rapidamente.

---

### User Story 2 - Trocar o evento pai de um ensaio (Priority: P2)

Como equipe de ensaio, quero poder **trocar** o show de um ensaio que já está vinculado (ex.:
vinculei ao show errado), para corrigir o vínculo sem precisar recriar o ensaio.

**Why this priority**: Mesmo mecanismo do P1; cobre correção de vínculo.

**Acceptance Scenarios**:

1. **Given** um ensaio já vinculado a um show, **When** a equipe escolhe outro show e confirma,
   **Then** o ensaio passa a apontar para o novo show (e some da lista do show antigo).

---

### Edge Cases

- **Nenhum show selecionado**: nada muda; mensagem clara.
- **Tentar vincular a um evento que é ensaio**: não permitido (pai deve ser um show/evento
  comum, não outro ensaio).
- **Vincular ao próprio ensaio**: não permitido.
- **Permissão**: apenas equipe de ensaio/casting/admin pode vincular; demais veem leitura.
- **Ensaio que não é do tipo ENSAIO**: a ação não se aplica (só ensaios têm "evento pai").

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A página de um ensaio MUST oferecer (para perfis autorizados) uma ação para
  **vincular o ensaio a um evento pai** (show), escolhendo-o de uma lista.
- **FR-002**: A ação MUST funcionar para ensaios **órfãos** (sem pai) e para **trocar** o pai de
  um ensaio já vinculado.
- **FR-003**: A lista de shows para escolher MUST permitir **busca por nome** e MUST excluir
  eventos do tipo ENSAIO e o próprio ensaio.
- **FR-004**: Após vincular, o ensaio MUST passar a exibir o show como origem (com link) e MUST
  aparecer entre os ensaios daquele show.
- **FR-005**: A ação MUST ser restrita à equipe de ensaio/casting/admin; demais usuários não
  veem a ação.
- **FR-006**: Vincular a um pai inválido (outro ensaio, o próprio ensaio, ou seleção vazia) MUST
  ser recusado com mensagem clara, sem alterar o vínculo.

### Key Entities

- **Ensaio (existente)**: evento do tipo ENSAIO com um campo de "evento pai". Esta feature
  permite **definir/alterar** esse vínculo depois da criação.
- **Show/Evento pai (existente)**: qualquer evento que não seja ensaio; passa a ter o ensaio
  vinculado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um ensaio órfão pode ser vinculado a um show em poucos cliques, direto da página
  do ensaio.
- **SC-002**: Após vincular, o ensaio aparece junto do show escolhido em 100% dos casos.
- **SC-003**: Vínculos inválidos (outro ensaio, próprio ensaio, vazio) são recusados em 100% das
  tentativas, sem corromper o vínculo atual.

## Assumptions

- "Evento pai" é o show ao qual o ensaio pertence (mesmo campo já usado quando o ensaio é criado
  a partir do show).
- A ação fica na **página do ensaio** (feature 062), no bloco "Show de origem".
- Não há restrição de data entre ensaio e show (pode-se vincular a qualquer show da agenda); a
  escolha é responsabilidade do usuário.
- Permissões seguem as já usadas para editar/cancelar ensaio (equipe de ensaio/casting/admin).
- Vincular não altera a agenda do Google (é só o vínculo interno entre ensaio e show).
