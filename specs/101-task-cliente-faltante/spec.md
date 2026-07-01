# Feature Specification: Task para o comercial completar clientes de eventos sem cliente

**Feature Branch**: `101-task-cliente-faltante`

**Created**: 2026-07-01

**Status**: Draft

**Input**: "Eventos sem cliente a partir da data de início do sistema configurada no painel do admin geram uma task para o comercial completar."

## Contexto

Com a associação de clientes a eventos (features 094/100), muitos eventos — especialmente os que entram
pela sincronização da agenda — ficam **sem cliente associado**. O comercial precisa ser lembrado de
**completar o cliente** desses eventos.

A **"Data de início do sistema"** já existe no painel do admin (`release_date`) e já é o corte usado
pelas demais tarefas da home (casting, figurino, ensaio, cobranças). Esta feature adiciona mais uma
**tarefa do comercial**: listar os eventos **sem cliente** a partir dessa data, para o comercial
completar.

## Decisões de escopo (confirmadas)

- **Quais eventos geram a task**: **todos os eventos, exceto ENSAIO**, a partir da data de início, que
  **não tenham cliente** associado — mesmo sem venda registrada.
- **Onde aparece**: no bloco **Comercial** da home (junto de "Sem valor de venda" e "Cobranças
  pendentes"), visível para quem já vê as tarefas comerciais.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver e completar eventos sem cliente (Priority: P1) 🎯 MVP

Como comercial, quero ver na home uma lista de **eventos sem cliente** (a partir da data de início do
sistema) para **associar o cliente** de cada um.

**Why this priority**: É a feature inteira — sem a lista, o comercial não é lembrado de completar.

**Independent Test**: Com um evento futuro (a partir da data de início) sem cliente, abrir a home como
comercial e ver esse evento na lista de "Sem cliente"; associar um cliente e ver o item sair da lista.

**Acceptance Scenarios**:

1. **Given** um evento a partir da data de início, **When** ele não tem cliente associado, **Then** ele
   aparece como tarefa "Sem cliente" no bloco Comercial da home.
2. **Given** que associo um cliente a esse evento, **When** volto à home, **Then** ele **não** aparece
   mais na lista de "Sem cliente".
3. **Given** um evento **anterior** à data de início, **When** ele está sem cliente, **Then** ele **não**
   gera task (fora da janela).
4. **Given** um evento do tipo **ENSAIO** sem cliente, **When** vejo a home, **Then** ele **não** gera
   task (ensaios são excluídos).
5. **Given** que não sou comercial (nem financeiro/super admin), **When** vejo a home, **Then** **não**
   vejo a lista de eventos sem cliente.

### Edge Cases

- **Evento satélite de um grupo**: não gera task própria (herda o comercial do evento principal), como já
  ocorre em "Sem valor de venda".
- **Data de início não configurada**: usa **hoje** como corte (mesmo comportamento das demais tarefas).
- **Evento com cliente removido depois**: volta a aparecer na lista enquanto ficar sem cliente.
- **Contagem do bloco Comercial**: a pendência "Sem cliente" entra no total de pendências do bloco
  Comercial (junto de sem valor e cobranças).

## Requirements *(mandatory)*

- **FR-001**: A home MUST listar, para o comercial, os **eventos sem cliente** a partir da **data de
  início do sistema** (configurada no painel do admin), como uma tarefa a completar.
- **FR-002**: A lista MUST **excluir** eventos do tipo **ENSAIO** e **eventos satélite** de grupo.
- **FR-003**: Um evento MUST **sair** da lista assim que **um** cliente for associado a ele.
- **FR-004**: A lista MUST usar o mesmo **corte de data** das demais tarefas da home (a data de início do
  sistema, ou hoje se não configurada).
- **FR-005**: A lista MUST ser visível apenas para quem já vê as tarefas **comerciais** (comercial,
  financeiro ou super admin), no bloco Comercial.
- **FR-006**: Cada item MUST permitir **abrir o evento** para associar o cliente, e MUST contar como
  pendência no resumo do bloco Comercial.

## Key Entities *(include if feature involves data)*

- **Evento** (existente): entra na lista quando, a partir da data de início, **não** possui nenhum
  cliente associado (e não é ENSAIO nem satélite). Nenhum dado novo é criado — a tarefa é **derivada**.
- **Data de início do sistema** (existente, `release_date` em configurações): define a janela das
  tarefas, inclusive esta.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos eventos elegíveis (a partir da data, não-ENSAIO, não-satélite) **sem cliente**
  aparecem na lista do comercial.
- **SC-002**: Ao associar um cliente, o evento **sai** da lista na próxima visualização (0 falsos
  pendentes).
- **SC-003**: Eventos **anteriores** à data de início e **ENSAIOs** **nunca** aparecem na lista.
- **SC-004**: A lista é vista apenas por papéis comerciais; nenhum outro papel a vê.

## Assumptions

- **"Sem cliente"** = evento sem **nenhuma** associação de cliente (fonte de verdade da feature 100).
- **Tarefa derivada**: não há novo modelo/tabela — a lista é calculada na home, como as demais tarefas
  (casting/figurino/cobranças).
- **Exclusão de satélites** segue o mesmo critério de "Sem valor de venda" (satélite herda o comercial do
  principal).
- **Permissões**: reutiliza o `show_comercial` já existente (comercial/financeiro/super admin).
- **A data já é configurável** no painel do admin (`release_date`); esta feature apenas a consome — só
  ajusta o texto de ajuda para mencionar a nova tarefa.
