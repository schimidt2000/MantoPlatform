# Feature Specification: Acréscimos tipados no orçamento, com tipo BV (repasse) e pagamento por PIX

**Feature Branch**: `099-orcamento-acrescimos-bv`

**Created**: 2026-07-01

**Status**: Draft

**Input**: "Na tela de orçamentos precisamos melhorar os acréscimos. Existem diferentes acréscimos por motivos diferentes. Poderia ser 'adicionar acréscimo', a vendedora escolhe o tipo e coloca o valor. Um dos tipos deve ser BV. Quando BV, isso entra nas finanças da Manto não como lucro, mas como um valor a ser pago à organizadora (ou quem for). O BV não entra na comissão da vendedora. Ao selecionar BV, na tela comercial do evento deve haver um campo para o PIX de quem recebe o BV, e isso vai para a planilha de pagamentos."

## Contexto

Hoje o orçamento tem **um único acréscimo** (um valor em R$ ou %), sem distinguir o motivo. Na prática há
**vários tipos de acréscimo** por razões diferentes, e um deles — o **BV** — tem tratamento financeiro
especial: é um valor cobrado no orçamento mas **repassado** a um terceiro (a organizadora do evento, por
exemplo). Portanto o BV **não é lucro da Manto** e **não entra na comissão da vendedora** — é um valor a
**pagar**, que precisa aparecer na **planilha de pagamentos**, com o **PIX de quem recebe**.

## Decisões de escopo (confirmadas)

- **Tipos de acréscimo**: uma **lista fixa** de motivos + **BV** + **Outro (descrever)**. Lista inicial
  (ajustável): *Taxa de urgência*, *Deslocamento/Logística*, *Domingo/Feriado*, *Hora extra*, **BV**,
  *Outro*.
- **Valor**: cada acréscimo pode ser **R$ fixo** ou **percentual (%)** sobre o total.
- **BV oculto para o cliente**: o BV entra no **total** cobrado, mas **não** aparece como uma linha "BV"
  na proposta (mensagem/PDF) — é um repasse sensível, embutido no valor.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Adicionar acréscimos tipados no orçamento (Priority: P1) 🎯 MVP

Como vendedora, na tela de orçamentos, quero **adicionar um ou mais acréscimos**, cada um com um **tipo**
e um **valor** (R$ ou %), para refletir corretamente os diferentes motivos que aumentam o preço.

**Why this priority**: É a base do pedido; substitui o acréscimo único de hoje por acréscimos tipados.

**Independent Test**: Montar um orçamento, adicionar dois acréscimos de tipos diferentes (um em R$ e um em
%), e conferir que o total sobe pela soma deles.

**Acceptance Scenarios**:

1. **Given** a tela de orçamentos, **When** clico em "Adicionar acréscimo", **Then** posso escolher um
   **tipo** (da lista + BV + Outro) e informar um **valor** em R$ ou %.
2. **Given** dois acréscimos (um R$ e um %), **When** calculo, **Then** o total reflete a soma dos dois
   sobre o valor base.
3. **Given** o tipo **Outro**, **When** seleciono, **Then** posso digitar uma **descrição** livre do
   motivo.
4. **Given** um acréscimo em %, **When** calculo, **Then** o percentual é aplicado sobre o total antes dos
   acréscimos (coerente com o comportamento atual do acréscimo único).
5. **Given** acréscimos adicionados, **When** removo um deles, **Then** o total recalcula sem ele.

### User Story 2 - BV não é lucro nem comissão (Priority: P1)

Como gestor financeiro, quero que o valor de **BV** seja tratado como um **repasse a pagar** — não como
lucro da Manto — e que **não entre na comissão** da vendedora, para que as finanças reflitam a realidade.

**Why this priority**: É a regra financeira central do pedido; sem ela o BV distorce lucro e comissão.

**Independent Test**: Criar um evento com venda contendo um acréscimo BV; conferir que o **lucro** do
evento desconta o BV e que a **comissão** da vendedora é calculada **sem** o BV.

**Acceptance Scenarios**:

