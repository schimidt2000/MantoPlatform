# Feature Specification: Clientes (CRM) — base importada do Kommo, associação a eventos e ecossistema de marketing

**Feature Branch**: `094-clientes-crm-eventos`

**Created**: 2026-06-29

**Status**: Draft

**Input**: "Esse csv eu exportei do Kommo CRM com nossos clientes. Preciso que em cada evento agora tenha a opção de associar um cliente. Os eventos sem cliente do passado ok, mas a partir de agora é obrigatório que tenha um cliente associado. Se o cliente não existe no banco, o vendedor pode criar. A ideia é que consiga ver quantos eventos esse cliente fechou, quais as datas… enfim. Um ecossistema completo para que eu possa fazer marketing com essa base de clientes. O arquivo é o kommo_export_leads_2026-06-29.csv"

## Contexto

A Manto usa hoje o Kommo CRM para gerir contatos/leads. O arquivo `kommo_export_leads_2026-06-29.csv`
(6.510 linhas) é uma exportação dessa base. A empresa quer trazer esses **clientes para dentro da
plataforma** e ligá-los aos **eventos**, criando um histórico próprio: quantos eventos cada cliente
fechou, em que datas, quanto gastou — uma base para ações de marketing e relacionamento.

Observações sobre o CSV (apuradas na análise do arquivo):

- Os campos confiáveis e quase sempre preenchidos são **"Nome completo"** (6.369) e **"Telefone
  comercial"** (5.606). E-mail, empresa e demais telefones estão praticamente vazios.
- O telefone vem no formato `'+5511942466868` (apóstrofo inicial de Excel + DDI/DDD) e precisa ser
  **normalizado** (apenas dígitos).
- A maioria das linhas são **leads não fechados** (venda R$ 0, etapas "leads de entrada"/"Cotação"/
  "Contato Realizado") e há **muita duplicata pelo mesmo telefone** (o mesmo cliente em vários leads).
- Metadados úteis para marketing: "Usuário responsável", "Tags", "Etapa do lead", "Funil de vendas",
  "Criado em", "Fechado às", "Lead venda R$".

## Decisões de escopo (confirmadas)

1. **Importar todos** os contatos com nome + telefone, **deduplicando por telefone** (um cliente por
   telefone, preservando o histórico de etapas/datas dos leads daquele telefone).
2. **Identidade do cliente = telefone normalizado** (chave única). Nome é complementar.
3. **Obrigatoriedade**: exigida **ao salvar os dados de venda** de um evento, não no sync do Google
   Calendar (os eventos continuam nascendo do calendário sem cliente).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Associar (ou criar) um cliente no evento (Priority: P1) 🎯 MVP

Como vendedor, na seção "Dados de Venda" de um evento, quero **buscar e associar um cliente** da base;
se ele ainda não existir, quero **criá-lo ali mesmo** (nome + telefone, e-mail/empresa opcionais) sem
sair da página.

**Why this priority**: É o coração do pedido — sem associação evento↔cliente nada do ecossistema
existe. Entrega valor sozinha mesmo antes da importação em massa.

**Independent Test**: Abrir um evento, buscar um cliente pelo nome/telefone, associá-lo, salvar e
reabrir o evento vendo o cliente vinculado; alternativamente criar um novo cliente inline e associá-lo.

**Acceptance Scenarios**:

1. **Given** um evento e um cliente existente na base, **When** busco pelo nome ou telefone e seleciono,
   **Then** o evento fica associado a esse cliente após salvar.
2. **Given** um cliente que **não existe**, **When** preencho nome + telefone no formulário inline de
   "novo cliente", **Then** o cliente é criado e já fica associado ao evento.
3. **Given** que tento criar um cliente com um **telefone que já existe** na base, **Then** o sistema
   reaproveita/aponta o cliente existente em vez de duplicar (telefone é chave única).
4. **Given** um evento já associado, **When** reabro a página, **Then** vejo o cliente vinculado (nome +
   telefone) e posso trocá-lo ou removê-lo.

### User Story 2 - Importar a base do Kommo (deduplicada) (Priority: P1)

Como administrador, quero **importar o CSV do Kommo** para popular a base de clientes de uma vez,
deduplicando por telefone, para não começar do zero.

**Why this priority**: Sem a base importada, o vendedor teria que recadastrar tudo à mão. Habilita o
valor de marketing prometido ("base de clientes").

**Independent Test**: Rodar a importação apontando para o CSV e verificar que a base de clientes foi
criada com um cliente por telefone único, com contagem de criados/mesclados/ignorados reportada.

**Acceptance Scenarios**:

1. **Given** o arquivo `kommo_export_leads_2026-06-29.csv`, **When** executo a importação, **Then** cada
   **telefone único** vira **um** cliente, com nome preenchido a partir de "Nome completo".
