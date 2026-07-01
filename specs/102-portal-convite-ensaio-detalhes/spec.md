# Feature Specification: Convite do portal — detalhes de evento e ensaio bem organizados

**Feature Branch**: `102-portal-convite-ensaio-detalhes`

**Created**: 2026-07-01

**Status**: Draft

**Input**: "No convite que aparece no portal já aparecem os horários dos vários ensaios, se houver? Está faltando o horário do fim do ensaio. Vale especificar: Data do evento, Horário do evento, Local do evento (mostrando o endereço completo). E no ensaio, organizar melhor: Data do ensaio, horário do ensaio e local do ensaio. Pra ficar bem claro para as pessoas conseguirem visualizar bem."

## Contexto

No **portal do artista**, o cartão de **convite pendente** (e os cartões de **próximos eventos**) mostra
os dados do evento e dos ensaios. Hoje:

- Os dados do **evento** aparecem rotulados (Data, Horário, Local), mas os rótulos podem ser mais claros
  e o **Local** deve mostrar o **endereço completo** do evento.
- O **ensaio** aparece de forma **apertada** (data, hora e local numa linha só) e **falta o horário de
  término** — só mostra o início. Quando há **vários ensaios**, todos aparecem, mas sem organização
  clara.

O objetivo é deixar o convite **bem claro e legível**, separando com rótulos: **Data do evento /
Horário do evento / Local do evento** e, para cada ensaio, **Data do ensaio / Horário do ensaio (com
início e fim) / Local do ensaio**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver o horário de início e fim do ensaio (Priority: P1) 🎯 MVP

Como artista, quero ver **o horário de início e de fim** de cada ensaio no convite, para saber quanto
tempo o ensaio dura.

**Why this priority**: É a lacuna concreta — o fim do ensaio já existe, mas não é exibido.

**Independent Test**: Abrir um convite de um evento com ensaio (que tem início e fim) e ver o horário
como "início – fim".

**Acceptance Scenarios**:

1. **Given** um convite com um ensaio que tem início e fim, **When** vejo o cartão, **Then** o horário do
   ensaio mostra **início – fim** (ex.: "08:30 – 10:30").
2. **Given** um ensaio sem horário de fim, **When** vejo o cartão, **Then** mostra só o início (sem
   travar).

### User Story 2 - Ensaio organizado em Data / Horário / Local (Priority: P1)

Como artista, quero que cada ensaio apareça **organizado em linhas rotuladas** (Data do ensaio, Horário
do ensaio, Local do ensaio), para entender rápido, em vez de tudo numa linha só.

**Why this priority**: Clareza visual é o cerne do pedido.

**Independent Test**: Abrir um convite com ensaio e ver linhas separadas e rotuladas para data, horário
e local do ensaio.

**Acceptance Scenarios**:

1. **Given** um ensaio, **When** vejo o cartão, **Then** vejo linhas rotuladas: **Data do ensaio**,
   **Horário do ensaio** (início – fim) e **Local do ensaio**.
2. **Given** um ensaio **sem local**, **When** vejo o cartão, **Then** a linha de local do ensaio é
   omitida (sem rótulo vazio).
3. **Given** um ensaio com **observação/materiais**, **When** vejo o cartão, **Then** eles continuam
   aparecendo, abaixo dos dados do ensaio.
4. **Given** **vários ensaios**, **When** vejo o cartão, **Then** cada um aparece como um bloco próprio,
   claramente separado dos demais.

### User Story 3 - Evento com Data / Horário / Local (endereço completo) claros (Priority: P2)

Como artista, quero ver o **evento** com rótulos claros — **Data do evento**, **Horário do evento** e
**Local do evento** com o **endereço completo** — para não confundir com os dados do ensaio.

**Why this priority**: Complementa a clareza; os dados do evento já existem, só melhora rótulo/exibição.

**Independent Test**: Abrir um convite e ver as linhas do evento rotuladas como "do evento" e o Local
exibindo o endereço como cadastrado, sem corte.

**Acceptance Scenarios**:

