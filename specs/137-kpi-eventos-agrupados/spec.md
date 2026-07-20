# Feature Specification: KPIs financeiros de evento agrupado

**Feature Branch**: `137-kpi-eventos-agrupados`

**Created**: 2026-07-20

**Status**: Draft

**Input**: User description: "https://app.mantoproducoes.com.br/events/319 esse evento por exemplo é um evento agrupado, não faz sentido os gastos extras e custo de cache serem apenas do evento selecionado. Na realidade pode até mostrar relacionado a esse individual os custos de cache mas em algum lugar precisa mostrar as informações do agrupamento"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver o resultado financeiro real de um contrato agrupado (Priority: P1)

Alguém do Comercial ou Financeiro abre a página de qualquer evento que faz parte de um
grupo comercial (contrato único cobrindo vários eventos/personagens agrupados, feature
053) e precisa entender se aquele contrato deu lucro ou prejuízo. Hoje, o painel
financeiro do evento mostra "Custo (cachês)" e "Gastos extras" olhando só para o evento
individual aberto — mas a "Venda" e a "Comissão" já refletem o contrato inteiro (dados do
evento principal). Isso produz um "Lucro líquido" sem sentido: por exemplo, um satélite
sem valor de venda próprio (zerado ao entrar no grupo) mostrando um lucro líquido
fortemente negativo, mesmo que o contrato como um todo tenha dado lucro.

**Why this priority**: É a dor relatada diretamente pelo usuário com um caso real em
produção — o painel financeiro de um evento agrupado hoje induz a uma leitura errada do
resultado do contrato, o que é crítico para decisões comerciais/financeiras.

**Independent Test**: Abrir a página de qualquer evento satélite ou principal de um grupo
com mais de um evento e conferir que "Custo (cachês)", "Gastos extras" e "Lucro líquido"
refletem a soma de todos os eventos do grupo (principal + satélites), não só do evento
aberto.

**Acceptance Scenarios**:

1. **Given** um grupo comercial com evento principal e 2 satélites, cada um com talentos
   escalados (cachês) e gastos extras aprovados próprios, **When** alguém abre a página de
   um dos satélites, **Then** o painel financeiro mostra "Custo (cachês)" e "Gastos
   extras" somando os três eventos do grupo, e o "Lucro líquido" é calculado com a venda
   do principal menos essa soma.
2. **Given** o mesmo grupo, **When** alguém abre a página do evento principal, **Then** os
   mesmos totais agregados aparecem (o resultado financeiro do contrato é idêntico visto
   de qualquer evento do grupo).
3. **Given** um evento que não pertence a nenhum grupo (não é satélite nem principal),
   **When** alguém abre sua página, **Then** o painel financeiro continua mostrando apenas
   os números daquele evento (comportamento atual, sem mudança).

---

### User Story 2 - Ver o custo individual de cada evento dentro do grupo (Priority: P2)

Ainda olhando o painel financeiro de um evento agrupado, quem está analisando quer saber
não só o total do contrato, mas também quanto cada evento/personagem individual do grupo
custou em cachê — por exemplo, para entender se um evento específico do grupo ficou caro
demais em relação aos outros.