2. **Given** linhas **sem telefone utilizável** (vazio ou sem dígitos suficientes), **When** importo,
   **Then** essas linhas são **ignoradas** e contabilizadas no relatório (sem quebrar a importação).
3. **Given** múltiplas linhas com o **mesmo telefone**, **When** importo, **Then** elas formam **um
   único** cliente; metadados de marketing (tags, etapa, datas, valor de venda) do(s) lead(s) são
   preservados/agregados nesse cliente.
4. **Given** que a importação é executada **novamente** (re-run), **Then** clientes já existentes
   (mesmo telefone) **não são duplicados** (idempotência por telefone).

### User Story 3 - Cliente obrigatório a partir de agora (Priority: P2)

Como gestor, quero que, **a partir da ativação desta funcionalidade**, **não seja possível salvar os
dados de venda** de um evento sem um cliente associado; eventos **passados/antigos** sem cliente
permanecem válidos (grandfathering).

**Why this priority**: Garante a qualidade da base daqui pra frente sem travar o histórico nem o sync
do calendário.

**Independent Test**: Tentar salvar a venda de um evento novo sem cliente e ver o bloqueio com mensagem
clara; salvar com cliente e ver sucesso; editar um evento antigo sem cliente e não ser bloqueado.

**Acceptance Scenarios**:

1. **Given** um evento elegível (a partir da data de ativação) **sem** cliente, **When** tento salvar os
   dados de venda, **Then** o sistema **bloqueia** e exibe mensagem pedindo para associar/criar um
   cliente; nenhum dado de venda é perdido (o formulário mantém o que foi preenchido).
2. **Given** o mesmo evento **com** cliente associado, **When** salvo, **Then** a venda é salva
   normalmente.
3. **Given** um evento **antigo/passado** sem cliente, **When** edito qualquer outro dado, **Then**
   **não** sou obrigado a associar cliente (grandfathering).
4. **Given** o sync do Google Calendar criando eventos, **Then** ele **não** é bloqueado pela ausência
   de cliente.

### User Story 4 - Ecossistema do cliente (lista + ficha de marketing) (Priority: P2)

Como time de marketing/comercial, quero uma **lista de clientes** pesquisável e uma **ficha por
cliente** mostrando **quantos eventos fechou, as datas e os valores**, além dos metadados de marketing,
para planejar ações sobre a base.

**Why this priority**: É o "ecossistema completo" pedido; depende de US1/US2 existirem, por isso P2.

**Independent Test**: Abrir a lista de clientes, pesquisar um nome, abrir a ficha e conferir a contagem
de eventos, as datas e o total gasto batendo com os eventos associados.

**Acceptance Scenarios**:

1. **Given** a base de clientes, **When** abro a lista, **Then** vejo clientes com nome, telefone e
   **nº de eventos** associados, com busca por nome/telefone.
2. **Given** um cliente com eventos associados, **When** abro a ficha, **Then** vejo a **lista de
   eventos** (data, título, valor de venda, status) e os **totais** (nº de eventos, soma de vendas).
3. **Given** um cliente **sem** eventos, **When** abro a ficha, **Then** vejo um estado vazio claro
   ("nenhum evento associado ainda") e os metadados de marketing disponíveis.
4. **Given** os metadados importados (tags, etapa, responsável, origem), **When** abro a ficha, **Then**
   eles aparecem para apoiar a segmentação de marketing.

### Edge Cases

- **Telefone normaliza para o mesmo número, nome diferente**: trata como o mesmo cliente (telefone é a
  chave); mantém o nome já existente e registra divergência de nome como informação, sem duplicar.
- **Nome presente, telefone ausente**: na importação a linha é ignorada (sem chave). Na criação inline,
  o telefone é obrigatório.
- **Telefone curto/inválido** (menos dígitos que um número discável): ignorado na importação; rejeitado
  com mensagem na criação inline.
- **Evento satélite de um grupo**: a associação de cliente é do próprio evento (não herda do principal
  nesta feature), coerente com os demais dados comerciais.
- **Excluir um cliente que tem eventos**: a exclusão é bloqueada (ou os eventos ficam sem cliente) —
  ver FR-013.

## Requirements *(mandatory)*

### Importação

- **FR-001**: O sistema MUST importar contatos do CSV do Kommo criando **um cliente por telefone
  normalizado único**, usando "Nome completo" como nome.
- **FR-002**: O sistema MUST **ignorar** linhas sem telefone utilizável e **reportar** ao final
  contagens de criados, mesclados (telefone repetido) e ignorados.
- **FR-003**: A importação MUST ser **idempotente** por telefone: re-execução não cria duplicatas.
- **FR-004**: O sistema MUST preservar metadados de marketing por cliente a partir do(s) lead(s)
  correspondente(s): tags, etapa do lead, funil, usuário responsável, origem, data de criação e valor
  de venda do lead (quando houver).

### Associação ao evento

