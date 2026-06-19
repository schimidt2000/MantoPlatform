# Feature Specification: Seleção múltipla estilo planilha nos pagamentos

**Feature Branch**: `064-selecao-multipla-pagamentos`

**Created**: 2026-06-19

**Status**: Draft

**Input**: User description: "Preciso de uma função similar ao Google Sheets nos pagamentos. Ao selecionar vários pagamentos, mostrar em algum lugar a quantidade e a soma dos selecionados. E poder selecionar vários usando shift (intervalo, como num explorador de arquivos) ou ctrl (um a um), sem ficar clicando em cada caixinha."

## Contexto

A tela de pagamentos já permite selecionar linhas por caixas de seleção e agir em lote
(marcar pago/no banco/não pago/excluir), mostrando a **quantidade** de selecionados. Faltam duas
comodidades no estilo de uma planilha/explorador de arquivos:

1. Ao selecionar, ver também a **soma em R$** dos itens selecionados (não só a quantidade).
2. Selecionar **vários de uma vez** com **Shift** (intervalo entre o último clique e o atual) e
   ajustar item a item com o comportamento de marcar/desmarcar individual — sem precisar clicar
   em cada caixinha uma por uma.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver quantidade e soma dos selecionados (Priority: P1) 🎯 MVP

Como responsável pelos pagamentos, quero ver a **quantidade** e a **soma em R$** dos pagamentos
que selecionei, para conferir rapidamente o total que vou marcar/pagar sem somar na mão.

**Why this priority**: É metade do pedido e dá controle imediato sobre o total selecionado.

**Independent Test**: Selecionar alguns pagamentos e conferir que aparece "N selecionados" e a
soma em R$ correspondente; a soma muda ao marcar/desmarcar.

**Acceptance Scenarios**:

1. **Given** alguns pagamentos selecionados, **When** a seleção muda, **Then** a barra mostra a
   **quantidade** e a **soma em R$** dos selecionados, atualizada na hora.
2. **Given** itens sem valor (—), **When** selecionados, **Then** entram como R$ 0 na soma (não
   quebram o total).
3. **Given** nenhuma seleção, **When** a tela está em repouso, **Then** a barra de seleção fica
   oculta (como hoje).

---

### User Story 2 - Selecionar com Shift (intervalo) e ajuste individual (Priority: P1)

Como responsável pelos pagamentos, quero clicar em um item e, segurando **Shift**, clicar em
outro para selecionar **todo o intervalo** entre eles; e quero continuar podendo marcar/desmarcar
**um a um**, para montar a seleção rápido sem clicar em cada caixinha.

**Why this priority**: É a outra metade do pedido e o maior ganho de agilidade.

**Independent Test**: Marcar uma linha, segurar Shift e marcar outra mais abaixo; todas as
linhas entre as duas ficam selecionadas. Sem Shift, cada clique marca/desmarca só aquela.

**Acceptance Scenarios**:

1. **Given** uma linha marcada, **When** o usuário segura **Shift** e clica em outra linha,
   **Then** todas as linhas **entre** as duas (inclusive) assumem o mesmo estado do clique.
2. **Given** o filtro/busca ativo (linhas ocultas), **When** um intervalo é selecionado com
   Shift, **Then** apenas as linhas **visíveis** do intervalo são afetadas.
3. **Given** qualquer momento, **When** o usuário clica numa caixinha sem Shift, **Then** apenas
   aquela linha alterna (marca/desmarca), como hoje.
4. **Given** uma seleção feita por Shift, **When** concluída, **Then** a quantidade e a soma
   refletem o total selecionado.

---

### Edge Cases

- **Shift sem clique anterior**: comporta-se como clique simples (marca/desmarca só a atual).
- **Intervalo cruzando linhas ocultas pelo filtro**: linhas ocultas não são selecionadas.
- **"Selecionar tudo"**: continua selecionando as linhas visíveis (comportamento atual) e a soma
  reflete isso.
- **Itens de tipos diferentes** (cachê, salário, gasto, comissão): todos entram na contagem e na
  soma normalmente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Ao haver itens selecionados, a tela MUST exibir a **quantidade** e a **soma em
  R$** dos selecionados, atualizando imediatamente a cada mudança de seleção.
- **FR-002**: A soma MUST considerar o valor de cada item selecionado; itens sem valor contam
  como R$ 0.
- **FR-003**: O usuário MUST conseguir selecionar um **intervalo** de linhas segurando **Shift**
  entre o último item clicado e o atual.
- **FR-004**: A seleção por Shift MUST afetar apenas as linhas **visíveis** (respeitando o
  filtro/busca em vigor).
- **FR-005**: O clique simples (sem Shift) MUST continuar marcando/desmarcando apenas a linha
  clicada (ajuste individual), como hoje.
- **FR-006**: A soma e a quantidade MUST estar corretas após qualquer forma de seleção (clique
  individual, Shift, "selecionar tudo", limpar).
- **FR-007**: A soma MUST ser apresentada no formato monetário brasileiro (R$ com ponto de
  milhar e vírgula de centavos).

### Key Entities

- **Pagamento (item da lista, existente)**: linha selecionável com um valor em R$. A feature usa
  o valor para somar os selecionados; não altera dados.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Com qualquer seleção, a quantidade e a soma exibidas batem exatamente com os itens
  marcados.
- **SC-002**: Selecionar um intervalo de N linhas leva no máximo 2 cliques (primeiro + Shift no
  último), em vez de N cliques.
- **SC-003**: A soma reflete a mudança em menos de ~0,2s após marcar/desmarcar.
- **SC-004**: Nenhuma regressão nas ações em lote já existentes (marcar pago/no banco/não pago/
  excluir).

## Assumptions

- A feature é de **interface** na tela de pagamentos; não muda dados nem as ações em lote
  existentes.
- "Ctrl para ir de um em um" corresponde ao comportamento já existente de marcar/desmarcar
  caixas individualmente (cada clique alterna uma linha); o ganho novo é o **Shift** para
  intervalos.
- A soma usa os valores já exibidos na lista (mesma base monetária do restante do sistema).
- O escopo é a tela de pagamentos do financeiro (onde já existe a seleção em lote).
