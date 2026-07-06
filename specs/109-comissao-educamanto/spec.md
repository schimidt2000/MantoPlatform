# Feature Specification: Comissão EducaManto + Padronização dos Orçamentos

**Feature Branch**: `109-comissao-educamanto`

**Created**: 2026-07-06

**Status**: Draft

**Input**: User description: "preciso que exista uma padronização no funcionamento das duas partes do sistema que geram orçamento (calculadora de orçamentos e EducaManto). Quando algum EducaManto é vendido, o Gabriel Lara recebe uma comissão; preciso também que ele receba o valor na planilha de pagamento e que ele consiga acompanhar da mesma forma que a Thays os eventos EducaManto fechados. A forma de pensar: eventos com (EDU) no começo serão os EducaManto. Gabriel recebe a comissão apenas após realização do evento. Quero também que seja possível ver os orçamentos realizados, quem gerou e tudo mais, fazendo com que os dois orçamentos funcionem de forma semelhante."

## Contexto

O sistema tem dois geradores de orçamento: a **Calculadora de Orçamentos** (`/orcamento/`,
eventos comuns) e o **EducaManto** (`/educamanto/`, espetáculos educacionais por pacote).
Hoje eles funcionam de forma desigual:

- **Comissão**: a venda de um evento comum gera comissão para a vendedora (ex.: Thays),
  registrada automaticamente e paga no dia 5 do mês seguinte à venda. A venda de um
  EducaManto não gera comissão nenhuma para o responsável pelo EducaManto (Gabriel Lara) —
  ele não aparece na planilha de pagamentos nem tem onde acompanhar os eventos fechados.
- **Histórico**: o histórico da calculadora mostra quem gerou cada orçamento e tem filtros
  (período, vendedor, valores); o histórico do EducaManto só tem busca por texto e não mostra
  quem gerou.

A convenção adotada pela empresa: eventos EducaManto na agenda têm título começando com
**"(EDU"** — ex.: "(EDU) Escola X" ou "(EDUCAMANTO) BETO + GIFA…" (já existe evento assim).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Comissão do responsável EducaManto após a realização do evento (Priority: P1)

Um evento EducaManto (título começando com "(EDU") tem a venda registrada. O sistema gera a
comissão para o **responsável EducaManto** (hoje, Gabriel Lara), e não para quem digitou a
venda. Diferente das comissões comuns (pagas pelo mês da venda), a comissão do EducaManto só
entra no ciclo de pagamento **depois que o evento acontece**: aparece na planilha de
pagamentos do mês seguinte ao da realização, no dia 5, junto das demais comissões.

**Why this priority**: é o pedido central — sem isso Gabriel não recebe nada pelos
EducaManto vendidos e o financeiro controla esse pagamento fora do sistema.

**Independent Test**: registrar venda num evento "(EDU) …" com data passada e noutro com
data futura; confirmar que a comissão é criada em nome do responsável EducaManto e que só a
do evento já realizado aparece como pagável na planilha do mês seguinte à realização.

**Acceptance Scenarios**:

1. **Given** um evento com título começando com "(EDU" e venda registrada, **When** a
   comissão é gerada, **Then** o beneficiário é o responsável EducaManto configurado (não o
   usuário que registrou a venda).
2. **Given** um evento EducaManto vendido com data **futura**, **When** o financeiro abre a
   planilha de pagamentos, **Then** a comissão desse evento NÃO aparece como pagável em
   nenhum mês anterior ao da realização.
3. **Given** um evento EducaManto vendido e **já realizado** em um mês M, **When** o
   financeiro abre a planilha de pagamentos do mês M+1, **Then** a comissão aparece somada
   na linha de comissões do responsável EducaManto, com vencimento dia 5.
4. **Given** um evento comum (sem "(EDU" no título) vendido pela Thays, **When** a comissão
   é gerada, **Then** nada muda em relação a hoje (beneficiária Thays, ciclo pelo mês da
   venda).
5. **Given** que não há responsável EducaManto configurado, **When** um evento EducaManto é
   vendido, **Then** a comissão segue a regra atual (vendedor do evento), sem erro.

---

### User Story 2 - Responsável EducaManto acompanha seus eventos fechados (Priority: P2)

