# Feature Specification: Vincular gasto extra a um evento

**Feature Branch**: `015-gasto-vinculado-evento`

**Created**: 2026-06-01

**Status**: Draft

**Input**: User description: "O gasto extra pode ser vinculado a um evento (campo que pesquisa
eventos por data). Isso entra como gasto do evento para o balanço (gasto x ganho). Ao ser aprovado,
aparece na página do evento. Também quero anexar gastos antigos a eventos que já ocorreram, para
organizar o passado."

## Contexto

Os gastos extras (features 004/005/013/014) hoje vivem soltos, sem ligação com eventos. A empresa
quer poder **associar um gasto a um evento** — tanto na criação (buscando o evento por data) quanto
depois, vinculando **gastos antigos a eventos já ocorridos**. Quando o gasto é **aprovado**, ele
deve **aparecer na página do evento** e **abater do "Lucro líquido"** já exibido ali (venda −
cachês − gastos extras), dando um balanço de gasto × ganho mais fiel por evento.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Vincular um evento ao registrar o gasto (Priority: P1)

Ao registrar um gasto extra, o usuário pode (opcionalmente) buscar um evento **por data** e
selecioná-lo. O fluxo de criação continua o mesmo; o vínculo é um campo a mais, opcional.

**Why this priority**: É o caminho principal de associação no dia a dia.

**Independent Test**: Abrir o formulário de gasto, escolher uma data, ver os eventos daquela data,
selecionar um, salvar e confirmar que o gasto ficou vinculado àquele evento.

**Acceptance Scenarios**:

1. **Given** o formulário de gasto, **When** o usuário escolhe uma data, **Then** vê os eventos
   daquela data para selecionar.
2. **Given** um evento selecionado, **When** o gasto é salvo, **Then** ele fica vinculado a esse
   evento (status inicial pendente, como hoje).
3. **Given** nenhum evento selecionado, **When** o gasto é salvo, **Then** ele é criado normalmente,
   sem vínculo (campo opcional).

---

### User Story 2 - Gasto aprovado aparece e abate no evento (Priority: P1)

Quando um gasto vinculado é **aprovado**, ele passa a aparecer na página do evento (na área
financeira) e entra no cálculo: **Lucro líquido = venda − cachês − gastos extras aprovados**.

**Why this priority**: É o valor de negócio central — enxergar o gasto real por evento.

**Independent Test**: Vincular um gasto a um evento, aprová-lo e confirmar que ele aparece listado
na página do evento e que o Lucro líquido foi reduzido pelo valor do gasto.

**Acceptance Scenarios**:

1. **Given** um gasto vinculado **pendente**, **When** alguém abre a página do evento, **Then** ele
   ainda **não** aparece nem afeta o lucro.
2. **Given** um gasto vinculado **aprovado**, **When** alguém com acesso financeiro abre a página do
   evento, **Then** ele aparece na lista de gastos extras do evento, com valor e Nota Fiscal.
3. **Given** um ou mais gastos vinculados aprovados, **When** a página do evento é exibida, **Then**
   o "Lucro líquido" é igual a venda − cachês − soma dos gastos extras aprovados.

---

### User Story 3 - Organizar o passado: vincular gastos antigos (Priority: P2)

O super admin pode vincular (ou alterar/remover o vínculo de) um gasto **já existente** a um evento,
inclusive gastos já aprovados e eventos que já ocorreram — para organizar o histórico.

**Why this priority**: Permite reconstruir o balanço de eventos passados.

**Independent Test**: Como super admin, abrir a lista de gastos, escolher um gasto antigo, buscar um
evento passado por data, vinculá-lo e confirmar que (se aprovado) ele passa a aparecer naquele
evento.

**Acceptance Scenarios**:

1. **Given** um gasto existente sem vínculo, **When** o super admin define um evento, **Then** o
   gasto passa a ficar vinculado a esse evento.
