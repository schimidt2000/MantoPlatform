# Feature Specification: Corrigir salário desatualizado nos Pagamentos

**Feature Branch**: `025-fix-salario-pagamentos`

**Created**: 2026-06-04

**Status**: Draft

**Input**: User description: "Fix na integração de pegar os salários e colocar nos pagamentos.
Atualizei o salário de várias pessoas, mas a página de pagamentos ainda mostra o salário antigo."

## Contexto

Os pagamentos de salário do mês são gerados a partir do salário vigente de cada pessoa. Hoje, esses
registros são criados **uma vez** e nunca atualizados: se o salário muda depois, a página de
Pagamentos continua mostrando o **valor antigo** (ex.: João aparece R$ 8.000 nos Pagamentos, mas o
salário atual dele é R$ 4.000). O usuário precisa que a lista de Pagamentos **reflita o salário
atual** das pessoas para os pagamentos ainda **não realizados**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pagamentos refletem o salário atualizado (Priority: P1)

Ao atualizar o salário de uma pessoa, os pagamentos de salário **ainda não pagos** do mês passam a
mostrar o **valor novo**.

**Acceptance Scenarios**:

1. **Given** um pagamento de salário do mês ainda não pago, **When** o salário da pessoa é
   atualizado, **Then** ao abrir os Pagamentos a linha mostra o novo valor.
2. **Given** vários salários atualizados, **When** o financeiro abre os Pagamentos, **Then** todas
   as linhas não pagas refletem os valores atuais (não os antigos).

---

### User Story 2 - Pagamentos já realizados não mudam (Priority: P1)

Pagamentos de salário que já foram marcados como **pagos** (ou "no banco") **não** são alterados —
eles registram o que de fato foi pago.

**Acceptance Scenarios**:

1. **Given** um pagamento de salário já marcado como pago, **When** o salário é atualizado depois,
   **Then** aquele pagamento pago mantém o valor com que foi pago.

---

### User Story 3 - Mudança de frequência/condição (Priority: P2)

Se a frequência de pagamento muda (ex.: de quinzenal para semanal) ou a pessoa passa a receber só
comissão, os pagamentos **não pagos** do mês se ajustam ao novo cenário, sem deixar lançamentos
antigos pendurados.

**Acceptance Scenarios**:

1. **Given** uma pessoa que era quinzenal e passou a semanal, **When** os Pagamentos são abertos,
   **Then** as datas/lançamentos não pagos refletem a nova frequência (sem datas antigas órfãs).
2. **Given** uma pessoa que passou a receber só comissão, **When** os Pagamentos são abertos,
   **Then** ela não tem mais lançamentos de salário não pagos no mês.

---

### Edge Cases

- **Pagamento parcialmente processado** ("no banco"): preservado como está (não regenerado).
- **Salário reduzido/aumentado**: o valor não pago passa a refletir o atual, para mais ou para menos.
- **Observação manual em um lançamento não pago**: pode ser perdida ao regenerar (lançamentos não
  pagos são recompostos do salário vigente).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Os pagamentos de salário **não pagos** do mês MUST refletir o **salário vigente** atual
  de cada pessoa (valor e frequência), mesmo que o salário tenha sido alterado depois de gerados.
- **FR-002**: Pagamentos de salário já **pagos** (ou "no banco") NÃO MUST ser alterados.
- **FR-003**: Mudança de frequência (semanal/quinzenal) MUST ajustar os lançamentos não pagos do mês
  (sem deixar datas antigas órfãs nem duplicar).
- **FR-004**: Pessoa que passa a receber **só comissão** (ou sem salário vigente) NÃO MUST ter
  lançamentos de salário não pagos no mês.
- **FR-005**: A correção MUST acontecer automaticamente ao abrir a página de Pagamentos (sem ação
  manual extra).
- **FR-006**: Os totais e demais itens da página de Pagamentos MUST permanecer corretos.

### Key Entities *(include if feature involves data)*

- **Pagamento de salário** (já existe): lançamentos não pagos do mês passam a ser **recompostos** a
  partir do salário vigente; os pagos são preservados.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos pagamentos de salário não pagos do mês exibem o valor do salário atual.
- **SC-002**: 0 pagamentos já pagos têm o valor alterado por uma mudança posterior de salário.
- **SC-003**: 0 lançamentos órfãos após mudança de frequência; 0 duplicados.
- **SC-004**: A correção aparece sem nenhuma ação manual além de abrir a página.

## Assumptions

- "Pagamento antigo" = lançamento de salário gerado com um valor que ficou desatualizado.
- A recomposição vale para o mês visualizado e para lançamentos **não pagos**; pagos são histórico.
- Sem mudança de banco — é uma correção na geração dos pagamentos de salário.
