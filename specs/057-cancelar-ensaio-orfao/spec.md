# Feature Specification: Cancelar ensaio órfão (sem evento na agenda)

**Feature Branch**: `057-cancelar-ensaio-orfao`

**Created**: 2026-06-17

**Status**: Draft

**Input**: User description: "Tínhamos um Show em novembro e foi cancelado (não está mais na agenda). E eu já havia criado ensaio para ele, agora eu não consigo cancelar o ensaio porque não tem mais o evento disponível na agenda, e não encontrei opção de cancelamento no ensaio no sistema."

## Contexto

Os ensaios são criados **a partir da página de um show** e ficam vinculados a ele. Hoje, a
única forma de cancelar um ensaio é pela página do show pai (onde aparece o botão "Cancelar
ensaio") ou editá-lo pelo painel da home. Quando o **show é removido da agenda** (cancelado
no Google Calendar e sincronizado), o ensaio pode ficar **órfão**: continua existindo no
sistema/agenda, mas **não há mais a página do show** para gerenciá-lo, e a página do próprio
ensaio **não oferece** opção de cancelamento. Resultado: o usuário não consegue cancelar o
ensaio de jeito nenhum.

O sistema **já tem** a ação interna de cancelar ensaio (que remove o ensaio do sistema e do
Google Calendar, sem afetar o show pai); o que falta é **expor essa opção** para ensaios
órfãos e na própria página do ensaio.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cancelar um ensaio órfão (show removido da agenda) (Priority: P1) 🎯 MVP

Como equipe de ensaio, quero encontrar e cancelar um ensaio cujo show já não existe mais na
agenda, para que ele não fique pendurado no sistema e na agenda.

**Why this priority**: É exatamente o problema relatado — hoje é impossível cancelar esse
ensaio. Sem isso, a feature não resolve nada.

**Independent Test**: Ter um ensaio cujo show pai foi removido; abri-lo/localizá-lo no
sistema e cancelá-lo; confirmar que ele some do sistema e da agenda (Google Calendar).

**Acceptance Scenarios**:

