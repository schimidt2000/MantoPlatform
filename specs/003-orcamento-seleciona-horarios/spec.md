# Feature Specification: Selecionar quais durações entram no orçamento

**Feature Branch**: `003-orcamento-seleciona-horarios`

**Created**: 2026-05-29

**Status**: Draft

**Input**: User description: "na pagina de criar orçamento ... o vendedor vai selecionar qual
horario ele quer incluir no orçamento, por padrao deixa todos selecionados. Ai ele marca a
caixa de qual ele quer que va para o orçamento da pagina seguinte."

## Contexto

O orçamento hoje sempre apresenta três durações fixas — **1 hora, 2 horas e 4 horas** — na
mensagem de WhatsApp, no resumo de valores da página de resultado e no PDF. O vendedor quer
poder escolher **quais dessas durações** entram no orçamento entregue ao cliente.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Escolher as durações do orçamento (Priority: P1)

Na página de criar orçamento, o vendedor vê uma caixa de seleção para cada duração padrão
(1h, 2h, 4h), **todas marcadas por padrão**. Ele desmarca as que não quer. Ao gerar, o
orçamento da página seguinte (mensagem, resumo e PDF) mostra **apenas** as durações marcadas.

**Why this priority**: É o pedido central. Dá ao vendedor controle sobre o que o cliente vê,
sem precisar editar a mensagem manualmente depois.

**Independent Test**: Criar um orçamento marcando só "2 horas" e "4 horas" e confirmar que a
mensagem, o resumo e o PDF mostram apenas essas duas durações.

**Acceptance Scenarios**:

1. **Given** a página de criar orçamento, **When** o vendedor a abre, **Then** as três
   durações (1h, 2h, 4h) aparecem com a caixa marcada por padrão.
2. **Given** o vendedor desmarca "1 hora", **When** gera o orçamento, **Then** a mensagem,
   o resumo de valores e o PDF não mostram a duração de 1 hora.
3. **Given** a seção de pagamento "À Vista (PIX)" lista valores por duração, **When** uma
   duração é desmarcada, **Then** ela também some dessa seção.

---

### User Story 2 - Padrão preserva o comportamento atual (Priority: P2)

Quem não mexe nas caixas obtém exatamente o orçamento de hoje (as três durações).

**Why this priority**: Garante que a mudança não atrapalhe o fluxo de quem já usa a ferramenta.

**Independent Test**: Gerar um orçamento sem tocar nas caixas e confirmar que o resultado é
idêntico ao atual (1h, 2h e 4h presentes).

**Acceptance Scenarios**:

1. **Given** todas as caixas marcadas (padrão), **When** o vendedor gera o orçamento,
   **Then** o resultado é igual ao comportamento atual.

---

### Edge Cases

- **Nenhuma duração marcada**: o sistema não pode gerar um orçamento vazio — nesse caso
  trata como "todas marcadas".
- **Duração extra personalizada**: quando informada, continua aparecendo normalmente; ela não
  faz parte das três caixas padrão.
- **Modo "por entradas"**: a seleção funciona igual, apenas com os rótulos de entradas.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A página de criar orçamento MUST oferecer uma caixa de seleção para cada
  duração padrão (1 hora, 2 horas, 4 horas).
- **FR-002**: Por padrão, todas as durações MUST vir marcadas.
- **FR-003**: O orçamento gerado (mensagem para WhatsApp, resumo de valores na tela e PDF)
  MUST incluir apenas as durações marcadas.
- **FR-004**: A seção de formas de pagamento que lista valores por duração (PIX à vista)
  MUST refletir apenas as durações marcadas.
- **FR-005**: Se nenhuma duração for marcada, o sistema MUST evitar orçamento vazio, tratando
  a situação como "todas marcadas".
- **FR-006**: A duração extra personalizada, quando informada, MUST continuar aparecendo,
  independentemente das três caixas padrão.
- **FR-007**: NÃO MUST haver regressão para quem não interage com as caixas — o resultado
  deve ser idêntico ao atual.

### Key Entities *(include if feature involves data)*

- **Orçamento gerado**: já existe (durações + totais + mensagem). Ganha a informação de
  quais durações foram selecionadas, propagada para tela e PDF.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O vendedor consegue incluir/excluir uma duração com 1 clique (marcar/desmarcar).
- **SC-002**: Durações desmarcadas não aparecem em nenhuma saída do orçamento entregue ao
  cliente (mensagem, resumo na tela e PDF) — 0 vazamentos.
- **SC-003**: 0 regressão: orçamento gerado sem interagir com as caixas é idêntico ao atual.

## Assumptions

- "Horário" no pedido = as durações padrão do orçamento (1h, 2h, 4h).
- A seleção vale para todas as saídas do orçamento: mensagem de WhatsApp, resumo na tela e PDF.
- A duração extra personalizada permanece como está; a seleção cobre apenas as três padrão.
- Desmarcar todas recai em "todas marcadas", para nunca gerar um orçamento sem valores.