Gabriel Lara entra no sistema e acompanha os eventos EducaManto fechados da mesma forma que
a Thays acompanha as vendas dela: vê a lista de eventos EducaManto com valores de venda,
custo e a comissão dele, e a tela de comissões com o que tem a receber e o que já foi pago.

**Why this priority**: sem visibilidade, a comissão continua sendo "conferida por fora"; mas
o pagamento em si (US1) já funciona sem esta história.

**Independent Test**: logar como o responsável EducaManto (perfil ENSAIO, sem COMERCIAL) e
confirmar que o Pipeline de Vendas abre mostrando **apenas** eventos EducaManto e que a tela
de Comissões mostra apenas as comissões dele.

**Acceptance Scenarios**:

1. **Given** o responsável EducaManto logado, **When** abre o Pipeline de Vendas, **Then**
   vê somente os eventos EducaManto (título "(EDU…"), com venda/custo/comissão.
2. **Given** o responsável EducaManto logado, **When** abre a tela de Comissões, **Then** vê
   somente as comissões dele (leitura, sem gerenciar).
3. **Given** o responsável EducaManto logado, **When** olha o menu lateral, **Then** vê os
   atalhos de Pipeline de Vendas e Comissões (que hoje não aparecem para o perfil dele).
4. **Given** um usuário ENSAIO que NÃO é o responsável EducaManto, **When** tenta acessar o
   Pipeline de Vendas ou Comissões, **Then** continua sem acesso (403), como hoje.
5. **Given** a Thays (COMERCIAL) logada, **When** abre o Pipeline de Vendas, **Then**
   continua vendo todos os eventos, como hoje.

---

### User Story 3 - Históricos de orçamento padronizados (Priority: P3)

Um super admin abre o histórico do EducaManto e enxerga o mesmo padrão do histórico da
calculadora: quem gerou cada orçamento, filtros por período e por usuário, além da busca por
texto que já existe. Os dois históricos passam a "funcionar de forma semelhante".

**Why this priority**: dá a rastreabilidade pedida ("quem gerou e tudo mais"), mas não
envolve dinheiro — pode ser entregue por último.

**Independent Test**: gerar orçamentos EducaManto com dois usuários diferentes; como super
admin, abrir o histórico, ver a coluna "Gerado por" e filtrar por usuário e por período.

**Acceptance Scenarios**:

1. **Given** orçamentos EducaManto gerados por usuários distintos, **When** o super admin
   abre o histórico do EducaManto, **Then** vê quem gerou cada orçamento.
2. **Given** o histórico do EducaManto, **When** o super admin filtra por usuário ou por
   período de geração, **Then** a lista reflete o filtro (mesmo comportamento do histórico
   da calculadora).
3. **Given** um usuário sem papel de super admin com acesso ao EducaManto, **When** abre o
   histórico, **Then** continua vendo a lista como hoje (sem o filtro por usuário, espelhando
   a regra da calculadora).

---

### Edge Cases

- Evento EducaManto cancelado depois de a comissão ter sido paga: o estorno segue o fluxo já
  existente de comissões (linha negativa), agora em nome do responsável EducaManto.
- Troca do responsável EducaManto na configuração: comissões **pendentes** acompanham a
  configuração atual (mesma reconciliação já usada quando a taxa muda); comissões **pagas**
  nunca são alteradas.
- Evento EducaManto sem data definida ou remarcado: a comissão acompanha a data atual do
  evento — se o evento for adiado, o pagamento adia junto.
- Título editado depois da venda (ganha ou perde o prefixo "(EDU"): ao reprocessar a venda,
  a comissão é recalculada segundo o título atual (mesma reconciliação já usada quando a
  taxa muda).
- Responsável EducaManto marcado como "não recebe comissão" no cadastro: não gera comissão
  (mesma regra dos vendedores hoje).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE identificar como "evento EducaManto" todo evento cujo título
  comece com "(EDU" (cobre "(EDU)" e "(EDUCAMANTO)"), sem diferenciar maiúsculas/minúsculas.
- **FR-002**: O sistema DEVE permitir configurar qual usuário é o **responsável EducaManto**
  (nas configurações administrativas), podendo ficar vazio.
- **FR-003**: Ao registrar/atualizar a venda de um evento EducaManto, a comissão DEVE ser
  gerada em nome do responsável EducaManto configurado, usando as mesmas regras de taxa das
  comissões atuais (taxa padrão do sistema, com possibilidade de taxa específica por evento).
