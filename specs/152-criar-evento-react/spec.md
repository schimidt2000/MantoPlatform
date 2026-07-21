# Feature Specification: criar evento em React (152)

**Feature Branch**: `152-criar-evento-react`

**Created**: 2026-07-21

**Status**: Draft

**Input**: Continuação da migração 144 (US2 — Agenda e Eventos). Casting (146-148), confirmar/
logística (149), observações (150) e excluir/sincronizar (151) já migrados. Esta fatia migra a
**criação de evento** (`GET/POST /events/new`, view `create_event`, template `event_create.html`)
para React — a tela com mais lógica de negócio do sistema depois do detalhe do evento. Escopo:
os campos centrais do formulário (dados do evento, financeiro, origem por orçamento, elenco,
vínculos de cliente/pré-contrato, reembolso, observações). Fora de escopo: qualquer campo de
upload de arquivo (nota fiscal, contrato, comprovantes de pagamento, comprovante de reembolso,
imagem de observação) — adiados para uma fatia futura de upload, mesmo padrão já usado em
148/149/150/151 (onde imagem/arquivo ficou só em leitura ou foi adiado inteiramente).

## Contexto

Mesmo padrão strangler-fig das fatias anteriores: núcleo compartilhado reaproveitado pelo wrapper
Jinja existente e por um endpoint JSON novo, verificação por paridade contra `manto_local` com o
Google Calendar mockado (a criação de evento chama `insert_event` no Google antes de gravar no
banco). RBAC idêntica ao Jinja: `_CAN_CREATE` (Comercial, Superadmin — conferir constante exata em
`routes.py` no plano).

Diferença desta fatia em relação às anteriores: `create_event` não é uma ação única, é um
formulário com ~9 grupos de dados que hoje chegam juntos em um único POST multipart. Para manter
"Planejar antes de codar" e fatias verificáveis, esta spec organiza esses grupos em User Stories
priorizadas — mesmo sabendo que, na prática, todas devem ser entregues juntas numa única tela
React (um formulário de criação pela metade não é utilizável em produção). A priorização serve
para orientar a ordem de implementação/verificação dentro da mesma fatia, não para um lançamento
parcial em produção.

**Já migrado (não é escopo aqui)**: elenco pós-criação (escalar/convidar/dispensar — 146-148),
confirmar evento e logística (149), observações pós-criação (150), excluir/sincronizar (151).

**Fora de escopo (adiado)**: nota fiscal com arquivo, contrato com arquivo, comprovantes de
pagamento (múltiplos arquivos), comprovante de reembolso, imagem em observação — todos os campos
`*_file`/`*_image[]` do form atual. Não existe hoje um endpoint genérico de upload (`POST
/api/uploads` foi só uma assumption da spec 144, nunca implementado); construí-lo fica para a
fatia que primeiro precisar dele de verdade.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Criar evento com dados essenciais (Priority: P1)

O Comercial (ou Superadmin) cria um evento novo em React informando título, tipo, data, horário de
início/fim, local e descrição. O evento é criado no Google Calendar e no banco, e a tela navega
para o detalhe do evento recém-criado.

**Why this priority**: é o MVP absoluto — sem isso não existe "criar evento" nenhum; toda regra
adicional (financeiro, elenco, etc.) só faz sentido em cima de um evento que já existe.

**Independent Test**: preencher só os campos essenciais (título, tipo, data, horário, local),
enviar, e conferir que o evento aparece no banco com `google_event_id` preenchido (Google
mockado), e que a tela navega para `/events/<id>` — mesmo efeito do POST Jinja com os mesmos
campos mínimos.

**Acceptance Scenarios**:

1. **Given** o formulário de criação vazio, **When** o usuário preenche título/tipo/data/horário/
   local e envia, **Then** o evento é criado (Google + banco) e a tela navega ao detalhe.
2. **Given** título vazio, data vazia, ou apenas um dos horários (início/fim) preenchido, **When**
   o usuário envia, **Then** a tela mostra os erros de validação correspondentes sem perder o que
   já foi digitado (Princípio V), igual ao Jinja.
