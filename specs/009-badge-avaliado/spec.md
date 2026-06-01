# Feature Specification: Badge "✓ Avaliado" no histórico

**Feature Branch**: `009-badge-avaliado`

**Created**: 2026-05-30

**Status**: Draft

**Input**: User description: "Adicionar um check marcado quando o evento já foi avaliado."

## Contexto

No portal do talento (feature 008), eventos elegíveis no histórico mostram o botão "⭐ Avaliar".
Quando o talento avalia, o botão simplesmente **desaparece**, sem qualquer indicação — o que
parece um erro ("sumiu o botão"). O usuário quer um **indicador visual de "já avaliado"** para
que fique claro que aquele evento foi avaliado, em vez de o botão apenas sumir.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver que um evento já foi avaliado (Priority: P1)

No histórico de eventos, um evento que o talento **já avaliou** mostra um indicador "✓ Avaliado"
no lugar do botão "Avaliar".

**Why this priority**: É o pedido. Dá feedback claro e elimina a impressão de bug ("o botão sumiu").

**Independent Test**: Avaliar um evento e confirmar que, no histórico, ele passa a mostrar
"✓ Avaliado" em vez do botão "Avaliar".

**Acceptance Scenarios**:

1. **Given** um evento que o talento já avaliou, **When** ele vê o histórico, **Then** aquele
   evento mostra "✓ Avaliado".
2. **Given** um evento elegível ainda não avaliado, **When** ele vê o histórico, **Then** aquele
   evento mostra o botão "⭐ Avaliar" (comportamento atual).
3. **Given** um evento avaliado, **When** ele vê o histórico, **Then** o botão "Avaliar" NÃO
   aparece (substituído pelo "✓ Avaliado").

---

### Edge Cases

- **Evento avaliado mas antigo (fora da janela de 7 dias)**: continua mostrando "✓ Avaliado"
  (o registro de avaliação não expira; só a possibilidade de avaliar de novo).
- **Evento passado, não avaliado e fora da janela**: não mostra nem "Avaliar" nem "✓ Avaliado"
  (não é elegível e não foi avaliado).
- **O indicador aparece nos mesmos lugares do botão**: histórico recente (home) e página de
  histórico completo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: No histórico, um evento já avaliado pelo talento MUST exibir um indicador
  "✓ Avaliado".
- **FR-002**: Para eventos já avaliados, o botão "Avaliar" NÃO MUST ser exibido.
- **FR-003**: Eventos elegíveis e não avaliados MUST continuar exibindo "⭐ Avaliar"
  (sem regressão da feature anterior).
- **FR-004**: O indicador "✓ Avaliado" MUST aparecer tanto no histórico recente (home) quanto na
  página de histórico completo.
- **FR-005**: O indicador "✓ Avaliado" NÃO MUST depender da janela de 7 dias — um evento avaliado
  permanece marcado como avaliado mesmo depois da janela.

### Key Entities *(include if feature involves data)*

- **Avaliação de evento** (já existe): a existência de uma avaliação daquele talento para aquele
  evento determina o indicador "✓ Avaliado".

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos eventos já avaliados pelo talento exibem "✓ Avaliado" no histórico.
- **SC-002**: 0 eventos avaliados exibem o botão "Avaliar".
- **SC-003**: O talento identifica, sem ambiguidade, quais eventos já avaliou — eliminando a
  impressão de "o botão sumiu".

## Assumptions

- "Já avaliado" = existe uma avaliação registrada daquele talento para aquele evento (a mesma
  base usada hoje para remover o evento da lista de elegíveis).
- O indicador é informativo (não clicável) — não reabre a avaliação.
- Vale para os dois pontos do histórico (home + página completa), espelhando o botão "Avaliar".