- **FR-005**: Cada evento MUST poder ser **associado a no máximo um cliente** (campo opcional no nível
  de dados; passados podem ficar sem cliente).
- **FR-006**: O vendedor MUST poder **buscar** um cliente por nome ou telefone e associá-lo ao evento.
- **FR-007**: O vendedor MUST poder **criar** um cliente inline (nome + telefone obrigatórios; e-mail/
  empresa opcionais) e ele já fica associado ao evento.
- **FR-008**: Ao criar inline com um telefone já existente, o sistema MUST **reaproveitar** o cliente
  existente em vez de duplicar.
- **FR-009**: O vendedor MUST poder **trocar ou remover** o cliente associado a um evento.

### Obrigatoriedade

- **FR-010**: A partir da **data de ativação** da funcionalidade, o sistema MUST **impedir o salvamento
  dos dados de venda** de um evento elegível sem cliente associado, com mensagem clara e sem descartar o
  que o usuário preencheu.
- **FR-011**: Eventos **anteriores** à ativação (passados/antigos sem cliente) MUST permanecer
  editáveis **sem** exigir cliente (grandfathering).
- **FR-012**: A ausência de cliente MUST **não** bloquear a sincronização de eventos do Google Calendar.

### Ecossistema / Marketing

- **FR-013**: O sistema MUST oferecer uma **lista de clientes** pesquisável (nome/telefone) com o número
  de eventos associados por cliente, restrita a papéis comercial/financeiro/superadmin.
- **FR-014**: O sistema MUST oferecer uma **ficha de cliente** com dados de contato, metadados de
  marketing e a **lista de eventos associados** (data, título, valor, status) e **totais** (nº de
  eventos, soma de vendas).
- **FR-015**: A exclusão de um cliente com eventos associados MUST ser tratada com segurança (bloquear a
  exclusão **ou** desvincular os eventos), nunca deixando referências órfãs.

### Acesso

- **FR-016**: As funcionalidades de clientes (lista, ficha, criação, associação) MUST ser restritas a
  usuários com papel **COMERCIAL**, **FINANCEIRO** ou **SUPERADMIN**, coerente com a área comercial
  existente.

## Key Entities *(include if feature involves data)*

- **Cliente**: uma pessoa/contato da base. Atributos: nome, **telefone normalizado (único)**, e-mail
  (opcional), empresa (opcional), origem (`kommo_import` | `manual`), metadados de marketing (tags,
  etapa do lead, funil, usuário responsável, valor de venda do lead, datas do Kommo), referência ao lead
  Kommo (rastreabilidade), data de criação. Relaciona-se a zero ou mais **Eventos**.
- **Evento** (existente): ganha referência opcional a **um Cliente**. Eventos passados podem não ter
  cliente; novos exigem cliente ao salvar dados de venda.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos telefones únicos válidos do CSV resultam em exatamente **um** cliente; nenhum
  telefone único gera duplicata após uma ou múltiplas execuções da importação.
- **SC-002**: Um vendedor consegue associar ou criar um cliente em um evento em **menos de 30 segundos**,
  sem sair da página do evento.
- **SC-003**: Após a ativação, **0** eventos elegíveis conseguem ter dados de venda salvos sem cliente
  associado; eventos antigos continuam editáveis sem cliente.
- **SC-004**: Na ficha de um cliente, a **contagem de eventos** e a **soma de vendas** batem exatamente
  com os eventos associados a ele.
- **SC-005**: A importação processa as ~6,5 mil linhas do CSV sem erro e apresenta um relatório com
  criados/mesclados/ignorados.

## Assumptions

- **"Mensagem"/canal não se aplica aqui**: o foco é dado/relacionamento; nenhuma integração de envio
  (WhatsApp/e-mail) faz parte deste escopo — apenas a base e as telas para apoiar marketing.
- **Normalização de telefone**: remove tudo que não é dígito; mantém DDI/DDD; números com poucos
  dígitos são considerados inválidos. Dois números que normalizam igual são o mesmo cliente.
- **Nome do cliente** vem de "Nome completo"; "Pessoa de contato" muitas vezes é "Manto Produções" (a
  própria empresa) e **não** é usado como nome.
- **Data de ativação** = data em que a funcionalidade entra em produção (a partir do deploy desta
  feature). Eventos com data de início anterior a essa data são grandfathered.
- **Elegibilidade da obrigatoriedade** recai sobre o **salvamento dos dados de venda** (seção comercial
  do evento), não sobre criação/edição de campos não comerciais nem sobre o sync do calendário.
- **Sem novo papel de usuário**: reutiliza os papéis comerciais existentes (COMERCIAL/FINANCEIRO/
  SUPERADMIN).
- **Importação via comando administrativo** (rodada pelo time técnico/admin), não uma tela de upload de
  CSV nesta primeira entrega; a criação contínua de clientes se dá inline no evento e na tela de
  clientes.
