# Feature Specification: Corrigir persistência do adiantamento de salário + máscara BR

**Feature Branch**: `068-corrigir-adiantamento-salario`

**Created**: 2026-06-20

**Status**: Draft

**Input**: User description: "Coloquei o valor e o comprovante, salvei. Aparece a mensagem que o adiantamento foi salvo, só que não altera o valor a ser pago e não aparece em lugar nenhum onde esse valor fica salvo. Fora que saiu do padrão de digitação com máscara que estabelecemos antes."

## Contexto

A feature 067 (adiantamento de salário) está **quebrada**: ao salvar um adiantamento aparece
"salvo", mas o valor a pagar não muda e o adiantamento some.

**Causa raiz** (diagnóstico): a tela de pagamentos, ao carregar, **regenera** os salários não
pagos do mês — apaga os lançamentos "não pago" e os recria a partir do salário vigente. Como o
salvamento do adiantamento redireciona de volta para a tela, o lançamento recém-editado é
**apagado e recriado sem o adiantamento**. Por isso o "salvo" é real, mas o valor é perdido no
recarregamento.

Além disso, o campo de valor do adiantamento **perdeu a máscara** padrão de R$ do sistema; o
cliente quer a mesma máscara usada nos demais campos de valor.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Adiantamento persiste e desconta de verdade (Priority: P1) 🎯 MVP

Como financeiro, quero que, ao salvar um adiantamento, ele **permaneça** salvo e o valor a pagar
do salário passe a refletir o líquido — inclusive depois de recarregar/filtrar a tela.

**Why this priority**: É o bug central; sem isso a feature não funciona.

**Independent Test**: Registrar adiantamento num salário; recarregar a tela de pagamentos; o
adiantamento continua lá e o valor a pagar mostra o líquido (salário − adiantamento).

**Acceptance Scenarios**:

1. **Given** um salário não pago, **When** registro um adiantamento com comprovante e a tela
   recarrega, **Then** o adiantamento **continua salvo** e o valor a pagar mostra o líquido.
2. **Given** um salário com adiantamento, **When** a planilha do mês é regenerada (comportamento
   normal ao abrir a tela), **Then** o lançamento **não é apagado** e mantém o adiantamento e o
   comprovante.
3. **Given** um adiantamento salvo, **When** abro a tela, **Then** vejo claramente o valor
   adiantado e o link do comprovante no item.

---

### User Story 2 - Campo de valor com a máscara padrão de R$ (Priority: P1)

Como usuário, quero digitar o valor do adiantamento com a **mesma máscara** dos outros campos de
R$ do sistema, para manter o padrão.

**Acceptance Scenarios**:

1. **Given** o campo de adiantamento, **When** digito, **Then** ele se comporta como os demais
   campos de R$ (máscara padrão brasileira).

---

### Edge Cases

- **Salário já pago / "no banco"**: o adiantamento (se houver) continua preservado (esses já não
  eram regenerados).
- **Mudança do valor de salário vigente**: ao preservar um lançamento com adiantamento, mantém-se
  o adiantamento; a atualização de valor por regeneração não deve apagar o adiantamento.
- **Adiantamento removido (zerado)**: o lançamento volta a ser regenerável normalmente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Um adiantamento salvo MUST **persistir** após o recarregamento/regeneração da
  planilha de pagamentos do mês (não pode ser apagado pela rotina de regeneração).
- **FR-002**: Com adiantamento salvo, o valor a pagar do salário MUST exibir o **líquido**
  (salário − adiantamento), de forma estável entre recarregamentos.
- **FR-003**: O item de salário com adiantamento MUST mostrar o **valor adiantado** e o **link do
  comprovante**.
- **FR-004**: O campo de valor do adiantamento MUST usar a **máscara padrão de R$** do sistema
  (igual aos demais campos monetários).
- **FR-005**: A correção MUST preservar o comportamento de regeneração para salários **sem**
  adiantamento (continuam atualizando valor/frequência conforme o salário vigente).
- **FR-006**: A correção MUST manter as regras da 067 (comprovante obrigatório p/ adiantamento >
  0; não exceder o salário; custo de salário do balanço inalterado).

### Key Entities

- **Pagamento de salário (existente)**: tem valor, valor adiantado e comprovante. A regeneração
  mensal **não** pode descartar lançamentos que têm adiantamento.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Após salvar um adiantamento e recarregar a tela, o adiantamento persiste em 100% dos
  casos e o valor a pagar mostra o líquido.
- **SC-002**: O valor adiantado e o comprovante ficam visíveis no item.
- **SC-003**: O campo de valor usa a máscara padrão de R$.
- **SC-004**: Salários sem adiantamento continuam sendo regenerados normalmente (sem regressão).

## Assumptions

- A regeneração mensal de salários não pagos é intencional (atualiza valor/frequência); o ajuste
  é **excluir** dessa regeneração os lançamentos que possuem adiantamento, preservando-os.
- A máscara padrão é a já usada no sistema (estilo calculadora, feature 059) aplicada via a classe
  de input monetário.
- Não há mudança de modelo nem migration (as colunas de adiantamento já existem — feature 067).
