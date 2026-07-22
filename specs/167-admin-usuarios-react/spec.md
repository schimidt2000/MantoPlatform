# Feature Specification: Gestão de Usuários (Admin) em React

**Feature Branch**: `167-admin-usuarios-react`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Migrar a gestão de usuários do blueprint `admin` (9 rotas) para
React + API JSON, fatia da User Story 6 (Cauda Administrativa) da migração 144. Escopo: listar
usuários, criar usuário (com ou sem acesso ao sistema), editar identidade/papéis, atualizar
PIX, registrar salário, conceder acesso a pessoa só-pagamento, resetar senha, excluir usuário.
RBAC: `require_users_access` (SUPERADMIN ou FINANCEIRO, para listar/editar-PIX/salário) vs.
`require_superadmin` (identidade/papéis/criar/conceder-acesso/resetar-senha/excluir)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Listar e consultar usuários (Priority: P1)

Como usuário Superadmin ou Financeiro, preciso ver a lista de todos os usuários do sistema (com
o salário vigente de cada um) pela interface React.

**Why this priority**: é a tela de entrada de todo o módulo — sem ela, nenhuma das ações abaixo
tem como ser alcançada pela interface nova.

**Independent Test**: abrir a lista de usuários em React com um usuário Superadmin e com um
usuário Financeiro, e conferir que os dados batem com a tela antiga (`/admin/users`) para os
dois.

**Acceptance Scenarios**:

1. **Given** um usuário Superadmin ou Financeiro autenticado, **When** ele abre a lista de
   usuários em React, **Then** vê todos os usuários (ordenados por id) com o salário vigente de
   cada um (quando houver).
2. **Given** um usuário sem nenhum dos dois papéis, **When** ele tenta acessar a lista ou a API
   diretamente, **Then** recebe 403.

---

### User Story 2 - Criar usuário (Priority: P2)

Como Superadmin, preciso criar um usuário novo — com acesso ao sistema (email + senha
temporária + papéis) ou só para receber pagamento (sem login) — opcionalmente já com PIX e
salário.

**Why this priority**: é a ação de escrita mais completa do módulo (mistura os três
sub-formulários — identidade, PIX, salário) e a mais restrita (só Superadmin) — vem logo após a
leitura por ser o próximo passo natural do fluxo.

**Independent Test**: criar um usuário com acesso (papéis + senha temporária) e um usuário só-
pagamento (sem email/senha), cada um com PIX e salário preenchidos, e conferir que os dados
gravados são idênticos aos que a tela antiga gravaria para a mesma entrada.

**Acceptance Scenarios**:

1. **Given** um Superadmin autenticado, **When** ele cria um usuário "com acesso" com nome,
   email, senha temporária e papéis, **Then** o usuário é criado com `must_change_password=true`
   e os papéis selecionados.
2. **Given** o mesmo Superadmin, **When** ele cria uma pessoa "só pagamento" (sem email/senha),
   **Then** a pessoa é criada com `has_access=false`, sem papéis.
3. **Given** um email já cadastrado, **When** o Superadmin tenta criar outro usuário com o mesmo
   email, **Then** a API recusa com mensagem de campo (400).
4. **Given** PIX e/ou salário preenchidos no mesmo formulário de criação, **When** o usuário é
   criado, **Then** o PIX é salvo direto no usuário e um registro de salário vigente é criado
   junto — mesma regra de hoje (seção de salário é opcional; "somente comissão" zera o valor).
5. **Given** um usuário sem papel Superadmin, **When** ele tenta criar usuário pela API
   diretamente, **Then** recebe 403.

---

### User Story 3 - Editar identidade e papéis (Priority: P3)

Como Superadmin, preciso editar nome, email, papéis, status ativo/inativo e a flag de
comissão de um usuário existente.

**Why this priority**: é a segunda ação mais completa (mesma superfície de validação de e-mail
único da criação), mas menos frequente que criar — usuários existentes mudam menos que a
frequência de cadastro de novos.

**Independent Test**: editar nome/papéis/status de um usuário existente e conferir que os dados
batem com o que a tela antiga gravaria para a mesma entrada; tentar editar como Financeiro
(sem Superadmin) e confirmar 403 nessa ação específica (Financeiro só edita PIX/salário, US4).

**Acceptance Scenarios**:

1. **Given** um Superadmin autenticado, **When** ele edita nome, papéis, status ativo e a flag
   de comissão de um usuário, **Then** os dados são persistidos — papéis só mudam se o usuário
   tiver acesso (`has_access=true`).
2. **Given** um usuário com acesso sem email preenchido, **When** o Superadmin tenta salvar,
   **Then** a API recusa (400) — email é obrigatório para quem tem acesso.
3. **Given** um usuário Financeiro (sem Superadmin), **When** ele tenta editar identidade/papéis
   pela API, **Then** recebe 403 — mesmo tendo acesso de leitura à ficha do usuário.

---

### User Story 4 - PIX, salário, conceder acesso, resetar senha e excluir (Priority: P4)

Como Superadmin ou Financeiro (conforme a ação), preciso atualizar a chave PIX de um usuário,
registrar um novo salário, conceder acesso ao sistema para alguém cadastrado só-pagamento,
resetar a senha de um usuário e (só Superadmin) excluir um usuário sem histórico financeiro
vinculado.

**Why this priority**: são as ações mais pontuais do módulo — cada uma é uma mutação pequena e
independente das demais; vêm por último por serem, individualmente, a menor fatia de uso.

**Independent Test**: atualizar o PIX e registrar um salário como usuário Financeiro; conceder
acesso, resetar senha e excluir como Superadmin — incluindo o caso de exclusão bloqueada por
histórico financeiro e o caso de auto-exclusão bloqueada.

