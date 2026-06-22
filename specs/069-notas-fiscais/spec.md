# Feature Specification: Notas fiscais — task de emissão + custo no balanço + múltiplas notas

**Feature Branch**: `069-notas-fiscais`

**Created**: 2026-06-22

**Status**: Draft

**Input**: "Quando o vendedor diz que o valor final é com nota fiscal, gera uma task para o super
admin emitir a nota (subir o arquivo e marcar como emitida conclui a task). O vendedor pode subir
a nota já na venda. Para o balanço, apenas eventos com nota: pega o valor total e subtrai 16% (o
que pago de nota); o que sobra é dividido para cachês e comissão. No painel financeiro mostrar por
mês quanto gastamos com pagamento de nota, com visualização detalhada de quais eventos geraram esse
custo. Pode ser necessário emitir mais de uma nota, em datas diferentes."

## Contexto

Hoje o evento tem só um flag `with_invoice`, um único arquivo de nota e uma única data prevista de
emissão. A DRE já desconta 16% (taxa configurável) das vendas com nota. Faltam três coisas:

1. **Fluxo de emissão**: não existe a "tarefa" para o super admin emitir a nota, nem o estado
   *a emitir → emitida*.
2. **Múltiplas notas por evento**, cada uma com **valor e data próprios** (a soma fecha o total).
3. **Relatório mensal do custo de nota** (16% por nota), reconhecido pelo **mês de emissão**, com
   visão detalhada de quais eventos/notas geraram o custo.

## Decisões do cliente (clarificações)

- **Múltiplas notas**: cada nota tem **valor + data próprios**; a soma das notas deve fechar o valor
  total da venda; o custo de 16% é calculado **por nota**.
- **Mês do custo de nota**: o custo de cada nota entra no **mês da emissão** (visão de caixa). O
  balanço/DRE continua reconhecendo imposto pela **data do evento** (competência), como hoje.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Vendedor marca "com nota" e gera tarefa de emissão (Priority: P1) 🎯 MVP

Como vendedor, ao fechar uma venda "com nota fiscal", quero registrar uma ou mais notas (valor +
data) para que apareça uma **tarefa para o super admin emitir** cada nota. Posso já anexar a nota
na hora da venda (o que marca a nota como emitida).

**Why this priority**: É o coração do fluxo de emissão pedido.

**Independent Test**: Em um evento com nota, adicionar uma nota (valor + data) sem arquivo → ela
aparece como **a emitir** na lista de tarefas do super admin; adicionar outra já com arquivo → ela
nasce **emitida** e não vira tarefa.

**Acceptance Scenarios**:

1. **Given** uma venda marcada "com nota", **When** o vendedor adiciona uma nota (valor + data) sem
   arquivo, **Then** essa nota fica **a emitir** e aparece na lista de notas a emitir do super admin.
2. **Given** uma nota **a emitir**, **When** o super admin sobe o arquivo e marca como **emitida**,
   **Then** a tarefa some da lista de pendências e a nota fica registrada como emitida (com arquivo).
3. **Given** uma venda "com nota", **When** o vendedor já anexa o arquivo da nota na venda, **Then**
   a nota nasce **emitida** (não gera tarefa).

---

### User Story 2 - Múltiplas notas em datas diferentes (Priority: P1)

Como comercial/super admin, quero registrar **mais de uma nota** para o mesmo evento, cada uma com
valor e data próprios, para casos em que a NF é emitida em partes/datas diferentes.

**Independent Test**: Em um evento de R$10.000 com nota, registrar NF1 R$5.000 em 10/06 e NF2
R$5.000 em 10/07; o sistema mostra as duas, soma R$10.000 e avisa se a soma não fechar o total.

**Acceptance Scenarios**:

1. **Given** um evento com nota, **When** registro duas notas com valores e datas distintas,
   **Then** ambas são salvas e listadas com seus valores/datas/estado.
2. **Given** notas cuja soma ≠ valor total da venda, **When** salvo, **Then** o sistema **sinaliza**
   a divergência (sem bloquear), para o usuário conferir.
3. **Given** uma nota registrada, **When** removo a nota, **Then** ela sai da lista (e das tarefas/
   custos).

---

### User Story 3 - Custo de nota por mês de emissão, com detalhe (Priority: P1)

Como financeiro/super admin, quero ver **por mês quanto gastamos de nota** (16% por nota emitida),
podendo abrir o detalhe de **quais eventos/notas** geraram esse custo.

**Independent Test**: Com NF1 emitida em junho e NF2 em julho (R$5.000 cada, 16%), o painel mostra
R$800 de custo de nota em junho e R$800 em julho; o detalhe lista o evento e a nota de cada custo.