- **FR-004**: A comissão de um evento EducaManto SÓ PODE entrar como pagável na planilha de
  pagamentos após a realização do evento — no ciclo do mês seguinte ao mês da realização
  (vencimento dia 5), em vez do mês da venda.
- **FR-005**: Comissões de eventos comuns (sem o prefixo) NÃO PODEM mudar de comportamento:
  mesmo beneficiário (vendedor), mesmo ciclo (mês da venda).
- **FR-006**: Se não houver responsável EducaManto configurado, a venda de um evento
  EducaManto DEVE seguir a regra atual (comissão do vendedor, ciclo do mês da venda).
- **FR-007**: O responsável EducaManto DEVE conseguir acessar o Pipeline de Vendas vendo
  APENAS os eventos EducaManto, e a tela de Comissões vendo apenas as próprias comissões
  (leitura) — mesmo sem os papéis COMERCIAL/FINANCEIRO.
- **FR-008**: Usuários que hoje têm acesso ao Pipeline/Comissões NÃO PODEM perder nem mudar
  seu acesso; usuários sem acesso (e que não sejam o responsável) continuam bloqueados.
- **FR-009**: O histórico do EducaManto DEVE mostrar quem gerou cada orçamento e oferecer
  filtros por período de geração e por usuário (este último só para super admin), espelhando
  o histórico da calculadora.
- **FR-010**: O registro de quem gerou cada orçamento (nos dois históricos) DEVE ser
  preservado como já é hoje — nenhum dado existente pode ser perdido na padronização.

### Key Entities

- **Evento EducaManto (CalendarEvent)**: evento cujo título começa com "(EDU"; nenhuma
  coluna nova — a classificação deriva do título.
- **Responsável EducaManto (configuração)**: referência a um usuário do sistema nas
  configurações administrativas; beneficiário das comissões EducaManto.
- **Comissão (CommissionPayment)**: ganha a noção de "pagável a partir de" (data da
  realização do evento) usada apenas por comissões EducaManto; demais campos e fluxos
  (estorno, pago/a pagar, cancelamento) inalterados.
- **Orçamento EducaManto (EducaMantoQuote)**: já registra autor e data; passa a exibi-los e
  filtrá-los no histórico.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das vendas registradas em eventos com título "(EDU…" geram comissão para
  o responsável EducaManto configurado (visível na tela de Comissões).
- **SC-002**: Nenhuma comissão EducaManto aparece como pagável na planilha de pagamentos
  antes da realização do evento (0 casos nos testes).
- **SC-003**: Comissões de eventos comuns permanecem idênticas antes/depois da mudança
  (mesmo beneficiário, mesmo mês de cobrança) em 100% dos casos testados.
- **SC-004**: O responsável EducaManto encontra seus eventos fechados e comissões em até 2
  cliques a partir do menu lateral, sem ver eventos que não sejam EducaManto.
- **SC-005**: O super admin identifica quem gerou qualquer orçamento EducaManto diretamente
  na lista do histórico, sem abrir o PDF.

## Assumptions

- "Gabriel Lara" não é gravado em código: a feature cria a configuração "responsável
  EducaManto" e o valor inicial aponta para o usuário Gabriel Lara já existente
  (gabriel@mantoproducoes.com.br); trocável a qualquer momento pelo admin.
- A taxa de comissão EducaManto segue as regras atuais (taxa padrão do sistema, hoje 2,5%,
  com override por evento editável pelo super admin) — o usuário não pediu taxa diferente;
  se quiserem taxa própria para EducaManto, basta usar o override por evento.
- "Planilha de pagamento" = tela Pagamentos do financeiro (`/financeiro/pagamentos`), onde
  as comissões já aparecem agregadas por beneficiário com vencimento dia 5.
- "Acompanhar da mesma forma que a Thays" = Pipeline de Vendas + tela de Comissões (leitura
  das próprias), porém restrito aos eventos EducaManto — menor privilégio: o responsável não
  passa a ver vendas de eventos comuns.
- "Realização do evento" = data/hora de término do evento já passou (horário de Brasília).
- A padronização dos históricos é feita elevando o histórico do EducaManto ao padrão da
  calculadora (que já atende ao pedido); o histórico da calculadora não muda.