**Acceptance Scenarios**:

1. **Given** um usuário Financeiro ou Superadmin, **When** ele atualiza a chave PIX de um
   usuário, **Then** o dado é persistido.
2. **Given** o mesmo usuário, **When** ele registra um novo salário, **Then** o salário vigente
   anterior (se houver) é encerrado na data de início do novo, e o novo passa a vigorar — mesma
   regra de hoje; tipo de pagamento inválido ou valor ausente (fora de "somente comissão")
   recusa com mensagem de erro.
3. **Given** um Superadmin, **When** ele concede acesso a uma pessoa só-pagamento (email + senha
   temporária), **Then** ela passa a ter `has_access=true` e `must_change_password=true`.
4. **Given** um Superadmin, **When** ele reseta a senha de um usuário, **Then** a nova senha
   temporária é definida e `must_change_password=true`.
5. **Given** um Superadmin, **When** ele tenta excluir um usuário sem nenhum histórico
   financeiro vinculado (comissões, orçamentos, gastos extras, vendas de eventos), **Then** o
   usuário é excluído (folha de pagamento e vínculos opcionais são desfeitos junto).
6. **Given** um usuário com histórico financeiro vinculado, **When** o Superadmin tenta excluí-
   lo, **Then** a API recusa (400) com a lista do que está bloqueando, orientando desativar em
   vez de excluir.
7. **Given** o próprio usuário autenticado, **When** ele tenta excluir a si mesmo, **Then** a
   API recusa (400).
8. **Given** um usuário Financeiro (sem Superadmin), **When** ele tenta conceder acesso, resetar
   senha ou excluir pela API, **Then** recebe 403 — essas três ações são exclusivas de
   Superadmin.

---

### Edge Cases

- Seção de salário deixada em branco na criação/edição → nenhum registro de salário é criado,
  sem erro (comportamento hoje já opcional).
- Tipo de pagamento "somente comissão" → salário sempre gravado como 0, independente do valor
  digitado.
- Concessão de acesso a usuário que já tem acesso → recusada com mensagem específica.
- Exclusão do próprio usuário logado → sempre bloqueada, mesmo sendo Superadmin.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE expor a lista de usuários (com salário vigente de cada um) como
  endpoint JSON, restrito a SUPERADMIN/FINANCEIRO.
- **FR-002**: O sistema DEVE expor a criação de usuário (com acesso ou só-pagamento, papéis,
  PIX e salário opcionais) como endpoint JSON, restrito a SUPERADMIN, reaproveitando as mesmas
  validações de hoje (email único, email+senha obrigatórios para "com acesso", validação de
  salário/tipo de pagamento).
- **FR-003**: O sistema DEVE expor a edição de identidade/papéis/status/comissão de um usuário
  como endpoint JSON, restrito a SUPERADMIN, com as mesmas validações de hoje (email obrigatório
  se `has_access`, email único).
- **FR-004**: O sistema DEVE expor a atualização de PIX e o registro de novo salário como
  endpoints JSON, restritos a SUPERADMIN/FINANCEIRO, reaproveitando exatamente as regras de
  validação de salário/tipo de pagamento já existentes.
- **FR-005**: O sistema DEVE expor conceder-acesso, resetar-senha e excluir usuário como
  endpoints JSON, restritos a SUPERADMIN — incluindo os bloqueios de hoje (auto-exclusão,
  histórico financeiro vinculado).
- **FR-006**: Toda validação de erro (email duplicado, campo obrigatório, salário inválido, bloqueio
  de exclusão) DEVE retornar mensagem amigável em pt-BR, incluindo o campo específico quando
  aplicável, para o formulário React destacar o campo certo sem apagar o que foi digitado.
- **FR-007**: O comportamento das rotas Jinja antigas (`/admin/users*`) DEVE permanecer idêntico
  ao de antes desta fatia até serem desativadas — sem regressão enquanto ambas coexistirem.

### Key Entities

- **Usuário (User)**: nome, email (opcional para só-pagamento), senha, papéis, status ativo,
  flag de comissão, PIX; já existente — esta fatia não adiciona campos.
- **Histórico de Salário (SalaryHistory)**: valor, tipo de pagamento, data de início/fim,
  observações; já existente — um usuário tem no máximo um salário vigente (`end_date=null`) por
  vez.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário Superadmin consegue listar, criar, editar, conceder acesso, resetar
  senha e excluir usuários inteiramente pela interface React, sem abrir a tela antiga; um
  usuário Financeiro consegue listar, atualizar PIX e registrar salário pela mesma interface.
- **SC-002**: Os dados gravados por qualquer ação em React são idênticos aos que a tela antiga
  gravaria para a mesma entrada — verificado por paridade automatizada.
- **SC-003**: Nenhuma ação restrita a Superadmin (criar, editar identidade, conceder acesso,
  resetar senha, excluir) é executável por um usuário Financeiro puro nem por qualquer outro
  papel — 403 em todos os casos, tanto na tela quanto na API.

## Assumptions

- Valores monetários (salário) usam `@manto/money` (formatBRL/parseBRL) como fonte única no
  frontend; o backend continua recebendo/validando o valor já convertido para inteiro
  (`parse_brl_int`), sem reimplementar a máscara.
- Fora do escopo desta fatia: `/admin/settings`, `/admin/logs`, `/admin/sync`,
  `/admin/desempenho`, `/admin/portal-announcement`, `/admin/migrar-arquivos`,
  `/admin/importar-catalogo` e `/admin/catalogo/*` — cada um é uma fatia futura própria da US6
  (168 e 169).
