# Feature Specification: Unir Usuários + Funcionários numa só seção

**Feature Branch**: `022-unir-usuarios-funcionarios`

**Created**: 2026-06-04

**Status**: Draft

**Input**: User description: "A parte de usuários e de funcionários está redundante. O PIX está num
lugar, quanto recebe está em outro. Unir os dois numa seção apenas de Usuários."

## Contexto

Hoje há duas telas que listam as mesmas pessoas:
- **Usuários** (Admin): identidade — nome, e-mail, papéis, senha, **PIX**, ativo (só SUPERADMIN).
- **Funcionários** (Financeiro): **salário** — valor, tipo (semanal/quinzenal/comissão) e histórico
  (FINANCEIRO/SUPERADMIN).

Isso é redundante e confunde (PIX num lugar, "quanto recebe" em outro). O usuário quer **uma só
seção de Usuários** com tudo da pessoa: identidade + papéis + PIX + salário.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tudo da pessoa numa página só (Priority: P1)

Ao abrir um usuário, vê-se identidade, papéis, PIX e salário (com histórico) na mesma página — sem
precisar de uma tela separada de "Funcionários".

**Acceptance Scenarios**:

1. **Given** a página de um usuário, **When** ela é aberta, **Then** mostra os dados de identidade,
   PIX e o salário atual + histórico.
2. **Given** o menu, **When** o usuário olha, **Then** existe **uma** entrada "Usuários" (não há
   mais "Funcionários" separado).

---

### User Story 2 - Permissões corretas (Priority: P1)

O Superadmin edita tudo (identidade, papéis, senha, PIX, salário, excluir). O Financeiro acessa a
página de Usuários e edita apenas os **dados de pagamento** (PIX e salário) — não mexe em papéis,
senha nem exclusão.

**Acceptance Scenarios**:

1. **Given** um Superadmin, **When** abre um usuário, **Then** pode editar identidade, papéis, PIX,
   salário e excluir.
2. **Given** um Financeiro, **When** abre um usuário, **Then** edita PIX e salário, mas **não** vê
   nem aciona editar papéis/senha/excluir.
3. **Given** um usuário sem esses papéis, **When** tenta acessar a seção de Usuários, **Then** o
   acesso é negado.

---

### User Story 3 - Sem quebrar links antigos (Priority: P2)

Quem acessar as URLs antigas de "Funcionários" é levado para a seção unificada de Usuários.

**Acceptance Scenarios**:

1. **Given** uma URL antiga de Funcionários, **When** acessada, **Then** redireciona para a página
   correspondente em Usuários, sem erro.

---

### Edge Cases

- **Financeiro sem ser superadmin**: continua conseguindo registrar/editar salário (não perde o que
  tinha) e passa a editar PIX; mas não vê papéis/senha/exclusão.
- **Cálculos financeiros** que usam salário (custo de pessoal no painel) seguem iguais — muda só
  onde se edita, não como se calcula.
- **Lista de usuários**: mostra o salário atual de cada pessoa para quem tem acesso financeiro.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Deve existir **uma** seção "Usuários" que reúne identidade, papéis, PIX e salário
  (valor, tipo e histórico) de cada pessoa.
- **FR-002**: A seção "Funcionários" separada MUST deixar de existir (menu e telas), com as URLs
  antigas redirecionando para Usuários.
- **FR-003**: Superadmin MUST poder editar identidade, papéis, senha, PIX, salário e excluir.
- **FR-004**: Financeiro MUST poder acessar Usuários e editar **apenas** PIX e salário; NÃO MUST ver
  nem acionar edição de papéis, senha ou exclusão.
- **FR-005**: Usuários sem papel Superadmin/Financeiro NÃO MUST acessar a seção de Usuários.
- **FR-006**: O registro de salário (novo valor encerra o anterior, com histórico) MUST continuar
  funcionando, agora dentro da página de Usuários.
- **FR-007**: Os cálculos financeiros que usam salário MUST permanecer inalterados.
- **FR-008**: Nenhuma mudança de dados (PIX, salários já registrados) é perdida na unificação.

### Key Entities *(include if feature involves data)*

- **Usuário** (já existe): passa a concentrar identidade + PIX + salário (via histórico de salário).
- **Histórico de salário** (já existe): sem mudança; passa a ser gerenciado na página de Usuários.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Existe 1 seção de pessoas no menu (Usuários); 0 entradas de "Funcionários".
- **SC-002**: Em 1 página é possível ver/editar identidade, PIX e salário (conforme permissão).
- **SC-003**: Financeiro edita PIX e salário, e 0 vezes consegue alterar papéis/senha/excluir.
- **SC-004**: URLs antigas de Funcionários redirecionam para Usuários (0 páginas quebradas).
- **SC-005**: Cálculos financeiros (custo de pessoal) idênticos aos de antes.

## Assumptions

- A seção unificada vive na área de **Usuários** (Admin), agora acessível também ao Financeiro.
- "Dados de pagamento" que o Financeiro edita = PIX + salário (valor/tipo/histórico).
- Sem mudança de banco (PIX e histórico de salário já existem).
- A área Admin restante (Identidade do site, Logs, Sync, Desempenho) continua só para Superadmin.
