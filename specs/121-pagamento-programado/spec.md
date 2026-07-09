# Feature Specification: Pagamento Programado (Gastos Recorrentes)

**Feature Branch**: `121-pagamento-programado`

**Created**: 2026-07-09

**Status**: Draft

**Input**: User description: "Dentro de gastos recorrentes, um pagamento programado: descrevo o gasto, coloco quantas parcelas, coloco quais as datas, e decido se é o mesmo valor em todas ou se cada uma tem um valor. Ex.: pagar para a Edileuza R$ 1.500 nos dias 20/07, 05/08, 20/08, 05/09, 20/09, 05/10, 20/10, 05/11. Deve aparecer na planilha de pagamentos em cada data e ser visível no painel de gastos recorrentes."

## Contexto

Gastos recorrentes hoje cobrem três padrões: conta variável (valor muda todo mês), débito
automático e assinatura (valor fixo, cadência mensal/semanal/quinzenal/anual). Nenhum
desses cobre um compromisso com **datas específicas e não regulares** — por exemplo,
parcelar um pagamento a alguém em datas combinadas que não caem num ciclo fixo (duas vezes
em alguns meses, uma em outros). Hoje isso exigiria lançar cada parcela manualmente como
gasto extra avulso, perdendo a visão de conjunto do compromisso todo.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cadastrar um pagamento programado (Priority: P1)

O financeiro descreve o pagamento (para quem, por quê), informa as datas em que cada
parcela vence, e escolhe se todas as parcelas têm o mesmo valor ou se cada uma tem seu
próprio valor. Ao salvar, todas as parcelas já existem no sistema, cada uma na sua data.

**Independent Test**: cadastrar um pagamento com 3 datas e valores diferentes; conferir que
3 lançamentos foram criados, cada um com sua data e valor corretos.

**Acceptance Scenarios**:

1. **Given** o formulário de pagamento programado, **When** o financeiro escolhe "mesmo
   valor para todas" e informa 8 datas + 1 valor, **Then** 8 parcelas são criadas, todas com
   aquele valor, cada uma na data informada.
2. **Given** o mesmo formulário, **When** o financeiro escolhe "valor individual por
   data" e informa um valor diferente para cada data, **Then** cada parcela é criada com o
   valor daquela data específica.
3. **Given** duas datas do pagamento caem no mesmo mês (ex.: 05/08 e 20/08), **Then** ambas
   as parcelas são criadas e nenhuma sobrescreve a outra.
4. **Given** o formulário sem nome ou sem nenhuma data válida, **Then** o cadastro é
   rejeitado com mensagem clara, nada é criado.

### User Story 2 - Ver o pagamento programado na planilha de pagamentos (Priority: P1)

Cada parcela cadastrada aparece na planilha de pagamentos (financeiro) exatamente na sua
data de vencimento, com o valor daquela parcela — do mesmo jeito que as demais contas
recorrentes já aparecem.

**Independent Test**: cadastrar um pagamento com parcela em uma data específica; abrir a
planilha de pagamentos do mês daquela data; conferir que a parcela aparece com a data e o
valor certos.

**Acceptance Scenarios**:

1. **Given** uma parcela com vencimento em 20/08, **When** a planilha de pagamentos de
   agosto é aberta, **Then** a parcela aparece naquela data, com o valor cadastrado.
2. **Given** duas parcelas no mesmo mês (05/08 e 20/08), **Then** as duas aparecem na
   planilha daquele mês, cada uma na sua data.
3. **Given** uma parcela marcada como paga na planilha (ou no painel de recorrentes),
   **Then** o status atualiza nos dois lugares.

### User Story 3 - Acompanhar o pagamento programado no painel de gastos recorrentes (Priority: P2)

No painel de gastos recorrentes, o financeiro vê cada pagamento programado como um
compromisso só, com a lista completa de parcelas (passadas e futuras), quantas já foram
pagas, e pode marcar uma parcela como paga ou desfazer isso, direto ali.

**Acceptance Scenarios**:

1. **Given** um pagamento programado cadastrado, **When** o painel de gastos recorrentes é
   aberto (em qualquer mês), **Then** o pagamento aparece com todas as suas parcelas
   visíveis (não só as do mês em exibição).