**Acceptance Scenarios**:

1. **Given** notas emitidas no período, **When** abro o painel financeiro no mês, **Then** vejo o
   **total de custo de nota** do mês (soma de 16% das notas com emissão no mês).
2. **Given** o total de custo de nota do mês, **When** abro o detalhe, **Then** vejo a lista de
   eventos/notas (valor da nota, data de emissão e custo de 16%).
3. **Given** o período filtrado, **When** mudo o filtro de período, **Then** o custo de nota e o
   detalhe acompanham o período selecionado (pela data de emissão da nota).

---

### Edge Cases

- **Venda sem nota** (`with_invoice = false`): não gera notas, tarefas nem custo de nota.
- **Nota a emitir sem data**: aparece nas pendências, mas sem data não entra em nenhum mês do
  relatório de custo (até ser emitida com data).
- **Soma das notas ≠ total**: permitido, apenas sinalizado.
- **Cortesia/permuta**: venda tratada como 0 → sem custo de nota.
- **Eventos antigos** (feature 065): a nota única existente (`invoice_file`/`invoice_due_date`) é
  migrada para uma nota no novo formato, sem perda.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Um evento "com nota" MUST poder ter **uma ou mais notas**, cada uma com **valor** e
  **data de emissão** próprios e um **estado** (a emitir | emitida) e um **arquivo** opcional.
- **FR-002**: O sistema MUST exibir ao **super admin** a lista de notas **a emitir** como tarefas;
  subir o arquivo e marcar como **emitida** MUST concluir a tarefa (sai da lista).
- **FR-003**: O **vendedor** MUST poder registrar nota(s) na venda; se já anexar o arquivo, a nota
  MUST nascer **emitida**.
- **FR-004**: O sistema MUST sinalizar (sem bloquear) quando a **soma das notas ≠ valor total** da
  venda.
- **FR-005**: O painel financeiro MUST mostrar, **por mês**, o **custo de nota** = 16% (taxa
  configurável, `SiteSetting.tax_rate`) de cada **nota com data de emissão no mês**.
- **FR-006**: O painel MUST oferecer **detalhe** do custo de nota do período: evento, valor da nota,
  data de emissão e custo (16%).
- **FR-007**: O balanço/DRE MUST continuar reconhecendo o imposto sobre vendas com nota pela **data
  do evento** (competência), como hoje — esta feature **não** altera a cascata da DRE.
- **FR-008**: A nota única pré-existente de cada evento (065) MUST ser **migrada** para o novo
  formato (uma nota), preservando arquivo e data; se já tinha arquivo, fica **emitida**, senão
  **a emitir**.
- **FR-009**: Remover uma nota MUST removê-la das listas de tarefas e dos custos.
- **FR-010**: Os valores monetários da nota MUST usar a **máscara padrão de R$** do sistema.

### Key Entities

- **Nota fiscal do evento (novo)**: pertence a um evento; tem **valor**, **data de emissão**,
  **estado** (a emitir | emitida), **arquivo** (opcional) e marca de quando foi emitida.
- **Evento (existente)**: mantém `with_invoice` ("venda exige nota"); passa a ter **várias** notas.
- **Configuração (existente)**: `tax_rate` (16% padrão) define o percentual do custo de nota.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das vendas "com nota" sem arquivo aparecem como tarefa de emissão para o super
  admin; ao marcar emitida, somem das pendências.
- **SC-002**: É possível registrar ≥2 notas com valores/datas diferentes no mesmo evento e o sistema
  sinaliza quando a soma ≠ total.
- **SC-003**: O custo de nota mensal bate com 16% da soma das notas emitidas naquele mês, com
  detalhe por evento/nota.
- **SC-004**: A DRE/balanço permanece igual ao comportamento atual (sem regressão na cascata).
- **SC-005**: Nenhum evento perde a nota antiga após a migração.

## Assumptions

- "Custo de nota" = `tax_rate` (16% padrão) aplicado ao **valor de cada nota**.
- O relatório mensal de custo de nota é uma **visão de caixa** (mês da emissão), separada da DRE
  (competência por data do evento) — as duas coexistem.
- Comissão e cachês continuam calculados como hoje; "dividido para cachês e comissão" descreve a
  cascata atual (total − imposto − cachês − comissão), não redefine a base da comissão.
- Permissões: registrar/editar notas = mesma regra do bloco comercial (COMERCIAL/FINANCEIRO/
  SUPERADMIN); marcar **emitida** e ver pendências de emissão = **SUPERADMIN** (e FINANCEIRO).
- Sem mudança na forma de recebimento (parcelas/`EventInstallment`) — nota é independente de
  recebimento.
