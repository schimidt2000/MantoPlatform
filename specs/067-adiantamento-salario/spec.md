# Feature Specification: Adiantamento de salário com comprovante (descontado do valor a pagar)

**Feature Branch**: `067-adiantamento-salario`

**Created**: 2026-06-20

**Status**: Draft

**Input**: User description: "Acontece muito de eu pagar uma parte do salário antecipadamente e isso precisar ser descontado no próximo salário. Quero, na própria parte de pagamentos, clicar em qualquer salário para editar, colocar quanto já paguei antecipadamente, obrigatoriamente anexar um print comprovando, e isso é descontado do valor que deve ser pago."

## Contexto

Na tela de **Pagamentos**, os salários aparecem como itens a pagar (por pessoa/data). É comum o
gestor adiantar uma parte do salário antes da data. Hoje não há como registrar esse adiantamento:
o item continua mostrando o valor cheio, e o controle vira manual.

O cliente quer poder **clicar em um salário e editar**, informando **quanto já foi pago
antecipadamente** e **anexando obrigatoriamente um comprovante** (print). O sistema então mostra
o **valor líquido a pagar** = salário − adiantamento.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar adiantamento com comprovante (Priority: P1) 🎯 MVP

Como financeiro, quero abrir um salário na tela de pagamentos e registrar o valor já adiantado,
anexando o comprovante, para que o valor a pagar passe a ser o líquido (salário − adiantamento).

**Why this priority**: É o pedido central e evita pagar duas vezes.

**Independent Test**: Abrir um salário, informar um valor de adiantamento + anexar um comprovante,
salvar; o item passa a mostrar o líquido (salário − adiantamento) e o comprovante fica acessível.

**Acceptance Scenarios**:

1. **Given** um salário de R$ 1.000 na lista, **When** registro adiantamento de R$ 300 com
   comprovante, **Then** o item passa a mostrar **R$ 700 a pagar** e indica o adiantamento.
2. **Given** o registro do adiantamento, **When** salvo, **Then** o comprovante anexado fica
   acessível a partir do item.
3. **Given** que tento registrar um adiantamento **sem** anexar comprovante, **When** salvo,
   **Then** a ação é **recusada** com mensagem clara (comprovante é obrigatório).

---

### User Story 2 - Editar/zerar o adiantamento (Priority: P2)

Como financeiro, quero corrigir ou zerar o adiantamento de um salário, para ajustar erros.

**Acceptance Scenarios**:

1. **Given** um salário com adiantamento, **When** altero o valor (com novo comprovante) e salvo,
   **Then** o líquido a pagar é recalculado.
2. **Given** um salário com adiantamento, **When** zero o adiantamento, **Then** o item volta a
   mostrar o valor cheio (e o comprovante deixa de ser exigido).

---

### Edge Cases

- **Adiantamento sem comprovante**: recusado (comprovante obrigatório quando o adiantamento é
  maior que zero).
- **Adiantamento maior que o salário**: recusado com mensagem (não pode passar do valor do
  salário).
- **Adiantamento zero/vazio**: permitido; item mostra o valor cheio e não exige comprovante.
- **Comprovante**: imagem ou PDF; tamanho limitado (padrão dos uploads do sistema).
- **Reflexo no balanço**: o adiantamento **não reduz o custo de salário** do período (o salário
  continua sendo o valor cheio); ele apenas reduz **o que falta pagar agora** (é caixa, não
  custo).
- **Permissão**: apenas o financeiro/admin (quem já acessa a tela de pagamentos) registra
  adiantamento.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Na tela de pagamentos, o usuário MUST conseguir abrir um **salário** para editar e
  registrar um **valor adiantado**.
- **FR-002**: Ao registrar um adiantamento maior que zero, o sistema MUST **exigir** o anexo de um
  comprovante; sem ele, a ação é recusada.
- **FR-003**: O **valor a pagar** do salário MUST passar a ser **salário − adiantamento** (valor
  líquido), exibido na lista.
- **FR-004**: O adiantamento MUST **não** poder exceder o valor do salário.
- **FR-005**: O comprovante anexado MUST ficar **acessível** a partir do item do salário.
- **FR-006**: O usuário MUST conseguir **alterar** ou **zerar** o adiantamento (zerar dispensa o
  comprovante e restaura o valor cheio).
- **FR-007**: O registro/edição de adiantamento MUST ser restrito a quem já tem acesso à tela de
  pagamentos (financeiro/admin) e MUST ser auditado.
- **FR-008**: O adiantamento MUST afetar apenas o **valor a pagar** (caixa); o **custo de salário**
  do período no balanço permanece o valor cheio.

### Key Entities

- **Pagamento de salário (existente)**: item a pagar por pessoa/data. Ganha um **valor adiantado**
  e um **comprovante** do adiantamento; o valor a pagar passa a ser o líquido.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: É possível registrar um adiantamento com comprovante e ver o valor líquido a pagar
  na lista, em poucos cliques.
- **SC-002**: 100% das tentativas de registrar adiantamento (>0) **sem** comprovante são
  recusadas.
- **SC-003**: 100% das tentativas de adiantamento maior que o salário são recusadas.
- **SC-004**: O custo de salário do período no balanço não muda por causa do adiantamento (só o
  valor a pagar muda).

## Assumptions

- O adiantamento é registrado **no próprio salário** que será pago (o "próximo salário" do qual se
  desconta) — editando o item na tela de pagamentos.
- Um salário tem **um** valor de adiantamento acumulado + **um** comprovante (substituível ao
  editar); não é um histórico de múltiplos adiantamentos.
- O comprovante segue o padrão de upload do sistema (imagem/PDF, limite de tamanho), guardado como
  os demais comprovantes de pagamento.
- "Editar qualquer salário" = abrir o item de salário na tela de pagamentos (não cria nova tela
  separada).
- Acesso e auditoria seguem o que já existe na tela de pagamentos (financeiro/admin).