2. **Given** uma parcela ainda não paga, **When** o financeiro marca como paga, **Then** o
   status muda ali e reflete também na planilha de pagamentos.
3. **Given** um pagamento programado com parcela ainda não paga, **When** o financeiro
   exclui só aquela parcela (por engano de cadastro), **Then** as demais parcelas
   permanecem intactas.

## Requirements *(mandatory)*

- **FR-001**: O sistema DEVE permitir cadastrar um "pagamento programado": nome/descrição,
  lista de datas (uma ou mais) e, para cada data, um valor.
- **FR-002**: No cadastro, o financeiro DEVE poder escolher entre "mesmo valor para todas
  as datas" (informa o valor uma vez) ou "valor individual por data" (informa o valor de
  cada uma separadamente).
- **FR-003**: Ao salvar, o sistema DEVE criar uma parcela (lançamento) por data informada,
  imediatamente — sem geração posterior por mês.
- **FR-004**: Cada parcela DEVE aparecer na planilha de pagamentos no mês/dia da sua data
  de vencimento, com o valor daquela parcela.
- **FR-005**: Duas ou mais parcelas do mesmo pagamento programado que caiam no mesmo mês
  DEVEM aparecer todas, sem se sobrescreverem.
- **FR-006**: O painel de gastos recorrentes DEVE mostrar cada pagamento programado com a
  lista completa das suas parcelas (não restrita ao mês em exibição), incluindo situação
  de cada uma (a pagar / paga).
- **FR-007**: O financeiro DEVE poder marcar uma parcela como paga e desfazer isso, com o
  mesmo efeito nos dois lugares (planilha de pagamentos e painel de recorrentes) — reusa o
  mecanismo já existente de pagar/reabrir lançamento.
- **FR-008**: O financeiro DEVE poder excluir uma parcela específica ainda não paga (para
  corrigir um erro de cadastro), sem afetar as demais parcelas do mesmo pagamento.
- **FR-009**: O pagamento programado inteiro (a conta) só PODE ser excluído se não tiver
  nenhuma parcela — na prática, a exclusão total é feita desativando o compromisso, mesmo
  padrão já usado para as demais contas recorrentes.
- **FR-010**: O cadastro DEVE ser rejeitado, com mensagem clara, se faltar nome ou se não
  houver ao menos uma data com valor válido.

### Key Entities

- **Pagamento Programado**: um compromisso com nome/descrição, criado como um tipo de
  conta recorrente; não segue um ciclo automático — a lista de datas é definida no
  cadastro.
- **Parcela**: um lançamento com data e valor próprios, ligado ao pagamento programado;
  mesmo tipo de registro já usado para os lançamentos das demais contas recorrentes
  (a pagar → paga).

## Success Criteria *(mandatory)*

- **SC-001**: O financeiro cadastra um pagamento com 8 parcelas em datas não regulares em
  menos de 2 minutos, num único formulário.
- **SC-002**: 100% das parcelas cadastradas aparecem na planilha de pagamentos na data
  certa, com o valor certo — inclusive quando duas caem no mesmo mês.
- **SC-003**: O financeiro consegue ver o pagamento programado inteiro (todas as parcelas,
  passadas e futuras) num único lugar no painel de gastos recorrentes.

## Assumptions

- Sem alerta na home para parcelas de pagamento programado vencidas/pendentes — o pedido
  foi especificamente sobre planilha de pagamentos e painel de recorrentes; alertas na home
  hoje só existem para contas variáveis.
- Não há edição em massa do cronograma depois de criado (mudar todas as datas/valores de
  uma vez) — para corrigir, exclui-se a parcela errada (se ainda não paga) e cadastra-se de
  novo o que for necessário. Editar nome/PIX/observações do pagamento como um todo também
  fica fora desta primeira versão.
- Datas repetidas (duas parcelas na mesma data) são permitidas — não há motivo de negócio
  para bloquear duas cobranças no mesmo dia.
- Comprovante de pagamento não é exigido nas parcelas (diferente do adiantamento de
  salário) — mesmo padrão que as demais contas recorrentes hoje.
