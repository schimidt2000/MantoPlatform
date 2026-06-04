# Feature Specification: Resumo de comissões nos Pagamentos (dia 5)

**Feature Branch**: `024-comissoes-pagamentos`

**Created**: 2026-06-04

**Status**: Draft

**Input**: User description: "No dia 5 de cada mês deve aparecer nos pagamentos uma somatória das
comissões dos eventos vendidos no mês anterior."

## Contexto

As comissões já são calculadas por evento (a partir da venda) e existe uma página de Comissões. Mas
no fluxo de **Pagamentos** (onde o financeiro paga cachês, salários e gastos), as comissões não
aparecem. Como as comissões de um mês são pagas no **dia 5 do mês seguinte**, o usuário quer que, na
lista de Pagamentos, apareça — **datada no dia 5** — a **somatória das comissões por vendedor** dos
**eventos vendidos no mês anterior**, podendo marcar como paga ali mesmo (sincronizando com a página
de Comissões).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver as comissões a pagar no dia 5 (Priority: P1)

Na página de Pagamentos, ao ver o mês corrente, aparece uma linha **por vendedor** com a soma das
comissões dos eventos vendidos no **mês anterior**, datada no **dia 5**, junto com os demais
pagamentos.

**Acceptance Scenarios**:

1. **Given** eventos vendidos no mês anterior com comissão, **When** abro Pagamentos do mês atual,
   **Then** vejo uma linha por vendedor com a soma das comissões, datada no dia 5, com nome e PIX.
2. **Given** que ainda não chegou o dia 5, **When** vejo a lista, **Then** a linha aparece marcada
   como "futuro" (a vencer), como os outros itens datados à frente.
3. **Given** um vendedor sem comissões no mês anterior, **When** vejo a lista, **Then** não há linha
   de comissão para ele.

---

### User Story 2 - Marcar a comissão como paga (Priority: P1)

Na própria linha de comissão dos Pagamentos, o financeiro pode marcar como paga; isso passa as
comissões daquele vendedor/período para "pago" — refletindo na página de Comissões (uma só fonte de
verdade, sem pagar em dobro).

**Acceptance Scenarios**:

1. **Given** uma linha de comissão a pagar, **When** marco como paga, **Then** as comissões daquele
   vendedor referentes àquele período passam a "pago".
2. **Given** que marquei como paga, **When** abro a página de Comissões, **Then** elas aparecem como
   pagas (consistente).
3. **Given** uma linha marcada como paga, **When** desfaço para "não pago", **Then** as comissões
   daquele vendedor/período voltam a "a pagar".

---

### Edge Cases

- **Sem comissões no mês anterior**: nenhuma linha de comissão é exibida.
- **Comissão já paga**: a linha aparece como "pago" (não entra no total a pagar).
- **Estorno (valor negativo) no período**: reduz a soma do vendedor; se a soma der zero, a linha não
  aparece.
- **Eventos sem data de venda**: não entram nesse resumo (o resumo é dos "vendidos no mês anterior").

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A página de Pagamentos MUST exibir, para o mês visualizado, uma linha **por vendedor**
  com a **soma das comissões** dos eventos **vendidos no mês anterior**, datada no **dia 5**.
- **FR-002**: A linha de comissão MUST mostrar nome do vendedor, valor total e a chave PIX dele.
- **FR-003**: Antes do dia 5, a linha MUST aparecer como item futuro (a vencer), como os demais.
- **FR-004**: O financeiro MUST poder marcar a linha de comissão como paga (e desfazer); isso MUST
  atualizar o status das comissões daquele vendedor/período de forma consistente com a página de
  Comissões.
- **FR-005**: A soma MUST considerar comissões elegíveis (a pagar/pago) e descontar estornos do
  período; somas zeradas NÃO MUST gerar linha.
- **FR-006**: O resumo MUST entrar nos totais da página de Pagamentos como os demais itens.
- **FR-007**: Não MUST haver duplicação de pagamento: marcar pago nos Pagamentos e na página de
  Comissões refletem o mesmo estado.

### Key Entities *(include if feature involves data)*

- **Comissão (pagamento de comissão)** — já existe: passa a ser **resumida por vendedor/período** na
  tela de Pagamentos; sem mudança de estrutura.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos vendedores com comissão no mês anterior aparecem com uma linha (datada no dia
  5) na página de Pagamentos do mês atual.
- **SC-002**: O valor de cada linha é igual à soma das comissões daquele vendedor no mês anterior
  (diferença de R$ 0,00).
- **SC-003**: Marcar pago nos Pagamentos reflete 100% na página de Comissões (e vice-versa).
- **SC-004**: 0 linhas de comissão com soma zero.

## Assumptions

- "Mês anterior" = comissões cujos eventos têm **data de venda** no mês anterior ao mês visualizado.
- "No dia 5" = a linha é datada no dia 5 do mês visualizado (aparece como futura até lá, como os
  outros itens).
- Granularidade **por vendedor** e linha **acionável** (marca pago), sincronizando com a página de
  Comissões (decisões confirmadas com o usuário).
- Sem mudança de banco: o resumo é derivado das comissões já registradas.
