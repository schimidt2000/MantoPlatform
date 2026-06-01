# Feature Specification: Editar avaliação de eventos (até 30 dias)

**Feature Branch**: `010-editar-avaliacao`

**Created**: 2026-05-30

**Status**: Draft

**Input**: User description: "No histórico de evento, a pessoa pode editar a sua avaliação dos
eventos realizados nos últimos 30 dias."

## Contexto

No portal do talento, eventos já avaliados mostram "✓ Avaliado" no histórico (feature 009), mas
não há como **alterar** uma avaliação depois de enviada. O usuário quer permitir que o talento
edite sua avaliação de eventos realizados nos **últimos 30 dias**. A tela de avaliação já
suporta reabrir e atualizar uma avaliação existente; falta o caminho a partir do histórico.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Editar uma avaliação já enviada (Priority: P1)

No histórico, um evento que o talento **já avaliou** e que ocorreu nos **últimos 30 dias** mostra
a opção de "Editar avaliação". Ao acessá-la, o talento vê sua avaliação atual já preenchida e
pode alterar a nota e o comentário.

**Why this priority**: É o pedido central — permitir corrigir/atualizar a avaliação dentro de
uma janela razoável.

**Independent Test**: Avaliar um evento recente, depois abrir "Editar avaliação" no histórico,
mudar a nota e salvar; confirmar que a nova nota fica registrada.

**Acceptance Scenarios**:

1. **Given** um evento avaliado realizado há 10 dias, **When** o talento vê o histórico,
   **Then** aquele evento mostra a opção "Editar avaliação".
2. **Given** a tela de edição, **When** o talento abre, **Then** vê sua nota e comentário atuais
   já preenchidos.
3. **Given** o talento altera a nota e salva, **When** confirma, **Then** a avaliação é
   atualizada (sem criar uma segunda avaliação).
4. **Given** um evento avaliado realizado há mais de 30 dias, **When** o talento vê o histórico,
   **Then** NÃO há opção de editar (apenas o indicador "✓ Avaliado").

---

### Edge Cases

- **Evento avaliado entre 8 e 30 dias**: ainda não está na janela de *primeira* avaliação (7
  dias), mas **está** na janela de **edição** (30 dias) — deve mostrar "Editar avaliação".
- **Evento avaliado há mais de 30 dias**: continua "✓ Avaliado", mas sem edição.
- **Evento ainda não avaliado**: segue a regra atual (botão "Avaliar" se dentro de 7 dias).
- **Nota abaixo de 4 ao editar**: mantém a regra existente de exigir comentário.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: No histórico, um evento já avaliado e realizado nos últimos 30 dias MUST oferecer
  a opção "Editar avaliação".
- **FR-002**: A edição MUST reaproveitar a tela de avaliação existente, com a nota e o comentário
  atuais já preenchidos.
- **FR-003**: Salvar uma edição MUST atualizar a avaliação existente, sem criar duplicata.
- **FR-004**: Eventos avaliados há mais de 30 dias NÃO MUST oferecer edição (apenas "✓ Avaliado").
- **FR-005**: Eventos não avaliados MUST manter o comportamento atual (botão "Avaliar" dentro da
  janela de 7 dias).
- **FR-006**: As validações atuais da avaliação (nota 1–5; comentário obrigatório para nota < 4)
  MUST continuar valendo na edição.

### Key Entities *(include if feature involves data)*

- **Avaliação de evento** (já existe): pode ser atualizada; a data do evento define a janela de
  edição de 30 dias.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O talento consegue iniciar a edição de uma avaliação elegível em no máximo 1 clique
  a partir do histórico.
- **SC-002**: 100% dos eventos avaliados realizados nos últimos 30 dias oferecem edição.
- **SC-003**: 0 eventos avaliados há mais de 30 dias oferecem edição.
- **SC-004**: Editar nunca cria uma segunda avaliação para o mesmo evento/talento.

## Assumptions

- A janela de 30 dias conta a partir do **término** do evento (com fallback no início), mesma
  base de tempo das features anteriores.
- "Editar avaliação" reutiliza a tela de avaliação existente, que já carrega e atualiza a
  avaliação anterior.
- A edição cobre a nota geral e o comentário; sub-avaliações detalhadas seguem o fluxo já
  existente da tela.
- A janela de **primeira avaliação** (7 dias) permanece inalterada; esta feature adiciona a
  janela de **edição** (30 dias) para quem já avaliou.