3. **Given** horário de início igual ao de fim, **When** o usuário envia, **Then** recebe erro
   "horário de fim deve ser diferente do início" — paridade com o Jinja.
4. **Given** falha do Google Calendar ao criar o evento, **When** o usuário envia um formulário
   válido, **Then** recebe mensagem amigável (não stack trace) e nada é criado no banco — paridade
   com o Jinja.
5. **Given** um usuário sem papel Comercial/Superadmin, **When** acessa a tela ou envia o form,
   **Then** recebe 403 — paridade com o gate `_CAN_CREATE` do Jinja.

---

### User Story 2 - Dados financeiros da venda (Priority: P2)

Ao criar o evento, o Comercial informa os dados financeiros: valor antes do desconto, valor de
venda, transporte, acréscimos tipados, vendedor responsável, data de venda, forma de pagamento
(incluindo parcelamento no PIX) e se a venda tem nota fiscal (só a flag — sem anexar arquivo
ainda). Um evento pode ser marcado como cortesia/permuta, dispensando os valores obrigatórios.

**Why this priority**: é a segunda coisa mais crítica do formulário (comissão do vendedor e
faturamento dependem disso), mas só faz sentido depois que o evento em si (US1) já existe.

**Independent Test**: criar um evento preenchendo os campos financeiros e conferir que
`CalendarEvent` grava `sale_value`, `sale_value_gross`, `transport_value`, `seller_id`,
`payment_method`/`payment_installments`/`payment_due_date`, `with_invoice` exatamente como o Jinja
gravaria para o mesmo input; conferir que os acréscimos tipados viram linhas `EventAcrescimo` com
o mesmo cálculo (percentual vs. valor fixo); conferir que marcar cortesia/permuta dispensa a
obrigatoriedade dos valores e zera `sale_value`.

**Acceptance Scenarios**:

1. **Given** um evento não-cortesia, **When** o usuário não informa valor antes do desconto ou
   valor de venda (ou informa zero/negativo), **Then** recebe erro de validação — paridade com o
   Jinja.
2. **Given** a forma de pagamento "dividido no PIX", **When** o número de parcelas está fora de
   2–12 ou vazio, **Then** recebe erro de validação — paridade com o Jinja.
3. **Given** o evento marcado como cortesia/permuta, **When** o usuário não informa valores,
   **Then** o evento é criado com `sale_value = 0` e sem exigir os campos financeiros — paridade
   com o Jinja.
4. **Given** nenhum vendedor selecionado, **When** o usuário envia, **Then** recebe erro
   "selecione o vendedor responsável" — paridade com o Jinja.
5. **Given** acréscimos tipados (percentual e valor fixo) informados, **When** o evento é criado,
   **Then** as linhas `EventAcrescimo` gravam o mesmo `amount_brl` calculado que o Jinja calcularia
   para os mesmos valores de entrada.

---

### User Story 3 - Elenco e pré-escala de talento (Priority: P3)

Ao criar o evento, o Comercial adiciona os personagens/vagas do elenco (nome, ficha de figurino —
selecionada ou auto-detectada pelo nome —, se precisa de maquiagem, se é cantor, cachê) e
opcionalmente pré-escala um talento específico em cada vaga (sem disparar convite automático).

**Why this priority**: depende do evento já existir (US1) e é conceitualmente separado do
financeiro (US2) — pode ser desenvolvido/verificado de forma independente.

**Independent Test**: criar um evento com 2+ personagens, um deles com talento pré-escalado, e
conferir que as linhas `EventRole` gravam `character_name`/`figurino_sheet_id`/`cache_value`/
`needs_makeup`/`is_singer`/`talent_id`/`assigned_at` exatamente como o Jinja gravaria; conferir que
um talento já usado em outra vaga do mesmo formulário não pode ser reaproveitado; conferir que
conflito de agenda do talento pré-escalado gera aviso não-bloqueante (evento é criado mesmo assim).

