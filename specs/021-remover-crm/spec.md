# Feature Specification: Remover o módulo de CRM

**Feature Branch**: `021-remover-crm`

**Created**: 2026-06-04

**Status**: Draft

**Input**: User description: "Primeiramente retire toda a parte de CRM. Não estou usando agora e não
quero que cause confusão."

## Contexto

O CRM (Pipeline, Organizações, Métricas, negócios/deals) não está em uso e gera confusão na
navegação. O usuário quer **removê-lo por completo** — interface, código, menu e os **dados no
banco** (decisão confirmada: remoção total, irreversível). O que **não** é CRM permanece:
- **"Pipeline de Vendas" (`/vendas`)**: é do Financeiro (comissão/custo por evento) e fica.
- A integração de assinatura **ClickSign** era usada **apenas pelo CRM** (contrato de negócio) →
  sai junto.

Esta é a primeira de duas reformas pedidas; a segunda (unir Usuários + Funcionários) será uma
feature separada.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Navegação sem CRM (Priority: P1)

O usuário não vê mais a seção de CRM (Pipeline, Organizações, Métricas) no menu nem consegue
acessar suas telas.

**Acceptance Scenarios**:

1. **Given** qualquer usuário logado, **When** olha o menu lateral, **Then** não há itens de CRM
   (Pipeline / Organizações / Métricas).
2. **Given** uma URL antiga de CRM, **When** o usuário tenta acessá-la, **Then** ela não existe mais
   (página não encontrada), sem quebrar o resto do sistema.

---

### User Story 2 - Resto do sistema intacto (Priority: P1)

Remover o CRM não pode quebrar nenhuma outra parte: agenda, eventos, financeiro, orçamentos,
talentos, gastos e admin continuam funcionando.

**Acceptance Scenarios**:

1. **Given** o painel financeiro, **When** é aberto, **Then** carrega normalmente — sem o bloco de
   "CRM / Pipeline e Conversão" e sem erro.
2. **Given** a exclusão de um evento, **When** acontece, **Then** funciona normalmente (sem depender
   de CRM).
3. **Given** "Pipeline de Vendas" (Financeiro), **When** é aberto, **Then** continua funcionando.
4. **Given** as configurações do admin, **When** abertas, **Then** funcionam (sem a configuração de
   assinatura ClickSign, que era do CRM).

---

### User Story 3 - Dados de CRM removidos (Priority: P2)

Os dados do CRM (negócios, organizações, contatos, etapas, notas, lembretes) são removidos do banco.

**Acceptance Scenarios**:

1. **Given** o banco após a remoção, **When** consultado, **Then** as tabelas de CRM não existem
   mais.

---

### Edge Cases

- **Referência de evento ao CRM**: hoje, ao excluir um evento, o sistema "desvincula" negócios de
  CRM; com o CRM removido, essa etapa simplesmente deixa de existir (sem erro).
- **Configuração ClickSign no admin**: deixa de aparecer; integração era exclusiva do CRM.
- **Outras áreas que liam dados de CRM** (ex.: painel financeiro): deixam de exibir esse conteúdo,
  sem erro.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A seção de CRM (Pipeline, Organizações, Métricas) MUST ser removida do menu.
- **FR-002**: As telas/rotas de CRM MUST deixar de existir; URLs antigas retornam "não encontrado".
- **FR-003**: O painel financeiro MUST deixar de exibir o bloco de CRM (pipeline/conversão) e MUST
  continuar carregando normalmente.
- **FR-004**: A exclusão de eventos e demais fluxos que referenciavam CRM MUST continuar
  funcionando, sem a etapa de CRM.
- **FR-005**: As tabelas e dados de CRM MUST ser removidos do banco (remoção completa).
- **FR-006**: A integração ClickSign (exclusiva do CRM) MUST ser removida, incluindo sua
  configuração no admin; o restante do admin MUST continuar funcionando.
- **FR-007**: Áreas não-CRM (agenda, eventos, financeiro incl. "Pipeline de Vendas", orçamentos,
  talentos, gastos, admin, portal) MUST permanecer funcionando.
- **FR-008**: A remoção NÃO MUST afetar nenhum orçamento já salvo nem outros dados não-CRM.

### Key Entities *(include if feature involves data)*

- **Entidades de CRM** (negócio/deal, organização, contato, etapa, nota, lembrete): **removidas**.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 itens de CRM no menu; 0 rotas de CRM acessíveis.
- **SC-002**: Painel financeiro, admin e "Pipeline de Vendas" abrem sem erro após a remoção.
- **SC-003**: 0 tabelas de CRM no banco após a migração.
- **SC-004**: Nenhuma regressão nas áreas não-CRM (sistema sobe e as páginas principais respondem).

## Assumptions

- "Toda a parte de CRM" = blueprint/rotas, telas, itens de menu, modelos/tabelas, o bloco de CRM no
  painel financeiro, a referência na exclusão de evento e a integração ClickSign (exclusiva do CRM).
- "Pipeline de Vendas" (`/vendas`, Financeiro) **não** é CRM e permanece.
- Remoção de dados é **completa e irreversível** (decisão do usuário).
- A união de Usuários + Funcionários é uma **feature separada** (próxima).
- Migration escrita à mão (autogenerate do projeto está quebrado).
