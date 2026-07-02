# Feature Specification: Corrigir acréscimos ausentes no orçamento final gerado

**Feature Branch**: `103-fix-acrescimo-orcamento-final`

**Created**: 2026-07-01

**Status**: Draft

**Input**: "Os valores adicionados como acréscimo não estão aparecendo no orçamento final. Por favor verifique o estado e o funcionamento desses acréscimos."

## Contexto

Na calculadora de orçamentos, ao **adicionar um acréscimo** (ex.: tipo "Outro", R$ 13.000), a **prévia**
de valores no rodapé da tela **soma o acréscimo** corretamente (ex.: 1h ≈ R$ 20.485). Porém, ao clicar em
**"Gerar Orçamento"**, a **mensagem final** (proposta para WhatsApp/PDF) apresenta valores **sem o
acréscimo** (ex.: 1h ≈ R$ 5.009). Ou seja, o acréscimo **some** na proposta gerada — é um **defeito**.

Causa observada: os campos do editor de acréscimos da calculadora existem apenas para o cálculo **na
tela** (prévia), mas **não são enviados** junto do formulário quando o orçamento é gerado. Assim, o
cálculo do **servidor** (que monta a mensagem/PDF) recebe a lista de acréscimos **vazia** e não os aplica.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Acréscimo aparece no orçamento final (Priority: P1) 🎯 MVP

Como vendedor, ao adicionar um ou mais acréscimos e gerar o orçamento, quero que os valores finais
(mensagem e PDF) **incluam os acréscimos** — iguais aos da prévia — para não enviar propostas com valor
errado.

**Why this priority**: É a correção do defeito; sem ela, propostas saem com valor a menor.

**Independent Test**: Montar um orçamento com um acréscimo (R$ e/ou %), conferir a prévia, gerar o
orçamento e verificar que os valores da mensagem final **batem** com a prévia (incluem o acréscimo).

**Acceptance Scenarios**:

1. **Given** um orçamento com um acréscimo em **R$** (ex.: R$ 13.000), **When** gero o orçamento, **Then**
   os valores da mensagem final **incluem** esse acréscimo (batem com a prévia).
2. **Given** um acréscimo em **%**, **When** gero o orçamento, **Then** o percentual é aplicado também na
   mensagem final (bate com a prévia).
3. **Given** **vários** acréscimos, **When** gero o orçamento, **Then** **todos** entram no valor final.
4. **Given** um acréscimo do tipo **BV**, **When** gero o orçamento, **Then** ele entra no **total** (sem
   ser rotulado ao cliente) e é transportado ao evento, como especificado.
5. **Given** **nenhum** acréscimo, **When** gero o orçamento, **Then** os valores finais permanecem os da
   base (sem regressão).

### Edge Cases

- **Reabrir orçamento do histórico**: os acréscimos reexibidos continuam sendo enviados/aplicados ao
  gerar de novo.
- **Acréscimo com valor vazio/zero**: é ignorado (não altera o total), como já ocorre.
- **Tipo "Outro" com descrição**: a descrição acompanha o acréscimo no snapshot, sem afetar o cálculo.

## Requirements *(mandatory)*

- **FR-001**: Ao gerar o orçamento, os acréscimos adicionados na calculadora MUST ser **enviados** e
  **aplicados** no cálculo do servidor, de modo que os valores finais **incluam** os acréscimos.
- **FR-002**: Os valores finais (mensagem e PDF) MUST **coincidir** com a prévia exibida na tela para o
  mesmo conjunto de acréscimos (R$ e %).
- **FR-003**: **Vários** acréscimos MUST ser todos aplicados; percentuais incidem sobre o total antes dos
  acréscimos (comportamento já especificado).
- **FR-004**: O comportamento do **BV** (entra no total, não rotulado ao cliente, transportado ao evento)
  MUST continuar válido no fluxo corrigido.
- **FR-005**: Orçamentos **sem** acréscimo MUST permanecer inalterados (sem regressão).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Para 100% dos orçamentos com acréscimo, os valores da mensagem final **batem** com a prévia
  (diferença zero).
- **SC-002**: Um acréscimo de R$ X aumenta cada valor de duração da mensagem final em **exatamente X**
  (quando em R$).
- **SC-003**: Nenhuma regressão: orçamentos sem acréscimo geram os mesmos valores de antes.

## Assumptions

- **Causa raiz**: os campos do editor de acréscimos da calculadora não têm identificação de envio de
  formulário, então não chegam ao servidor. A correção é garantir que esses campos sejam **enviados** com
  o formulário (os nomes que o servidor já espera).
- **Sem mudança de regra**: o cálculo (percentual sobre o total pré-acréscimos; BV embutido) já está
  especificado; a correção é apenas de **transmissão** dos dados ao servidor.
- **Escopo**: calculadora de orçamentos (`/orcamento`). O editor de acréscimos da **página do evento** já
  funciona e não é afetado.
