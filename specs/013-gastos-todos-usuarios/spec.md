# Feature Specification: Gastos extras abertos a todos, balanço só para admin

**Feature Branch**: `013-gastos-todos-usuarios`

**Created**: 2026-06-01

**Status**: Draft

**Input**: User description: "Qualquer usuário pode adicionar um gasto extra. Só o admin pode
aprovar. Os outros usuários não podem ver o balanço de aprovados e pendentes."

## Contexto

As features 004/005 criaram a página de Gastos Extras e, depois, **restringiram tudo a super
admin** (registrar, ver lista e ver o balanço). Na prática, isso impede que um colaborador comum
registre um gasto que ele teve (ex.: comprou figurino e quer reembolso). O usuário quer **abrir o
registro para qualquer colaborador**, mantendo a **aprovação só com o super admin** e mantendo o
**balanço financeiro (totais aprovados/pendentes) invisível** para quem não é admin.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Qualquer colaborador registra um gasto (Priority: P1)

Um colaborador autenticado (não-admin) acessa a página de Gastos Extras, preenche descrição,
valor, data, forma de desembolso e comprovante, e registra o gasto. Ele entra como **pendente**,
aguardando aprovação.

**Why this priority**: É o pedido central — destravar o registro para todos.

**Independent Test**: Logar como usuário comum, abrir Gastos Extras, registrar um gasto e
confirmar que ele aparece como pendente para esse usuário.

**Acceptance Scenarios**:

1. **Given** um usuário comum autenticado, **When** ele abre a página de Gastos Extras, **Then** vê
   o formulário de registro e consegue enviar um gasto.
2. **Given** um gasto recém-registrado por um usuário comum, **When** ele é salvo, **Then** fica com
   status "pendente" e registra o autor.

---

### User Story 2 - Apenas o admin aprova (Priority: P1)

Somente o super admin pode aprovar ou rejeitar gastos. O usuário comum não vê esses botões e não
consegue aprovar nem por acesso direto.

**Why this priority**: Garante o controle financeiro — só o admin decide o que entra no balanço.

**Independent Test**: Como usuário comum, confirmar que não há botões de aprovar/rejeitar; tentar a
ação diretamente e receber negação.

**Acceptance Scenarios**:

1. **Given** um usuário comum, **When** ele vê a lista de gastos, **Then** não há opção de aprovar
   nem rejeitar.
2. **Given** um usuário comum, **When** ele tenta aprovar/rejeitar por acesso direto, **Then** a
   ação é negada.
3. **Given** um super admin, **When** ele abre a página, **Then** pode aprovar e rejeitar gastos
   pendentes.

---

### User Story 3 - Balanço só para o admin (Priority: P1)

O balanço (totais de aprovados e de pendentes) aparece somente para o super admin. O usuário comum
não vê esses totais — e também não vê os gastos de outras pessoas, apenas os seus.

**Why this priority**: É a restrição de privacidade financeira pedida explicitamente.

**Independent Test**: Como usuário comum, confirmar que não há cards de total aprovado/pendente e
que a lista mostra apenas os próprios gastos; como admin, confirmar que os totais aparecem.

**Acceptance Scenarios**:

1. **Given** um usuário comum, **When** ele abre a página, **Then** não vê os totais de aprovados
   nem de pendentes.
2. **Given** um usuário comum, **When** ele vê a lista, **Then** vê apenas os gastos que ele mesmo
   registrou (não os de terceiros).
3. **Given** um super admin, **When** ele abre a página, **Then** vê os totais e todos os gastos de
   todos os colaboradores.

---

### Edge Cases

- **Usuário comum sem gastos**: vê o formulário e uma lista vazia (sem totais), com uma mensagem de
  estado vazio.
- **Excluir o próprio gasto**: o autor continua podendo excluir o próprio gasto enquanto pendente;
  o super admin pode excluir qualquer um (comportamento atual mantido).
- **Acesso direto às ações de admin**: aprovar/rejeitar por usuário comum é negado pelo servidor,
  não só escondido na tela.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Qualquer usuário autenticado MUST conseguir acessar a página de Gastos Extras e
  registrar um novo gasto (status inicial "pendente").
- **FR-002**: O acesso à página de Gastos Extras (link de menu e rota) MUST estar disponível para
  qualquer usuário autenticado, não só super admin.
- **FR-003**: Apenas o super admin MUST poder aprovar ou rejeitar gastos; a restrição vale tanto na
  interface (botões escondidos) quanto no servidor (ação negada para não-admin).
- **FR-004**: O balanço (total de aprovados e total de pendentes) MUST ser visível somente para o
  super admin.
- **FR-005**: Um usuário comum MUST ver apenas os gastos que ele mesmo registrou; o super admin
  MUST ver os gastos de todos.
- **FR-006**: O autor de um gasto MUST continuar podendo excluí-lo enquanto pendente; o super admin
  MUST poder excluir qualquer gasto (comportamento atual mantido).
- **FR-007**: O fluxo de aprovação e o impacto no balanço financeiro (gasto aprovado entra no
  balanço) MUST permanecer inalterados.

### Key Entities *(include if feature involves data)*

- **Gasto extra** (já existe): sem mudança de estrutura; muda apenas **quem pode registrar/ver** e
  **o que cada perfil enxerga**.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos usuários autenticados conseguem registrar um gasto extra.
- **SC-002**: 0 usuários não-admin conseguem aprovar ou rejeitar um gasto (nem pela tela, nem por
  acesso direto).
- **SC-003**: 0 usuários não-admin veem os totais do balanço ou gastos de terceiros.
- **SC-004**: 100% dos super admins continuam vendo os totais, todos os gastos e as ações de
  aprovar/rejeitar — sem regressão em relação ao comportamento atual.

## Assumptions

- "Outros usuários" = qualquer usuário autenticado da plataforma que não seja super admin.
- "Não ver o balanço" cobre tanto os totais agregados quanto os gastos de outras pessoas — por isso
  o usuário comum vê apenas os próprios gastos (decisão confirmada com o usuário).
- A forma de desembolso (reembolso a funcionário / pagamento a fornecedor) continua disponível no
  formulário para todos; o usuário que pagou pode pedir reembolso a si mesmo.
- O comportamento de aprovação, rejeição, exclusão e o impacto no balanço financeiro não mudam.
