# Feature Specification: Usuários sem acesso (só pagamento) + limpeza da tela de Usuários

**Feature Branch**: `042-usuarios-sem-acesso`

**Created**: 2026-06-12

**Status**: Draft

**Input**: User description: "qual o sentido da identidade visual nessa tela? pode tirar e acho que
essa tela de identidade visual nao serve pra nada. pode excluir. Eu preciso poder adicionar dois
tipos de um usuario: um que é completo e crio acesso, email salario e tudo mais e um outro que é
apenas uma pessoa que recebe um salario e nao deve ter um acesso. Inclusive, ao clicar em novo
usuario abre uma tela que ja poderia ser mais completa, ja podendo colocar o pix, salario e tudo
mais."

## Contexto

Na tela de Usuários:
- Há um botão "Identidade visual" que não tem relação com usuários. Ele leva à tela de
  **Configurações** do sistema — que, apesar do rótulo confuso, guarda itens críticos: taxa de
  comissão padrão, data de início do sistema, endereço base (cálculo de viagem), chave do Google
  Maps, e o logo (exibido nas telas de login do sistema e do portal). **A tela não pode ser
  excluída sem perder essas funções** — o que será feito é tirar o botão da tela de Usuários e
  corrigir os rótulos "Identidade (Visual)" para "Configurações".
- Todo usuário criado precisa de email + senha (acesso ao sistema). Não há como cadastrar uma
  pessoa que apenas recebe salário (ex.: funcionário operacional) sem dar login a ela.
- O formulário "Novo usuário" só tem nome/email/senha/cargos — PIX e salário precisam ser
  preenchidos depois, em outra tela.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cadastrar pessoa só de pagamento (Priority: P1)

O super admin cadastra uma pessoa que recebe salário mas **não deve ter acesso** ao sistema: só
nome, PIX e salário. Essa pessoa nunca consegue fazer login, mas aparece na lista de usuários e na
folha de pagamentos do financeiro.

**Acceptance Scenarios**:

1. **Given** o formulário de novo usuário, **When** escolhe o tipo "Apenas pagamento (sem acesso)",
   **Then** os campos de email/senha/cargos somem e o cadastro exige apenas o nome.
2. **Given** uma pessoa sem acesso cadastrada com salário quinzenal, **Then** ela aparece na lista
   de usuários com selo "sem acesso" e entra na folha de pagamentos do financeiro normalmente.
3. **Given** uma pessoa sem acesso, **When** alguém tenta logar com qualquer credencial dela,
   **Then** o acesso é negado.

---

### User Story 2 - Novo usuário completo em uma tela só (Priority: P1)

Ao criar um usuário (com ou sem acesso), o super admin já preenche PIX (chave + tipo) e salário
(valor, tipo de pagamento, início de vigência) na mesma tela — sem precisar editar depois.

**Acceptance Scenarios**:

1. **Given** o formulário de novo usuário com acesso, **When** preenche nome, email, senha, cargos,
   PIX e salário, **Then** tudo é salvo de uma vez (salário já vigente no histórico).
2. **Given** PIX e salário em branco, **Then** o usuário é criado sem esses dados (continuam
   opcionais, editáveis depois).

---

### User Story 3 - Conceder acesso depois (Priority: P2)

Uma pessoa cadastrada sem acesso pode ser promovida: o super admin define email + senha temporária
na tela de edição e ela passa a poder logar (trocando a senha no primeiro acesso).

**Acceptance Scenarios**:

1. **Given** a tela de edição de uma pessoa sem acesso, **Then** as seções de cargos/resetar senha
   não aparecem; aparece a opção "Conceder acesso".
2. **When** o super admin concede acesso com email + senha temporária, **Then** a pessoa loga e é
   obrigada a trocar a senha.

---

### User Story 4 - Tela de Usuários sem o botão fora de contexto (Priority: P3)

O botão "Identidade visual" sai da tela de Usuários. A tela de Configurações continua existindo
(acessível pelo painel admin), com os rótulos corrigidos de "Identidade (Visual)" para
"Configurações".

**Acceptance Scenarios**:

1. **Given** a tela de Usuários, **Then** não existe mais botão "Identidade visual".
2. **Given** o painel/menu admin, **Then** o item se chama "Configurações" e a tela continua
   funcionando (comissão padrão, data de início, logo etc.).

---

### Edge Cases

- Pessoa sem acesso não tem email: a lista mostra "—" no lugar (nunca "None").
- Email de pessoa sem acesso é opcional (apenas contato); se preenchido, vale a regra de email
  único.
- Excluir/editar pessoa sem acesso funciona como qualquer usuário (PIX/salário inclusive por
  financeiro).
- Usuários existentes não mudam: todos continuam com acesso.
- Pessoa sem acesso não entra em listas de vendedores (não tem cargo) nem recebe convites.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O cadastro de usuário MUST oferecer dois tipos: "Com acesso ao sistema" (nome, email,
  senha temporária, cargos) e "Apenas pagamento" (só nome obrigatório; sem login).
- **FR-002**: O formulário de novo usuário MUST permitir preencher PIX (chave + tipo) e salário
  (valor, tipo, início de vigência, observações) na criação — opcionais.
- **FR-003**: Pessoas sem acesso MUST ser recusadas no login em qualquer circunstância.
- **FR-004**: A lista de usuários MUST diferenciar pessoas sem acesso (selo) e exibir "—" quando
  não houver email.
- **FR-005**: A tela de edição de pessoa sem acesso MUST ocultar cargos/resetar senha e oferecer
  "Conceder acesso" (email + senha temporária, troca obrigatória no primeiro login) — só super
  admin.
- **FR-006**: O botão "Identidade visual" MUST sair da tela de Usuários; os rótulos da tela de
  configurações MUST passar a "Configurações". A tela em si permanece (funções críticas).
- **FR-007**: Pessoas sem acesso MUST aparecer na folha de pagamentos do financeiro como qualquer
  funcionário com salário vigente.

### Key Entities

- **Usuário** — ganha a distinção "tem acesso" (login permitido) vs. "apenas pagamento"; email e
  senha passam a ser opcionais para quem não tem acesso.
- **Salário / PIX** — mesmos registros de hoje, agora preenchíveis já no cadastro.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Cadastrar uma pessoa só de pagamento (nome + PIX + salário) leva 1 tela e 1 envio.
- **SC-002**: 0 logins possíveis para pessoas sem acesso.
- **SC-003**: 100% das pessoas com salário vigente (com ou sem acesso) aparecem na folha de
  pagamentos.
- **SC-004**: A tela de Usuários não exibe mais nada de "identidade visual".

## Assumptions

- A tela `/admin/settings` ("identidade visual" no rótulo antigo) NÃO é excluída: ela concentra
  taxa de comissão padrão, data de início do sistema, endereço base, chave Google Maps e logo
  (usado nas telas de login). A interpretação adotada: remover o botão fora de contexto e corrigir
  os rótulos. Se o usuário quiser mesmo excluir a tela, essas funções precisariam de novo lar.
- "Recebe comissão" continua com padrão atual (ligado) e editável na tela de edição.
- Pessoas sem acesso não recebem cargo nenhum (cargos implicam permissões de login).
- Usuários existentes permanecem todos como "com acesso".