**Acceptance Scenarios**:

1. **Given** um personagem sem ficha de figurino selecionada manualmente, **When** o nome do
   personagem bate (case-insensitive) com uma ficha existente, **Then** a vaga é auto-vinculada a
   essa ficha — paridade com o Jinja.
2. **Given** um talento pré-escalado em uma vaga, **When** ele já está pré-escalado em outra vaga
   do mesmo formulário, **Then** a segunda tentativa é ignorada (vaga nasce sem talento) — paridade
   com o Jinja.
3. **Given** um talento pré-escalado com conflito de horário com outro evento, **When** o evento é
   criado, **Then** o evento é criado normalmente e a tela mostra um aviso de conflito (não
   bloqueia) — paridade com o Jinja.
4. **Given** nenhum coordenador pré-escalado e a criação não vem de um orçamento, **When** o
   evento é criado, **Then** uma vaga de coordenador vazia é garantida automaticamente — paridade
   com `_ensure_coordinator`.
5. **Given** o tipo do evento é "SHOW", **When** o evento é criado, **Then** a vaga de técnico de
   som é garantida automaticamente — paridade com `_ensure_sound_technician`.

---

### User Story 4 - Origem por orçamento (Priority: P4)

Ao abrir a tela de criação a partir de um orçamento salvo (`OrcamentoHistory`), os campos
essenciais, financeiros e o elenco vêm pré-preenchidos a partir do snapshot do orçamento, incluindo
a escolha de duração (1h/2h/3h/4h/personalizada) que recalcula os totais e os cachês por
personagem.

**Why this priority**: é uma otimização de fluxo (evita redigitar um orçamento já calculado) sobre
uma criação que já funciona sem ela (US1-3) — por isso vem depois.

**Independent Test**: abrir a criação com `?orcamento_id=<id>` de um orçamento existente, conferir
que os campos vêm pré-preenchidos com os valores do snapshot (incluindo transporte recalculado se
fora de SP), trocar a duração e conferir que o total exibido muda para o valor daquela duração;
enviar e conferir que `orcamento_history_id` é gravado no evento e que os cachês por personagem
batem com a duração escolhida.

**Acceptance Scenarios**:

1. **Given** um `orcamento_id` válido na URL, **When** a tela carrega, **Then** os campos
   essenciais e financeiros vêm pré-preenchidos a partir do snapshot — paridade com o Jinja.
2. **Given** um `orcamento_id` inexistente ou inválido, **When** a tela carrega, **Then** o
   formulário abre vazio (sem erro) — paridade com o Jinja.
3. **Given** a duração trocada de 1h para 3h, **When** o usuário muda a seleção, **Then** o total e
   os cachês por personagem recalculam para os valores da duração de 3h do snapshot.

---

### User Story 5 - Vínculos e observações (sem upload) (Priority: P5)

Ao criar o evento, o Comercial pode associar um ou mais clientes existentes (com o tipo de
relação), vincular uma resposta de pré-contrato já recebida, registrar um reembolso a cobrar da
cliente (descrição + valor, sem comprovante ainda) e adicionar observações em texto ou link (sem
imagem ainda).

**Why this priority**: são complementos que enriquecem o evento recém-criado mas não bloqueiam a
criação em si — por isso vêm por último na ordem de implementação.

**Independent Test**: criar um evento associando 2 clientes (um deles marcado como principal),
vinculando uma resposta de pré-contrato existente e sem evento ainda, adicionando um reembolso e
uma observação de texto e uma de link; conferir que `EventClient`, `FormResponse.event_id`,
`EventReimbursement` e `EventObservation` gravam exatamente como o Jinja gravaria para o mesmo
input.

**Acceptance Scenarios**:

1. **Given** 2+ clientes associados na criação, **When** o evento é criado, **Then** as linhas
   `EventClient` são gravadas e o cliente principal é definido — paridade com o Jinja.
