# Feature Specification: Nome do agrupamento de eventos

**Feature Branch**: `055-nome-do-agrupamento`

**Created**: 2026-06-17

**Status**: Draft

**Input**: User description: "Eu gostaria também que desse para dar um nome para o agrupamento. Assim, na home nas tasks de comercial aparece apenas o evento principal com o nome do grupo. Não mais várias cobranças diferentes. Mesma coisa para quando esse evento aparecer nos balanços financeiros"

## Contexto

O agrupamento de eventos por contrato (features 053/054) já vincula vários eventos sob um
evento principal, e os dados comerciais (venda, cobrança) ficam só no principal. Hoje,
porém, o grupo não tem **identidade própria**: na home do comercial e nos balanços
financeiros, o que aparece é o **título do evento principal** (ex.: "(CORP) MENSAGEIRO 1"),
que não comunica que aquilo representa o contrato inteiro. Além disso, os eventos satélites
ainda podem poluir essas listas (ex.: aparecendo como "evento sem valor de venda").

Esta feature adiciona um **nome ao agrupamento** e faz a home comercial e os balanços
financeiros exibirem o grupo como **uma única entrada, com o nome do grupo**, em vez de
várias linhas/cobranças separadas.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Dar um nome ao agrupamento (Priority: P1) 🎯 MVP

