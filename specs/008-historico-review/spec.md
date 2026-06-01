# Feature Specification: Avaliar qualquer evento elegível pelo histórico

**Feature Branch**: `008-historico-review`

**Created**: 2026-05-30

**Status**: Draft

**Input**: User description: "No portal só está dando para fazer review do último evento. O
ideal seria ter um histórico de eventos e o usuário poder avaliar qual evento ele quiser
dentro de um período de 7 dias."

## Contexto

No portal do talento, a avaliação aparece num banner de destaque cujo texto diz "Avalie seu
último evento". Embora o sistema considere todos os eventos terminados nos últimos 7 dias sem
avaliação, a experiência passa a impressão de que só dá para avaliar **um** (o último). Além
disso, a lista de **histórico recente** de eventos não oferece um caminho para avaliar — então
quem quer avaliar um evento que não está em destaque não encontra como.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Avaliar qualquer evento elegível pelo histórico (Priority: P1)

No histórico de eventos do portal, cada evento **terminado nos últimos 7 dias e ainda não
avaliado** mostra um botão "Avaliar". O talento escolhe qual evento avaliar, não apenas o mais
recente.

**Why this priority**: É o pedido central — liberdade de escolher qual evento avaliar dentro da
janela, a partir do histórico.

**Independent Test**: Ter dois eventos terminados nos últimos 7 dias e confirmar que ambos
mostram "Avaliar" no histórico; avaliar o mais antigo dos dois e confirmar que funciona.

**Acceptance Scenarios**:

1. **Given** dois eventos terminados há 2 e 5 dias, ambos não avaliados, **When** o talento
   abre o portal, **Then** os dois aparecem no histórico com um botão "Avaliar".
2. **Given** um evento elegível, **When** o talento clica em "Avaliar" no histórico, **Then** é
   levado à tela de avaliação daquele evento.
3. **Given** um evento já avaliado, **When** o talento vê o histórico, **Then** aquele evento
   não mostra "Avaliar" (mostra que já foi avaliado, ou nada).
4. **Given** um evento terminado há mais de 7 dias, **When** o talento vê o histórico, **Then**
   ele não mostra "Avaliar" (fora da janela).

---

### User Story 2 - Mensagem condizente com vários eventos (Priority: P2)

O destaque de avaliação no topo deixa de falar em "último evento" e passa a refletir que pode
haver mais de um evento a avaliar.

**Why this priority**: Remove a impressão de que só dá para avaliar um; alinhamento com o
comportamento real.

**Acceptance Scenarios**:

1. **Given** dois eventos a avaliar, **When** o talento abre o portal, **Then** o destaque
   indica que há eventos (no plural) aguardando avaliação e lista todos.
2. **Given** um único evento a avaliar, **When** o talento abre o portal, **Then** o texto fica
   coerente no singular.

---

### Edge Cases

- **Evento elegível só no histórico, não no destaque**: deve poder ser avaliado pelo histórico.
- **Janela de 7 dias**: vale a partir do **término** do evento (consistente com a regra atual);
  eventos sem término definido usam o horário de início.
- **Evento já avaliado**: não oferece "Avaliar" novamente (evita avaliação duplicada).
- **Nenhum evento elegível**: o histórico aparece normalmente, apenas sem botões "Avaliar".

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: No histórico de eventos do portal, cada evento elegível para avaliação MUST exibir
  um botão "Avaliar".
- **FR-002**: Um evento é elegível quando **terminou nos últimos 7 dias** e **ainda não foi
  avaliado** por aquele talento.
- **FR-003**: O botão "Avaliar" do histórico MUST levar à mesma tela de avaliação já existente
  para aquele evento.
- **FR-004**: Eventos já avaliados NÃO MUST oferecer "Avaliar" novamente.
- **FR-005**: Eventos terminados há mais de 7 dias NÃO MUST oferecer "Avaliar".
- **FR-006**: O destaque de avaliação no topo MUST usar texto coerente com a possibilidade de
  haver mais de um evento a avaliar (plural quando aplicável).
- **FR-007**: A elegibilidade MUST usar o término do evento como referência; quando não houver
  término definido, usa o horário de início.

### Key Entities *(include if feature involves data)*

- **Avaliação de evento** (já existe): determina se um evento já foi avaliado por um talento.
- **Evento no histórico** (já existe): passa a carregar a informação de "elegível para avaliar".

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O talento consegue iniciar a avaliação de qualquer evento elegível a partir do
  histórico em no máximo 1 clique.
- **SC-002**: 100% dos eventos terminados nos últimos 7 dias e não avaliados exibem "Avaliar"
  no histórico.
- **SC-003**: 0 eventos já avaliados ou fora da janela exibem "Avaliar".
- **SC-004**: O texto do destaque reflete corretamente singular/plural conforme a quantidade.

## Assumptions

- A janela de 7 dias e a regra de término (com fallback para início) são as mesmas já aplicadas
  ao destaque de avaliação atual (consistência com a feature anterior).
- A tela de avaliação por evento já existe e é reutilizada; esta feature apenas amplia os pontos
  de entrada (histórico) e ajusta a mensagem.
- "Histórico" refere-se à lista de eventos passados exibida no portal do talento.
- Não há mudança na estrutura de dados; apenas marcação de elegibilidade para exibição.
