# Feature Specification: Migração para arquitetura desacoplada (React SPA + Flask API)

**Feature Branch**: `144-migracao-react-spa`

**Created**: 2026-07-20

**Status**: Pronta para planejamento — perguntas de clarificação respondidas (ver seção própria)

**Input**: User description: "Atualizei a constituição do projeto (versão 2.0.0) para uma
arquitetura desacoplada: Frontend em React (Vite) + TypeScript + Tailwind CSS + shadcn/ui +
Framer Motion e Backend Flask atuando estritamente como API RESTful JSON. Leia a constituição
atualizada e faça uma auditoria geral no projeto atual para gerar a especificação completa de
migração, mapeando: (1) rotas Flask que usam render_template e como viram endpoints JSON, (2)
telas/formulários/componentes a recriar no React, (3) como estruturar loading/erro/formulários
(react-hook-form/zod)/animações (Framer Motion), (4) pontos de atenção para não quebrar regras
de negócio existentes (máscara monetária pt-BR, feedback visual)."

## Contexto e escopo real do sistema atual

Auditoria feita em 2026-07-20 contra o código em `main` (commit `202374b`):

- **17 blueprints Flask** registrados (`app/__init__.py`), ~194 rotas no total. Um 18º
  blueprint (`tools_bp`, calculadora de transporte) existe no código mas **não está
  registrado** — está órfão/inacessível em produção hoje.
- **91 templates Jinja2** (`app/templates/`), dos quais ~38 são páginas **standalone**
  (não estendem `base.html`): páginas de erro, `/cadastro` público, todo o Catálogo público
  (8 arquivos), `/f/pre-contrato` e `/f/corporativo`, feedback por token, ficha de figurino
  para impressão, e **todo o Portal do Artista** (12 arquivos, `/portal/...`, sessão de login
  própria, separada da sessão de staff).
- **6 arquivos JS estáticos** (`app/static/js/`) + uma quantidade grande de JS inline em
  templates — destaque para `event_detail.html` (3201 linhas, ~934 de JS inline em 11
  blocos) e `event_create.html` (1210 linhas, ~591 de JS inline): as duas telas com mais
  lógica de negócio no cliente hoje.
- Já existem ~65 rotas que retornam JSON puro (`jsonify`) — mais concentradas em
  `orcamento` (16), `revisao` (12) e `clientes` (6). `calendar` e `figurino` têm zero rotas
  JSON — são as mais acopladas a template e exigirão mais trabalho de conversão.
- Padrões que não têm equivalente direto em uma API JSON stateless: **upload de arquivo**
  (hoje é campo dentro de um `<form multipart>`, resposta é redirect — não há endpoint de
  upload dedicado retornando URL em JSON); **streaming SSE** (`/figurinos/sync-drive/stream`);
  **download binário** (PDF de orçamento/pacote EducaManto, CSV de pagamentos) — hoje
  servidos como `Response` com `Content-Disposition: attachment`, terão que virar contrato
  de blob-download consumido via `fetch` + `URL.createObjectURL` no React.