**Why this priority**: Explicitamente pedido pelo usuário ("pode até mostrar relacionado a
esse individual os custos de cache") — é um complemento à visão agregada, não a
funcionalidade central da correção.

**Independent Test**: Na página de um evento pertencente a um grupo, é possível ver quanto
esse evento específico contribuiu para o custo total de cachês do grupo, sem precisar
abrir cada evento satélite individualmente.

**Acceptance Scenarios**:

1. **Given** um grupo com 3 eventos, cada um com cachês diferentes, **When** alguém abre a
   página de um deles, **Then** consegue ver o detalhamento por evento (qual evento, quanto
   de cachê) dentro da mesma seção que mostra o total agregado do grupo.

---

### Edge Cases

- Evento principal sem nenhum satélite (grupo de 1): comportamento idêntico ao evento
  avulso de hoje — nenhuma mudança visível.
- Gastos extras vinculados a um satélite que ainda está com status "pendente" (não
  aprovado): continuam de fora do total, mesma regra de hoje (`status="aprovado"`).
- Um evento do grupo é excluído: o total agregado do grupo recalcula automaticamente na
  próxima vez que a página de qualquer evento remanescente do grupo for aberta (nada
  precisa ser "recalculado e salvo" — é sempre calculado na hora).
- Desagrupar um evento (ação já existente "Desfazer agrupamento"): a partir daí ele volta a
  mostrar só os próprios números, e o restante do grupo recalcula sem ele.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Ao exibir o painel financeiro (KPIs de Custo de cachês, Gastos extras e
  Lucro líquido) de um evento que pertence a um grupo comercial (é principal ou é
  satélite), o sistema MUST calcular esses três valores somando todos os eventos do grupo
  (o principal e todos os satélites), não apenas o evento aberto.
- **FR-002**: Para um evento que não pertence a nenhum grupo, o sistema MUST manter o
  comportamento atual (KPIs calculados apenas com os dados daquele evento).
- **FR-003**: O sistema MUST deixar claro, na própria tela, que os valores exibidos são do
  grupo/contrato como um todo (não apenas do evento aberto) quando o evento pertence a um
  grupo — para não repetir a confusão relatada.
- **FR-004**: O sistema MUST continuar permitindo ver o custo de cachês referente
  especificamente ao evento aberto (não só o total do grupo), em algum ponto visível da
  mesma tela.
- **FR-005**: A lista de "Gastos extras vinculados" (com nota fiscal) exibida na página
  MUST mostrar os gastos de todos os eventos do grupo quando o evento pertence a um grupo,
  identificando a qual evento do grupo cada gasto pertence.
- **FR-006**: O cálculo de Comissão MUST continuar usando a venda do evento principal
  (comportamento já existente, não afetado por esta feature).

### Key Entities

- **Grupo comercial**: já modelado hoje (evento principal + eventos satélites via
  `group_leader_id`). Esta feature não cria entidade nova — apenas agrega, para exibição,
  dados que já existem por evento (talentos escalados/cachês via papéis do evento, e
  gastos extras aprovados vinculados ao evento).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Ao abrir qualquer evento de um grupo com mais de um evento, o "Lucro
  líquido" mostrado bate com o resultado real do contrato (venda do principal menos o
  custo total de cachês e gastos extras de todos os eventos do grupo) — não mais um número
  distorcido por olhar só o evento individual.
- **SC-002**: O mesmo grupo mostra o mesmo "Lucro líquido" e os mesmos totais de custo,
  não importa qual evento do grupo esteja aberto.
- **SC-003**: Eventos fora de qualquer grupo continuam mostrando exatamente os mesmos
  números de hoje (nenhuma regressão para o caso comum).

## Assumptions

- "Custo (cachês)" continua definido como a soma dos `cache_value` dos papéis com talento
  escalado — só que agora somada por todos os eventos do grupo, em vez de um único evento.
- "Gastos extras" continua restrito a `SpecialExpense` com status `aprovado` — só que
  agora somados por todos os eventos do grupo.
- BV (repasse a terceiros, feature 099) segue a mesma lógica de agregação: soma dos
  acréscimos marcados como BV de todos os eventos do grupo (consistente com custo e gastos
  extras passarem a ser agregados).
- A seção "Elenco"/papéis de cada evento individual (que já lista talento e cachê por
  evento) permanece como está — ela já cobre o requisito de "ver o custo individual desse
  evento" (FR-004/User Story 2) sem precisar de UI nova; a mudança relevante é nos KPIs
  agregados e na lista de gastos extras.
- Fora de escopo: mudar como "Venda", "Comissão" ou os dados comerciais (pagamentos,
  parcelas, contrato) são calculados para eventos agrupados — isso já segue o principal
  hoje e não foi apontado como problema.
- Fora de escopo: mudar a Planilha de Pagamentos, relatórios financeiros gerais ou
  qualquer tela fora da página do evento — o pedido é especificamente sobre o painel
  financeiro visto na página do evento.