Como usuário comercial, quero atribuir um nome ao agrupamento (ex.: "Campanha Mensageiros
— Empresa X") ao agrupar eventos ou depois, para que o contrato tenha uma identidade clara
em vez de aparecer pelo título de um dos eventos.

**Why this priority**: É a base da feature — sem o nome não há o que exibir nas demais
telas. Entrega valor sozinha (a identidade do grupo já fica visível na tela do evento).

**Independent Test**: Agrupar eventos informando um nome; abrir o evento principal e
confirmar que o nome do grupo aparece; editar o nome e confirmar que persiste.

**Acceptance Scenarios**:

1. **Given** o usuário está agrupando eventos, **When** informa um nome para o grupo e
   confirma, **Then** o nome é salvo e associado ao grupo (ao evento principal).
2. **Given** um grupo já existente, **When** o usuário edita o nome do grupo na tela do
   evento principal, **Then** o novo nome é persistido e exibido.
3. **Given** o usuário agrupa sem informar nome, **When** confirma, **Then** o grupo é
   criado normalmente e, onde o nome seria exibido, usa-se o título do evento principal
   como rótulo padrão (fallback).
4. **Given** a tela do evento principal e dos satélites, **When** exibida, **Then** o nome
   do grupo aparece junto da indicação de agrupamento já existente (features 053/054).

---

### User Story 2 - Home comercial mostra só o principal com o nome do grupo (Priority: P1)

Como usuário comercial, quero que as tarefas comerciais da home (cobranças pendentes e
eventos sem valor) mostrem **uma única entrada por grupo**, identificada pelo nome do
grupo, em vez de várias cobranças/itens dos eventos do mesmo contrato.

**Why this priority**: É a dor relatada diretamente ("não mais várias cobranças
diferentes"). Depende do nome (US1).

**Independent Test**: Criar um grupo nomeado com cobrança pendente no principal e satélites
sem valor; abrir a home comercial e confirmar que aparece só uma linha, com o nome do
grupo, e que os satélites não aparecem como itens separados.

**Acceptance Scenarios**:

1. **Given** um grupo com cobrança pendente no principal, **When** o comercial abre a home,
   **Then** aparece **uma** linha de cobrança identificada pelo **nome do grupo** (não pelo
   título do evento principal, quando houver nome).
2. **Given** eventos satélites de um grupo, **When** a home comercial é montada, **Then**
   eles **não** aparecem na lista de "eventos sem valor de venda" (o valor está no
   principal, não neles).
3. **Given** um grupo sem nome definido, **When** exibido na home, **Then** usa o título do
   evento principal como rótulo (fallback), mantendo a regra de uma entrada por grupo.
4. **Given** eventos não agrupados, **When** exibidos na home, **Then** continuam aparecendo
   normalmente, pelo próprio título (sem regressão).

---

### User Story 3 - Balanços financeiros mostram o grupo como uma entrada nomeada (Priority: P2)

Como usuário financeiro, quero que, nos balanços/painel financeiro, o grupo apareça como
**uma única entrada com o nome do grupo** (consolidando venda e custos no principal), sem
listar os eventos satélites como linhas separadas.

**Why this priority**: Complementa a consistência da identidade do grupo nos relatórios.
Depende do nome (US1) e reforça o comportamento de consolidação já iniciado na 053.

**Independent Test**: Com um grupo nomeado e satélites com cachês, abrir o painel financeiro
e confirmar que a tabela de eventos mostra **uma** linha com o nome do grupo (consolidando
os custos) e não mostra os satélites em linhas próprias.

**Acceptance Scenarios**:

1. **Given** um grupo nomeado, **When** o financeiro abre o painel/balanço, **Then** a
   listagem de eventos exibe o **nome do grupo** na linha do principal.
2. **Given** eventos satélites de um grupo, **When** o balanço é montado, **Then** eles
   **não** aparecem como linhas separadas na tabela de eventos do período.
3. **Given** os indicadores consolidados (venda, custo, comissão, lucro) do grupo, **When**
   exibidos, **Then** permanecem corretos e idênticos aos das features 053 (grupo conta
   como 1 venda; custo dos satélites somado no principal) — sem regressão de cálculo.
4. **Given** um grupo sem nome, **When** exibido no balanço, **Then** usa o título do
   evento principal como rótulo (fallback).

---

### Edge Cases

- **Grupo sem nome**: em qualquer exibição, cair no título do evento principal (fallback),
  nunca mostrar vazio.
- **Satélite que ainda tem saldo/é referenciado**: como os dados comerciais ficam no
  principal (053), o satélite não gera cobrança; garantir que também não apareça como
  "sem valor" na home.
- **Desagrupar um satélite**: ao voltar a ser independente, ele reaparece normalmente nas
  listas pelo seu próprio título; o nome do grupo continua no principal.
- **Nome muito longo**: o rótulo deve caber/quebrar adequadamente nas telas (truncar ou
  quebrar linha, sem estourar layout).
- **Editar o nome do grupo em um evento que não é principal**: não permitido — o nome
  pertence ao grupo (ao principal).
- **Excluir/limpar o nome**: deixar o nome em branco volta ao comportamento de fallback
  (título do principal).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST permitir associar um **nome** ao agrupamento (vinculado ao
  evento principal do grupo).
- **FR-002**: O sistema MUST permitir informar o nome do grupo **no momento do
  agrupamento** (opcional) e **editá-lo depois** na tela do evento principal.
- **FR-003**: Quando o grupo não tiver nome, o sistema MUST usar o **título do evento
  principal** como rótulo padrão (fallback) em todas as exibições.
- **FR-004**: A home comercial MUST exibir, para um grupo, **uma única entrada** (a do
  evento principal) identificada pelo nome do grupo — nas cobranças pendentes e nos demais
  itens comerciais.
- **FR-005**: A home comercial MUST **não** exibir eventos satélites como itens próprios
  (em especial, não listá-los como "eventos sem valor de venda").
- **FR-006**: Os balanços/painel financeiro MUST exibir o grupo como **uma única entrada**
  com o nome do grupo, **sem** listar os eventos satélites como linhas separadas.
- **FR-007**: Os valores consolidados do grupo (venda, custo de cachês, comissão, lucro)
  MUST permanecer corretos e equivalentes aos das features 053 (grupo = 1 venda; custos
  dos satélites somados no principal) — sem regressão de cálculo.
- **FR-008**: A tela do evento (principal e satélites) MUST exibir o nome do grupo junto à
  indicação de agrupamento já existente.
- **FR-009**: A edição do nome do grupo MUST ser restrita aos perfis que já podem agrupar
  (COMERCIAL, FINANCEIRO, SUPERADMIN), mesma regra das features 053/054.
- **FR-010**: Eventos **não agrupados** MUST continuar aparecendo normalmente (pelo próprio
  título) na home e nos balanços, sem regressão.

### Key Entities

- **Agrupamento (grupo de eventos)**: representa o contrato único que reúne vários eventos.
  Ganha um atributo **nome do grupo** (texto, opcional). O grupo continua representado pelo
  vínculo evento-principal ↔ eventos-satélites já existente (features 053/054); o nome é um
  atributo do **evento principal**. Não há nova entidade independente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um contrato com N eventos agrupados aparece como **1 entrada** (não N) na home
  comercial e no balanço financeiro.
- **SC-002**: A entrada do grupo é identificada pelo **nome do grupo** em 100% dos casos em
  que um nome foi definido; nos demais, pelo título do principal.
- **SC-003**: Eventos satélites **não** aparecem como itens/linhas próprias na home
  comercial nem na tabela de eventos do balanço financeiro.
- **SC-004**: Os totais financeiros do grupo (venda, custo, comissão, lucro) permanecem
  idênticos aos calculados antes desta feature (sem regressão) — verificável comparando os
  valores consolidados.
- **SC-005**: O usuário consegue nomear um grupo e ver o nome refletido na home e no balanço
  sem passos extras além de informar/editar o nome.

## Assumptions

- O **nome do grupo** é um atributo opcional do evento principal; quando ausente, o rótulo
  exibido é o título do evento principal (fallback). Decisão alinhada ao "gostaria que desse
  para dar um nome" (capacidade opcional, não obrigatória).
- A feature reutiliza o vínculo de agrupamento das features 053/054 (não cria nova entidade
  de grupo). O nome é mais um campo do evento principal.
- "Balanços financeiros" refere-se ao painel financeiro existente (`/financeiro/`) e às
  listagens de eventos por período; o cálculo consolidado do grupo já existe desde a 053 e
  não muda — muda apenas a **apresentação** (uma linha nomeada, satélites ocultos).
- O título original de cada evento (sincronizado do Google Agenda) **não** é alterado; o
  nome do grupo é uma camada de apresentação adicional.
- Onde o nome do grupo é exibido como cobrança/linha, o link continua levando ao evento
  principal do grupo.
- A formatação de valores monetários segue o padrão brasileiro já vigente (constituição,
  Princípio VII) — sem mudança.
