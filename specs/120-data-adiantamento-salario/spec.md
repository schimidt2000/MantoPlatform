# Feature Specification: Data Customizável no Adiantamento de Salário

**Feature Branch**: `120-data-adiantamento-salario`

**Created**: 2026-07-08

**Status**: Draft

**Input**: User description: "Na tela dos adiantamentos eu preciso que a data possa ser customizada e se não mexer em nada, seja a data atual mesmo."

## Contexto

Na tela de Pagamentos (financeiro), ao lançar um adiantamento de salário, a data exibida
na lista de adiantamentos é sempre o momento exato em que o registro foi salvo no
sistema — não dá para informar que o adiantamento foi combinado ou pago em outro dia
(ex.: lançar hoje um adiantamento pago sexta-feira passada). O financeiro precisa poder
escolher a data; se não mexer em nada, deve continuar valendo a data de hoje, como já
acontece.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Lançar adiantamento com data escolhida (Priority: P1)

O financeiro abre o modal de adiantamentos de um salário, vê um campo de data já
preenchido com o dia de hoje, e pode trocar por outra data antes de salvar o
adiantamento. A data escolhida aparece na lista de adiantamentos daquele salário.

**Independent Test**: abrir o modal, trocar a data para um dia anterior, informar valor e
comprovante, salvar; conferir que a lista mostra a data escolhida (não a de hoje).

**Acceptance Scenarios**:

1. **Given** o modal de adiantamentos aberto, **When** o financeiro não mexe no campo de
   data, **Then** o adiantamento é salvo com a data de hoje (comportamento atual
   preservado).
2. **Given** o modal de adiantamentos aberto, **When** o financeiro escolhe uma data
   diferente (passada ou futura) e salva, **Then** o adiantamento é salvo com a data
   escolhida, e essa é a data exibida na lista.
3. **Given** um adiantamento já lançado com uma data, **When** a lista de adiantamentos é
   consultada novamente (reabrir o modal, recarregar a página), **Then** a data mostrada
   continua sendo a que foi escolhida no lançamento.

## Requirements *(mandatory)*

- **FR-001**: O formulário de lançar adiantamento DEVE ter um campo de data editável, cujo
  valor inicial é a data de hoje.
- **FR-002**: Se o campo de data não for alterado, o adiantamento DEVE ser salvo com a
  data de hoje (comportamento hoje implícito, agora explícito).
- **FR-003**: Se o campo de data for alterado, o adiantamento DEVE ser salvo com a data
  escolhida, não com o momento em que o registro foi gravado no sistema.
- **FR-004**: A lista de adiantamentos de um salário DEVE exibir a data escolhida em cada
  lançamento.
- **FR-005**: Se o campo de data vier vazio ou inválido no envio do formulário, o sistema
  DEVE assumir a data de hoje em vez de rejeitar o lançamento.

### Key Entities

- **Adiantamento de Salário (SalaryAdvance)**: ganha uma data própria, escolhida no
  lançamento — deixa de depender do instante em que o registro foi salvo.

## Success Criteria *(mandatory)*

- **SC-001**: Financeiro lança um adiantamento com data retroativa ou futura em um único
  passo, sem precisar de campo ou tela extra.
- **SC-002**: Nenhum adiantamento já lançado antes desta mudança perde ou exibe uma data
  incorreta.

## Assumptions

- Não há restrição de intervalo (não impede datas futuras nem datas muito antigas) — mesmo
  padrão de outros campos de data do financeiro (ex.: data de gasto extra), que também não
  restringem intervalo.
- Adiantamentos já lançados antes desta feature recebem, na migração, a data do próprio
  registro (o dia em que foram salvos) como valor inicial — não há como recuperar uma data
  "real" diferente que não foi capturada.
