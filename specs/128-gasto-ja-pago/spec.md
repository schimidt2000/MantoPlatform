# Feature Specification: Gasto Extra Já Nasce Pago

**Feature Branch**: `128-gasto-ja-pago`

**Created**: 2026-07-14

**Status**: Draft

**Input**: "Na página de gastos extras eu quero que seja possível eu criar um gasto que
já nasça como pago. Porque eu hoje, por exemplo, paguei uma conta a partir da conta da
Manto Produções mesmo, do próprio PIX — não precisa ser reembolsado a ninguém. Ele é um
pagamento a fornecedor que não precisa ir para a planilha de pagamentos."

## Contexto

Hoje, ao registrar um gasto extra com desembolso (reembolso a funcionário ou pagamento a
fornecedor), ele sempre nasce como "a pagar" — e, quando aprovado, sempre aparece na
Planilha de Pagamentos esperando uma ação (marcar como pago, no banco, etc.). Mas às
vezes o pagamento já foi feito na hora, direto da conta da empresa (ex.: PIX para um
fornecedor), sem passar por nenhum fluxo de reembolso. Hoje não existe como registrar
esse gasto sem ele "poluir" a Planilha de Pagamentos com um item que, na prática, já está
resolvido.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar um gasto que já foi pago na hora (Priority: P1)

Um usuário paga um fornecedor direto da conta da empresa (PIX, na hora) e depois registra
esse gasto no sistema. Ao preencher o formulário de novo gasto, ele marca que o pagamento
já foi feito — o gasto nasce com esse pagamento já resolvido, sem precisar de nenhuma
ação posterior na Planilha de Pagamentos.

**Why this priority**: é o pedido central — sem isso, todo gasto com desembolso vira uma
pendência na planilha, mesmo quando já está pago.

**Independent Test**: registrar um gasto com "Pagamento a fornecedor" marcando "já foi
pago"; aprovar o gasto; abrir a Planilha de Pagamentos do mês e confirmar que esse gasto
NÃO aparece nela, em nenhuma situação (a pagar, no banco ou pago).

**Acceptance Scenarios**:

1. **Given** o formulário de registrar um gasto com desembolso (reembolso ou
   fornecedor), **When** o usuário marca que o pagamento já foi feito, **Then** o gasto é
   registrado já com o desembolso marcado como pago.
2. **Given** um gasto registrado dessa forma e depois aprovado por um super admin,
   **When** a Planilha de Pagamentos do mês correspondente é aberta, **Then** esse gasto
   não aparece nela.
3. **Given** um gasto registrado dessa forma, **When** ele é visualizado na lista de
   Gastos Extras, **Then** fica claro visualmente que ele já está pago e por que motivo
   não está na planilha.
4. **Given** o formulário de registrar um gasto SEM desembolso (nenhuma opção de "como
   será pago" escolhida), **When** o usuário preenche o formulário, **Then** a opção de
   marcar como já pago não se aplica (não há desembolso para marcar como pago).

### Edge Cases

- O gasto ainda passa pela aprovação normal de um super admin (esta feature não pula
  a aprovação) — só o desembolso já nasce resolvido.
- O valor do gasto continua contando no balanço financeiro (aprovados) normalmente —
  marcar como "já pago" não isenta do impacto no balanço, só tira da fila de pagamentos.
- Um gasto marcado como "já pago" continua contando como custo do evento, se estiver
  vinculado a um.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Ao registrar um gasto com desembolso (reembolso a funcionário ou
  pagamento a fornecedor), o usuário DEVE poder indicar que o pagamento já foi feito no
  ato do registro.
- **FR-002**: Um gasto registrado como já pago DEVE nascer com seu desembolso já marcado
  como pago — sem exigir nenhuma ação manual posterior de marcação de pagamento.
- **FR-003**: Um gasto registrado como já pago NUNCA PODE aparecer na Planilha de
  Pagamentos, em nenhum mês nem em nenhuma situação (a pagar, no banco ou pago) — nem
  antes nem depois de aprovado.
- **FR-004**: A lista de Gastos Extras DEVE deixar visualmente claro quando um gasto foi
  marcado como já pago no ato do registro, distinguindo-o de um gasto que foi marcado
  como pago posteriormente pela Planilha de Pagamentos.
- **FR-005**: Marcar um gasto como já pago NÃO PODE alterar o fluxo de aprovação
  (continua exigindo aprovação de super admin) nem o impacto no balanço financeiro ou no
  custo de um evento vinculado.
- **FR-006**: A opção de marcar como já pago só se aplica quando o gasto tem um
  desembolso definido (reembolso ou fornecedor) — não existe "pagamento" para marcar
  quando não há desembolso nenhum.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um gasto registrado como já pago nunca aparece na Planilha de Pagamentos,
  verificado em qualquer mês.
- **SC-002**: 100% dos gastos aprovados (com ou sem a marcação de já pago) continuam
  contando corretamente no balanço financeiro e no custo de eventos vinculados.
- **SC-003**: Um usuário consegue distinguir, olhando a lista de Gastos Extras, entre um
  gasto pago na hora do registro e um gasto pago depois pela planilha.

## Assumptions

- A marcação "já pago" está disponível tanto para reembolso a funcionário quanto para
  pagamento a fornecedor — o exemplo dado (PIX direto da conta da empresa para um
  fornecedor) é o caso mais comum, mas a mesma necessidade pode existir num reembolso já
  feito na hora (ex.: dinheiro na mão).
- Corrigir um gasto marcado por engano como "já pago" segue o mesmo caminho que já existe
  hoje para qualquer erro de cadastro (excluir e registrar de novo) — esta feature não
  adiciona uma tela de edição que não existe hoje para gastos extras.