2. **Given** uma resposta de pré-contrato já existente e ainda sem evento vinculado, **When** o
   evento é criado com essa resposta selecionada, **Then** `FormResponse.event_id` passa a apontar
   para o evento novo — paridade com o Jinja.
3. **Given** um reembolso com descrição e valor válidos (sem arquivo), **When** o evento é criado,
   **Then** `EventReimbursement` é gravado sem `invoice_file_path` — comprovante fica para a fatia
   de upload.
4. **Given** uma observação do tipo imagem enviada no formulário, **When** o evento é criado,
   **Then** essa observação específica é ignorada (sem arquivo ainda) mas texto/link continuam
   funcionando — mesmo padrão já adotado na feature 150 (upload de imagem adiado).

---

### Edge Cases

- **Cortesia/permuta**: dispensa os campos financeiros obrigatórios e força `sale_value = 0` —
  checagem preservada exatamente como no Jinja.
- **Falha do Google Calendar**: a criação inteira é abortada (nada grava no banco) com mensagem
  amigável — diferente de excluir/sincronizar (151), aqui a falha do Google É bloqueante porque o
  evento nasce do `insert_event`.
- **Talento pré-escalado duplicado no mesmo formulário**: a segunda ocorrência do mesmo
  `talent_id` em vagas diferentes é ignorada silenciosamente (paridade com `_preassign_talent_id` /
  `used_talent_ids`).
- **Conflito de agenda do talento pré-escalado**: não bloqueia a criação, apenas gera aviso —
  paridade com o comportamento pós-commit do Jinja.
- **Origem por orçamento inexistente/inválida**: formulário abre vazio, sem erro — paridade com o
  Jinja (`if entry:` silencioso).
- **Imagem de observação enviada sem endpoint de upload**: a observação de imagem específica é
  descartada nesta fatia (paridade com o padrão já usado em 150); texto/link continuam
  funcionando.
- **Campos de arquivo em geral** (nota fiscal, contrato, comprovantes de pagamento, comprovante de
  reembolso): nenhum desses aparece na tela React desta fatia — ficam para a fatia de upload.
- **Coexistência**: o Jinja (`app.`) continua criando eventos normalmente durante a transição; um
  só núcleo compartilhado evita divergência entre os dois caminhos.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A criação de evento em React MUST produzir exatamente o mesmo estado no banco que o
  fluxo Jinja produziria para o mesmo input (mesmas tabelas: `CalendarEvent`, `EventRole`,
  `EventClient`, `EventAcrescimo`, `EventInvoice`, `EventReimbursement`, `EventObservation`,
  `EventLog`), reusando a mesma lógica de validação e gravação já existente (Princípio I) — não
  reimplementada.
- **FR-002**: RBAC MUST ser idêntica ao Jinja (`_CAN_CREATE`) — aplicada no servidor.
- **FR-003**: Validações obrigatórias (título, data, horários início/fim distintos e ambos
  presentes, valores financeiros quando não-cortesia, vendedor responsável, parcelas do PIX
  parcelado) MUST produzir os mesmos erros que o Jinja produz para o mesmo input, preservando os
  valores já digitados (Princípio V) — nenhum campo apagado ao re-exibir erro.
- **FR-004**: Falha do Google Calendar ao criar o evento MUST abortar a criação inteira (nada grava
  no banco) e mostrar mensagem amigável — nunca stack trace.
- **FR-005**: O elenco informado na criação MUST gravar `EventRole` por personagem, com
  auto-detecção de ficha de figurino por nome quando não selecionada manualmente, e MUST respeitar
  a pré-escala opcional de talento (sem convite automático, sem duplicar talento entre vagas do
  mesmo formulário, com aviso não-bloqueante de conflito de agenda).
- **FR-006**: Coordenador e (para eventos tipo SHOW) técnico de som MUST ser garantidos
  automaticamente quando não vierem de um orçamento e não houver pré-escala manual — paridade com
  `_ensure_coordinator`/`_ensure_sound_technician`.
