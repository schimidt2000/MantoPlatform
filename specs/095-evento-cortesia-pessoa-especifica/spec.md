# Feature Specification: Evento cortesia/permuta e solicitação de pessoa específica na criação

**Feature Branch**: `095-evento-cortesia-pessoa-especifica`

**Created**: 2026-06-30

**Status**: Draft

**Input**: "Preciso que ao criar evento dê para marcar que o evento é cortesia ou permuta — dessa forma, não precisa colocar valor de venda ou com desconto. Também preciso que tenha uma parte que dê para o vendedor, durante a criação do evento, marcar se precisa de alguém específico — seja coordenador específico ou artista específico."

## Contexto

Na tela de **criação de evento** (`/events/new`), o vendedor preenche dados comerciais e a equipe do
evento (personagens/artistas e coordenador). Hoje há duas lacunas:

1. **Cortesia/permuta**: o evento pode ser uma cortesia ou permuta (sem venda em dinheiro), mas a tela
   de criação **exige** "valor antes do desconto" e "valor de venda" maiores que zero — impossível
   registrar uma cortesia ali. O conceito de cortesia/permuta **já existe** na página do evento (o
   evento já tem essa marcação, que zera a venda e trata os cachês como custo de marketing), mas **não**
   na criação.
2. **Pessoa específica**: às vezes o vendedor fecha o evento já sabendo que precisa de **uma pessoa
   específica** — um **coordenador** específico ou um **artista** específico. Hoje ele não tem como
   indicar isso na criação; quem monta a equipe é o casting, depois, sem essa informação.

## Decisões de escopo (confirmadas)

- **Pessoa específica = pré-escalar o talento na vaga**: ao indicar a pessoa, o vendedor **já atribui**
  o talento àquela vaga (coordenador ou personagem). O casting **confere e envia o convite** — reaproveita
  o fluxo de convite/conflito existente (a vaga não fica "aberta").
- **Origem = Banco de Talentos**: a pessoa é **selecionada do banco de talentos** (cadastro existente),
  tanto para coordenador quanto para artista.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Criar evento cortesia/permuta sem exigir valor (Priority: P1) 🎯 MVP

Como vendedor, ao criar um evento, quero **marcar que é cortesia ou permuta** e, com isso, **não ser
obrigado** a informar valor de venda nem desconto, para registrar corretamente eventos sem venda em
dinheiro.

**Why this priority**: É um bloqueio real — hoje não dá para criar cortesia/permuta pela tela de
criação. Entrega valor sozinha.

**Independent Test**: Criar um evento marcando "cortesia/permuta", deixar os valores em branco e salvar
com sucesso; abrir o evento e ver que a venda é zero e a marcação de cortesia/permuta está ativa.

**Acceptance Scenarios**:

1. **Given** a tela de criação, **When** marco "cortesia/permuta", **Then** os campos de valor (antes do
   desconto e valor de venda) deixam de ser obrigatórios e o formulário deixa claro que não há venda.
2. **Given** "cortesia/permuta" marcado e valores em branco, **When** salvo, **Then** o evento é criado
   com **venda = 0** e a marcação de cortesia/permuta registrada (sem erro de "informe o valor").
3. **Given** "cortesia/permuta" **desmarcado**, **When** salvo sem valor, **Then** o sistema continua
   **exigindo** o valor de venda (comportamento atual preservado para vendas normais).
4. **Given** um evento de cortesia/permuta criado, **When** abro sua página, **Then** ele aparece como
   cortesia/permuta de forma consistente com a marcação já existente no evento (cachês tratados como
   custo de marketing, como hoje).

### User Story 2 - Solicitar artista específico na criação (Priority: P1)

Como vendedor, ao montar a equipe na criação do evento, quero **indicar um artista específico do banco
de talentos** para um personagem, **pré-escalando** essa pessoa naquela vaga, para garantir que o
casting saiba e mantenha quem o cliente pediu.

**Why this priority**: É a parte estruturada do pedido e entrega o maior valor; depende só do banco de
talentos que já existe.

**Independent Test**: Na criação, adicionar um personagem, escolher um talento específico do banco para
ele e salvar; abrir o evento e ver o talento já atribuído àquela vaga (aguardando convite do casting).

**Acceptance Scenarios**:

1. **Given** uma linha de personagem na criação, **When** busco e seleciono um talento do banco para
   ela, **Then** ao salvar a vaga já fica **com o talento atribuído** (pré-escalado).
2. **Given** um personagem **sem** talento específico, **When** salvo, **Then** a vaga fica **aberta**
   (comportamento atual — casting escala depois).
3. **Given** uma vaga pré-escalada, **When** o casting abre o evento, **Then** vê o talento já atribuído
   e pode **enviar o convite** normalmente (a pré-escala não envia convite automático).
4. **Given** o talento pré-escalado tem conflito de agenda no horário, **When** salvo/abro o evento,
   **Then** o sistema **sinaliza o conflito** (aviso), sem impedir a pré-escala.

### User Story 3 - Solicitar coordenador específico na criação (Priority: P2)

Como vendedor, ao criar o evento, quero **indicar um coordenador específico do banco de talentos**,
pré-escalando-o na vaga de coordenador, para casos em que o coordenador certo já é conhecido.

**Why this priority**: Mesma mecânica do artista, aplicada à vaga de coordenador (que hoje é criada
automaticamente vazia). Complementa US2.

**Independent Test**: Na criação, escolher um coordenador específico e salvar; abrir o evento e ver a
vaga de Coordenador já com esse talento atribuído.

**Acceptance Scenarios**:

