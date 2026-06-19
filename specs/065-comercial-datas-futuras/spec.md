# Feature Specification: NF futura e parcelas com datas no comercial + recebimentos no painel

**Feature Branch**: `065-comercial-datas-futuras`

**Created**: 2026-06-19

**Status**: Draft

**Input**: User description: "Entrou um evento em que a nota será emitida numa data futura e o pagamento será feito em duas vezes em datas futuras. Precisamos habilitar registrar informações comerciais nesse estilo e pensar em como isso afeta o painel financeiro."

## Contexto

Hoje, nos dados comerciais de um evento, é possível registrar forma de pagamento (à vista,
dividido no PIX por quantidade, faturado/futuro com **uma** data) e marcar "emitir nota". Faltam
dois casos reais:

1. **NF emitida em data futura**: hoje só há a marcação "emitir nota" e o anexo do arquivo;
   não há como registrar **quando** a nota será emitida.
2. **Pagamento parcelado em datas futuras** (ex.: 2x): hoje o "dividido no PIX" guarda só a
   **quantidade** de parcelas, e o "faturado/futuro" guarda **uma** data. Não dá para registrar
   **cada parcela com sua própria data e valor**.

Decisões de produto já tomadas para esta feature:

- A **receita** continua sendo reconhecida no painel **pela data do evento** (como hoje) — não
  muda o DRE.
- O painel ganha uma **visão de "Recebimentos previstos / NF a emitir"** por data (fluxo de
  caixa), para enxergar o que entra e quando, sem alterar quando a receita conta.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar parcelas com data e valor (Priority: P1) 🎯 MVP

Como vendedor/financeiro, quero registrar o pagamento de um evento como um **cronograma de
parcelas**, cada uma com **data de vencimento e valor**, para refletir fielmente combinações como
"2x em datas futuras".

**Why this priority**: É o caso concreto que motivou o pedido.

**Independent Test**: Num evento, escolher pagamento parcelado em datas, adicionar 2 parcelas
(datas/valores), salvar e reabrir; as parcelas aparecem como cadastradas.

**Acceptance Scenarios**:

1. **Given** um evento, **When** escolho "parcelado em datas" e adiciono parcelas (data + valor),
   **Then** elas são salvas e exibidas ao reabrir.
2. **Given** parcelas cadastradas, **When** edito/removo/adiciono parcelas e salvo, **Then** o
   cronograma reflete as mudanças.
3. **Given** a soma das parcelas, **When** exibida, **Then** o usuário consegue conferir se bate
   com o valor de venda (aviso se divergir — informativo, não bloqueia).

---

### User Story 2 - Registrar a data prevista de emissão da NF (Priority: P1)

Como financeiro, quero registrar **quando** a nota fiscal será emitida (data futura), para não
perder o prazo e para o painel mostrar "NF a emitir".

**Why this priority**: Outra metade do pedido; evita esquecer a emissão.

**Acceptance Scenarios**:

1. **Given** um evento com "emitir nota", **When** informo a **data prevista de emissão**,
   **Then** ela é salva e exibida.
2. **Given** uma data de emissão futura, **When** chega/está próxima, **Then** o evento aparece
   na visão de "NF a emitir" do painel/financeiro.

---

### User Story 3 - Ver recebimentos previstos e NF a emitir no painel (Priority: P1)

Como financeiro, quero ver no painel uma lista dos **recebimentos previstos** (parcelas por data)
e das **notas a emitir** (por data), para planejar o fluxo de caixa — **sem** que isso mude a
receita reconhecida (que segue pela data do evento).

**Why this priority**: É o "como isso afeta o painel" pedido.

**Acceptance Scenarios**:

1. **Given** parcelas com datas no período visualizado, **When** abro o painel, **Then** vejo os
   recebimentos previstos daquele período (data, evento, valor), com total.
2. **Given** notas com data de emissão no período, **When** abro o painel, **Then** vejo a lista
   de NF a emitir (data, evento, valor).
3. **Given** a receita do período, **When** comparo com antes, **Then** ela é a **mesma** (o
   reconhecimento por data do evento não mudou).

---

### Edge Cases

- **Parcelas que não somam o valor de venda**: permitido, com aviso informativo (não bloqueia).
- **Parcela sem data ou sem valor**: não é salva (ou exige os dois campos).
- **Evento sem nota**: a data de emissão da NF não se aplica/ fica oculta.
- **Parcela já recebida**: pode ser marcada como recebida para sair de "previsto"; o comprovante
  de pagamento (já existente) continua funcionando.
- **Permissões**: editar dados comerciais segue as regras atuais (comercial/financeiro/admin).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST permitir registrar um **cronograma de parcelas** para um evento,
  cada parcela com **data de vencimento** e **valor**.
- **FR-002**: O usuário MUST poder adicionar, editar e remover parcelas e salvar o cronograma.
- **FR-003**: O sistema MUST permitir registrar a **data prevista de emissão da NF** para eventos
  com nota.
- **FR-004**: O painel financeiro MUST exibir uma visão de **recebimentos previstos** (parcelas)
  no período, com data, evento e valor, e um **total**.
- **FR-005**: O painel financeiro MUST exibir uma visão de **NF a emitir** (eventos com data de
  emissão no período), com data, evento e valor.
- **FR-006**: A **receita reconhecida** no painel MUST permanecer baseada na **data do evento**
  (sem alteração do DRE por causa desta feature).
- **FR-007**: O sistema MUST mostrar a **soma das parcelas** e indicar (informativo) se diverge do
  valor de venda do evento.
- **FR-008**: Uma parcela MUST poder ser marcada como **recebida**, saindo de "previsto".
- **FR-009**: Esta feature MUST preservar o comportamento atual dos demais métodos de pagamento
  (à vista, faturado/futuro, dividido por quantidade) e dos comprovantes de pagamento.

### Key Entities

- **Parcela de recebimento (nova)**: pertence a um evento; tem **data de vencimento**, **valor** e
  estado **recebida/prevista**. Representa um recebimento planejado.
- **Evento (existente)**: ganha a **data prevista de emissão da NF**; mantém valor de venda, data
  do evento (base da receita) e os campos comerciais atuais.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: É possível cadastrar um evento com 2 parcelas em datas futuras distintas e a data
  de emissão da NF, e tudo persiste ao reabrir.
- **SC-002**: O painel lista os recebimentos previstos e as NF a emitir do período, com totais
  corretos.
- **SC-003**: A receita reconhecida no painel para um período não muda em relação ao
  comportamento anterior (mesmo número).
- **SC-004**: Nenhuma regressão nos métodos de pagamento e comprovantes já existentes.

## Assumptions

- A receita continua reconhecida pela **data do evento** (decisão do cliente); as datas de NF e
  parcelas servem para **planejamento/fluxo de caixa** e lembretes, não para mudar o DRE.
- "Recebimentos previstos" e "NF a emitir" são visões **informativas** no painel/financeiro,
  filtradas pelo período já existente.
- O cronograma de parcelas é uma forma de pagamento adicional; os métodos atuais continuam
  disponíveis. A soma das parcelas idealmente bate com o valor de venda, mas divergência é só
  alertada (não bloqueia).
- Marcar parcela como recebida é um indicador de fluxo; o comprovante de pagamento (anexo) segue
  como o registro de prova.
- Permissões de edição comercial e visualização do painel seguem as já existentes.