- **FR-007**: A criação a partir de um orçamento salvo (`?orcamento_id=`) MUST pré-preencher os
  campos essenciais/financeiros e recalcular totais/cachês conforme a duração escolhida (1h–4h ou
  personalizada), com o mesmo cálculo hoje usado no Jinja; um id inválido/inexistente MUST abrir o
  formulário vazio sem erro.
- **FR-008**: Clientes associados, vínculo de pré-contrato (`FormResponse`) e reembolso (sem
  arquivo) informados na criação MUST gravar exatamente como no Jinja.
- **FR-009**: Observações de texto/link informadas na criação MUST gravar normalmente; observações
  do tipo imagem MUST ser aceitas pela interface mas descartadas na gravação nesta fatia (sem
  endpoint de upload ainda) — mesmo padrão já adotado na feature 150.
- **FR-010**: Nenhum campo de arquivo (nota fiscal, contrato, comprovantes de pagamento,
  comprovante de reembolso) MUST aparecer na tela React desta fatia.
- **FR-011**: O fluxo Jinja de criação de evento MUST continuar funcionando inalterado durante a
  transição (coexistência, mesmo banco).
- **FR-012**: Nenhum botão de ação MUST ficar "morto" ao clique (Princípio V); um clique a mais
  NUNCA cria dois eventos.
- **FR-013**: A tela React de criação MUST cumprir o Princípio VIII (mobile-first) — sem rolagem
  horizontal, alvos de toque adequados, em viewport 320–430px.

### Key Entities

Sem entidade nova. Grava em `CalendarEvent`, `EventRole`, `EventClient`, `EventAcrescimo`,
`EventInvoice` (sem arquivo), `EventReimbursement` (sem arquivo), `EventObservation` (texto/link),
`EventLog`, e atualiza `FormResponse.event_id` quando aplicável. Nenhuma mudança de schema.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Criar um evento pela API com qualquer combinação de campos suportados produz um
  estado de banco indistinguível de criar o mesmo evento pelo Jinja — verificado contra
  `manto_local` (Google mockado).
- **SC-002**: Todas as validações de erro do Jinja (título, data, horário, financeiro, vendedor,
  parcelamento) têm equivalente na API, com o formulário preservando os dados já digitados.
- **SC-003**: Falha do Google nunca deixa o banco em estado parcial (evento sem elenco/financeiro
  ou vice-versa) — é tudo ou nada.
- **SC-004**: Nenhum campo de arquivo aparece na tela React desta fatia; nenhuma regressão no
  fluxo Jinja de criação durante a transição.

## Assumptions

- **Núcleo compartilhado**: a lógica de validação + gravação de `create_event` é extraída para uma
  função reaproveitada pelo wrapper Jinja (comportamento inalterado) e por um endpoint JSON novo —
  mesmo padrão de 146-151. Nome/local exato da função e do(s) endpoint(s) (`POST /api/events` no
  plano, em `app/api/agenda_write.py`) ficam para o `/speckit-plan`.
- **Upload adiado por completo nesta fatia**: nenhum campo de arquivo é migrado agora — inclusive
  os que hoje são opcionais no Jinja (nota fiscal, contrato, comprovantes, reembolso, imagem de
  observação). A fatia de upload futura decide o contrato genérico (`POST /api/uploads` ou
  multipart no próprio recurso) e então reintroduz esses campos na tela de criação.
- **Verificação** mocka `insert_event` (Google) e roda contra `manto_local`, cobrindo as 5 User
  Stories acima por paridade linha-a-linha com o resultado do POST Jinja equivalente. Requests do
  test client fora de `app_context`.
- **Prioridade das User Stories** reflete ordem de implementação/verificação dentro desta mesma
  fatia — não um lançamento parcial em produção (um formulário de criação incompleto não é
  utilizável); a tela React só é considerada pronta com as 5 User Stories entregues juntas.
- Continuação natural da migração da agenda: depois desta fatia, falta em Jinja apenas as ações de
  upload (contrato/pagamento/reembolso/imagem de observação/nota fiscal) — última fatia da US2.
