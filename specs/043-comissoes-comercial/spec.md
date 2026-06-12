# Feature Specification: Comissões visíveis para o time comercial (somente leitura)

**Feature Branch**: `043-comissoes-comercial`

**Created**: 2026-06-12

**Status**: Draft

**Input**: User description: "Precisamos fazer que essa tela de comissões seja visível para o time
comercial. Dessa forma eles podem acompanhar quais são as suas comissões e se já foram recebidas.
Mas sem poder editar, apenas visualizar e/ou entrar nos eventos para fazer algum ajuste."

## Contexto

A tela de Comissões (`/financeiro/comissoes`) hoje é exclusiva do financeiro/super admin. As
vendedoras não têm onde acompanhar suas comissões — precisam perguntar. A tela tem ações de
gestão (marcar pago, cancelar, reverter, processar estorno) que NÃO podem vazar para o comercial.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Vendedora acompanha as próprias comissões (Priority: P1)

Quem é do comercial abre a tela de Comissões e vê **apenas as suas** comissões do mês: evento,
data da venda, valor, status (a pagar / pago) e data de pagamento. Vê também seus estornos
pendentes, se houver.

**Acceptance Scenarios**:

1. **Given** uma vendedora logada, **When** abre Comissões, **Then** vê só comissões em que ela é a
   vendedora — nunca as de colegas.
2. **Given** uma comissão paga em 08/06, **Then** ela aparece com status "Pago" e a data.
3. **Given** o financeiro/super admin, **Then** continua vendo todas as comissões de todos.

---

### User Story 2 - Somente leitura para o comercial (Priority: P1)

Para o comercial, a tela não tem nenhum botão de gestão (marcar pago, cancelar ✕, reverter,
processar estorno) — e as ações são recusadas no servidor se forçadas.

**Acceptance Scenarios**:

1. **Given** uma vendedora na tela de Comissões, **Then** nenhum botão de ação aparece.
2. **Given** uma tentativa direta de marcar pago/cancelar por quem é só comercial, **Then** o
   servidor recusa.

---

### User Story 3 - Acesso fácil e link para o evento (Priority: P2)

O comercial encontra "Comissões" no menu lateral (junto do Pipeline de Vendas) e consegue abrir o
evento de cada comissão para ajustar dados da venda (permissão que já tem hoje).

**Acceptance Scenarios**:

1. **Given** uma vendedora logada, **Then** o menu lateral mostra "Comissões".
2. **Given** uma comissão vinculada a evento, **When** clica no título, **Then** abre a tela do
   evento.

---

### Edge Cases

- Comissão de evento excluído (sem vínculo): aparece só como texto, sem link.
- Vendedora sem comissões no mês: estado vazio amigável.
- Filtro de mês continua funcionando para todos.
- O total mostrado ao comercial considera apenas as comissões dela (não o total geral).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A tela de Comissões MUST ser acessível ao perfil comercial, mostrando somente as
  comissões (e estornos) do próprio usuário.
- **FR-002**: Para o comercial, a tela MUST ser somente leitura: sem botões de gestão; ações de
  mudança de status MUST continuar restritas a financeiro/super admin no servidor.
- **FR-003**: O menu lateral MUST exibir "Comissões" para o comercial.
- **FR-004**: O link do evento em cada comissão MUST continuar funcionando (ajustes são feitos na
  tela do evento, com as permissões já existentes).
- **FR-005**: Financeiro e super admin MUST manter a visão e as ações atuais sem mudança.

### Key Entities

- **Comissão** — registro por evento/vendedora com valor, status e data de pagamento (já existe).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das comissões exibidas a um comercial pertencem a ele.
- **SC-002**: 0 ações de gestão disponíveis/aceitas para o perfil comercial.
- **SC-003**: A vendedora encontra suas comissões em até 2 cliques (menu → Comissões).

## Assumptions

- "Time comercial" = perfil COMERCIAL (inclui quem também é financeiro/super admin — esses mantêm
  a visão completa).
- O comercial vê os próprios estornos pendentes (transparência do desconto futuro), sem poder
  processá-los.
- O botão "← Financeiro" do topo só aparece para quem tem acesso ao painel financeiro.