1. **Given** um evento cuja venda inclui um BV de R$ X, **When** o lucro é calculado, **Then** o BV é
   **descontado** (não conta como lucro).
2. **Given** o mesmo evento, **When** a comissão da vendedora é calculada, **Then** a base **exclui** o
   valor do BV (a vendedora não é comissionada sobre o BV).
3. **Given** acréscimos **não-BV** (ex.: Taxa de urgência), **When** lucro/comissão são calculados,
   **Then** eles **continuam** contando normalmente (como parte da venda) — só o BV é especial.
4. **Given** um evento **sem** BV, **When** lucro/comissão são calculados, **Then** nada muda em relação
   ao comportamento atual.

### User Story 3 - PIX do BV na tela comercial do evento e na planilha de pagamentos (Priority: P1)

Como financeiro, quando um evento tem **BV**, quero informar na **tela comercial do evento** o **PIX de
quem recebe** o BV (e o nome), para que esse valor entre na **planilha de pagamentos** como um valor a
pagar.

**Why this priority**: Fecha o ciclo do BV — sem o PIX/pagamento, o repasse não acontece.

**Independent Test**: Em um evento com BV, preencher o PIX/nome do recebedor na tela comercial; abrir a
planilha de pagamentos e ver o BV listado como pagamento pendente para aquele recebedor, no valor certo.

**Acceptance Scenarios**:

1. **Given** um evento com acréscimo **BV**, **When** abro a tela comercial do evento, **Then** vejo um
   campo para **PIX** e **nome** de quem recebe o BV.
2. **Given** o PIX/nome preenchidos, **When** salvo os dados comerciais, **Then** o BV aparece na
   **planilha de pagamentos** como um item a pagar, com o valor do BV, o recebedor e o PIX.
3. **Given** o BV na planilha, **When** marco como **pago**, **Then** o status do pagamento do BV é
   atualizado (igual aos demais pagamentos).
4. **Given** um evento **sem** BV, **When** abro a tela comercial, **Then** **não** aparece o campo de PIX
   de BV.
5. **Given** um evento com BV **sem** PIX preenchido, **When** o financeiro vê a planilha, **Then** o BV
   aparece sinalizado como **pendente de dados** (falta PIX) para não ser esquecido.

### Edge Cases

- **Acréscimo em % e BV em %**: o percentual do BV incide sobre o total base; o valor em R$ resultante é
  o que vira repasse (a planilha e as regras de lucro/comissão usam o **valor em R$** apurado).
- **Vários acréscimos, um deles BV**: só a parcela BV é excluída de lucro/comissão; os demais entram
  normalmente.
- **Mais de um BV**: soma-se o total de BV; o PIX/recebedor é informado no evento (um recebedor por
  evento nesta entrega — ver Assumptions).
- **Editar/remover o BV depois**: se o BV é removido do evento, o item de pagamento correspondente deixa
  de existir (ou é marcado como cancelado) e lucro/comissão voltam ao normal.
- **Evento criado direto (sem orçamento)**: os acréscimos (inclusive BV) também podem ser informados na
  tela comercial do evento, não só via orçamento.
- **Cliente não vê BV**: o BV nunca aparece rotulado na proposta ao cliente (mensagem/PDF).

## Requirements *(mandatory)*

### Acréscimos tipados (orçamento e evento)

- **FR-001**: O orçamento MUST permitir **adicionar múltiplos acréscimos**, cada um com **tipo** (lista
  fixa + BV + Outro), **valor** (R$ ou %) e, para "Outro", uma **descrição**.
- **FR-002**: O **total** do orçamento MUST somar todos os acréscimos; percentuais incidem sobre o total
  antes dos acréscimos.
- **FR-003**: Os acréscimos MUST ser transportados para o **evento** ao criá-lo a partir do orçamento, e
  MUST poder ser **informados/editados** na tela comercial do evento (para eventos sem orçamento).
- **FR-004**: Nenhum acréscimo (incluindo BV) MUST ser exibido de forma **rotulada** ao cliente na
  proposta (mensagem/PDF) — todos entram embutidos no total.

### Regras financeiras do BV

