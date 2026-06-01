# Feature Specification: Avaliação só após o evento + feedback do show no geral

**Feature Branch**: `006-avaliacao-pos-evento`

**Created**: 2026-05-30

**Status**: Draft

**Input**: User description: "Está aparecendo para a pessoa avaliar o evento antes dele
terminar. Preciso que a avaliação apareça apenas após o evento acabar. E trocar o feedback
sobre o 'texto do show' por feedback sobre o show no geral, com a dica: 'Falar sobre
coreografia, posicionamento, texto e interações'."

## Contexto

No portal do talento, eventos confirmados aparecem na seção "para avaliar". Hoje a avaliação
surge assim que o evento **começa** — antes de terminar —, o que não faz sentido. Além disso,
um dos campos de avaliação de show é especificamente sobre o "texto do show"; o usuário quer
ampliá-lo para o show como um todo.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Avaliação aparece só após o evento terminar (Priority: P1)

Um talento confirmado em um evento só vê a opção de avaliá-lo **depois que o evento termina**.
Enquanto o evento não acabou (ainda não começou ou está em andamento), ele não aparece na
seção "para avaliar".

**Why this priority**: É o bug relatado; avaliar um evento que ainda não terminou não faz sentido.

**Independent Test**: Para um evento que termina no futuro, confirmar que ele NÃO aparece para
avaliar; para um evento já terminado (dentro da janela), confirmar que aparece.

**Acceptance Scenarios**:

1. **Given** um evento que ainda não terminou (em andamento ou futuro), **When** o talento abre
   o portal, **Then** o evento NÃO aparece na seção "para avaliar".
2. **Given** um evento que já terminou e ainda não foi avaliado, **When** o talento abre o
   portal, **Then** o evento aparece na seção "para avaliar".
3. **Given** um evento já avaliado, **When** o talento abre o portal, **Then** ele não reaparece
   para avaliar.

---

### User Story 2 - Feedback do show no geral (Priority: P2)

Na avaliação de um show, o campo antes chamado "Texto do Show" passa a ser sobre o **show no
geral**, com uma dica orientando o que comentar: "Falar sobre coreografia, posicionamento,
texto e interações".

**Why this priority**: Melhora a qualidade do feedback coletado; pedido direto do usuário.

**Independent Test**: Abrir a avaliação detalhada de um show e confirmar que o campo aparece com
o novo título e a dica, e que a nota/comentário enviados são salvos normalmente.

**Acceptance Scenarios**:

1. **Given** a avaliação detalhada de um show, **When** o talento a abre, **Then** vê um campo
   "Show no geral" com a dica "Falar sobre coreografia, posicionamento, texto e interações".
2. **Given** esse campo preenchido com nota e comentário, **When** o talento envia, **Then** os
   dados são salvos como antes (sem perda das avaliações já existentes).

---

### Edge Cases

- **Evento sem horário de término definido**: usa-se o horário de início como referência de
  término (não pode ficar oculto para sempre nem aparecer cedo demais).
- **Avaliações antigas do campo "texto"**: continuam válidas e visíveis nos relatórios; apenas
  o rótulo exibido muda.
- **Janela de avaliação**: mantém-se o prazo atual de exibição após o término (eventos recentes).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Um evento só MUST aparecer na seção "para avaliar" após o seu término.
- **FR-002**: Quando o evento não tiver horário de término definido, o sistema MUST usar o
  horário de início como referência para considerar o evento "terminado".
- **FR-003**: O sistema MUST continuar não exibindo eventos já avaliados.
- **FR-004**: O sistema MUST manter a janela de tempo atual de exibição de eventos recentes
  (após o término).
- **FR-005**: Na avaliação de show, o campo "Texto do Show" MUST passar a se chamar "Show no
  geral", com a dica "Falar sobre coreografia, posicionamento, texto e interações".
- **FR-006**: O envio do campo renomeado MUST continuar salvando nota e comentário sem perda
  das avaliações já registradas.

### Key Entities *(include if feature involves data)*

- **Avaliação de evento** (já existe): inalterada na estrutura.
- **Sub-avaliação por categoria** (já existe): a categoria de show "texto" passa a ser
  apresentada como "Show no geral" na interface; o identificador interno é preservado para não
  perder histórico.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 eventos não terminados aparecem na seção "para avaliar".
- **SC-002**: 100% dos eventos já terminados (dentro da janela, não avaliados) aparecem para avaliar.
- **SC-003**: O campo de feedback do show exibe o novo título e a dica em 100% das avaliações de show.
- **SC-004**: 0 avaliações históricas perdidas após a mudança de rótulo.

## Assumptions

- "Após o evento acabar" = após o horário de término (`end_at`); sem término definido, usa o
  horário de início.
- A janela atual de exibição (eventos recentes após o término) é preservada como está.
- Para não perder dados históricos, mantém-se o identificador interno da categoria do campo de
  show; muda-se apenas o rótulo e a dica exibidos ao usuário.
- A mudança vale para a seção do portal do talento que lista eventos a avaliar e para a tela de
  avaliação detalhada do show.
