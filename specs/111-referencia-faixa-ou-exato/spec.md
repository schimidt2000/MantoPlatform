# Feature Specification: Conta Variável — Referência por Faixa ou Valor Exato

**Feature Branch**: `111-referencia-faixa-ou-exato`

**Created**: 2026-07-06

**Status**: Draft

**Input**: User description: "não necessariamente é de uma faixa esperada, eu posso querer escolher se é faixa ou valor exato"

## Contexto

Ajuste da feature 110 (gastos recorrentes): hoje a conta variável só aceita uma **faixa
esperada** (min–max) como referência. Há contas cujo valor esperado é um número único
conhecido (ex.: internet — sempre R$ 149,90, mas que ainda precisa de PIX/boleto todo mês,
diferente do débito automático). O financeiro deve escolher, ao cadastrar/editar a conta
variável, se a referência é uma **faixa** ou um **valor exato** — o resto do fluxo
(alerta na home, preencher, planilha de pagamentos) não muda.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Escolher faixa ou valor exato na conta variável (Priority: P1)

Ao cadastrar (ou editar) uma conta variável, o financeiro escolhe o tipo de referência:
"Faixa esperada" (min–max, como hoje) ou "Valor exato esperado" (um número). A referência
aparece na lista de contas e no alerta da home. Ao preencher a conta do mês com um valor
diferente do exato esperado (ou fora da faixa), o lançamento ganha o destaque "fora do
esperado" — apenas visual, como hoje.

**Independent Test**: cadastrar conta variável com valor exato esperado; ver a referência
na lista e no alerta; preencher com valor diferente → destaque; preencher com o valor
igual → sem destaque.

**Acceptance Scenarios**:

1. **Given** o formulário de conta variável, **When** o financeiro escolhe "Valor exato",
   **Then** informa um único valor e a conta é salva com essa referência.
2. **Given** uma conta variável com valor exato esperado, **When** listada ou alertada na
   home, **Then** mostra "esperado R$ X" (em vez de faixa).
3. **Given** o lançamento do mês preenchido com valor ≠ esperado, **Then** ganha o mesmo
   destaque visual de "fora do esperado" que a faixa usa hoje.
4. **Given** contas variáveis existentes com faixa, **Then** continuam funcionando
   exatamente como antes (sem tocar nos dados).
5. **Given** a edição de uma conta, **When** o financeiro troca entre faixa e valor exato,
   **Then** a nova referência vale para exibições/destaques futuros.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Conta variável DEVE aceitar referência em dois modos: faixa (min–max) OU
  valor exato — escolha do financeiro no cadastro/edição, podendo trocar depois.
- **FR-002**: A referência escolhida DEVE aparecer na lista de contas e nos alertas da home
  ("faixa R$ x – y" ou "esperado R$ x").
- **FR-003**: O destaque "fora do esperado" DEVE valer para os dois modos: fora da faixa,
  ou diferente do valor exato. Continua sendo apenas visual (não bloqueia).
- **FR-004**: Contas variáveis existentes (com faixa) NÃO PODEM mudar de comportamento;
  débito automático e assinaturas não são tocados.
- **FR-005**: A referência continua opcional (conta variável pode não ter faixa nem valor
  exato — sem destaque nesse caso).

### Key Entities

- **Gasto recorrente variável**: passa a ter referência em um de dois modos — faixa
  (min–max) ou valor exato esperado. Sem dado novo: o valor exato usa o mesmo campo de
  valor fixo já existente no cadastro (hoje não utilizado para variáveis).

## Success Criteria *(mandatory)*

- **SC-001**: Financeiro cadastra conta variável com valor exato em uma única tela, sem
  passos extras em relação à faixa.
- **SC-002**: 100% dos preenchimentos com valor diferente do exato esperado exibem o
  destaque "fora do esperado"; preenchimentos iguais não exibem.
- **SC-003**: Zero regressão nas contas variáveis com faixa e nos tipos fixos (verificação
  da 110 continua passando nos pontos equivalentes).

## Assumptions

- "Valor exato esperado" é referência, não trava: o preenchimento aceita qualquer valor
  (igual à faixa hoje) — a conta pode vir com juros/desconto.
- Sem migração: o modo é derivado dos campos preenchidos (valor exato usa o campo de valor
  já existente; faixa usa min–max). Preencher um modo limpa o outro.
