# Feature Specification: Comissão padrão 2,5% + vendedor visível + taxa travada

**Feature Branch**: `023-comissao-2-5`

**Created**: 2026-06-04

**Status**: Draft

**Input**: User description: "A comissão padrão foi setada errada como 2%, deveria ser 2,5%. É o
primeiro mês de comissões automáticas (maio). Na aba comercial de cada evento, o comercial precisa
ver quem é o vendedor responsável. A taxa de comissão deve travar em 2,5% para o comercial, só
podendo ser alterada pelo super admin."

## Contexto

A comissão de cada evento é calculada com a **taxa do próprio evento**, ou — quando o evento não
tem taxa própria — com a **taxa padrão do sistema**. A taxa padrão foi configurada como 2%, mas o
correto é **2,5%**. Como maio é o primeiro mês de comissões automáticas e a maioria dos eventos usa
o padrão, ajustar o padrão para 2,5% faz maio sair correto. Além disso:
- O **comercial** precisa **ver o vendedor responsável** no evento (hoje só Financeiro/Superadmin vê).
- A **taxa de comissão** deve ficar **travada** para o comercial (e demais), **só o super admin**
  pode alterá-la por evento.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Comissão padrão correta (2,5%) (Priority: P1)

A taxa padrão do sistema passa a ser 2,5%. Eventos sem taxa própria passam a calcular comissão a
2,5%.

**Acceptance Scenarios**:

1. **Given** um evento sem taxa própria, **When** a comissão é calculada, **Then** usa 2,5%.
2. **Given** um evento com taxa própria definida pelo super admin, **When** a comissão é calculada,
   **Then** usa a taxa do evento (não o padrão).

---

### User Story 2 - Comercial vê o vendedor responsável (Priority: P1)

Na aba comercial de cada evento, qualquer pessoa do comercial vê quem é o vendedor responsável.

**Acceptance Scenarios**:

1. **Given** um usuário do comercial, **When** abre a aba comercial de um evento, **Then** vê o
   vendedor responsável.
2. **Given** Financeiro/Superadmin, **When** abrem a aba comercial, **Then** continuam podendo
   **escolher/alterar** o vendedor.

---

### User Story 3 - Taxa de comissão travada (só super admin altera) (Priority: P1)

Na aba comercial, a taxa de comissão aparece travada (somente leitura) para o comercial e o
financeiro; apenas o super admin pode alterá-la por evento.

**Acceptance Scenarios**:

1. **Given** um usuário do comercial ou financeiro, **When** vê a taxa de comissão do evento,
   **Then** ela aparece travada (não editável), mostrando a taxa vigente (a do evento ou 2,5%).
2. **Given** um super admin, **When** abre o evento, **Then** pode alterar a taxa de comissão
   daquele evento.
3. **Given** um usuário não-super-admin, **When** tenta enviar uma alteração de taxa, **Then** a
   taxa não é alterada.

---

### Edge Cases

- **Eventos passados sem taxa própria**: passam a usar 2,5% (efeito desejado — 2,5% é a taxa
  correta; é o primeiro mês de comissões automáticas).
- **Eventos com taxa própria** (definida pelo super admin): não mudam com a alteração do padrão.
- **Vendedor não definido**: o comercial vê "— não definido —".

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A taxa de comissão padrão do sistema MUST ser 2,5% (incluindo a correção do valor já
  configurado como 2%).
- **FR-002**: A aba comercial do evento MUST exibir o vendedor responsável para o comercial.
- **FR-003**: Financeiro/Superadmin MUST poder escolher/alterar o vendedor responsável (como hoje).
- **FR-004**: A taxa de comissão por evento MUST ser editável **apenas** pelo super admin; para os
  demais (comercial e financeiro) aparece **travada** (somente leitura), mostrando a taxa vigente.
- **FR-005**: Tentativa de alterar a taxa por quem não é super admin NÃO MUST surtir efeito (validado
  no servidor, não só escondido na tela).
- **FR-006**: A correção do padrão para 2,5% MUST valer em produção (aplicada no deploy), não só em
  desenvolvimento.
- **FR-007**: Eventos com taxa própria MUST permanecer com a sua taxa (não sobrescritos).

### Key Entities *(include if feature involves data)*

- **Configuração do sistema** (já existe): a taxa padrão de comissão passa a 2,5%.
- **Evento** (já existe): mantém a taxa própria opcional (só super admin define); exibe vendedor e
  taxa vigente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos eventos sem taxa própria calculam comissão a 2,5%.
- **SC-002**: O comercial vê o vendedor responsável em 100% dos eventos.
- **SC-003**: 0 alterações de taxa por não-super-admin surtem efeito.
- **SC-004**: A taxa padrão em produção fica 2,5% após o deploy.

## Assumptions

- A taxa "travada" exibida é a **vigente** do evento: a taxa própria, se houver; senão o padrão
  (2,5%).
- "Só super admin altera a comissão" implica que o Financeiro **deixa** de editar a taxa por evento
  (passa a só visualizar) — antes podia.
- A correção do padrão em produção é feita por migração de dados (atualiza o valor 2% → 2,5%).
- Não há recálculo/"congelamento" retroativo: maio deve mesmo sair a 2,5% (taxa correta).
