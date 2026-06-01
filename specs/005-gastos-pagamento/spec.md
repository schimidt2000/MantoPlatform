# Feature Specification: Gastos — acesso restrito + entrada na lista de pagamentos

**Feature Branch**: `005-gastos-pagamento`

**Created**: 2026-05-30

**Status**: Draft

**Input**: User description: "Esse quadro deve ficar visível apenas para super admin. E faltou
uma coisa lógica: às vezes um funcionário fez o pagamento e precisa ser reembolsado; às vezes
o pagamento precisa ser feito diretamente ao fornecedor. Em ambos os casos, isso deve virar um
item na lista de pagamentos do painel financeiro."

## Contexto

A página de Gastos Especiais (feature 004) hoje é visível a qualquer colaborador. O usuário
pediu para restringir o acesso a super admin. Além disso, falta fechar o ciclo financeiro:
um gasto aprovado normalmente precisa de um **desembolso** — ou reembolsar o funcionário que
pagou do próprio bolso, ou pagar diretamente o fornecedor. Esse desembolso deve aparecer na
**lista de pagamentos** do painel financeiro, junto com cachês e salários.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Página de Gastos restrita a super admin (Priority: P1)

A página de Gastos Extras (e seu item de menu) passa a ser visível e acessível **apenas** para
super admin. Outros perfis não veem o menu nem conseguem abrir a página.

**Why this priority**: Pedido direto do usuário; envolve controle de acesso a dados financeiros.

**Independent Test**: Logar como super admin e ver/abrir a página; logar como outro perfil e
confirmar que o item some do menu e a página retorna acesso negado.

**Acceptance Scenarios**:

1. **Given** um super admin, **When** abre o sistema, **Then** vê o item "Gastos Extras" e
   consegue abrir a página.
2. **Given** um colaborador não super admin, **When** abre o sistema, **Then** NÃO vê o item de
   menu e, se tentar a URL direta, recebe acesso negado.

---

### User Story 2 - Definir o destino do desembolso ao registrar o gasto (Priority: P1)

Ao registrar um gasto, o super admin indica como o desembolso será feito:
- **Reembolso a funcionário**: escolhe qual funcionário será reembolsado; ou
- **Pagamento ao fornecedor**: informa o nome do fornecedor e a chave PIX (quando houver).

**Why this priority**: É a informação que permite ao financeiro saber para quem pagar.

**Independent Test**: Registrar um gasto escolhendo "reembolso" a um funcionário e outro como
"fornecedor" com PIX, e confirmar que cada um guarda corretamente o destinatário.

**Acceptance Scenarios**:

1. **Given** um novo gasto do tipo reembolso, **When** o super admin escolhe o funcionário e
   salva, **Then** o gasto fica associado àquele funcionário como destinatário do reembolso.
2. **Given** um novo gasto do tipo fornecedor, **When** informa nome e PIX do fornecedor e
   salva, **Then** o gasto guarda esses dados de pagamento.

---

### User Story 3 - Gasto aprovado vira item na lista de pagamentos (Priority: P1)

Quando um gasto é **aprovado**, ele passa a aparecer como um item na lista de pagamentos do
painel financeiro, no mês da data do gasto, ao lado de cachês e salários — com nome do
destinatário, valor (R$), chave PIX (quando houver) e um status de pagamento próprio
(não pago / pago / no banco), que o financeiro atualiza como nos demais itens.

**Why this priority**: É o coração do pedido — fechar o ciclo até o desembolso efetivo.

**Independent Test**: Aprovar um gasto com data no mês atual e confirmar que ele aparece na
lista de pagamentos do mês, com o destinatário correto, e que dá para marcar como "pago".

**Acceptance Scenarios**:

1. **Given** um gasto aprovado do tipo reembolso, **When** o financeiro abre a lista de
   pagamentos do mês da data do gasto, **Then** vê um item com o nome do funcionário, o valor e
   o PIX dele, com status inicial "não pago".