1. **Given** um convite, **When** vejo o cartão, **Then** as linhas do evento aparecem rotuladas como
   **Data do evento**, **Horário do evento** e **Local do evento**.
2. **Given** o evento com um endereço cadastrado, **When** vejo o Local do evento, **Then** ele mostra o
   **endereço completo** como cadastrado (sem truncar).
3. **Given** que os rótulos deixam claro "do evento" vs "do ensaio", **When** há evento e ensaio no mesmo
   cartão, **Then** não há confusão entre os dois locais/horários.

### Edge Cases

- **Sem ensaio**: o cartão mostra só os dados do evento (nenhum bloco de ensaio).
- **Ensaio sem fim**: mostra só o início.
- **Ensaio sem local**: omite a linha de local do ensaio.
- **Vários ensaios**: todos aparecem, cada um num bloco separado e legível.
- **Local do evento vazio**: omite a linha de Local do evento.
- **Consistência**: a melhoria de exibição do ensaio (com fim) vale também para os cartões de **próximos
  eventos**, não só para o convite pendente.

## Requirements *(mandatory)*

- **FR-001**: O convite MUST exibir o **horário de fim** do ensaio junto do início (início – fim) quando
  houver fim; quando não houver, exibir só o início.
- **FR-002**: Cada ensaio MUST ser exibido em **linhas rotuladas**: **Data do ensaio**, **Horário do
  ensaio** (início – fim) e **Local do ensaio**.
- **FR-003**: A linha de **Local do ensaio** MUST ser **omitida** quando o ensaio não tiver local.
- **FR-004**: As observações e materiais do ensaio MUST continuar aparecendo, abaixo dos dados do ensaio.
- **FR-005**: **Vários ensaios** MUST aparecer, cada um em um **bloco próprio** claramente separado.
- **FR-006**: As linhas do **evento** MUST ser rotuladas como **Data do evento**, **Horário do evento** e
  **Local do evento**.
- **FR-007**: O **Local do evento** MUST exibir o **endereço completo** como cadastrado no evento, sem
  truncar; quando vazio, a linha é omitida.
- **FR-008**: A exibição do ensaio com **início – fim** MUST valer também para os cartões de **próximos
  eventos** (consistência), não só para o convite pendente.

## Key Entities *(include if feature involves data)*

- **Convite/Vaga** (existente): exibido no portal; referencia um **Evento** e o **artista**.
- **Evento** (existente): fornece **data**, **horário (início–fim)** e **local (endereço)** exibidos.
- **Ensaio** (existente, um Evento do tipo ENSAIO vinculado): fornece **data**, **horário (início e
  fim, ambos já armazenados)**, **local**, além de observação e materiais. A novidade é **exibir o fim**
  e **organizar** os campos com rótulos.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos ensaios com horário de fim exibem **início – fim** no convite (e nos próximos
  eventos).
- **SC-002**: Cada ensaio aparece com as três linhas rotuladas (data, horário, local) — local omitido
  quando ausente.
- **SC-003**: As linhas do evento aparecem rotuladas como "do evento" e o Local mostra o endereço
  completo cadastrado.
- **SC-004**: Com vários ensaios, o artista distingue cada bloco sem ambiguidade (100% separados).

## Assumptions

- **Endereço completo do evento** = o valor do campo de **local do evento** como cadastrado. Não há um
  campo separado de "endereço completo": para mostrar o endereço inteiro, ele deve estar no local do
  evento. (A observação "Evento em: …" que às vezes aparece na descrição do ensaio é um texto digitado à
  mão pela equipe de ensaio e continua sendo exibida como observação do ensaio.)
- **Horário de fim do ensaio** já é armazenado (o ensaio tem início e fim); a mudança é **exibir** o fim.
- **Escopo = portal do artista** (cartões de convite pendente e de próximos eventos). Nenhuma mudança de
  modelo/dados é necessária — é reorganização de exibição.
- **Sem alteração** no fluxo de aceitar/recusar convite nem nas demais seções do portal.