2. **Given** um gasto já vinculado, **When** o super admin troca ou remove o evento, **Then** o
   vínculo é atualizado/removido.
3. **Given** um usuário que não é super admin, **When** ele tenta vincular um gasto existente a um
   evento, **Then** a ação é negada.

---

### Edge Cases

- **Gasto pendente vinculado**: não aparece no evento nem afeta o lucro até ser aprovado.
- **Evento sem gastos vinculados aprovados**: a área de gastos extras do evento fica vazia e o lucro
  segue como venda − cachês.
- **Vínculo a evento inexistente/ inválido**: o sistema ignora o vínculo (cria sem vínculo) e/ou
  avisa; não cria referência quebrada.
- **Data sem eventos**: a busca por data não retorna opções; o usuário pode salvar sem vínculo.
- **Gasto rejeitado vinculado**: não aparece no evento nem afeta o lucro.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O formulário de gasto extra MUST permitir, opcionalmente, vincular o gasto a um
  evento, buscando os eventos **por data**.
- **FR-002**: O fluxo de criação do gasto MUST permanecer o mesmo; o vínculo é opcional e não
  bloqueia o registro quando ausente.
- **FR-003**: Um gasto vinculado **aprovado** MUST aparecer na página do evento, na área financeira,
  com descrição, valor e acesso à Nota Fiscal.
- **FR-004**: O "Lucro líquido" exibido na página do evento MUST passar a descontar a soma dos
  gastos extras **aprovados** vinculados àquele evento (venda − cachês − gastos extras).
- **FR-005**: Gastos vinculados **pendentes** ou **rejeitados** NÃO MUST aparecer no evento nem
  afetar o lucro.
- **FR-006**: O super admin MUST conseguir vincular, alterar ou remover o evento de um gasto **já
  existente** (inclusive aprovados e eventos passados).
- **FR-007**: Vincular/alterar o evento de um gasto existente MUST ser restrito ao super admin (na
  interface e no servidor).
- **FR-008**: A visibilidade dos gastos do evento na página do evento MUST seguir o mesmo controle
  da área financeira já existente (Financeiro/Superadmin).
- **FR-009**: O restante do fluxo de gastos (Nota Fiscal obrigatória, aprovação, balanço financeiro
  global, permissões da feature 013) MUST permanecer inalterado.

### Key Entities *(include if feature involves data)*

- **Gasto extra** (já existe): ganha um **vínculo opcional a um evento**.
- **Evento** (já existe): passa a ter, de forma derivada, a lista de gastos extras aprovados a ele
  vinculados e o respectivo total.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: É possível vincular um gasto a um evento buscando por data em até 3 ações (escolher
  data → escolher evento → salvar).
- **SC-002**: 100% dos gastos vinculados aprovados aparecem na página do respectivo evento.
- **SC-003**: O "Lucro líquido" do evento reflete venda − cachês − gastos extras aprovados (erro de
  R$ 0,00 em relação à soma manual).
- **SC-004**: 0 usuários não-super-admin conseguem alterar o vínculo de um gasto existente.
- **SC-005**: Nenhuma regressão no fluxo de gastos nem no restante da página do evento.

## Assumptions

- "Pesquisa por data" = o usuário escolhe uma data e o sistema lista os eventos daquela data para
  seleção; o vínculo é explícito (escolha do evento), não automático por data.
- Apenas gastos **aprovados** entram no evento e no lucro (decisão do usuário: "ao ser aprovado").
- O Lucro líquido do evento passa a descontar os gastos extras aprovados **agora** (decisão do
  usuário), sobre o KPI já existente na página do evento.
- Vincular gastos antigos é tarefa de organização financeira → restrito ao **super admin** (decisão
  do usuário).
- Um gasto vincula-se a **no máximo um** evento.
- O balanço financeiro global (dashboard por período) não muda nesta entrega; o foco é o vínculo e a
  visão por evento.