1. **Given** a criação do evento, **When** seleciono um coordenador específico do banco, **Then** a vaga
   de Coordenador é criada **já com esse talento** atribuído.
2. **Given** que **não** seleciono coordenador específico, **When** salvo, **Then** a vaga de
   Coordenador é criada **vazia**, como hoje (a designação fica para depois).
3. **Given** um coordenador específico pré-escalado, **When** o casting abre o evento, **Then** vê o
   coordenador atribuído e pode enviar o convite.

### Edge Cases

- **Cortesia/permuta com valor digitado**: se o vendedor marca cortesia/permuta mas ainda assim digita
  um valor, a venda é tratada como **zero** (a marcação prevalece), coerente com o comportamento atual
  do evento.
- **Mesmo talento em duas vagas do evento**: pré-escalar a mesma pessoa em dois personagens do mesmo
  evento deve ser evitado/avisado (não faz sentido a pessoa em duas vagas simultâneas).
- **Talento pré-escalado indisponível/conflito**: sinaliza, mas não bloqueia (o casting decide).
- **Evento vindo de orçamento**: a pré-escala convive com os cachês pré-calculados do orçamento (o
  talento ocupa a vaga; o cachê/teto segue a regra atual do orçamento).
- **Coordenador**: continua sendo uma vaga de equipe ("extra") chamada "Coordenador"; a única novidade é
  poder já vir com talento atribuído.

## Requirements *(mandatory)*

### Cortesia/permuta na criação

- **FR-001**: A tela de criação de evento MUST oferecer uma marcação de **cortesia/permuta**.
- **FR-002**: Quando cortesia/permuta estiver marcado, o sistema MUST **não exigir** "valor antes do
  desconto" nem "valor de venda" e MUST permitir salvar com esses campos em branco.
- **FR-003**: Ao salvar um evento marcado como cortesia/permuta, o sistema MUST registrar **venda = 0** e
  a marcação de cortesia/permuta, de forma consistente com a marcação já existente na página do evento.
- **FR-004**: Quando cortesia/permuta **não** estiver marcado, o sistema MUST manter as validações atuais
  (valor de venda obrigatório > 0).

### Pessoa específica (pré-escala) na criação

- **FR-005**: Para cada **personagem** na criação, o vendedor MUST poder **opcionalmente** selecionar um
  **talento do banco** para pré-escalar naquela vaga.
- **FR-006**: O vendedor MUST poder **opcionalmente** selecionar um **coordenador** específico do banco
  para pré-escalar na vaga de Coordenador.
- **FR-007**: Ao salvar, cada vaga com talento selecionado MUST ser criada **já atribuída** a esse
  talento (pré-escalada), **sem** enviar convite automaticamente (o casting envia depois).
- **FR-008**: Vagas **sem** talento selecionado MUST permanecer **abertas** (comportamento atual).
- **FR-009**: A seleção de talento MUST ser feita por **busca no banco de talentos** (nome), retornando
  talentos cadastrados.
- **FR-010**: O sistema MUST **sinalizar** (aviso, sem bloquear) quando o talento pré-escalado tiver
  **conflito de agenda** no horário do evento, reaproveitando a checagem de conflito existente.
- **FR-011**: O casting MUST conseguir, na página do evento, **ver** as vagas pré-escaladas e **enviar o
  convite** normalmente (fluxo existente).

## Key Entities *(include if feature involves data)*

- **Evento** (existente): ganha, na criação, a marcação de **cortesia/permuta** (campo já existente no
  modelo) e a possibilidade de já nascer com vagas pré-escaladas.
- **Vaga/Role do evento** (existente, `EventRole`): pode nascer **com talento atribuído** (pré-escala)
  na criação — tanto para personagens quanto para a vaga de Coordenador. Reusa o vínculo a **Talento** e
  o fluxo de convite já existentes.
- **Talento** (existente): a pessoa específica selecionada vem do **banco de talentos**.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos eventos marcados como cortesia/permuta na criação são salvos **sem** exigir valor
  e ficam com **venda = 0**.
- **SC-002**: Vendas normais (sem a marcação) continuam **exigindo** valor — 0 regressões nesse fluxo.
- **SC-003**: 100% das vagas com talento selecionado na criação nascem **atribuídas** ao talento certo;
  vagas sem seleção nascem **abertas**.
- **SC-004**: O casting consegue enviar convite a uma vaga pré-escalada sem passos extras além dos atuais.
- **SC-005**: Conflitos de agenda de talentos pré-escalados são **sinalizados** na criação/abertura do
  evento.

## Assumptions

- **Reuso do campo existente**: a marcação de cortesia/permuta usa o campo já presente no evento
  (`is_cortesia_permuta`), apenas exposto agora na criação; a lógica financeira (cachês como custo de
  marketing) já existe e não muda.
- **Pré-escala = atribuição sem convite**: a vaga nasce com o talento atribuído, mas o **convite não é
  enviado automaticamente** na criação — fica a cargo do casting (mantém o controle de comunicação).
- **Conflito não bloqueia**: a checagem de conflito de agenda é informativa na criação; o casting decide.
- **Coordenador**: permanece como vaga "extra" chamada "Coordenador"; quando o vendedor escolhe um
  coordenador específico, essa vaga nasce com o talento atribuído em vez de vazia.
- **Permissões**: criação de evento e pré-escala seguem os papéis que já podem criar evento
  (COMERCIAL/SUPERADMIN); a seleção de talento usa o banco de talentos existente.
- **Sem distinção contábil entre "cortesia" e "permuta"**: ambas resultam em venda = 0 e cachês como
  custo de marketing (como hoje); a marcação é única (cortesia/permuta), sem subtipos nesta entrega.
