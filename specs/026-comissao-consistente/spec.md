# Feature Specification: Comissão consistente entre as telas

**Feature Branch**: `026-comissao-consistente`

**Created**: 2026-06-04

**Status**: Draft

**Input**: User description: "As duas telas estão divergentes no cálculo da comissão. Precisa ser
consertado de forma consistente."

## Contexto

A comissão de um mesmo evento aparece com valores diferentes em telas distintas:
- **Aba comercial do evento**: calcula **ao vivo** com a taxa atual — ex.: venda R$ 2.745,00 ×
  2,5% = **R$ 68,63**.
- **Página de Comissões** (e, por tabela, o resumo nos Pagamentos): mostra o valor **gravado** no
  momento em que a comissão foi registrada — ex.: **R$ 54,90** (2.745 × 2%, a taxa **antiga**).

A causa: o valor da comissão a pagar foi "congelado" quando a taxa padrão ainda era 2%; ao corrigir
o padrão para 2,5%, o cálculo ao vivo mudou, mas o valor gravado das comissões **ainda não pagas**
não foi atualizado. O usuário quer que todas as telas mostrem o **mesmo** valor (o cálculo atual).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Mesmo valor de comissão em todas as telas (Priority: P1)

Para um evento ainda **não pago**, a comissão exibida na aba comercial, na página de Comissões e no
resumo dos Pagamentos é **idêntica** (a do cálculo atual).

**Acceptance Scenarios**:

1. **Given** um evento com comissão a pagar, **When** comparo a aba comercial e a página de
   Comissões, **Then** o valor da comissão é o mesmo.
2. **Given** a taxa padrão foi corrigida (2% → 2,5%), **When** abro a página de Comissões, **Then**
   as comissões **a pagar** refletem 2,5% (não o 2% antigo).
3. **Given** o resumo de comissões nos Pagamentos, **When** é exibido, **Then** bate com a página de
   Comissões e com a aba comercial.

---

### User Story 2 - Comissões já pagas não mudam (Priority: P1)

Comissões já marcadas como **pagas** mantêm o valor com que foram pagas (histórico), mesmo que a
taxa mude depois.

**Acceptance Scenarios**:

1. **Given** uma comissão já paga, **When** a taxa muda, **Then** o valor pago permanece o mesmo.

---

### Edge Cases

- **Vendedor que deixou de receber comissão / venda removida**: a comissão a pagar deixa de ser
  elegível e é tratada como hoje (sem valor a pagar), de forma consistente.
- **Estorno (valor negativo)**: não é recalculado pela taxa; permanece como está.
- **Taxa específica do evento** (definida pelo super admin): prevalece sobre a padrão, de forma
  consistente nas telas.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Para um mesmo evento **não pago**, o valor da comissão MUST ser idêntico na aba
  comercial, na página de Comissões e no resumo dos Pagamentos.
- **FR-002**: As comissões **a pagar** MUST refletir o cálculo atual (taxa do evento, ou a padrão
  vigente) — sem ficar presas a uma taxa antiga.
- **FR-003**: Comissões já **pagas** NÃO MUST ter o valor alterado por mudanças posteriores de taxa.
- **FR-004**: A reconciliação MUST acontecer automaticamente ao abrir as telas de Comissões e de
  Pagamentos (sem ação manual).
- **FR-005**: Regras de elegibilidade (vendedor recebe comissão; venda existente) e estornos MUST
  permanecer coerentes; estornos não são recalculados pela taxa.
- **FR-006**: Os totais (a pagar) MUST refletir os valores reconciliados.

### Key Entities *(include if feature involves data)*

- **Comissão (pagamento de comissão)** — já existe: o valor das comissões **a pagar** passa a
  acompanhar o cálculo atual do evento; as pagas são preservadas.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Para 100% dos eventos não pagos, o valor da comissão é igual nas três telas (diferença
  de R$ 0,00).
- **SC-002**: Após a correção da taxa, 100% das comissões a pagar exibem o valor com a taxa vigente.
- **SC-003**: 0 comissões já pagas têm o valor alterado por mudança posterior de taxa.

## Assumptions

- O valor "correto" é o do **cálculo atual** do evento (taxa do evento ou padrão vigente) — a mesma
  base já usada na aba comercial.
- A reconciliação vale para comissões **a pagar**; pagas são histórico e estornos não mudam.
- Sem mudança de banco — é uma reconciliação do valor já registrado com o cálculo atual.