2. **Given** um gasto aprovado do tipo fornecedor, **When** o financeiro abre a lista, **Then**
   vê um item com o nome do fornecedor, o valor e o PIX informado.
3. **Given** um item de gasto na lista, **When** o financeiro marca como "pago", **Then** o
   status do desembolso daquele gasto é atualizado e refletido na página de gastos.
4. **Given** um gasto **pendente ou rejeitado**, **When** o financeiro abre a lista, **Then**
   ele NÃO aparece na lista de pagamentos.

---

### Edge Cases

- **Reembolso sem funcionário selecionado / fornecedor sem nome**: a interface exige o destino
  conforme o tipo escolhido; sem isso, não salva.
- **Gasto aprovado e depois excluído**: o item correspondente some da lista de pagamentos.
- **Funcionário sem PIX cadastrado**: o item aparece, mas sem PIX (igual aos demais itens sem PIX).
- **Status de pagamento do gasto** é independente do status de aprovação: aprovar ≠ pagar.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A página de Gastos Extras e seu item de menu MUST ser visíveis e acessíveis
  apenas para super admin; demais perfis recebem acesso negado na URL direta.
- **FR-002**: Ao registrar um gasto, o sistema MUST permitir escolher o tipo de desembolso:
  reembolso a um funcionário, ou pagamento a um fornecedor.
- **FR-003**: Para reembolso, o sistema MUST registrar qual funcionário será reembolsado; para
  fornecedor, MUST registrar o nome do fornecedor e, opcionalmente, a chave PIX.
- **FR-004**: Um gasto **aprovado** MUST aparecer como item na lista de pagamentos do painel
  financeiro, no mês correspondente à data do gasto.
- **FR-005**: O item de pagamento do gasto MUST exibir o nome do destinatário, o valor (R$) e a
  chave PIX quando houver.
- **FR-006**: O item de pagamento do gasto MUST ter status próprio (não pago / pago / no banco),
  atualizável pelo financeiro como os demais itens da lista.
- **FR-007**: Gastos com status pendente ou rejeitado NÃO MUST aparecer na lista de pagamentos.
- **FR-008**: Excluir um gasto aprovado MUST remover seu item da lista de pagamentos.
- **FR-009**: O status de pagamento do desembolso MUST ser independente do status de aprovação
  do gasto.

### Key Entities *(include if feature involves data)*

- **Gasto Especial** (já existe): ganha o **tipo de desembolso** (reembolso/fornecedor), o
  **funcionário a reembolsar** (quando reembolso), o **nome e PIX do fornecedor** (quando
  fornecedor) e um **status de pagamento** do desembolso.
- **Item de pagamento** (conceito já existente na lista do financeiro): passa a ter uma terceira
  origem além de cachê e salário — o **desembolso de gasto aprovado**.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos perfis não-super-admin não conseguem ver nem abrir a página de gastos.
- **SC-002**: Todo gasto aprovado com desembolso aparece na lista de pagamentos do mês correto,
  com destinatário e valor corretos.
- **SC-003**: O financeiro marca o desembolso de um gasto como "pago" em no máximo 1 clique,
  como faz com cachês e salários.
- **SC-004**: 0 gastos pendentes/rejeitados aparecem na lista de pagamentos.

## Assumptions

- "Esse quadro" = a página inteira de Gastos Extras (não apenas os cartões de totais).
- O destinatário do reembolso é um usuário do sistema (funcionário); o PIX usado é o cadastrado
  no perfil dele. O fornecedor não é cadastro — nome e PIX são digitados no próprio gasto.
- O desembolso entra na lista de pagamentos pelo mês da **data do gasto** (competência), igual
  ao critério do balanço (feature 004).
- O status de pagamento do desembolso reutiliza os mesmos estados dos demais itens
  (não pago / pago / no banco).
- A aprovação continua sendo exclusiva do super admin; o financeiro/super admin é quem marca o
  pagamento na lista (mesma permissão da lista de pagamentos atual).
