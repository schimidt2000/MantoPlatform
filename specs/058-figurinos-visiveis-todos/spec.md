# Feature Specification: Figurinos visíveis a todos (edição restrita)

**Feature Branch**: `058-figurinos-visiveis-todos`

**Created**: 2026-06-17

**Status**: Draft

**Input**: User description: "preciso que a seção figurinos fique visível a todos no meu sistema, por favor. Porém edições só podem ser feitas por admin e setor figurino."

## Contexto

Hoje a seção **Figurinos** (`/figurinos`) só aparece no menu para os perfis FIGURINO e
SUPERADMIN. Além disso, as rotas de **edição** (criar/editar/excluir ficha, girar foto,
sincronizar Drive) hoje exigem apenas estar logado — qualquer usuário com o link poderia
alterar fichas. O cliente quer:

1. A seção visível para **todos** os usuários (consulta/impressão).
2. As **edições** restritas a **SUPERADMIN** e **FIGURINO**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultar figurinos (todos os usuários) (Priority: P1) 🎯 MVP

Como qualquer usuário logado, quero ver o banco de figurinos (catálogo e fichas) e imprimir,
para consultar peças e personagens sem depender do setor de figurino.

**Why this priority**: É o pedido central — abrir a visualização para todos.

**Independent Test**: Logar com um perfil que não é FIGURINO nem SUPERADMIN (ex.: comercial),
ver o link "Figurinos" no menu, abrir a lista e uma ficha, e imprimir.

**Acceptance Scenarios**:

1. **Given** um usuário logado de qualquer perfil, **When** abre o menu, **Then** vê o item
   "Figurinos".
2. **Given** esse usuário, **When** acessa `/figurinos`, **Then** vê o catálogo de fichas e
   pode abrir a impressão de uma ficha (somente leitura).
3. **Given** esse usuário, **When** vê uma ficha, **Then** **não** vê botões de criar,
   editar, excluir nem sincronizar.

---

### User Story 2 - Edição restrita a admin e setor figurino (Priority: P1)

Como empresa, quero que apenas SUPERADMIN e FIGURINO possam criar, editar, excluir fichas,
girar foto ou sincronizar com o Drive, para proteger o conteúdo do banco de figurinos.

**Why this priority**: Sem isso, abrir a seção a todos exporia a edição a todos — risco. As
duas partes andam juntas.

**Independent Test**: Como usuário sem permissão, tentar acessar as ações de edição (pela UI
e pela URL direta) e confirmar que são recusadas; como FIGURINO/SUPERADMIN, confirmar que
funcionam.

**Acceptance Scenarios**:

1. **Given** um usuário **sem** perfil FIGURINO/SUPERADMIN, **When** tenta criar/editar/
   excluir ficha, girar foto ou sincronizar (por URL direta), **Then** a ação é recusada
   (acesso negado), sem alterar nada.
2. **Given** um usuário **com** perfil FIGURINO ou SUPERADMIN, **When** usa essas ações,
   **Then** funcionam normalmente como hoje.
3. **Given** os botões de edição na tela, **When** exibidos, **Then** só aparecem para quem
   pode editar (FIGURINO/SUPERADMIN).

---

### Edge Cases

- **URL direta de edição** por usuário sem permissão: recusada (não basta esconder o botão).
- **Impressão**: continua disponível a todos (é leitura).
- **Personagens sem ficha** (alerta no topo): visível a todos, mas o botão "Criar ficha" só
  para quem pode editar.
- **Sincronizar Drive**: ação de edição → restrita (hoje já é só superadmin no botão; manter
  no servidor também).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O item "Figurinos" no menu MUST ser visível para **todos** os usuários
  autenticados.
- **FR-002**: A listagem `/figurinos` e a **impressão** de fichas MUST ser acessíveis a
  qualquer usuário autenticado (somente leitura).
- **FR-003**: Criar, editar e excluir ficha, **girar foto** e **sincronizar com o Drive**
  MUST ser restritos a SUPERADMIN e FIGURINO — tanto na UI quanto no servidor (URL direta
  recusada com acesso negado).
- **FR-004**: Os botões/links de edição (criar, editar, excluir, sincronizar) MUST aparecer
  **somente** para usuários que podem editar.
- **FR-005**: Usuários sem permissão de edição MUST conseguir visualizar e imprimir, sem ver
  nenhuma ação de edição.
- **FR-006**: Nenhuma alteração de dado MUST ocorrer a partir de uma tentativa não
  autorizada (a recusa acontece antes de qualquer escrita).

### Key Entities

- **Ficha de figurino (existente)**: representa o figurino de um personagem (foto, peças,
  observações). Esta feature não muda os dados; muda **quem vê** (todos) e **quem edita**
  (SUPERADMIN/FIGURINO).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos usuários autenticados veem o menu "Figurinos" e conseguem abrir a
  lista e imprimir.
- **SC-002**: 100% das tentativas de edição por usuários sem permissão (UI ou URL direta)
  são recusadas, sem alterar dados.
- **SC-003**: SUPERADMIN e FIGURINO continuam criando/editando/excluindo/sincronizando sem
  regressão.

## Assumptions

- "Todos" = todos os usuários **autenticados** da plataforma (não há acesso público sem
  login).
- "Setor figurino" = perfil FIGURINO; "admin" = perfil SUPERADMIN.
- "Edições" inclui: criar ficha, editar ficha, excluir ficha, girar foto e sincronizar com o
  Google Drive (todas as ações que alteram dados).
- Impressão e visualização são leitura → liberadas a todos.
- A vinculação de ficha a personagem feita em outras telas (ex.: detalhe do evento) segue as
  permissões já existentes dessas telas — fora do escopo desta mudança.