- **FR-005**: O valor de **BV** MUST ser tratado como **repasse a pagar**, **descontado do lucro** do
  evento (não é lucro da Manto).
- **FR-006**: O valor de **BV** MUST ser **excluído da base de comissão** da vendedora.
- **FR-007**: Acréscimos **não-BV** MUST continuar contando normalmente para venda, lucro e comissão
  (comportamento atual preservado).
- **FR-008**: A apuração do BV para lucro/comissão/pagamento MUST usar o **valor em R$** efetivo (quando
  informado em %, converte-se para R$ sobre a base).

### PIX do BV e planilha de pagamentos

- **FR-009**: Quando o evento tem BV, a **tela comercial do evento** MUST oferecer campos para **PIX** e
  **nome** de quem recebe o BV.
- **FR-010**: O BV MUST aparecer na **planilha de pagamentos** como um item **a pagar**, com valor,
  recebedor e PIX, e com **status de pagamento** (pendente/pago) igual aos demais pagamentos.
- **FR-011**: Um BV **sem PIX** informado MUST aparecer sinalizado como **pendente de dados** na planilha,
  para não ser esquecido.
- **FR-012**: Alterar o valor do BV MUST atualizar o valor do item na planilha; remover o BV MUST remover/
  cancelar o item de pagamento correspondente.

## Key Entities *(include if feature involves data)*

- **Acréscimo do evento**: um item com **tipo** (lista + BV + Outro), **descrição** (para Outro), **base**
  (R$ ou %) e **valor**; pertence a um evento (e é pré-preenchido pelo orçamento). Marca se é **BV**.
- **Evento** (existente): passa a ter uma coleção de acréscimos e, quando há BV, dados do **recebedor do
  BV** (nome + PIX) e o **status de pagamento** do BV. O cálculo de **lucro** e **comissão** passa a
  descontar/excluir o total de BV.
- **Item de pagamento (planilha)** (existente): ganha uma nova origem — o **BV** — com recebedor, PIX,
  valor e status, no mês do evento.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A vendedora consegue adicionar **≥ 2 acréscimos** de tipos diferentes num orçamento, e o
  total reflete a soma correta (R$ e %).
- **SC-002**: Para um evento com BV de R$ X, o **lucro** exibido é **R$ X menor** do que seria sem a
  exclusão do BV, e a **comissão** é calculada sobre a venda **menos X**.
- **SC-003**: 100% dos eventos com BV aparecem na **planilha de pagamentos** com o valor e o recebedor
  corretos; BVs sem PIX aparecem sinalizados como pendentes de dados.
- **SC-004**: O cliente **nunca** vê uma linha "BV" na proposta (mensagem/PDF).
- **SC-005**: Eventos/orçamentos **sem** BV e o acréscimo único **legado** continuam funcionando sem
  regressão.

## Assumptions

- **Lista de tipos inicial** (Taxa de urgência, Deslocamento/Logística, Domingo/Feriado, Hora extra, BV,
  Outro) é um ponto de partida ajustável; "Outro" cobre casos não previstos com descrição livre.
- **Percentual** de um acréscimo incide sobre o **total antes dos acréscimos** (mesma semântica do
  acréscimo único atual), inclusive para BV informado em %.
- **Um recebedor de BV por evento** nesta entrega (se houver mais de um acréscimo BV, somam-se os valores
  para um único repasse/recebedor). Múltiplos recebedores ficam fora do escopo.
- **Planilha de pagamentos** = a lista de pagamentos financeiros já existente (onde aparecem cachês,
  salários, comissões e desembolsos), no mês do evento; o BV entra como um item a pagar com PIX.
- **Compatibilidade**: o acréscimo único legado (valor R$ já gravado em eventos antigos) permanece válido
  e é tratado como um acréscimo comum (não-BV); nenhum recálculo retroativo é feito.
- **Permissões**: adicionar acréscimos segue quem já usa o orçamento/edita dados comerciais; ver a
  planilha de pagamentos segue o papel financeiro atual.
- **Escopo = calculadora principal** (`/orcamento`) e módulo financeiro do app; o `Manto_Sales/` separado
  fica fora.