O `CLAUDE.md` do projeto **ainda descreve a stack antiga** ("Frontend: Jinja2 templates +
HTML/CSS/JS vanilla, sem framework JS") — está desatualizado em relação à constituição 2.0.0
e precisa ser reescrito como parte desta migração (fora do escopo desta spec definir o texto
exato, mas é um FR abaixo).

## Perguntas de clarificação (respondidas em 2026-07-20)

Estas três decisões mudam a forma do plano de implementação inteiro — não tinham um default
razoável dado o tamanho e a criticidade do sistema (ERP em produção, sem suíte de testes
automatizada, usado diariamente pela equipe). Respondidas pelo usuário — as User Stories e
Assumptions abaixo já refletem essas respostas (não são mais um cenário hipotético).

### Q1: Estratégia de corte — big-bang ou strangler-fig (incremental)?

**Contexto**: são 194 rotas, 91 templates, 17 blueprints. Migrar tudo de uma vez implica
"congelar" o Flask+Jinja atual até o React estar 100% pronto (semanas/meses sem poder
entregar nenhuma feature nova nem correção rápida no meio do caminho). Migrar
incrementalmente (blueprint por blueprint, coexistindo com o app antigo) permite entregar e
validar em produção aos poucos, mas exige rodar as duas stacks em paralelo por um tempo
(roteamento híbrido: algumas telas em React consumindo API, outras ainda em Jinja).

| Opção | Resposta | Implicação |
|-------|----------|------------|
| A | Big-bang: migrar tudo antes de qualquer deploy novo | Maior risco (nada em produção até o fim), mas sem complexidade de coexistência |
| B | Strangler-fig por blueprint, ordem de prioridade de negócio | Entregas incrementais e testáveis em produção; exige decidir uma ordem (ex.: Agenda/Eventos primeiro por ser o núcleo operacional) e um mecanismo de roteamento híbrido durante a transição |
| C | Strangler-fig, mas começando pelas superfícies públicas (Catálogo, /cadastro) por serem mais simples/isoladas, deixando o núcleo interno por último | Valida o padrão com risco baixo antes de tocar telas críticas, mas adia o ganho de produtividade nas telas mais usadas pela equipe |
| Custom | Outra ordem/estratégia | — |

**Escolha**: **B** — strangler-fig por blueprint, ordem: (1) Fundação [Auth + Dashboard +
padrão de API + componente monetário + proxy de dev], (2) Agenda e Eventos, (3) Talentos e
Figurino, (4) Financeiro e Vendas, (5) Superfícies Públicas e Catálogo, (6) Cauda
Administrativa. Justificativa do usuário: "Um big-bang em um ERP sem testes é um convite ao
desastre operacional. Precisamos entregar valor em produção de forma contínua e testável."
Esta é exatamente a ordem já assumida nas 6 User Stories abaixo — nenhum reordenamento
necessário.

### Q2: Um único app React ou apps/bundles separados por população de usuário?

**Contexto**: hoje há três populações de usuário com sessões e propósitos bem diferentes:
staff autenticado (admin/agenda/financeiro/etc.), talentos autenticados no Portal do Artista
(login próprio, `/portal`), e visitantes anônimos (Catálogo público, `/cadastro`,
formulários públicos, link de feedback por token). Servir tudo isso a partir de um único
bundle React manda JS de admin para quem só está vendo o catálogo — hoje essas páginas
públicas já são propositalmente leves e isoladas.

| Opção | Resposta | Implicação |
|-------|----------|------------|
| A | Um único app React, com code-splitting por rota | Mais simples de manter, mas exige disciplina de lazy-loading para não pesar as páginas públicas |
| B | Apps separados: (1) interno/staff, (2) Portal do Artista, (3) público anônimo (catálogo/cadastro/formulários/feedback) | Isolamento real de bundle/performance, mas triplica a configuração de build/deploy e duplica peças de UI compartilhadas (ex.: máscara monetária) |
| C | Dois apps: interno+portal juntos (ambos exigem login) vs público anônimo separado | Meio-termo — separa só o que realmente precisa ser leve/anônimo |
| Custom | Outra divisão | — |

**Escolha**: **B** — três apps/bundles React separados: (1) interno/staff, (2) Portal do
Artista, (3) público anônimo (catálogo/cadastro/formulários/feedback).

### Q3: Autenticação da API — sessão de cookie (como hoje) ou token (JWT)?

**Contexto**: hoje o Flask usa Flask-Login com sessão via cookie (mais um fluxo de sessão
separado para o Portal do Artista). Uma API JSON pura costuma usar token (JWT em header
`Authorization`) para evitar CSRF/CORS de cookie entre origens diferentes (Vite dev server
numa porta, Flask noutra) — mas migrar auth é also uma superfície de risco de segurança
alta, e manter cookie de sessão é a mudança mais barata/menos arriscada.

| Opção | Resposta | Implicação |
|-------|----------|------------|
| A | Manter cookie de sessão (Flask-Login), com `SameSite`/CORS configurado para o dev server e para o domínio de produção do React | Menor risco de segurança/regressão, reaproveita RBAC existente quase sem mudança no backend |
| B | Migrar para JWT em header `Authorization`, emitido em `/api/auth/login` | Mais "padrão API REST", mas é uma reescrita de autenticação inteira (logout, expiração, refresh token) em um sistema que hoje não tem isso — risco maior |
| Custom | Outra abordagem (ex.: cookie httpOnly + token CSRF separado) | — |

**Escolha**: **Custom** — manter cookie de sessão **HttpOnly** com Flask-Login, com CORS
configurado para os três apps/bundles (dev server(s) e domínio(s) de produção). Reaproveita
o RBAC existente quase sem mudança no backend; cobre também a sessão própria do Portal do
Artista (não só a de staff).

---

## User Scenarios & Testing *(mandatory)*

> As user stories abaixo refletem as respostas confirmadas às três perguntas acima:
> strangler-fig por blueprint (Q1: B), apps separados por população de usuário (Q2: B),
> cookie de sessão HttpOnly mantido com CORS configurado (Q3: Custom).

### User Story 1 - Fundação: primeira fatia vertical ponta-a-ponta (Priority: P1)

Antes de tocar qualquer uma das 91 telas existentes, a equipe precisa validar que o padrão
inteiro funciona de verdade: build React (Vite+TS+Tailwind+shadcn/ui+Framer Motion), pelo
menos um endpoint de API JSON no Flask, autenticação, RBAC, o componente de input monetário
BRL, o padrão de loading/erro/sucesso, e uma transição de Framer Motion — tudo isso na tela
mais simples e menos arriscada do sistema (login + dashboard inicial), antes de investir na
migração das telas grandes (Agenda/Eventos, Financeiro).

**Why this priority**: sem essa fatia provada, qualquer estimativa para as próximas 193
rotas é um chute — é o "hello world" que valida a arquitetura inteira, não só uma tela.

**Independent Test**: um usuário SUPERADMIN consegue logar via `/api/auth/login`
(React consumindo JSON, sem `render_template`), ver o dashboard inicial renderizado em React
com dados reais vindos de um endpoint JSON, e o botão de login mostra estado de
loading/erro/sucesso com transição Framer Motion — tudo isso rodando lado a lado com o app
Flask+Jinja antigo intacto (nenhuma outra rota migrada ainda).

**Acceptance Scenarios**:

1. **Given** a tela de login em React, **When** o usuário envia credenciais válidas,
   **Then** o botão mostra feedback visual imediato (loading), a API responde e o usuário é
   redirecionado ao dashboard React autenticado.
2. **Given** credenciais inválidas, **When** o usuário envia o formulário, **Then** o erro
   aparece no campo (via `react-hook-form` + `zod`) sem apagar o que foi digitado, igual ao
   comportamento já garantido hoje pelo Princípio V da constituição.
3. **Given** um usuário sem permissão SUPERADMIN, **When** ele tenta acessar uma rota
   restrita da API nova, **Then** recebe 403 e o React mostra mensagem amigável, não stack
   trace.

---

### User Story 2 - Núcleo operacional: Agenda e Eventos (Priority: P2)

Migrar o blueprint `calendar` — o mais crítico e o mais acoplado a template hoje (zero rotas
JSON, `event_detail.html` com quase mil linhas de JS inline cobrindo casting, contrato,
dados comerciais, pagamentos, reembolsos, logística, agrupamento de eventos-satélite). É o
módulo que a equipe comercial/operacional usa todo dia.

**Why this priority**: é o coração do sistema — qualquer regressão aqui impacta a operação
diária da empresa, então precisa vir logo depois da fundação provada, com tempo/atenção
dedicados, e não pode ser feito apressado misturado com módulos menores.

**Independent Test**: criar um evento, escalar elenco, registrar dados de venda/pagamento e
gerar a ficha de figurino a partir do evento — tudo pela nova interface React — produz
exatamente o mesmo estado no banco que o fluxo Jinja atual produziria (mesmas tabelas:
`CalendarEvent`, `EventRole`, `EventPayment`, `EventContract`, `EventReimbursement`).

**Acceptance Scenarios**:

1. **Given** a agenda em React, **When** o usuário navega por dia/mês, **Then** os eventos
   aparecem com os mesmos dados e mesma lógica de agrupamento comercial (principal+satélites)
   hoje em `_group_events`.
2. **Given** a tela de detalhe do evento, **When** o usuário executa qualquer uma das ações
   hoje despachadas via `_handle_*` (casting, contrato, pagamento, reembolso, logística),
   **Then** a ação chama um endpoint JSON dedicado (não mais um único POST multi-ação) e o
   estado da tela atualiza sem reload de página.

---

### User Story 3 - Banco de Talentos e Figurino (Priority: P3)

Migrar `talents` e `figurino` — inclui o fluxo de import de planilha (upload de arquivo) e o
streaming SSE de sync com Drive, os dois padrões "não-JSON" mais complexos identificados na
auditoria.

**Why this priority**: depende dos padrões de upload e streaming resolvidos na fundação
(US1) e reaproveitados aqui pela primeira vez em fluxos reais — bom sinal de que os
contratos genéricos (upload, SSE) escalam para o resto do sistema.

**Independent Test**: aprovar um talento pendente, editar sua ficha, criar uma ficha de
figurino com fotos, e rodar o sync com Drive acompanhando o progresso em tempo real — tudo
via React.

**Acceptance Scenarios**:

1. **Given** uma ficha de figurino em criação, **When** o usuário anexa uma foto,
   **Then** o upload usa o novo contrato de API (endpoint dedicado retornando `{"url": ...}`
   antes do submit final, ou multipart no próprio recurso) — nunca um `<form>` tradicional
   com redirect.
2. **Given** o sync com Drive rodando, **When** o processo emite progresso,
   **Then** o React consome o stream (SSE/fetch-stream) e atualiza a UI em tempo real, igual
   ao comportamento atual de `figurino_sync.html`.

---

### User Story 4 - Financeiro, Vendas, Gastos, Orçamento e EducaManto (Priority: P4)

Migrar os módulos que giram em torno de dinheiro — maior concentração de regras de negócio
sensíveis (comissão, cachê, reembolso, DRE) e dos dois geradores de PDF (`orcamento/pdf.py`,
`educamanto/pdf.py`) e do export CSV de pagamentos.

**Why this priority**: depende do componente de máscara monetária e do padrão de
download-binário resolvidos antes; é sensível o bastante (dinheiro real) para não ser a
primeira coisa migrada, mas não é o núcleo diário como Agenda.

**Independent Test**: gerar um orçamento, baixar o PDF, registrar um pagamento e exportar o
CSV de pagamentos — todos os valores em tela e no PDF/CSV seguem o padrão brasileiro
(`R$ 1.234,56`) igual a hoje.

**Acceptance Scenarios**:

1. **Given** qualquer campo de valor em qualquer tela migrada, **When** o usuário digita,
   **Then** o componente único de Input Monetário (Princípio VII da constituição) formata em
   tempo real no padrão brasileiro, e o valor numérico puro é o que vai no corpo JSON.
2. **Given** o botão de baixar PDF/CSV, **When** clicado, **Then** o React faz o download via
   blob (`fetch` + `URL.createObjectURL`) com o mesmo feedback de clique (Princípio V) que um
   envio de formulário comum.

---

### User Story 5 - Superfícies públicas (Catálogo, /cadastro, formulários, feedback) (Priority: P5)

Migrar as páginas sem login, hoje isoladas visualmente (`catalogo/*`, `cadastro/*`,
`/f/pre-contrato`, `/f/corporativo`, `feedback/public.html`). Inclui o formulário dinâmico
dirigido por `FormFieldDefinition` (não tem campos fixos — precisa de um componente
genérico de formulário no React, não um formulário hardcoded por caso).

**Why this priority**: são páginas mobile-first, de alto tráfego externo (Princípio VIII),
por isso vêm depois de provar os padrões em telas internas onde um erro custa menos (só a
equipe vê, não o cliente final).

**Independent Test**: um visitante anônimo navega o catálogo por categoria, adiciona itens à
lista de desejos (ainda 100% client-side/localStorage — sem mudança de arquitetura aqui) e
envia o formulário de pré-contrato — sem nenhuma tela quebrar em viewport de 320–430px.

**Acceptance Scenarios**:

1. **Given** o catálogo público em React, **When** a pessoa troca de foto na galeria do
   produto, **Then** a transição suave (cross-fade + altura animada) da feature 143 é
   recriada com Framer Motion, respeitando `prefers-reduced-motion`.
2. **Given** o formulário `/f/pre-contrato`, **When** os campos vêm de `FormFieldDefinition`
   no banco, **Then** o React renderiza o formulário dinamicamente a partir de um schema
   retornado pela API (não uma lista de campos fixa no código do componente).

---

### User Story 6 - Cauda administrativa (Admin, RH, Revisão de Mídia, Clientes, ferramentas) (Priority: P6)

Migrar o restante: `admin` (24 rotas — usuários, settings, gestão de catálogo), `rh`
(scaffolding), `revisao` (já é o blueprint mais próximo de API-shaped hoje — 12 rotas JSON e
padrão dual-mode `_wants_json()`), `clientes` (CRM), e decidir o destino do blueprint órfão
`tools_bp` (migrar ou remover definitivamente).

**Why this priority**: menor uso diário / menor criticidade de negócio — fecha a migração.

**Independent Test**: cada tela remanescente funciona via React consumindo API, sem nenhuma
rota do sistema ainda dependendo de `render_template`.

**Acceptance Scenarios**:

1. **Given** o blueprint `tools_bp` (hoje não registrado/inacessível), **When** a migração
   chegar nele, **Then** a decisão de migrar ou remover definitivamente já foi tomada
   explicitamente (não apenas herdada por omissão).

---

### Edge Cases

- **Upload de arquivo** (contrato, foto de talento/figurino/catálogo, comprovante de
  reembolso, mídia de revisão): não existe hoje um endpoint de upload dedicado — é sempre um
  campo dentro de um form maior. A migração precisa definir UM padrão reutilizável (endpoint
  `POST /api/uploads` retornando `{"url": ...}`, ou multipart aceito direto no endpoint do
  recurso) e aplicá-lo a todos os ~10 pontos de upload identificados na auditoria — não pode
  virar solução ad-hoc por tela.
- **Streaming (SSE)**: `/figurinos/sync-drive/stream` não tem equivalente JSON
  request/response simples — precisa de um contrato explícito (SSE ou polling) documentado
  antes de ser reproduzido no React.
- **Download binário** (2 PDFs, 1 CSV): resposta não é JSON — contrato de blob-download
  precisa ser definido uma vez e reaproveitado nos 3 casos.
- **Duas sessões de autenticação diferentes hoje** (staff via Flask-Login, talento via sessão
  própria do Portal): a migração de auth (Q3) precisa cobrir as duas, não só a de staff.
- **Formulário dinâmico dirigido por banco** (`FormFieldDefinition`): não pode virar campos
  hardcoded no componente React — precisa de um schema JSON servido pela API e um
  componente-fábrica que o interpreta (mantendo o padrão "fonte única" do Princípio I).
- **`event_detail.html` como "monólito de tela"**: uma única view Flask hoje despacha ~15
  ações distintas por dentro de um só POST. A migração para API precisa decidir se isso vira
  ~15 endpoints REST dedicados (mais alinhado ao Princípio III novo) ou um único endpoint de
  ações com um campo `action` no corpo (mais parecido com o padrão atual, migração mais
  barata, mas foge do REST "puro") — ver nota em Assumptions.
- **Rotas já JSON hoje** (`orcamento`, `revisao`, `clientes` etc.): precisam ser auditadas
  uma a uma para ver se o formato de resposta já bate com o que o novo frontend React vai
  esperar, ou se precisam de um pequeno ajuste de contrato mesmo sem lógica nova.

## Requirements *(mandatory)*

### Functional Requirements

**Mapeamento rotas → API (pedido 1)**

- **FR-001**: Cada rota que hoje usa `render_template` MUST ser reclassificada em uma das 4
  categorias identificadas na auditoria — (a) CRUD simples de recurso → endpoint REST
  padrão; (b) ação/comando (ex.: aprovar, sincronizar, dispensar) → endpoint de ação
  dedicado; (c) upload de arquivo → contrato de upload padronizado; (d) download binário/SSE
  → contrato próprio — e documentada em uma tabela rota-Jinja-atual → endpoint-JSON-novo
  antes de qualquer código ser escrito para aquele blueprint.
- **FR-002**: As ~65 rotas que já retornam `jsonify` hoje MUST ser reauditadas uma a uma
  quanto à forma da resposta (nomes de campo, paginação, formato de erro) antes de serem
  reaproveitadas como estão pelo novo frontend — "já é JSON" não significa "já está no
  formato certo".
- **FR-003**: Toda rota migrada MUST manter as mesmas regras de RBAC (papéis SUPERADMIN,
  CASTING, FIGURINO, COMERCIAL, FINANCEIRO, VENDAS, ENSAIO, RH) hoje aplicadas nas views
  Flask, agora como validação de permissão no endpoint de API.

**Telas/formulários/componentes a recriar (pedido 2)**

- **FR-004**: Cada um dos 91 templates MUST ser mapeado a uma tela/componente React
  correspondente antes de descartado — nenhum template é migrado "de cabeça", a partir de
  memória do que ele faz; a auditoria desta spec é o ponto de partida, não a fonte final.
- **FR-005**: As duas telas com maior volume de lógica cliente hoje (`event_detail.html`,
  `event_create.html`, juntas ~1500 linhas de JS inline) MUST ser quebradas em componentes
  React menores e testáveis — não um único componente gigante espelhando o template atual.
- **FR-006**: O formulário dinâmico dirigido por `FormFieldDefinition` (`/f/pre-contrato`,
  `/f/corporativo`) MUST ter um componente-fábrica único no React que renderiza campos a
  partir de um schema vindo da API — não um componente por tipo de formulário.
- **FR-007**: As páginas hoje standalone sem `base.html` (erros, catálogo público, cadastro,
  feedback público, ficha de figurino para impressão, Portal do Artista completo) MUST manter
  identidade visual/layout próprios no React — não herdar automaticamente o shell/nav do
  painel interno.

**Loading/erro/formulários/animação (pedido 3)**

- **FR-008**: Todo componente que dispara requisição assíncrona MUST usar TanStack Query e
  expor os 3 estados exigidos pelo Princípio V — loading, erro, sucesso — nunca deixar o
  usuário "sem resposta" depois de um clique.
- **FR-009**: Todo formulário MUST usar `react-hook-form` + `zod` para validação, preservando
  os valores já digitados em caso de erro (nunca limpar o formulário) e levando o foco ao
  primeiro campo inválido — replicando o comportamento hoje garantido pelo guard global de
  `base.html`.
- **FR-010**: Toda transição de estado visual perceptível (troca de página, abrir/fechar
  modal, expandir card, atualizar lista) em qualquer superfície MUST usar Framer Motion (ou
  utilitário do Tailwind) com duração de 150–350ms, respeitando `useReducedMotion()` —
  aplicando o Princípio IX (que já nasceu para o público, na feature 143) agora também às
  telas internas, por decisão explícita da constituição 2.0.0.
- **FR-011**: A galeria de fotos do catálogo público (cross-fade + altura animada + swipe da
  feature 143, hoje em CSS/JS vanilla) MUST ser recriada com paridade de comportamento
  usando Framer Motion — é o caso de teste mais recente e mais bem documentado de "animação
  com propósito" no sistema.

**Não quebrar regras de negócio existentes (pedido 4)**

- **FR-012**: A formatação/máscara monetária brasileira (Princípio VII: milhar `.`, decimal
  `,`, duas casas, nunca cru nem padrão americano) MUST ter uma única implementação
  reutilizável no novo frontend (hook/componente) — mesma exigência de "fonte única" que já
  existe hoje, só que migrada de `money-mask.js` para um equivalente React/TS.
- **FR-013**: Nenhum botão de ação MUST ficar "morto" ao clique (Princípio V) — feedback
  visual imediato (spinner, texto de estado, opacidade) em toda ação, rápida ou lenta, sem
  exceção — incluindo as ~15 ações hoje despachadas de dentro de `event_detail.html`.
- **FR-014**: Todas as superfícies hoje mobile-first (Portal do Artista, `/cadastro`,
  `/revisao`) MUST continuar cumprindo o Princípio VIII (sem rolagem horizontal 320–430px,
  alvos de toque ≥44px, texto ≥12px, teclado virtual considerado) depois de recriadas em
  React.
- **FR-015**: O `CLAUDE.md` do projeto (hoje desatualizado, ainda descrevendo Jinja2/vanilla)
  MUST ser reescrito para refletir a stack real (React/Vite/TS/Tailwind/shadcn/Framer Motion
  + Flask API) como parte desta migração — está fora de sincronia com a constituição 2.0.0
  desde a atualização da constituição.
- **FR-016**: O blueprint órfão `tools_bp` (calculadora de transporte, hoje não registrado
  em `app/__init__.py`) MUST ter uma decisão explícita registrada (migrar e reativar, ou
  remover definitivamente do código) — não pode continuar simplesmente esquecido.

### Key Entities

Nenhuma entidade de dados nova — esta é uma migração de camada de apresentação e de
contrato de comunicação (HTML server-rendered → JSON API + SPA React) sobre os modelos
SQLAlchemy já existentes em `app/models.py`. Nenhum modelo muda de forma por causa desta
spec.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Depois de cada fatia (User Story) migrada, zero regressão funcional
  observável nos fluxos cobertos por ela — verificado contra `manto_local` (mesmo padrão de
  verificação já usado no projeto, adaptado para chamar os novos endpoints JSON em vez do
  test client Flask renderizando HTML).
- **SC-002**: 100% das ~194 rotas atuais têm um endpoint JSON equivalente documentado (nem
  que a migração de UI daquela rota específica ainda não tenha acontecido) até o fim da
  auditoria de cada blueprint — nenhuma rota "esquecida".
- **SC-003**: Nenhuma tela migrada perde a paridade de UX hoje garantida pela constituição
  (feedback de clique, preservação de formulário em erro, máscara monetária, mobile-first
  onde aplicável) — validado tela a tela antes de considerar aquele pedaço "pronto".
- **SC-004**: O `CLAUDE.md` e a documentação do projeto refletem a stack real ao final da
  migração — nenhuma instrução desatualizada guiando trabalho futuro.

## Assumptions

- CORS será configurado por app/bundle React (interno, Portal do Artista, público) contra o
  cookie de sessão HttpOnly — detalhe de origem(ns) permitida(s) por ambiente (dev/produção)
  fica para o `/speckit-plan` da Fundação (US1), não para esta spec.
- `event_detail.html`'s ~15 ações despachadas por um único POST: assumido que a migração as
  quebra em endpoints REST dedicados (mais alinhado ao novo Princípio III), não um único
  endpoint de "ações" genérico — é a leitura mais consistente com "Backend é 100% API
  RESTful JSON", mas é uma decisão de design que o `/speckit-plan` deve confirmar
  explicitamente, não só herdar desta assumption.
- O upload de arquivo migra para um endpoint dedicado `POST /api/uploads` (opção "a" do
  Edge Case) por ser reutilizável entre os ~10 pontos de upload identificados, em vez de
  multipart-no-próprio-recurso (que exigiria 10 implementações diferentes).
- `app/storage.py` (abstração local/S3 já existente) é reaproveitado sem mudança de
  comportamento — só muda quem chama (endpoint de upload dedicado, não mais uma view que
  também renderiza template).
- Fora de escopo desta spec: escrever o `plan.md`/`tasks.md` de cada User Story
  individualmente (isso é responsabilidade do `/speckit-plan` de cada uma, quando chegar a
  vez) — esta spec só estabelece o mapeamento geral e a ordem.
- Fora de escopo: decidir a hospedagem/deploy do novo frontend (Vercel, mesmo Railway,
  etc.) — é uma decisão de infraestrutura, não de especificação de produto.
