# Feature Specification: Local do ensaio e da maquiagem no portal e na mensagem copiada

**Feature Branch**: `093-local-ensaio-maquiagem`

**Created**: 2026-06-29

**Status**: Draft

**Input**: "Preciso que tanto no portal quanto na mensagem copiada apareça para a pessoa o local do ensaio e/ou maquiagem, ambos apenas se existirem"

## Contexto

Quando o artista é escalado para um evento, ele recebe duas formas de comunicação dos detalhes:

1. **Mensagem de convite copiada** — o casting clica em "Copiar convite" na página do evento e
   cola a mensagem no WhatsApp do artista. A mensagem traz evento, personagem, data, horário, local
   do evento, cachê, bloco de **Maquiagem** e bloco de **Ensaio**.
2. **Portal do artista** — o artista vê seus convites pendentes e próximos eventos, com os blocos de
   **Maquiagem** e **Ensaio**.

Hoje há uma inconsistência: o **local da maquiagem** aparece na mensagem copiada e no portal, mas o
**local do ensaio** aparece apenas no portal — **não** é incluído na mensagem de convite copiada. O
artista que recebe só a mensagem fica sem saber onde será o ensaio.

O pedido é garantir que **o local do ensaio e o local da maquiagem** apareçam **tanto no portal quanto
na mensagem copiada**, cada um exibido **apenas quando estiver preenchido** (sem linhas vazias ou
rótulos órfãos quando o dado não existe).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Local do ensaio na mensagem de convite copiada (Priority: P1) 🎯 MVP

Como membro do casting, ao copiar o convite de um evento que tem um ensaio com local definido, quero que
a mensagem inclua o **local do ensaio**, para que o artista saiba onde comparecer sem precisar perguntar.

**Why this priority**: É a lacuna real — o local do ensaio existe no portal mas falta na mensagem
copiada, que é o canal mais usado para avisar o artista. Entrega valor imediato sozinha.

**Independent Test**: Em um evento com ensaio que tem local preenchido, clicar em "Copiar convite" e
verificar que o texto colado contém o local do ensaio na seção de Ensaio.

**Acceptance Scenarios**:

1. **Given** um evento com um ensaio que tem **local preenchido**, **When** copio o convite, **Then** a
   seção "Ensaio" da mensagem inclui uma linha com o local do ensaio.
2. **Given** um evento com um ensaio **sem local**, **When** copio o convite, **Then** a seção "Ensaio"
   aparece normalmente (data/horário) mas **sem** linha de local e **sem** rótulo de local vazio.
3. **Given** um evento **sem ensaio**, **When** copio o convite, **Then** nenhuma seção de Ensaio nem
   linha de local de ensaio aparece (comportamento atual preservado).

### User Story 2 - Local da maquiagem e do ensaio consistentes no portal e na mensagem (Priority: P2)

Como artista, quero ver o **local da maquiagem** e o **local do ensaio** tanto no portal quanto na
mensagem de convite que recebo, cada um apenas quando existir, para ter a informação completa em
qualquer canal.

**Why this priority**: Garante a consistência ponta-a-ponta pedida ("tanto no portal quanto na mensagem
copiada"). O local da maquiagem já aparece nos dois lugares; esta história protege esse comportamento e
alinha o do ensaio.

**Independent Test**: Para um evento com local de maquiagem e local de ensaio preenchidos, conferir que
ambos aparecem no portal (convite pendente e próximo evento) e na mensagem copiada; para um evento sem
esses locais, conferir que nenhuma linha/rótulo vazio aparece em nenhum dos canais.

**Acceptance Scenarios**:

1. **Given** um evento com **local de maquiagem** preenchido, **When** o artista vê o portal e **When**
   o casting copia o convite, **Then** o local da maquiagem aparece nos dois.
2. **Given** um evento com **local de ensaio** preenchido, **When** o artista vê o portal e **When** o
   casting copia o convite, **Then** o local do ensaio aparece nos dois.
3. **Given** locais não preenchidos, **When** o portal é exibido ou o convite é copiado, **Then**
   nenhuma linha de local vazia, rótulo órfão ou separador sobrando aparece.

### Edge Cases

- **Múltiplos ensaios no evento**: a mensagem copiada usa o **primeiro ensaio** (mais antigo por
  `start_at`), seguindo o comportamento atual; o local exibido é o desse primeiro ensaio. O portal
  continua listando todos os ensaios com seus respectivos locais.
- **Local de maquiagem padronizado**: valores especiais ("manto" → "Manto Produções"/"Sede Manto" e
  "local" → "Local do evento"/"no local") seguem o rótulo amigável já usado; endereço livre é exibido
  como digitado. Esse comportamento atual é mantido.
- **Ensaio com local mas sem horário** (ou vice-versa): cada dado aparece independentemente conforme
  estiver preenchido.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A mensagem de convite copiada MUST incluir o **local do ensaio** na seção de Ensaio quando
  o ensaio usado na mensagem tiver local preenchido.
- **FR-002**: A mensagem de convite copiada MUST **omitir** qualquer linha/rótulo de local de ensaio
  quando o ensaio não tiver local, sem deixar texto vazio ou separadores sobrando.
- **FR-003**: A mensagem de convite copiada MUST continuar incluindo o **local da maquiagem** quando
  preenchido e omiti-lo quando vazio (comportamento atual preservado).
- **FR-004**: O portal do artista MUST exibir o **local do ensaio** e o **local da maquiagem** quando
  preenchidos, nos cartões de convite pendente e de próximos eventos, e omiti-los quando vazios
  (comportamento atual preservado/garantido).
- **FR-005**: Quando houver mais de um ensaio, a mensagem copiada MUST usar o local do **primeiro
  ensaio** (mais antigo por data/horário de início), coerente com a data/horário já exibidos.
- **FR-006**: A exibição do local do ensaio na mensagem MUST seguir o mesmo padrão visual (ícone de
  local e formato) já usado para o local da maquiagem na mesma mensagem.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Para 100% dos eventos com ensaio que tenha local preenchido, a mensagem copiada contém o
  local do ensaio.
- **SC-002**: Para 100% dos eventos sem local de ensaio (ou sem ensaio), a mensagem copiada não contém
  nenhuma linha/rótulo de local de ensaio vazio.
- **SC-003**: Para um mesmo evento, o local do ensaio e o local da maquiagem exibidos no portal e na
  mensagem copiada coincidem em conteúdo (cada um quando existir).
- **SC-004**: Nenhuma regressão nos demais campos do convite (evento, personagem, data, horário, local
  do evento, cachê, materiais de ensaio) e nos blocos já existentes do portal.

## Assumptions

- **"Mensagem copiada" = convite ao artista**: refere-se à mensagem do botão "Copiar convite"
  (`buildWAMsg`) na página do evento, que é a comunicação direcionada ao artista ("a pessoa"). A
  mensagem de confirmação ao cliente (feature 083) não faz parte deste escopo.
- **Local do ensaio** vem do campo `location` do próprio ensaio (um `CalendarEvent` do tipo ENSAIO);
  **local da maquiagem** vem de `makeup_location` do evento. Nenhum modelo novo é necessário.
- **Portal já cobre os dois locais** nos cartões de convite pendente e próximos eventos; a mudança
  central de código é adicionar o local do ensaio à mensagem copiada, mantendo o portal como está.
- **Rótulos amigáveis de maquiagem** ("manto"/"local") permanecem como já implementados em cada canal.
