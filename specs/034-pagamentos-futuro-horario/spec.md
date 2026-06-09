# Feature Specification: "Futuro" pelo horário de término do evento (Pagamentos)

**Feature Branch**: `034-pagamentos-futuro-horario`

**Created**: 2026-06-09

**Status**: Draft

**Input**: User description: "nessa planilha também é importante que eventos que ainda não aconteceram
(horário) apareçam como futuro. Leve sempre em consideração o horário de término do evento. E sempre
padronizando em horário de Brasília, como sempre."

## Contexto

Na Planilha de Pagamentos, cada cachê de evento é classificado como **Futuro** (ainda vai acontecer)
ou **Pendente** (já deveria estar pago). Hoje essa classificação olha apenas a **data de início** do
evento comparada com **a data de hoje** — ignora o **horário** e usa o fuso do servidor.

Isso causa erros:
- Um evento **mais tarde hoje** (ainda não aconteceu) aparece como **Pendente**, não como Futuro.
- Um evento que **já terminou hoje** aparece igual a um que ainda vai começar.
- Perto da meia-noite, o fuso do servidor (não-Brasília) pode classificar errado.

Correção pedida: um cachê de evento é **Futuro** enquanto o evento **ainda não terminou**, levando em
conta o **horário de término** do evento, sempre no **horário de Brasília**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Evento que ainda não terminou é "Futuro" (Priority: P1)

Um cachê de um evento cujo **horário de término** ainda não passou aparece como **Futuro**; depois que
o evento termina, passa a contar como **Pendente** (se não pago).

**Why this priority**: É a correção pedida — separar corretamente o que ainda vai acontecer do que já
deveria ser pago.

**Independent Test**: Um evento que termina daqui a algumas horas (hoje) aparece como Futuro; um que
terminou há algumas horas aparece como Pendente.

**Acceptance Scenarios**:

1. **Given** um cachê de evento cujo término é depois de agora (Brasília), **When** abro a planilha,
   **Then** ele aparece como **Futuro** e soma no card "Futuro".
2. **Given** um cachê de evento cujo término já passou (Brasília) e não está pago, **When** abro a
   planilha, **Then** ele aparece como **Pendente** e soma no card "Pendentes".
3. **Given** um evento mais tarde **hoje** que ainda não terminou, **When** abro a planilha, **Then**
   ele é **Futuro** (não Pendente).

---

### User Story 2 - Sempre no horário de Brasília (Priority: P1)

A definição de "agora" para decidir Futuro vs Pendente usa **sempre o horário de Brasília**,
independentemente do fuso do servidor.

**Why this priority**: Garante consistência (o resto do sistema já padroniza Brasília) e evita erro
perto da virada do dia.

**Acceptance Scenarios**:

1. **Given** o servidor em outro fuso, **When** a planilha classifica Futuro/Pendente, **Then** o
   corte usa o horário de Brasília.

---

### Edge Cases

- **Evento sem horário de término**: usa o horário de início como referência; se também não houver,
  não é tratado como futuro.
- **Salários, desembolsos de gastos e comissões**: não são eventos com horário — continuam usando a
  data de vencimento/pagamento como hoje (fora do escopo da regra de "horário de término").
- **Exatamente no horário de término**: ao atingir o término, deixa de ser Futuro.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Um cachê de evento MUST ser classificado como **Futuro** enquanto o **horário de
  término** do evento ainda não tiver passado.
- **FR-002**: A comparação MUST usar o **horário de término** do evento (não a data de início) e,
  quando não houver término, o horário de início como reserva.
- **FR-003**: O "agora" usado na comparação MUST ser o **horário de Brasília**, independentemente do
  fuso do servidor.
- **FR-004**: Os cards "Futuro" e "Pendentes" MUST refletir essa classificação (um item não pago e
  ainda não terminado conta em Futuro; já terminado conta em Pendentes).
- **FR-005**: Itens que não são eventos (salário, desembolso de gasto, comissão) MUST manter a
  classificação atual por data de vencimento (não afetados por esta regra).

### Key Entities

- **Cachê de evento (EventRole + evento)** — sua classificação Futuro/Pendente passa a depender do
  horário de término do evento, em Brasília. Sem novos dados; usa o horário de término já existente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos cachês de eventos ainda não terminados (por horário, Brasília) aparecem como
  Futuro.
- **SC-002**: 100% dos cachês de eventos já terminados (e não pagos) aparecem como Pendentes.
- **SC-003**: A classificação é estável e correta na virada do dia (sem erro de fuso) em 100% dos
  casos.
- **SC-004**: Salário/gasto/comissão mantêm a classificação por data de vencimento (0 regressões).

## Assumptions

- Os horários dos eventos já são guardados em horário de Brasília (padrão do sistema).
- "Término já passou" inclui o exato instante do término (ao terminar, deixa de ser futuro).
- Sem mudança de banco — usa o horário de término já existente nos eventos.
