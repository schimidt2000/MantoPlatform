# Feature Specification: Personagens já na agenda no dia (calculadora de orçamento)

**Feature Branch**: `061-personagens-agenda-no-dia`

**Created**: 2026-06-18

**Status**: Draft

**Input**: User description: "Na calculadora de orçamentos, quando o vendedor colocar a data do evento, preciso que apareça para ele quais personagens já estão na agenda nesse dia. Para não ter perigo de vender duplicado. Ao colocar a data, aparece logo embaixo os personagens envolvidos em eventos no dia. Precisa ficar de uma forma clara e corriqueira. Fácil de entender quais personagens ele não pode vender no dia."

## Contexto

O vendedor monta o orçamento na calculadora e informa a **data do evento**. Hoje ele não tem
visibilidade, ali na hora, dos personagens que **já estão comprometidos** em outros eventos
naquele mesmo dia — o que abre risco de **vender o mesmo personagem em dois lugares no mesmo
dia** (venda duplicada).

A ideia é: assim que a data é informada, mostrar **logo abaixo** do campo de data a lista de
personagens já agendados naquele dia, de forma clara e direta, para o vendedor saber de cara o
que **não pode** vender.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver personagens já agendados ao escolher a data (Priority: P1) 🎯 MVP

Como vendedor, quero que, ao informar a data do evento na calculadora, apareça logo abaixo a
lista dos personagens já comprometidos em eventos naquele dia, para eu não vender um personagem
que já está alocado e evitar venda duplicada.

**Why this priority**: É o pedido central e o que previne o prejuízo (venda duplicada).

**Independent Test**: Escolher na calculadora uma data que tenha eventos com personagens
escalados e conferir que esses personagens aparecem listados logo abaixo do campo de data.

**Acceptance Scenarios**:

1. **Given** uma data com eventos que têm personagens escalados, **When** o vendedor informa
   essa data, **Then** aparece, logo abaixo do campo, a lista dos personagens daquele dia.
2. **Given** uma data **sem** eventos (ou sem personagens), **When** o vendedor a informa,
   **Then** aparece uma mensagem clara de que **não há personagens agendados** nesse dia.
3. **Given** uma data já preenchida, **When** o vendedor **troca** para outra data, **Then** a
   lista se atualiza para a nova data.
4. **Given** o mesmo personagem escalado em mais de um evento no dia, **When** a lista é
   exibida, **Then** ele aparece de forma não repetitiva (uma entrada por personagem).

---

### User Story 2 - Entender o contexto de cada personagem (Priority: P2)

Como vendedor, quero ver junto de cada personagem em qual evento/show ele está naquele dia, para
entender o contexto e confirmar o conflito com segurança.

**Why this priority**: Aumenta a clareza ("de uma forma fácil de entender"), mas o MVP já
entrega o valor central (a lista de nomes).

**Acceptance Scenarios**:

1. **Given** a lista de personagens do dia, **When** exibida, **Then** cada personagem mostra
   também o evento (título) em que está agendado.

---

### Edge Cases

- **Data sem eventos**: mensagem clara de "nenhum personagem agendado neste dia" (estado vazio).
- **Data limpa/inválida**: a lista some (nada a mostrar).
- **Eventos de ensaio**: não entram (não têm personagens vendáveis).
- **Papéis de apoio** (Coordenador, Técnico de Som, Presença, Maquiador): **não** são
  personagens vendáveis e **não** devem aparecer na lista.
- **Vaga sem talento**: o personagem escalado conta como "na agenda" mesmo que ainda não tenha
  talento atribuído (a vaga já está comprometida para aquele dia).
- **Falha ao consultar**: não quebrar o orçamento; no máximo, não exibir a lista.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Ao informar/alterar a **data do evento** na calculadora de orçamento, o sistema
  MUST exibir, logo abaixo do campo de data, os **personagens já agendados** naquele dia.
- **FR-002**: A lista MUST conter apenas **personagens vendáveis** — excluindo papéis de apoio
  (Coordenador, Técnico de Som, Presença, Maquiador) e eventos de ensaio.
- **FR-003**: Cada personagem MUST aparecer **uma única vez** no dia (sem repetição), mesmo que
  esteja em mais de um evento.
- **FR-004**: Quando **não houver** personagens agendados no dia, o sistema MUST mostrar uma
  mensagem clara de estado vazio (ex.: "Nenhum personagem agendado neste dia").
- **FR-005**: Ao trocar a data, a lista MUST se atualizar para a nova data; ao limpar a data,
  MUST sumir.
- **FR-006**: A informação MUST ser apresentada de forma clara e direta, deixando evidente que
  são os personagens que o vendedor **não pode vender** naquele dia.
- **FR-007**: A exibição MUST estar disponível para os usuários que usam a calculadora de
  orçamento (vendas/comercial e admin).
- **FR-008**: A lista SHOULD indicar, junto de cada personagem, o evento (título) em que está
  agendado naquele dia (contexto).

### Key Entities

- **Evento (existente)**: tem data e título. Eventos do dia escolhido são a base da consulta.
- **Personagem escalado (existente)**: papel de personagem associado a um evento (com ou sem
  talento atribuído). É o que define "personagem na agenda no dia".

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Ao escolher uma data com personagens agendados, 100% desses personagens
  (vendáveis, sem repetição) aparecem logo abaixo do campo de data.
- **SC-002**: A lista aparece/atualiza em até ~1 segundo após informar/alterar a data.
- **SC-003**: Papéis de apoio e ensaios nunca aparecem na lista (0 ocorrências).
- **SC-004**: Em datas sem agenda, o vendedor vê uma mensagem clara de "nenhum personagem",
  sem ambiguidade.

## Assumptions

- "Personagens na agenda" = os papéis de **personagem** escalados em eventos cuja data coincide
  com a data informada (independe de já ter talento atribuído — a vaga já está comprometida).
- Papéis de apoio (Coordenador, Técnico de Som, Presença, Maquiador) e eventos de ensaio não são
  personagens vendáveis e ficam fora.
- A lista é **informativa** (alerta de conflito); não bloqueia o orçamento — a decisão é do
  vendedor.
- A comparação de "mesmo dia" usa a data do evento (dia de calendário), ignorando horário.
- O acesso segue o mesmo da calculadora de orçamento (comercial/vendas e admin).
