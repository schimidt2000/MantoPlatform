# Feature Specification: Cálculo de transporte no EducaManto (igual ao orçamento)

**Feature Branch**: `076-educamanto-transporte`

**Created**: 2026-06-23

**Status**: Draft

**Input**: "Na parte do EducaManto preciso de uma partezinha que funcione exatamente igual à parte de
transporte da calculadora de orçamento: coloca um endereço, ele calcula; seleciona carro ou van
(com/sem carretinha), quantas pessoas vão, calcula os adicionais por pessoa de transporte e soma
isso no valor final."

## Contexto

A calculadora de orçamento tem um bloco de transporte: digita-se um endereço → o sistema calcula a
distância (Google Maps) → escolhe-se **van** (com/sem carretinha) ou **carro** → informa-se o número
de pessoas → calcula o transporte (tarifa por km + **adicional por pessoa**) e soma ao total. O
EducaManto (orçamentos por pacote musical) não tem isso. O cliente quer o **mesmo** mecanismo no
EducaManto, somando o transporte ao **valor final**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Calcular transporte por endereço e somar ao valor final (Priority: P1) 🎯 MVP

Como usuário do EducaManto, quero digitar o endereço do evento e ter o transporte calculado e
somado ao valor final, escolhendo van/carro, carretinha e número de pessoas — igual ao orçamento.

**Independent Test**: No EducaManto, com um pacote e dias preenchidos, digitar um endereço →
"Calcular" mostra a distância; escolher van + carretinha + N pessoas → o valor de transporte aparece
e é **somado** ao valor final exibido.

**Acceptance Scenarios**:

1. **Given** um endereço, **When** clico em "Calcular distância", **Then** a distância (km) é obtida
   (mesmo cálculo do orçamento) e exibida.
2. **Given** a distância calculada, **When** escolho **van** (com/sem carretinha) ou **carro** e
   informo o número de pessoas, **Then** o transporte é calculado = tarifa por km + **adicional por
   pessoa**, exatamente como no orçamento.
3. **Given** o transporte calculado, **When** vejo o resultado, **Then** ele é **somado ao valor
   final** e aparece como uma linha clara de "Transporte".
4. **Given** nenhum endereço calculado (km = 0), **When** vejo o resultado, **Then** o transporte é
   **zero** e o valor final é o do pacote (comportamento atual, sem regressão).

### Edge Cases

- **Google Maps não configurado / endereço inválido**: mostra mensagem amigável; transporte fica 0.
- **Trocar tipo/carretinha/pessoas** depois de calcular a distância: recalcula o transporte sem
  precisar buscar a distância de novo.
- **Trocar de pacote ou dias**: o transporte calculado é mantido e re-somado ao novo valor.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O EducaManto MUST ter um bloco de transporte com **endereço + botão de calcular
  distância**, reutilizando o mesmo cálculo de distância do orçamento.
- **FR-002**: O usuário MUST poder escolher **van (com/sem carretinha)** ou **carro** e informar o
  **número de pessoas**.
- **FR-003**: O transporte MUST ser calculado com a **mesma fórmula** do orçamento: tarifa por km
  (ida e volta) conforme tipo/carretinha + **adicional por pessoa** (rateio por pessoa que viaja).
- **FR-004**: O valor de transporte MUST ser **somado ao valor final** do EducaManto e exibido como
  uma linha própria ("Transporte").
- **FR-005**: Sem endereço/distância (km = 0), o transporte MUST ser **zero** e o valor final
  permanece o do pacote (sem regressão).
- **FR-006**: As tarifas/divisores de transporte MUST vir da **mesma configuração** usada pelo
  orçamento (fonte única) — sem números mágicos novos.
- **FR-007**: O bloco MUST estar disponível para os mesmos perfis que já usam o EducaManto.

### Key Entities

- **Configuração de transporte (existente)**: tarifas van (com/sem carretinha), R$/km do carro e
  divisor do adicional por pessoa — reutilizada do orçamento.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: É possível calcular o transporte por endereço no EducaManto e vê-lo somado ao valor
  final, com o mesmo resultado que o orçamento produziria para os mesmos parâmetros.
- **SC-002**: Sem endereço, o valor final é idêntico ao atual (sem regressão).
- **SC-003**: Mudar tipo/carretinha/pessoas recalcula o transporte na hora (sem nova busca de
  distância).

## Assumptions

- "Adicional por pessoa" = adicional fora-SP por colaborador do orçamento (rateio por pessoa que
  viaja). O **adicional de show** do orçamento **não** se aplica aqui (EducaManto não tem o conceito
  de "show"); fica fora.
- O transporte é somado **como custo de logística repassado** ao valor final (não entra na margem
  nem no desconto do pacote). Exibido tanto em "sem nota" quanto em "com nota".
- Reutiliza a configuração de transporte e o cálculo de distância do orçamento (fonte única).
- Mudança de interface + reuso de cálculo; sem novo modelo, sem migration.
