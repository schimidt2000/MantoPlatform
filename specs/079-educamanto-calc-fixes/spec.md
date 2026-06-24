# Feature Specification: Correções da calculadora EducaManto (tempo real, pessoas, com NF)

**Feature Branch**: `079-educamanto-calc-fixes`

**Created**: 2026-06-23

**Status**: Draft

**Input**: "Os valores não estão aparecendo em tempo real. O número de pessoas no transporte deve ser
igual ao número de catering da apresentação (quem vai na van). O acréscimo do vendedor no valor sem
nota fiscal apenas soma; e o valor com nota fiscal é calculado em cima do valor original + acréscimo."

## Contexto

Após as features 076–078, a calculadora do EducaManto ficou com três ajustes pendentes:

1. **Valores não atualizam em tempo real** — os cartões "Sem Nota Fiscal" e "Com Nota Fiscal" ficam
   em "—" mesmo com os dias preenchidos. (Causa: o cálculo quebrava por uma referência inexistente
   no script — `_brlSum`, que só existe em outra tela.)
2. **Pessoas no transporte** deveria ser **igual ao catering da apresentação** (a quantidade de
   pessoas que vão na van), não um número digitado à parte.
3. **Acréscimo do vendedor**: no **sem NF** ele apenas **soma**; o **com NF** deve ser calculado
   **sobre (valor original + acréscimo)** — e não somar o acréscimo depois do imposto.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Valores em tempo real (Priority: P1) 🎯 MVP

Como usuário do EducaManto, quero ver os valores (sem/com NF, custo, comissão) **atualizando na
hora** conforme mudo dias, ensemble, transporte ou acréscimo.

**Acceptance Scenarios**:

1. **Given** um pacote selecionado, **When** preencho/altero os dias, **Then** os cartões mostram os
   valores **imediatamente** (sem ficar em "—").
2. **Given** valores na tela, **When** mudo ensemble/acréscimo/transporte, **Then** os valores
   recalculam na hora.

### User Story 2 - Pessoas no transporte = catering da apresentação (Priority: P1)

Como usuário, quero que "Pessoas no transporte" seja **automaticamente** igual ao número de catering
da apresentação (quem vai na van), inclusive crescendo com o ensemble.

**Acceptance Scenarios**:

1. **Given** um pacote, **When** abro a calculadora, **Then** "Pessoas no transporte" mostra o
   headcount do catering da apresentação (somente leitura).
2. **Given** que adiciono ensemble, **When** recalcula, **Then** as pessoas no transporte aumentam
   junto com o catering da apresentação.

### User Story 3 - Acréscimo soma no sem NF; com NF sobre original + acréscimo (Priority: P1)

Como vendedor, quero que o acréscimo **apenas some** no valor sem NF, e que o valor com NF seja
calculado **em cima de (original + acréscimo)**.

**Acceptance Scenarios**:

1. **Given** um acréscimo de R$ X, **When** vejo o **sem NF**, **Then** ele é (valor original + X).
2. **Given** o mesmo acréscimo, **When** vejo o **com NF**, **Then** ele é (valor original + X)
   acrescido do imposto (gross-up), e **não** o com-NF original + X.
3. **Given** acréscimo zero, **When** vejo os valores, **Then** são os do pacote (sem mudança).

### Edge Cases

- Pacote sem item "Catering apresentação": pessoas no transporte ficam em 0 (sem erro).
- Transporte continua somado de forma plana aos dois valores (logística repassada, fora do gross-up).
- O PDF/geração usa os mesmos valores (com NF sobre original + acréscimo).

## Requirements *(mandatory)*

- **FR-001**: Os valores MUST atualizar em **tempo real** a cada mudança de dias/ensemble/transporte/
  acréscimo (sem travar o cálculo).
- **FR-002**: "Pessoas no transporte" MUST ser **igual ao headcount do catering da apresentação**
  (crescendo com o ensemble), exibido como **somente leitura**.
- **FR-003**: O acréscimo do vendedor MUST **somar** no valor **sem NF**.
- **FR-004**: O valor **com NF** MUST ser calculado **sobre (valor original + acréscimo)** (gross-up
  do imposto aplicado ao conjunto), não como (com-NF original) + acréscimo.
- **FR-005**: O transporte MUST continuar somado de forma plana aos dois valores (sem entrar no
  gross-up).
- **FR-006**: A geração do PDF MUST usar exatamente os mesmos valores da tela.

## Success Criteria *(mandatory)*

- **SC-001**: Com dias preenchidos, os cartões nunca ficam em "—" (valores aparecem na hora).
- **SC-002**: Pessoas no transporte = catering da apresentação (verificável no pacote).
- **SC-003**: sem NF = original + acréscimo; com NF = (original + acréscimo) com imposto; relação
  com/sem ≈ 1/0,84.
- **SC-004**: PDF reflete os mesmos valores.

## Assumptions

- "Catering da apresentação" é identificado pelo nome do item do pacote ("Catering apresentação").
- Transporte permanece como custo de logística somado plano (não sofre gross-up de NF).
- Apenas correções na calculadora do EducaManto; sem modelo, sem migration.