1. **Given** um ensaio cujo show pai não existe mais, **When** o usuário abre a área de
   ensaios, **Then** esse ensaio órfão aparece em uma lista identificável (ex.: "ensaios sem
   show") com a opção de cancelar.
2. **Given** um ensaio órfão exibido, **When** o usuário clica em "Cancelar ensaio" e
   confirma, **Then** o ensaio é removido do sistema e da agenda (Google Calendar), com
   mensagem de sucesso.
3. **Given** o cancelamento concluído, **When** a página recarrega, **Then** o ensaio órfão
   não aparece mais.

---

### User Story 2 - Botão de cancelar na própria página do ensaio (Priority: P1)

Como usuário que abriu um ensaio diretamente (pela agenda ou por link), quero ver ali uma
opção de cancelá-lo, para não depender da página do show pai.

**Why this priority**: O usuário relatou "não encontrei opção de cancelamento no ensaio" —
abrir o ensaio e não achar como cancelar. Resolve o caso geral (com ou sem show pai).

**Independent Test**: Abrir a página de um ensaio (órfão ou não) e confirmar que há um botão
de cancelar que funciona com confirmação.

**Acceptance Scenarios**:

1. **Given** a página de um evento do tipo ensaio, **When** exibida para a equipe de ensaio,
   **Then** há um botão "Cancelar ensaio" com confirmação antes de executar.
2. **Given** um ensaio **com** show pai, **When** cancelado pela página do ensaio, **Then**
   o show pai **não** é afetado e o usuário é levado de volta a um lugar coerente.
3. **Given** um ensaio **sem** show pai, **When** cancelado, **Then** o usuário é levado para
   um lugar coerente (ex.: a home), sem erro.

---

### User Story 3 - Cancelar ensaio direto no painel da home (Priority: P2)

Como equipe de ensaio, quero cancelar um ensaio direto no painel "Ensaios agendados" da
home (onde hoje só consigo editar), para agilizar sem abrir outra página.

**Why this priority**: Conveniência e consistência (já existe "Editar" ali). Não é o
bloqueio relatado, então P2.

**Independent Test**: Na home, no painel de ensaios agendados, cancelar um ensaio e
confirmar que ele some.

**Acceptance Scenarios**:

1. **Given** o painel "Ensaios agendados" da home com um ensaio, **When** o usuário aciona
   "Cancelar ensaio" e confirma, **Then** o ensaio é removido (sistema + agenda) e o painel
   reflete a remoção.
2. **Given** a ação de cancelar na home, **When** exibida, **Then** ela fica ao lado da ação
   de editar já existente, com confirmação antes de executar.

---

### Edge Cases

- **Ensaio sem vínculo com Google Calendar**: cancelar mesmo assim (remove do sistema), sem
  erro.
- **Falha ao remover do Google Calendar**: o ensaio é removido do sistema e o usuário é
  avisado de que a remoção no Google falhou (sem travar a operação).
- **Show pai existente**: cancelar o ensaio nunca remove nem altera o show pai.
- **Permissão**: apenas perfis que já podem gerenciar ensaios podem cancelar; demais não
  veem a opção e têm a ação recusada.
- **Mais de um ensaio órfão**: todos aparecem na lista de órfãos, cada um com sua opção de
  cancelar.
- **Ensaio órfão em data passada** (ex.: novembro): também aparece e pode ser cancelado
  (não filtrar só por futuros).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST permitir **cancelar um ensaio** cujo show pai não existe mais
  (ensaio órfão), removendo-o do sistema e da agenda (Google Calendar).
- **FR-002**: O sistema MUST exibir os **ensaios órfãos** (do tipo ensaio, sem show pai
  existente) em um local acessível da área de ensaios, com a opção de cancelar — incluindo
  ensaios órfãos em **datas passadas**.
- **FR-003**: A página de um evento do tipo **ensaio** MUST oferecer um botão "Cancelar
  ensaio" (com confirmação), válido para ensaios com ou sem show pai.
- **FR-004**: O cancelamento de um ensaio MUST **nunca** afetar o show pai (quando existir).
- **FR-005**: Toda ação de cancelar ensaio MUST pedir **confirmação** antes de executar
  (ação destrutiva).
- **FR-006**: O cancelamento MUST funcionar mesmo quando o ensaio não tem vínculo com o
  Google Calendar; e, se a remoção no Google falhar, o ensaio MUST ser removido do sistema
  com **aviso** da falha externa (sem travar).
- **FR-007**: A opção de cancelar ensaio (órfão, na página do ensaio e na home) MUST ser
  restrita aos perfis que já podem gerenciar ensaios; para os demais, a opção não aparece e
  a ação é recusada.
- **FR-008**: O painel "Ensaios agendados" da home MUST oferecer a opção de **cancelar** o
  ensaio ao lado da opção de editar já existente.
- **FR-009**: Após cancelar, o sistema MUST levar o usuário a um destino coerente (página do
  show pai, se existir; senão, a home) e confirmar com mensagem de sucesso.

### Key Entities

- **Ensaio (existente)**: evento do tipo "ensaio", normalmente vinculado a um show pai. Pode
  ficar **órfão** quando o show pai é removido da agenda. Esta feature não muda o que é um
  ensaio; muda **como ele pode ser cancelado/encontrado** quando órfão.
- **Show pai (existente)**: evento ao qual o ensaio se vincula; pode deixar de existir
  (cancelado/removido da agenda). Nunca é afetado pelo cancelamento de um ensaio.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos ensaios órfãos podem ser cancelados sem depender da página de um show
  (que não existe mais).
- **SC-002**: O usuário consegue cancelar o ensaio órfão em até 3 cliques a partir da home
  (localizar → cancelar → confirmar).
- **SC-003**: Cancelar um ensaio nunca remove nem altera nenhum show — 0 regressões em shows.
- **SC-004**: Após cancelar, o ensaio desaparece do sistema e da agenda (Google Calendar) em
  100% dos casos em que o Google respondeu com sucesso.

## Assumptions

- "Cancelar" o ensaio = removê-lo do sistema e da agenda (Google Calendar), comportamento já
  existente na ação interna de cancelar ensaio — esta feature apenas **expõe** essa ação para
  os casos órfão/página-do-ensaio/home.
- "Ensaio órfão" = evento do tipo ensaio cujo show pai não existe (sem vínculo de pai, ou
  com vínculo apontando para um show que já foi removido).
- Os perfis que gerenciam ensaios são os mesmos que hoje criam/editam/cancelam ensaios
  (equipe de ensaio, casting e super admin) — sem ampliar permissões.
- Não é necessário "reaproveitar" o ensaio órfão (revincular a outro show); o caso de uso é
  apenas **cancelá-lo**. Revínculo fica fora do escopo.
- A prevenção de que ensaios fiquem órfãos no futuro (ex.: cancelar ensaios junto quando o
  show é removido) fica **fora do escopo** desta feature, que foca em permitir o
  cancelamento do que já está órfão.
