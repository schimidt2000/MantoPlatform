# 03 — Histórico de Mutações

> **Documento vivo — APPEND ONLY.** Cada feature concluída adiciona uma entrada **no topo** da
> seção "Registro". Nunca reescrever entradas antigas (elas são o histórico); correções entram
> como nova entrada referenciando a anterior.
>
> Última atualização: **2026-07-29** · Estado do repositório: pós-feature **201**

Formato de cada entrada:

```
## <NNN> — <título>            (branch · data do merge · migration)
Motivação · O que mudou (Backend / Banco / Frontend) · Impacto em RBAC e regras de negócio ·
Rotas e endpoints novos/alterados · Riscos e pegadinhas
```

---

## Registro

### 201 — Acervo 3D: uma peça, vários arquivos
`201-acervo-3d-multi-arquivos` · **2026-07-29** · migration **`d9e3a5b7c124`** (*acervo 3d com
multiplos arquivos*)

**Motivação.** A feature 200 modelou a peça do Acervo com **um** arquivo 3D (`file_path`). Na
prática um mesmo presente quase nunca é um arquivo só: o modelo vem **fatiado em partes** (corpo,
argola, base), e o `.zip` estava sendo usado como gambiarra para empacotar tudo — o que obriga o
Artista 3D a baixar, descompactar e adivinhar o que é cada coisa.

**O que mudou.**

- **Banco.** Nova tabela `acervo_3d_files` (1:N com `acervo_3d_items`, `ON DELETE CASCADE`) com
  `file_path`, `original_name`, `position` e `created_at`. A coluna `acervo_3d_items.file_path`
  **saiu**. A migration **migra os dados antes de dropar**: um `INSERT ... SELECT` transforma
  cada peça já cadastrada numa linha de `acervo_3d_files` na posição 0, e só então a coluna é
  removida.
  - `original_name` existe porque o caminho salvo é um UUID — sem ele o Artista 3D veria três
    links indistinguíveis em vez de `corpo.stl` / `argola.3mf` / `base.stl`.
- **Backend.**
  - `Acervo3DFile` em `models.py`; `Acervo3DItem.files` com `cascade="all, delete-orphan"` e
    `order_by=position`.
  - `impressoes3d_ops.py`: `create_acervo_item` passou a receber `model_files: list` e exigir
    **pelo menos um**; `update_acervo_item` ganhou `model_files` (acrescenta) + `remove_file_ids`
    (remove) via `_apply_file_changes`, que **recusa deixar a peça com zero arquivos**;
    `delete_acervo_item` remove todos os arquivos do storage; novo `serialize_model_files`.
  - `impressoes3d_write.py`: `_model_files()` lê `request.files.getlist("files")` **e** o `file`
    singular da 200 (nenhum cliente antigo quebra), `_remove_file_ids()` lê `remove_file_ids[]`.
  - O payload da **Fila** passou a incluir os arquivos dentro de `item` — o Artista 3D baixa
    direto da fila, sem abrir o Acervo.
- **Frontend.**
  - `Acervo3DItem.file_path: string` virou `files: Acervo3DFile[]`; `SaveAcervoItemInput` ganhou
    `files: File[]` e `removeFileIds: number[]`.
  - `Acervo3DPage`: o `FileUpload` único do arquivo 3D virou um input `multiple` com lista dos
    arquivos já salvos (link de download + ✕/Desfazer para marcar remoção) e prévia dos que serão
    enviados. O card mostra badge com o nº de arquivos e um link por arquivo.
  - `Fila3DPage`: o dialog "Ver Detalhes para Impressão" lista os downloads de cada parte.

**Impacto em RBAC e regras de negócio.** RBAC inalterado. Regra nova: **peça do Acervo sempre tem
≥1 arquivo** — vale no cadastro e na edição.

**Rotas e endpoints.** Nenhuma rota nova. `POST /api/3d/acervo` passou a aceitar `files`
(múltiplos) em vez de `file`; `PATCH /api/3d/acervo/<id>` ganhou `files` e `remove_file_ids[]`. O
JSON da peça troca `file_path` por `files[]` — **breaking** para qualquer consumidor externo, mas
o único consumidor é o próprio frontend, atualizado no mesmo commit.

**Riscos e pegadinhas descobertos.**
1. **Ordem da migration é o ponto crítico.** O `INSERT ... SELECT` precisa rodar **antes** do
   `DROP COLUMN` — invertido, os arquivos das peças existentes sumiriam sem erro nenhum.
   Testado explicitamente: downgrade para `c8d2f4a6b013`, inserção de uma peça no schema antigo,
   upgrade → o arquivo apareceu em `acervo_3d_files` na posição 0.
2. **O downgrade perde dados por natureza** (volta a caber um arquivo só, fica o primeiro). Ele
   **não apaga peças** para satisfazer o NOT NULL: se sobrar alguma sem arquivo, a coluna fica
   nullable e o log avisa — perder uma peça inteira num rollback seria pior que a divergência.
3. **`FileUpload` guarda o nome do arquivo em estado interno.** Zerar o estado do formulário no
   `onSuccess` não limpava o campo: continuava exibindo "preview.png" como se ainda estivesse
   selecionado. Corrigido remontando o formulário por `key` — a limpeza agora é do chamador, não
   do próprio formulário. Vale para qualquer tela futura que reutilize o `FileUpload` em
   formulário de criação repetida.
4. **`.zip` continua aceito** (decisão do usuário): quem preferir mandar um pacote único segue
   podendo, e nada já cadastrado quebra.

**Verificação.** `scripts/db/verify_200_impressoes_3d.py` ampliado — **47/47 checks** (inclui
ordem/posição dos arquivos, PATCH acrescentando sem substituir, remoção individual e o 400 ao
tentar remover todos). Round-trip da migration testado com dado real. `tsc --noEmit` limpo,
build do internal OK, e conferido no app real: upload de 3 arquivos de uma vez, card com os 3
downloads nomeados, dialog de edição com ✕/Desfazer e formulário limpo após o sucesso.

---

### 200 — Módulo Core de Impressões 3D
`200-impressoes-3d` · **2026-07-29** · migration **`c8d2f4a6b013`** (*modulo core de impressoes 3d*)

**Motivação.** A entrega física dos Presentes 3D dos eventos `SHOW` era controlada fora do
sistema. O Artista 3D não tinha como saber, sem perguntar, **quantas peças imprimir e de que
idade** — informação que a cliente já preenche no formulário de pré-contrato — nem qual era o
prazo real de cada evento. O módulo nasce fechando esse ciclo: catálogo de peças com foto,
vínculo peça↔evento com prazo e status, e um painel operacional que **cruza elenco contratado +
respostas do formulário** numa tela só.

**O que mudou.**

- **Banco.** Duas tabelas novas, migração 100% aditiva:
  - `acervo_3d_items` (`Acervo3DItem`): `name`, `photo_url` e `file_path` (`.stl`/`.3mf`/`.zip`)
    — **os dois arquivos NOT NULL**: sem foto a peça não é selecionável visualmente (Princípio
    X.2) e sem arquivo ela não é imprimível, então uma entrada incompleta só sujaria o Acervo.
    Na edição, não enviar um arquivo significa manter o atual — nunca limpar. Mais `is_active`,
    `created_at`.
  - `event_3d_gifts` (`Event3DGift`): `event_id` (**ON DELETE CASCADE**), `item_id`, `status`,
    `deadline_date`, `quantity`, `notes`, `created_at`/`updated_at`; índices em `event_id`,
    `item_id` e `status`. Backref `CalendarEvent.presentes_3d` com
    `cascade="all, delete-orphan"`.
  - Nada de tabela existente foi alterado — eventos antigos seguem funcionando sem presente
    vinculado.
- **Backend.**
  - `app/constants.py`: papel `RoleName.ARTISTA_3D`, `EVENT_TYPE_SHOW` e `GIFT_3D_STATUSES`
    (`pendente` → `imprimindo` → `finalizado` → `entregue`) como fonte única do ciclo de vida.
  - `app/impressoes3d/impressoes3d_ops.py` (**novo núcleo de negócio**, funções puras): CRUD do
    Acervo com validação de extensão e troca de arquivo (upload novo apaga o antigo do storage),
    vínculo/edição/remoção de presentes, `list_print_queue()` e os serializadores
    (`serialize_acervo_item`, `serialize_gift`, `serialize_form_response`). Erros de validação
    viram `Impressao3DValidationError(field, message)` → `json_error(..., fields={campo: msg})`.
  - `app/api/impressoes3d_read.py` / `impressoes3d_write.py`: `/api/3d/acervo` (CRUD multipart),
    `/api/3d/fila` e `/api/events/<id>/3d-gifts[/<gift_id>]` (POST/PATCH/DELETE). RBAC como
    **função** (`require_3d_access()`) chamada no início de cada view, nunca decorator.
  - `app/api/agenda_read.py`: flag `can_manage_3d` em `_role_flags` e serialização de
    `presentes_3d` no detalhe do evento **só quando `event_type == 'SHOW'`** — reusando
    `serialize_gift` do módulo 3D, sem segunda montagem do payload (Princípio I).
  - `seed.py`: `get_or_create_role("ARTISTA_3D")`.
- **Frontend.**
  - `lib/impressoes3d.ts`: contrato JSON tipado + hooks TanStack Query + os helpers
    `formatDeadline`/`daysUntilDeadline`.
  - `pages/Acervo3DPage.tsx` (`/3d/acervo`): formulário de upload duplo e grade de cards com a
    contagem de usos, download do arquivo, edição em `Dialog`, inativar/reativar e exclusão
    confirmada.
  - `pages/Fila3DPage.tsx` (`/3d/fila`): tabela densa por prazo, selo de urgência, seletor rápido
    de status e o `Dialog` "Ver Detalhes para Impressão".
  - `components/EventDetail/Presente3DSection.tsx`: injetado na **coluna esquerda** de
    `/events/:id`, entre Logística e Observações; adição via `Combobox` de `@manto/ui` com
    `AvatarThumb` **quadrado** da peça (Princípio X.1/X.2).
  - `lib/navigation.tsx`: seção nova **"Impressão 3D"** (Fila + Acervo), visível para
    `ARTISTA_3D` e `SUPERADMIN`. `App.tsx`: rotas `/3d/fila` e `/3d/acervo`.

**Impacto em RBAC e regras de negócio.**
- Papel novo `ARTISTA_3D`: gestão total do módulo 3D + **leitura** dos eventos (herda o
  `api_login_required` de `GET /api/events/<id>`, que não é gated por papel) — é o que dá acesso
  ao elenco e ao formulário de pré-contrato.
- `can_manage_3d` = `ARTISTA_3D` ou `SUPERADMIN`. **Quem abre o evento lê a lista de presentes;
  só o Artista 3D edita.** Decisão consciente de não estender a escrita ao `COMERCIAL` — se a
  operação pedir, é um `has()` a mais em `_role_flags` e em `require_3d_access`.
- Presente 3D é **exclusivo de evento `SHOW`** (400 nos demais tipos).
- Peça com evento vinculado **não pode ser excluída** (400 orientando a inativar) — protege a
  contagem histórica de usos.

**Rotas e endpoints novos.** `GET|POST /api/3d/acervo` · `PATCH|DELETE /api/3d/acervo/<id>` ·
`GET /api/3d/fila` · `POST /api/events/<id>/3d-gifts` ·
`PATCH|DELETE /api/events/<id>/3d-gifts/<gift_id>` · telas `/3d/acervo` e `/3d/fila`.
**Alterado (aditivo)**: `GET /api/events/<id>` ganhou `presentes_3d` (só SHOW) e
`flags.can_manage_3d` (sempre).

**Riscos e pegadinhas descobertos.**
1. **Nome dos módulos Python.** A spec pedia `app/api/3d_read.py` e `app/3d_impressions/3d_ops.py`
   — impossível: identificador Python não pode começar com dígito, `from app.api import 3d_read`
   é erro de sintaxe. Ficaram `app/api/impressoes3d_{read,write}.py` e
   `app/impressoes3d/impressoes3d_ops.py`. **As URLs mantêm o `3d` exatamente como pedido.**
2. **`event_type` tem duas origens.** A coluna `CalendarEvent.event_type` (preenchida na
   sincronização a partir do prefixo do título) é o que o backend filtra; o JSON do detalhe expõe
   `parse_event_type(event.title)`. Hoje concordam porque a sincronização usa a mesma função —
   mas se algum dia divergirem, a seção some da tela enquanto o backend ainda aceita o vínculo.
3. **Data pura vs. `new Date()` no JS.** `new Date("2026-08-02")` é interpretado como **UTC**, o
   que em São Paulo (UTC−3) exibiria 01/08. `deadline_date` é data pura, então o módulo usa
   `formatDeadline` (split da string), e não `formatShortDate` de `@manto/ui` — este continua
   correto para os ISO **com hora** (`start_at`).
4. **Duas formas históricas de `FormResponse.data`.** Campos podem vir como
   `[chave, rótulo, valor]` (feature 123) ou `[rótulo, valor]` (anteriores).
   `serialize_form_response` normaliza as duas e **descarta campos vazios** — sem isso o extrato
   do formulário vira uma parede de rótulos em branco.
5. **`useAcervo3D` precisa de `enabled`.** O endpoint responde 403 para quem não é Artista 3D; a
   seção do evento só dispara a busca quando `can_manage_3d` é verdadeiro, senão todo `CASTING`
   que abrisse um SHOW geraria um 403 no console.

**Verificação.** `scripts/db/verify_200_impressoes_3d.py` contra `manto_local` — **40/40 checks**
(RBAC 401/403, upload duplo obrigatório com validação de extensão, vínculo recusado em não-SHOW,
status fora do ciclo de vida, presente de outro evento → 404, exclusão bloqueada de peça em uso,
elenco + formulário aninhados na fila, `entregue` sumindo da fila, `presentes_3d`/`can_manage_3d`
no detalhe do evento). `npx tsc --noEmit` limpo nos três apps e `npm run build` do internal OK.
Conferido no app real (Flask + Vite locais) com um evento SHOW de verdade: fila, dialog de
detalhes (leu "Rafael e Gabriel · 2 e 3 anos" direto do formulário), seção no evento, combobox
com miniatura e ausência da seção em evento `R&I`.

---

### 199 — Liberação do status 'No banco' para Comissões e Recorrentes
`199-no-banco-comissoes-recorrentes` · **2026-07-29** · **sem migration**

**Motivação.** A feature 189 restringiu de propósito "No banco" para itens `commission` e
`recurring` na Planilha de Pagamentos (`/financeiro/pagamentos`): em lote o backend devolvia o
item em `skipped` e a UI nem oferecia a opção no seletor. A operação do setor financeiro mudou —
hoje esses dois tipos também passam pelo mesmo fluxo bancário dos demais (cachê, salário, gasto,
BV) — então a trava intencional virou bloqueio indevido. Passou a ser exigido que os 3 status
(`nao_pago`/`no_banco`/`pago`) valham para **todos** os tipos de pagamento, sem exceção.

**O que mudou.**

- **Backend.**
  - `app/models.py`: docstrings de `CommissionPayment.status` e `RecurringExpenseEntry` (+
    `STATUSES`) passaram a documentar `no_banco` — o campo já era `db.String` livre, sem
    migration necessária.
  - **A causa raiz real não estava no endpoint de escrita, e sim na leitura**:
    `_build_commission_items`/`_build_recurring_items` (`app/financeiro/routes.py`) filtravam a
    query em `.in_(["a_pagar", "pago"])` — um item marcado `no_banco` **desaparecia da
    planilha** em vez de só não oferecer a opção. Ambos os filtros agora incluem `no_banco`, e o
    status do item agregado de comissão passou de binário (`pago`/`nao_pago`) para as 3 faixas
    (`pago` se todas as linhas do vendedor/período estão pagas, `no_banco` se todas estão no
    banco, `nao_pago` no resto/misto).
  - `set_payment_status`/`api_set_payment_status` (`app/financeiro/routes.py` e
    `app/api/financeiro_write.py`, mantidos em paridade manual — este módulo não usa `*_ops.py`
    compartilhado): o ramo `commission` calculava `target = "pago" if status == "pago" else
    "a_pagar"`, colapsando qualquer pedido de `no_banco` em `"a_pagar"` sem persistir nada; agora
    `target` aceita `pago`/`no_banco`/cai em `a_pagar` só para `nao_pago`. O ramo `recurring`
    tinha o mesmo colapso binário — ganhou o `elif status == "no_banco"`. Os filtros de status
    "aceito para reconsulta" (`CommissionPayment.status.in_(...)` /
    `entry.status not in (...)`) também passaram a incluir `no_banco`, senão um item já marcado
    não seria reencontrado para sair desse estado.
  - `_bulk_set_commission_period`/`bulk_payment_action`/`api_bulk_payment_action`: removida a
    trava explícita que devolvia `commission_ids` em `skipped` com a mensagem "não têm estado
    'no banco'" quando `action == "no_banco"`; o helper de bulk ganhou a mesma correção de
    mapeamento/filtro do endpoint individual.
- **Banco.** Nada — status seguem como string livre nas duas tabelas.
- **Frontend.** `frontend/apps/internal/src/pages/PagamentosPage.tsx`:
  `STATUS_OPTIONS_BY_TYPE` para `commission` e `recurring` passou de `["nao_pago", "pago"]` para
  `["nao_pago", "no_banco", "pago"]`, igual aos demais tipos; comentário que documentava a
  restrição intencional foi atualizado. `SELECTABLE_TYPES` **não** ganhou `recurring` — contas
  recorrentes nunca foram selecionáveis para ação em lote (limitação preexistente e
  independente do bug de `no_banco`; o backend de bulk-action não recebe `recurring_ids`), e
  estender isso é fora do escopo desta mudança.
- **Impacto em RBAC**: nenhum — mesmo gate `FINANCEIRO`/`SUPERADMIN` de sempre.
- **Verificação.** `scripts/db/verify_199_no_banco_comissao_recorrente.py` contra `manto_local`
  (test client, fora de `app_context`): set-status individual `commission`/`recurring`
  percorrendo os 3 status e voltando; `GET /api/financeiro/pagamentos` confirmando que um item
  em `no_banco` continua listado (e soma em `totals.no_banco`) em vez de sumir; bulk-action com
  `action=no_banco` para `commission_ids` deixando de cair em `skipped`. 16/16 checks.
- **Pegadinha para quem mexer aqui de novo**: este módulo **duplica** a lógica de
  `set_payment_status`/`bulk_payment_action` entre a view Jinja legada
  (`app/financeiro/routes.py`) e a API (`app/api/financeiro_write.py`) — não há um `*_ops.py`
  compartilhado como nos blueprints mais novos. Qualquer correção de regra de negócio aqui
  precisa ser replicada nos dois lugares manualmente (como foi feito nesta feature), ou vai
  divergir de novo.

### 197 — Refatoração do Dashboard de Avaliações de Clientes
`197-dashboard-avaliacoes-clientes` · **2026-07-28** · **sem migration**

**Motivação.** `/clientes/avaliacoes` estava quebrada e pobre: **a lista de avaliações nunca era
renderizada** (a página montava KPIs, distribuição e o bloco "Atenção", mas simplesmente não
usava `data.feedbacks`), o **comentário escrito pela cliente não era serializado pelo endpoint**
— ou seja, o texto que dá sentido à nota nunca chegava à tela — e o **filtro por tag não casava
nenhuma linha**. Como é a tela onde medimos a qualidade do serviço, virou um dashboard de
satisfação de verdade.

**O que mudou.**

- **Backend.** `app/clientes/client_ops.py`:
  - `summarize_feedback` ganhou `joinedload(ClientFeedback.event).joinedload(CalendarEvent.client)`
    — a serialização lê `f.event.title` e `f.event.client.name` por linha e o `lazy=True` fazia
    2 SELECTs por avaliação (N+1);
  - novo campo `pct_five` em `FeedbackSummary` (índice de excelência do recorte filtrado);
  - **correção do filtro por tag**: novo `_tag_match_conditions` + `_like_literal`. As duas rotas
    de escrita gravam com `json.dumps(...)` sem `ensure_ascii=False`, então o banco guarda a tag
    **escapada** (`["⏰ Pontualidade"]`); o filtro antigo procurava o emoji literal e ainda
    caía na barra invertida, que o PostgreSQL consome como escape do `LIKE`. Agora procura as duas
    formas com `ESCAPE '!'`. **A view Jinja legada de `app/clientes/routes.py` herda a correção.**
- **Banco.** Nada. Zero migration — `ClientFeedback.comment` e `client_name` já existiam
  (features 130/132); só não estavam sendo serializados.
- **Frontend.**
  - `@manto/ui` ganhou dois membros compartilhados (Princípio I): **`StarRating`**
    (`components/star-rating.tsx`) — estrelas somente-leitura, aceita nota fracionária,
    substitui os `StarsInt`/`StarsAvg` que viviam em cópia local dentro de
    `AvaliacaoCastingPage.tsx` — e **`formatShortDate`/`formatRelativeDay`** (`lib/date.ts`),
    promovidos de `apps/portal/src/lib/format.ts`, que agora só reexporta.
  - `lib/clientes.ts`: tipos novos `ClientFeedbackEvent`, `ClientFeedbackClient`,
    `ClientFeedbackKpis`; `ClientFeedbackItem` passou a ter `comment` e os relacionamentos
    aninhados no lugar dos antigos `event_title`/`client_name` planos.
  - `pages/ClientFeedbackPage.tsx` reescrita: 3 cards de KPI (nota média com estrelas, total,
    índice de excelência), distribuição por nota (mantida), barra de filtros funcional e grade de
    cards ricos (estrelas, cliente em destaque, evento com link para `/events/:id` + data,
    comentário em `blockquote`, tags) e empty state com ícone.
- **Verificação.** Script de test client contra `manto_local` (semeia, exercita e limpa):
  payload/aninhamento, fallback de nome, KPIs, cada filtro, formato do bloco "Atenção" e RBAC
  (COMERCIAL 200 · sem papel de vendas 403 · anônimo negado). Filtros, ordenação, empty state e
  layout mobile conferidos no navegador.

**Rotas e endpoints.**

| Método | Rota | Observação |
|---|---|---|
| GET | `/api/clientes/avaliacoes` | **contrato alterado (breaking)** — cada item de `feedbacks[]`/`attention[]` passou de `{id, score, tags, submitted_at, event_title, client_name}` para `{id, score, comment, tags, submitted_at, event: {id, title, event_date} \| null, client: {id, full_name} \| null}`; bloco novo `kpis: {media_geral, total_avaliacoes, percentual_5_estrelas}`. As demais chaves de topo (`total`, `avg_overall`, `clients_rated`, `dist`, `dist_max`, `clients_with_feedback`, `all_tags`, `filters`) seguem iguais. |

**Impacto em RBAC e regras de negócio.**

- RBAC **inalterado**: segue `_require_vendas()` (`COMERCIAL`, `FINANCEIRO`, `SUPERADMIN`).
- `client.full_name` cai para `ClientFeedback.client_name` (o nome digitado no formulário público,
  feature 132) quando o evento não tem cliente cadastrada vinculada — nesse caso `client.id` vem
  `null`. Sem isso a maioria dos cards apareceria sem nome, porque `CalendarEvent.client_id` é
  opcional e fica vazio na maior parte da base.
- Nota e ordenação **não** vão ao servidor: a faixa "3 ou menos" não cabe no parâmetro `score`
  (que só aceita nota exata), então busca textual, faixa de nota e ordenação são aplicadas no
  cliente sobre a lista já carregada. Período e tag continuam sendo filtros de servidor.
- O seletor de cliente saiu da tela — a busca textual cobre nome da cliente **e** título do
  evento. O parâmetro `client_id` do endpoint continua existindo e funcionando.

**Riscos e pegadinhas.**

- **`LIKE` sobre JSON com emoji**: a barra invertida do `\uXXXX` é o caractere de escape padrão do
  `LIKE` no PostgreSQL. Sem `ESCAPE '!'` explícito o padrão nunca casa. Vale para qualquer filtro
  futuro sobre `ClientFeedback.tags`.
- **`grid` sem `grid-cols-1`**: `grid gap-3 md:grid-cols-2` não define coluna no mobile, e a
  trilha implícita `auto` é dimensionada por `max-content` — o comentário longo esticava o card
  para ~880px dentro de um viewport de 375px, estourando a rolagem horizontal. Corrigido com
  `grid-cols-1` explícito (`minmax(0,1fr)`) nas duas grades.
- **`truncate` dentro de flex** precisa de `min-w-0` no item; sem isso o item não encolhe abaixo
  do texto e o corte não acontece (título do evento no card).
- **Sem animação de saída por card.** A transição é do bloco inteiro, com `key` no recorte atual.
  Animar a saída item a item mantém o card removido no DOM até a animação terminar — a lista
  exibida discorda do contador enquanto isso.
- `manto_local` tem **zero** `client_feedbacks` e nenhum `CalendarEvent.client_id` preenchido: para
  conferir a tela é preciso semear dados (e limpar depois).

### 196 — Pivot do Pipeline de Vendas para Dashboard Comercial
`196-dashboard-comercial` · **2026-07-28** · **sem migration**

**Motivação.** A tela `/vendas` ("Pipeline de Vendas", feature 156) tinha virado uma cópia
empobrecida da tabela do Painel Financeiro: mesma lista de eventos com venda/custo/lucro/comissão,
sem período, sem KPI e sem nada que o Painel Financeiro já não mostrasse melhor. Para o gestor era
redundante; para o vendedor era quase inútil — e é justamente o `COMERCIAL` quem **não tem acesso
ao Painel Financeiro**, ou seja, `/vendas` é a única superfície onde ele acompanha o próprio
resultado. A tela virou um **Dashboard Comercial**: metas, performance e acompanhamento das vendas
fechadas do período.

**O que mudou.**

- **Backend.** Novo `app/financeiro/vendas_ops.py` — núcleo puro do dashboard: `list_closed_sales`
  (recorte do funil), `build_kpis`, `serialize_sales`, `closing_date`, `contratante_name`,
  `contract_status_map`, `received_map` e `event_payment_status`. `api_vendas_pipeline` em
  `app/api/financeiro_read.py` foi reescrita sobre esse núcleo e ganhou `_resolve_vendas_scope()`
  (RBAC de servidor) e `_comercial_sellers()`. **Refatoração de reuso**: `api_financeiro_dashboard`
  passou a chamar `vendas_ops.event_payment_status` no lugar da cadeia `if/elif` inline — o status
  de cobrança agora tem fonte única e as duas telas mostram o mesmo rótulo.
- **Banco.** Nada. Zero migration, zero coluna nova — `sale_value_gross`, `sale_date`, `seller_id`,
  `EventContract.is_signed`, `EventPayment` e `EventClient` já existiam.
- **Frontend.** `lib/vendas.ts` reescrito (`useDashboardComercial`, tipos `VendaFechada`,
  `VendasKpis`, `ContractStatus`, `SalePaymentStatus`); `pages/VendasPipelinePage.tsx` reconstruído
  como layout gerencial em grid: filtros de período, filtro de vendedor (só gestor), 4 cards de KPI
  e tabela densa com `Table`/`TableRow`/`TableCell` + `Badge` de `@manto/ui`. Nome do arquivo e do
  componente mantidos (`VendasPipelinePage`) para não mexer na rota em `App.tsx`.
- **Verificação.** `scripts/db/verify_196_dashboard_comercial.py` — 55 checks contra `manto_local`.

**Rotas e endpoints.**

| Método | Rota | Observação |
|---|---|---|
| GET | `/api/vendas/pipeline?period=&seller_id=` | **reescrito (breaking)** — `{items[], is_financeiro}` deu lugar a `{period, start, end, kpis, eventos[], can_filter_seller, scope_label, sellers?}` |
| GET | `/api/financeiro/dashboard` | **inalterado no contrato** — só passou a derivar `eventos[].status` de `vendas_ops` |

**Impacto em RBAC e regras de negócio.**

- O gate de acesso continua `_can_view_vendas()`. O que mudou é o **escopo de dados**, decidido no
  servidor por `_resolve_vendas_scope()`: `FINANCEIRO`/`SUPERADMIN` veem a empresa toda e podem
  filtrar por `seller_id`; `COMERCIAL` sem papel de gestão recebe **só as próprias vendas** e o
  `seller_id` da querystring é ignorado; responsável EducaManto sem papel comercial segue restrito
  aos eventos `(EDU…`. Mesmo padrão da feature 187.
- **Custo e lucro saíram do payload**, não só da tela — informação do setor financeiro.
- `comissao_prevista` usa `_commission_beneficiary`, não `seller_id`: em evento EducaManto a
  comissão é do responsável, então ela cai no dashboard **dele**, não no do vendedor do evento.

**Riscos e pegadinhas descobertos.**

1. **`sale_value_gross` não é a receita.** O prompt original pedia somar `sale_value_gross` no
   "total vendido". Nesta base ele é o **preço de tabela antes do desconto** e fica `NULL` na
   maioria dos eventos — somar isso daria um total menor que o real e divergente da Receita Bruta
   do Painel Financeiro, que usa `sale_value`. O KPI usa `sale_value`; `sale_value_gross` virou o
   preço riscado na linha e o KPI derivado `desconto_concedido`.
2. **O eixo do período é a data de fechamento, não a data do evento.** Nesta operação a venda é
   fechada meses antes do evento (evento de julho vendido em janeiro). O Painel Financeiro recorta
   por `start_at` — correto para DRE; para o comercial o que importa é "o que eu fechei neste mês",
   que é `sale_date`. **As duas telas não batem por período de propósito**, e não é bug.
3. **`sale_date` `NULL` existe e vale dinheiro.** Em `manto_local`, 7 vendas com valor estão sem
   `sale_date` — filtrar só por `sale_date` sumiria com R$ 13.000 reais só em junho/2026. Daí o
   fallback para `start_at` em `closing_date()`.
4. **Mas o fallback sozinho polui o funil.** Na primeira versão ele arrastava para a tela todo
   evento de agenda **sem venda nenhuma** (15 linhas de `R$ 0,00` num mês). O recorte final exige
   `sale_value > 0` **ou** `is_cortesia_permuta` — evento sem valor não é venda, e quem cobra esse
   preenchimento é a auditoria do Painel Financeiro.
5. **Satélite de grupo comercial fica fora por SQL**, não em Python: o principal carrega o valor do
   grupo (FR-010/FR-011); incluir o satélite contaria a mesma venda duas vezes.
6. **`_resolve_period()` lê `request.args`** — por isso o período é resolvido na rota e passado
   pronto para `vendas_ops`, que precisa continuar puro (regra de arquitetura do projeto).

### 195 — Autocomplete de Endereços com Google Places e Comboboxes com Busca Visual
`195-autocomplete-enderecos-comboboxes` · **2026-07-28** · **sem migration**

**Motivação.** Duas regressões de usabilidade em relação ao sistema clássico, ambas com custo
operacional real. (1) O formulário de evento em React usava `<select>` nativos para figurino,
pré-escala de talento e coordenador — listas de centenas de itens onde o comercial rolava e
escolhia o nome errado, sem nenhuma foto para conferir. (2) Todo endereço do sistema era texto
livre: o operador digitava "Av Paulista 1000" e a Distance Matrix devolvia `NOT_FOUND`, quebrando
o cálculo de transporte no orçamento e no EducaManto. Endereço normalizado pelo Google é o que faz
o KM sair certo.

**O que mudou.**

- **Backend.** `app/maps.py` ganhou `address_autocomplete()` ao lado do `distance_km_ida()` já
  existente (feature 076) — fonte única da integração com o Maps — e o helper privado `_api_key()`,
  agora compartilhado pelas duas funções. Novo módulo `app/api/maps_read.py` com
  `GET /api/maps/address-autocomplete`, registrado em `app/api/__init__.py`.
  `_build_event_create_options()` em `app/calendar/routes.py` passou a incluir `photo_face_path`
  em cada item de `assignable_talents` (mudança aditiva — o Jinja legado ignora a chave).
- **Banco.** Nada. Zero migration, zero coluna nova — a `SiteSetting.google_maps_api_key` e o
  `Talent.photo_face_path` já existiam.
- **Frontend.** Dois componentes novos no design system (`@manto/ui`): `AvatarThumb` e `Combobox`.
  No app internal: `lib/maps.ts` (hook `useAddressAutocomplete`, debounced) e
  `components/GoogleAddressInput.tsx`. Telas tocadas: `EventFormBlocks/ElencoBlock.tsx`,
  `EventFormBlocks/DadosEventoBlock.tsx`, `pages/OrcamentoCalculadoraPage.tsx`,
  `pages/EducaMantoCalculadoraPage.tsx`. Tipos `FigurinoSheetOption`/`AssignableTalent` extraídos
  em `lib/eventCreate.ts`.
- **Constituição.** Novo **Princípio X** (v2.1.0) — dados complexos, comboboxes e autocomplete.

**Rotas e endpoints.**

| Método | Rota | Observação |
|---|---|---|
| GET | `/api/maps/address-autocomplete?q=&session_token=` | **novo** — proxy do Google Places |
| GET | `/api/events/new/options` | **alterado (aditivo)** — `assignable_talents[].photo_face_path` |

**Detalhe do que ficou de pé.**

1. **Proxy do Places, chave no servidor.** O React nunca vê a `google_maps_api_key`: fala só com
   `/api/maps/address-autocomplete`, que lê a chave de `SiteSetting` (com fallback para a env
   `GOOGLE_MAPS_API_KEY`) e devolve `{"items": [{description, place_id}]}`, no máximo 5, restrito
   ao Brasil e em pt-BR. Chave ausente → **503** com "Configure a API Key em Admin →
   Configurações"; falha do Google → **502** amigável, com o erro real em `logger.warning`.
2. **Economia de quota em dois níveis.** Termo com menos de 3 caracteres devolve lista vazia com
   200 **sem chamar o Google** (constante `AUTOCOMPLETE_MIN_CHARS`, espelhada no frontend como
   `ADDRESS_MIN_CHARS`); o `useAddressAutocomplete` ainda aplica debounce de 350ms e cache de 5min
   do TanStack Query. O `GoogleAddressInput` inicia com a busca vazia mesmo quando o campo já tem
   endereço salvo — abrir a edição de um evento **não** consulta o Google.
3. **`Combobox` é o novo padrão para lista grande.** Filtro local que ignora acentos ("José" casa
   com "jose"), navegação por setas/Enter/Esc, `aria-activedescendant`, botão de limpar, spinner de
   loading e dropdown com Framer Motion respeitando `useReducedMotion()`. Tem modo `freeSolo`, em
   que o valor é o texto digitado e as opções são só sugestões — é o que permite reusar o mesmo
   componente para endereço (nem todo local existe no Google).
4. **Miniaturas com forma semântica.** `AvatarThumb` é **circular** para pessoas (talento,
   coordenador — `photo_face_path`) e **quadrada** para figurino/personagem (`photo_url`). Sem foto
   salva, renderiza as iniciais do nome ou o ícone passado (🎭 para figurinos, 📍 nas sugestões de
   endereço). `@manto/ui` continua **sem** depender de `@manto/api-client`: quem chama resolve a
   URL com `assetUrl()` antes de passar.
5. **O botão de distância do orçamento passou a existir.** `useDistancia()` estava definido em
   `lib/orcamento.ts` desde a migração e **nunca era chamado** — o KM em `/orcamento` era 100%
   digitado à mão, enquanto o EducaManto já calculava. Agora há um "Calcular km (Maps)" ao lado de
   *Km (ida)*, e escolher uma sugestão do Google com "Fora de SP" ligado já dispara o cálculo.

**Impacto em RBAC e regras de negócio.** Nenhum. O endpoint novo é `api_login_required` puro (não
expõe dado do sistema, só o retorno público do Google) e as telas que o consomem mantêm o RBAC que
já tinham. Nenhuma regra de cálculo de orçamento, transporte ou elenco foi alterada — o que mudou
é *como o dado entra*.

**Riscos e pegadinhas.**

- **`onSelectSuggestion` recebe o texto explicitamente.** Ao escolher uma sugestão, o `onChange` do
  React ainda não refletiu o novo valor no mesmo tick; por isso `handleCalcularDistancia(override)`
  aceita o endereço por parâmetro. Sem isso, a primeira consulta iria com o endereço anterior.
- **`onClick={handleCalcularDistancia}` é armadilha.** Como a função passou a ter um parâmetro
  opcional `string`, ligar o handler direto no `onClick` passaria o `MouseEvent` como endereço.
  Sempre `onClick={() => handleCalcularDistancia()}`.
- **O `activeIndex` do `Combobox` não depende da identidade de `options`.** Um chamador que recria
  o array a cada render zeraria o item destacado a cada tecla; o reset ficou dividido em "volta ao
  topo quando a busca muda" + "reancora quando a lista encolhe".
- **A cópia local `manto_local` tem `manto_address = 'Rua V168 Teste, 123'`** (lixo deixado pelo
  `verify_168`), o que faz **qualquer** cálculo de distância local retornar 400 "Endereço não
  encontrado pelo Google Maps" — inclusive com endereço normalizado. Não é bug do código: com uma
  origem válida a Distance Matrix responde `OK`. Em produção o endereço-base é o real.
- **Verificação**: `scripts/db/verify_195_maps_autocomplete.py` (20/20) — monkeypatcha
  `googlemaps.Client` para cobrir sucesso e falha sem gastar quota nem depender de rede.

### 194 — Planilha de Pagamentos: cards-filtro, colorização por faixa e soma da seleção
`194-pagamentos-ux-cores-filtro` · **2026-07-28** · **sem migration**

**Motivação.** A planilha de `/financeiro/pagamentos` já tinha todos os dados certos, mas o
financeiro precisava ler linha a linha para saber o que estava pago, no banco, vencido ou por
vencer — os 5 cards de KPI no topo eram números mortos, sem interação, e as linhas só tinham cor
para "pago"/"no banco" (pendente e futuro ficavam ambos brancos). Faltava também o número que o
operador confere antes de disparar um lote no internet banking: **quanto soma o que está
marcado**.

**O que mudou.**

- **Backend / Banco.** Nada. Zero endpoint, zero migration, zero mudança de contrato JSON — toda
  a evolução é de apresentação e roda sobre o payload que `GET /api/financeiro/pagamentos` já
  devolvia desde a feature 159.
- **Frontend.** `frontend/apps/internal/src/pages/PagamentosPage.tsx` reescrita (typecheck e
  `npm run build` limpos) e um acréscimo ao design system em
  `frontend/packages/ui/tailwind-preset.ts`.

**Detalhe do frontend.**

1. **Cards de KPI viraram filtro da tabela.** Os 5 cards do topo agora são `<button>`
   (`Card asChild`, com `aria-pressed`) que filtram as linhas no cliente: **Pagos** →
   `status === "pago"`; **No banco** → `"no_banco"`; **Pendentes** → `"nao_pago"` já vencido;
   **Futuro** → `"nao_pago"` a vencer; **Total no período** (ou reclicar o card ativo) limpa o
   filtro. Cada card mostra também a contagem de itens da faixa e o rótulo "· filtro ativo".
   O card ativo ganha borda de 2px na cor do status + `ring` + fundo colorido e sombra; os
   demais ficam com `opacity-60 grayscale-[35%]` (volta ao normal no hover), então nunca há
   dúvida sobre qual filtro está ligado. Um `aria-live` anuncia "Filtro X ativo: N de M itens",
   e o cabeçalho da tabela vira "Itens do mês (N de M)" com um botão "Limpar filtro".
2. **A classificação das 4 faixas é a MESMA do backend.** `bucketOf()` deriva "pendente" e
   "futuro" do campo `is_future` que a API já manda (`_pagamentos` em
   `app/api/financeiro_read.py` soma `totals.pendente` como `nao_pago && !is_future` e
   `totals.futuro` como `nao_pago && is_future`) — **não** recomparando datas no cliente. Assim
   o filtro do card sempre bate com o valor exibido nele; se a regra de vencimento mudar no
   backend, a tela acompanha sozinha.
3. **Colorização da tabela por faixa.** Cada linha recebe uma nuance de fundo pela sua situação:
   `bg-green-50` (pago), `bg-blue-50` (no banco), `bg-rose-50` (pendente), `bg-gold-50` (futuro).
   O seletor de situação e o badge "⏳ Futuro" saem da mesma paleta (`BUCKET_TONE`), então a cor
   que o operador clica no card é exatamente a cor das linhas que aparecem. Descrição, favorecido
   e valor subiram para `font-bold text-ink` (#1a1a1a) — contraste ≥ 15:1 sobre os quatro fundos.
4. **Barra de ações em lote no topo da tabela, com a soma da seleção.** Nova
   `PagamentoBulkBar` (mesmo padrão de movimento do `CatalogBulkActionBar` da feature 186:
   `AnimatePresence` + `useReducedMotion`), renderizada dentro do `CardContent` acima da tabela.
   Texto à esquerda: **`"X selecionados • R$ Y.YYY,YY"`**, com a soma calculada por `reduce`
   sobre os itens marcados no estado do React e formatada por `formatBRL` de `@manto/money`
   (Princípio VII — fonte única).
5. **Spinner individual por ação em lote (Princípio V).** Antes, `bulkAction.isPending` fazia os
   4 botões girarem juntos. Agora a ação em voo é lida de `bulkAction.variables?.action`
   (TanStack Query v5) — só o botão clicado mostra spinner; os outros ficam `disabled` enquanto
   o lote roda, o que também impede disparar dois lotes concorrentes.
6. **Seleção.** "Selecionar tudo" passou a operar sobre as linhas **visíveis**: com um filtro
   ligado, marcar tudo marca só aquela faixa e não mexe no que já estava selecionado fora dela.
   A linha marcada ganha uma barra lateral roxa (`border-l-4 border-l-accent` no primeiro `td`,
   com `border-l-transparent` quando não marcada, para a linha não "pular" 4px). Trocar o mês
   limpa seleção e filtro.

**Design system.** `gold` ganhou os degraus **50 / 100 / 500 / 600** em
`frontend/packages/ui/tailwind-preset.ts` (`DEFAULT` e `soft` intactos — mudança puramente
aditiva). Motivo: `green`/`blue`/`red`/`rose` herdam a escala numérica padrão do Tailwind, mas
`gold` só tinha `DEFAULT`/`soft`, então `bg-gold-50` e `border-gold-500` não existiam. `gold`
continua sendo a cor de atenção/futuro do sistema — **não usar `amber`**, que não combina com o
dourado da marca.

**Impacto em RBAC e regras de negócio.** Nenhum. Acesso segue `FINANCEIRO`/`SUPERADMIN` pelo
endpoint; o filtro é 100% visual e não altera o que a ação em lote envia (ela continua mandando
os IDs selecionados, estejam visíveis ou não).

**Riscos e pegadinhas descobertas.**

- **`Card asChild` não desempata classe Tailwind.** O `Slot` do Radix apenas **concatena** o
  `className` do filho ao do pai — não passa por `twMerge`. Com as classes do card no `<button>`
  filho, `border` (do `Card`) e `border-2` (do card ativo) sobrevivem os dois e quem vence é a
  ordem no CSS gerado, não a ordem no atributo. Correção: passar **todas** as classes no
  `className` do próprio `<Card>` (que roda `cn`/`twMerge`) e deixar o `<button>` filho sem
  `className`.
- **`shadow-[inset_3px_0_0_theme(colors.accent.DEFAULT)]` é silenciosamente descartado.** O
  Tailwind 3.4 não gerou nenhuma regra para esse valor arbitrário com `theme()` dentro — e não
  emite erro: nem `tsc` nem `vite build` reclamam, a classe simplesmente não existe no CSS
  final. Só se pega conferindo o `dist/assets/*.css`. Trocado por `border-l-4 border-l-accent`.
  **Ao usar valor arbitrário do Tailwind, confirme no CSS buildado que a regra saiu.**
- **`vite build` falha com `EPERM ... dist/assets` se algum shell estiver com o `cwd` dentro de
  `dist/assets`** (o Windows trava a pasta e o `emptyDir` do Vite não consegue apagá-la). Sair da
  pasta antes de rebuildar.

### 193 — Importação Histórica do WhatsForm (One-time Migration)
`193-import-whatsform-history` · **2026-07-28** · **sem migration**

**Motivação.** O formulário de pré-contrato do Manto (features 118/119/123) substituiu o
WhatsForm em produção, mas os **1.445 preenchimentos de 2023-09 a 2026-07** continuavam presos
nos CSVs exportados da ferramenta antiga. A vendedora não tinha como buscar no Manto uma cliente
que já havia preenchido o formulário lá atrás, e a base de leads (até então só Kommo) ignorava
todo esse histórico de intenção de compra — o dado comercial mais quente que a empresa tinha.

**O que mudou.**

- **Backend.** Nenhum endpoint, rota ou tela nova — é uma **carga única por CLI**, por decisão
  explícita: um botão no sistema para algo que roda uma vez seria superfície morta. Todo o
  trabalho está em `scripts/db/import_whatsform_history.py` (novo, ~600 linhas, `ruff
  check`/`ruff format` limpos), que lê `instance/import_whatsform/*.csv` e grava via
  `db.session`. Reusa, sem duplicar (Princípio I): `normalize_phone` de
  `app/clientes/importer.py` e as chaves-sistema `SYSTEM_KEY_CPF`/`SYSTEM_KEY_CNPJ`/
  `SYSTEM_KEY_ADDRESS_*` de `app/formularios/formularios_ops.py`.
- **Banco (sem DDL).** Em **produção**: `form_responses` 28 → **1.473** linhas (+1.445);
  `clients` 5.533 → **6.198** (+665 criados, 767 reutilizados, 415 completados em colunas que
  estavam nulas). Antes disso a mesma carga rodou em `manto_local` (+693 criados, 739
  reutilizados) — a produção tinha mais clientes cadastrados que a cópia local, então 28 linhas
  a mais casaram em vez de duplicar. Valor novo em `clients.source`: **`whatsform_import`** (ao
  lado de `kommo_import` e `manual`) — coluna é texto livre, não há enum/constraint para alterar.
- **Frontend.** Zero mudança de código. As respostas importadas aparecem nas telas que já
  existiam (`/formularios`, buscador de resposta em `/events/new`, ficha do cliente) porque o
  script grava `form_type` em `comum`/`corporativo` e monta `FormResponse.data` no formato da
  feature 123 — `[{"secao", "campos": [[chave, rótulo, valor], …]}]`, com campos de 3 posições,
  que é o que `FormulariosAdminPage.tsx` destrutura.

**Regras de negócio implementadas.**

- **Deduplicação em 2 níveis**: telefone normalizado (dígitos, DDI `55` acrescentado em números
  de 10–11 dígitos) e, se não achar, CPF/CNPJ limpo. Cliente encontrado é **reaproveitado** e
  só tem preenchidas as colunas nulas (`email`, `cpf`, `cnpj`, `company`, `address`,
  `phone_display`) — `name` nunca é sobrescrito.
- **Lógica B2B premium** (3 planilhas corporativas): `name` = `"Nome do Responsável (Empresa)"`
  e telefone = **WhatsApp de quem preencheu**, não o fixo da empresa — em venda corporativa quem
  responde no WhatsApp é a pessoa. A razão social completa vai para `clients.company`.
- **CPF vs CNPJ**: o WhatsForm tinha campo único "CNPJ ou CPF"; o roteamento é por comprimento
  (14 dígitos → `clients.cnpj`, demais → `clients.cpf`), aproveitando as duas colunas que o
  model já tem.
- **`iNFORMACOES PARA PRE CONTRATO CORPORATIVO.csv`** não tem coluna de responsável: o nome sai
  da parte local do e-mail + tema, no padrão `"Contato (Tema: Halloween)"`.
- **`created_at` histórico** em respostas e nos clientes criados pela carga — a base reflete a
  linha do tempo real de captação, não a data do import.

**Impacto em RBAC.** Nenhum. Não há rota nova; quem já via `/formularios` (COMERCIAL,
FINANCEIRO, SUPERADMIN) passa a ver mais linhas.

**Rotas e endpoints novos/alterados.** Nenhum.

**Riscos e pegadinhas descobertas.**

- **`clients.phone` é `NOT NULL UNIQUE`** — linha sem telefone normalizável não pode virar
  cliente. Em vez de descartar a resposta, o script grava a `FormResponse` com `client_id`
  nulo (13 casos) para o comercial associar à mão depois. Não invente telefone-placeholder aqui:
  a unicidade do telefone é a identidade da base inteira.
- **`form_type` só aceita `comum`/`corporativo` na prática** — não é enum no banco, mas
  `frontend/apps/internal/src/lib/formulariosAdmin.ts` tipa assim e `FormulariosAdminPage`
  filtra por igualdade. Um valor como `"pre-contrato"` gravaria sem erro e **sumiria dos
  filtros** da tela. Mesma armadilha vale para qualquer carga futura.
- **Documento não confiável não deduplica.** Valores como `"2222222222"` (10 dígitos) aparecem
  nas planilhas; se entrassem na busca por CPF fundiriam clientes diferentes. Só documentos com
  11 ou 14 dígitos participam da deduplicação — os demais são gravados, mas ignorados na busca.
- **Console do Windows é cp1252**: `print` com glifos como `▶`/`═`/`✔` derruba o script com
  `UnicodeEncodeError` antes de qualquer linha ser gravada. A saída usa só ASCII (`>>`, `[OK]`,
  `[ERRO]`) — acentos pt-BR passam normalmente, os símbolos é que não.
- **`strptime` com `%a`/`%b` depende do locale da máquina.** O carimbo do WhatsForm
  (`"Wed, Jul 8, 2026 12:06 PM"`) é parseado por regex + tabela de meses própria, para a carga
  não mudar de comportamento conforme o computador que a roda.
- **Rodar duas vezes duplicaria tudo** — não há chave natural de resposta no banco para
  `upsert`. O script detecta respostas já importadas (mesmo `contact_name` + `created_at`) e
  **aborta o arquivo** com rollback, a menos que se passe `--force`. Verificado: a segunda
  execução não gravou nada.
- **Transação por arquivo**: erro em qualquer linha faz `rollback()` do CSV inteiro e loga
  arquivo + linha + contato. `--dry-run` processa tudo numa transação única e desfaz no fim —
  o resumo simulado bate número a número com o da carga real (foi assim que a carga foi
  validada antes de gravar).

**Como rodar (uma vez por ambiente).**

```powershell
# 1. Backup fresco ANTES de qualquer escrita
.\scripts\db\backup-railway.ps1

# 2. Cópia local (manto_local)
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path

# 2'. OU produção (Railway) — trocar o driver para psycopg3, ver pegadinha abaixo
$env:DATABASE_URL = (Get-Content .railway-db-url -Raw).Trim() -replace '^postgresql://', 'postgresql+psycopg://'
$env:PYTHONPATH = (Get-Location).Path

# 3. Ensaio e carga
.venv\Scripts\python.exe scripts\db\import_whatsform_history.py --dry-run   # ensaio
.venv\Scripts\python.exe scripts\db\import_whatsform_history.py             # carga
```

> **Status: concluído nos dois ambientes em 2026-07-28** — `manto_local` primeiro, produção
> (Railway) em seguida, ambas precedidas de ensaio limpo. Backup da produção imediatamente antes
> da carga: `backups/manto_2026-07-28_1119.dump`.

**Pegadinhas descobertas ao apontar para a produção** (valem para qualquer script CLI futuro):

- **`create_app()` sobe três workers de background** — `talent-sync`, `calendar-sync` e
  `review-cleanup`. Apontados para a produção, o `calendar-sync` pode reivindicar o slot de
  sincronização automática e disparar um sync real com o Google Calendar, e o `review-cleanup`
  apaga arquivos de revisão vencidos do armazenamento — efeito colateral que nada tem a ver com
  importar CSV. O script chama `build_app_without_background_workers()`, que ativa a guarda de
  dev já existente (`FLASK_ENV=development` sem `WERKZEUG_RUN_MAIN`) antes do `create_app()`.
  Isso **não** muda o banco: a `SQLALCHEMY_DATABASE_URI` vem sempre de `DATABASE_URL`, e nem
  `DevelopmentConfig` nem `ProductionConfig` a sobrescrevem.
- **Driver diferente entre a máquina de dev e a produção.** O `requirements.txt` traz
  `psycopg2-binary` (usado no deploy), mas o venv local tem só o **psycopg3** — por isso
  `.local-db-url` usa `postgresql+psycopg://`. A URL do Railway vem como `postgresql://`, que o
  SQLAlchemy resolve para psycopg2 e quebra com `ModuleNotFoundError` na máquina de dev. Reescrever
  o scheme para `postgresql+psycopg://` resolve — mesmo banco, cliente diferente.
- **Latência domina a carga remota.** A deduplicação consulta o banco linha a linha: imperceptível
  no Postgres local, ~100 ms por ida-e-volta contra o Railway → ~20 min para as 1.445 linhas
  (ensaio + carga = ~40 min). Foi aceito de propósito, para rodar exatamente o código validado em
  vez de otimizar o caminho crítico em cima de produção. Se algum dia precisar ser rápido, o
  caminho é carregar o índice de clientes em memória de uma vez, não paralelizar.

---

### 191 — Migração do Portal do Artista (React) e Auditoria de Segurança
`191-portal-artista-react-auditoria` · **2026-07-28** · **sem migration**

> Numeração fora de ordem em relação à 192 logo abaixo: a 192 foi um ajuste direto em `main`,
> feito enquanto esta fatia estava planejada. A ordem do documento continua sendo por data.

**Motivação.** A fatia **176** entregou 5 telas React do Portal do Artista (login, agenda,
convites, ficha de figurino, fotos/documentos) e deixou explicitamente de fora todo o resto —
primeiro acesso, troca de senha obrigatória, aceite de termos, "esqueci minha senha", edição de
perfil e avaliação de eventos continuaram só no Jinja (`app/talent_portal`). Na prática o
talento era jogado para a versão clássica no meio do login (`must_redirect_to_classic`), e o
histórico de cachês não existia em React. Além disso, **o bundle do portal nunca era publicado**:
`frontend/server.js` só montava `apps/internal` e `apps/public`, e o `build` agregado do
monorepo não incluía `apps/portal` — o app existia no repositório e nunca chegava a produção.

**Backend.** Nenhum endpoint antigo mudou de contrato. Três módulos de núcleo de negócio, todos
puros e reusáveis pelo Jinja legado (Princípio I):
- `app/talent_portal/portal_account_ops.py` (**novo**): `validate_password_strength`,
  `start_first_access`, `request_password_reset`, `find_talent_by_reset_token`,
  `reset_password_with_token`, `change_password`, `accept_terms`, `pending_account_steps`.
  O disparo de e-mail entra por callback injetado pela rota — o módulo não importa `request`.
- `app/talent_portal/portal_rating_ops.py` (**novo**): extraído de `routes.py` sem mudar a
  semântica em produção — janela de 7 dias para avaliar e 30 para editar (contadas do mais
  recente entre o fim do evento e `assigned_at`, feature 085), nota &lt;4 exige comentário,
  versionamento da avaliação anterior (feature 181) e as categorias de sub-nota.
- `app/talent_portal/portal_ops.py`: ganhou `get_profile`/`update_profile` (PATCH parcial com
  validação de altura e data), `add_portfolio_photo`/`add_portfolio_link`/
  `delete_portfolio_item` e `get_historico` (lista + somatórios pago/pendente).

**Endpoints novos** (12; total de `/api/portal/*` foi de 14 para 26):
`POST /api/portal/auth/first-access`, `POST /api/portal/auth/forgot-password`,
`GET /api/portal/auth/reset-password/<token>`, `POST /api/portal/auth/reset-password`,
`POST /api/portal/auth/change-password`, `POST /api/portal/auth/accept-terms`,
`GET|PATCH /api/portal/profile`, `POST /api/portal/profile/media/photo`,
`POST /api/portal/profile/media/link`, `DELETE /api/portal/profile/media/<id>`,
`GET /api/portal/historico`, `GET /api/portal/ratings/pending`,
`GET|POST /api/portal/events/<id>/rate`, `POST /api/portal/events/<id>/rate/detail`.
`GET /api/portal/auth/me` e o login agora devolvem `must_change_password`, `terms_accepted` e
`pending_steps`; `must_redirect_to_classic` virou sempre `false` (mantido por compatibilidade).

**Banco.** Sem migration — tudo já existia em `Talent` (`must_change_password`,
`password_reset_token/expires`, `terms_accepted_at`, medidas), `TalentMedia`, `EventRating`,
`EventSubRating` e `EventRatingVersion`.

**Frontend.** 8 telas novas em `frontend/apps/portal`: `PortalFirstAccessPage`,
`PortalForgotPasswordPage`, `PortalResetPasswordPage`, `PortalChangePasswordPage`,
`PortalTermsPage`, `PortalProfilePage`, `PortalHistoricoPage` e `PortalRatePage`. Componentes
compartilhados novos: `AuthCard`, `FormField`/`FormError`/`FormSuccess`, `PasswordChecklist`,
`StarRating` (radiogroup real, acessível) e `OnboardingGate`. `lib/format.ts` centraliza
data/hora amigável (Princípio VII) — `formatDateTime`, `formatWeekday`, `formatRelativeDay`,
`formatLongDate`, `formatShortDate`; valor monetário continua em `@manto/money`.
O texto do termo virou `lib/termsContent.ts`, transcrição fiel de `templates/portal/terms.html`
(o aceite gravado precisa se referir ao mesmo documento antes e depois).

**Deploy (a parte que faltava para o portal existir em produção).**
- `frontend/server.js`: passou de 2 para 3 SPAs, com uma lista de apps montados por prefixo —
  `/catalogo/*` → `apps/public/dist` e `/portal/*` → `apps/portal/dist`, raiz → `apps/internal`.
  Deep link e refresh funcionam nos três (cada um com seu próprio fallback de `index.html`).
- `frontend/apps/portal/vite.config.ts`: `base: "/portal/"` em produção (mesmo padrão da 186 no
  `apps/public`), e o React Router recebe `basename={import.meta.env.BASE_URL}`.
- `frontend/package.json`: `build` e `typecheck` agregados passam a incluir o portal, mais
  `dev:portal`/`build:portal`/`typecheck:portal`.
- `app/api/portal_auth.py::_reset_url` monta o link de redefinição a partir de `PORTAL_URL`
  (mesma base já usada pelos outros e-mails do portal), caindo na rota Jinja se a env não estiver
  configurada — o link não quebra em ambiente onde o front novo ainda não subiu.

**RBAC e regras de negócio.** Sem mudança de política. O RBAC do portal continua sendo "é o dono
do recurso": toda consulta parte do `talent_id` da sessão e nenhum endpoint aceita um id de
talento vindo do cliente (o PATCH de perfil ignora um `id` no corpo, verificado na auditoria).
A trava de onboarding é servida **no lugar** do app pelo `OnboardingGate`, não por redirect —
não existe URL de onboarding para pular, e um deep link para `/agenda` com senha pendente cai na
mesma trava. A API deliberadamente **não** bloqueia por termos pendentes: o gate é de produto,
não de segurança, e endurecer isso mudaria o comportamento do Jinja legado que ainda usa a mesma
sessão.

**Auditoria de segurança** (`scripts/security/overnight_security_audit.py`, **novo** — 76
verificações, saída com código 1 em qualquer falha, relatório em
`scripts/security/relatorio_seguranca.md`):
- **Cookies**: `HttpOnly` + `SameSite=Lax` confirmados nas sessões de Staff e de Talento, e
  `SESSION_COOKIE_SECURE=True` em `ProductionConfig` (em dev fica ausente de propósito, HTTP).
- **Isolamento de sessão**: as duas sessões são hermeticamente fechadas nos dois sentidos —
  cookie de talento dá 401 na API de staff e vice-versa, e cada login faz `session.clear()`,
  encerrando a sessão do outro tipo no mesmo cookie.
- **RBAC**: talento bloqueado em 13 endpoints internos; anônimo bloqueado; vendedor (COMERCIAL)
  bloqueado em usuários/RH/pagamentos/configurações/logs/desempenho (403); IDOR no portal
  (escalação, mídia e figurino de terceiros) devolve 404/403.
- **E-mails**: os 8 disparadores mapeados; todo caminho de `mail.send()` está sob `try/except`
  **e** atrás de `SiteSetting.email_notifications_enabled`; com a flag desligada o envio vira log
  silencioso e a request segue 200; com SMTP fora do ar a resposta continua 200 com mensagem
  amigável, sem 500; o reset de senha não permite enumeração de conta (mesmo status e mesmo corpo
  para CPF existente e inexistente).

**Riscos e pegadinhas descobertas.**
1. **`app/api/__init__.py` importa por efeito colateral em ordem de registro** — o módulo novo
   `portal_ratings` precisa entrar nessa lista, senão as rotas simplesmente não existem. O
   `ruff` acusa `I001` no arquivo (pré-existente): a ordem é deliberada, não ordene os imports.
2. **`query.delete()` em massa não passa pelo ORM** e deixa órfãs as linhas de associação —
   estourou FK em `user_roles` (auditoria) e em `event_sub_ratings` (verificação). Nos scripts,
   apagar objeto a objeto com `db.session.delete()` para a cascata do ORM valer.
3. **`send_quote_email` não usa `_send`** (precisa anexar PDF) e reimplementa o guarda. A
   auditoria verifica a *propriedade* (todo `mail.send(` sob try/except + gate) em vez de exigir
   uma função única — contar chamadas dava falso positivo.
4. **Reset de senha de staff não existe por e-mail**: um SUPERADMIN define a senha temporária à
   mão em `user_ops.reset_password`. Só o Portal do Artista tem fluxo self-service. Registrado
   como observação na auditoria, não como falha.
5. **`FileUpload` do design system tinha alvo de toque de 36px** (`size="sm"`, único controle do
   componente). Corrigido na origem com `min-h-[44px]` — o portal é mobile-only (Princípio VIII)
   e no desktop o botão só cresce 8px.
6. **O baseline de versionamento da avaliação vai e volta pelo cliente** na API (a tela Jinja
   guarda na sessão, mas o slot único já estourou o tamanho do cookie uma vez). É só um detector
   de mudança: adulterá-lo no máximo registra — ou deixa de registrar — uma versão no histórico,
   nunca altera a nota gravada.
7. **Proxy Vite de `/portal` foi estreitado para `/portal/photo`** — o prefixo largo funcionava
   quando o app React vivia só na raiz em dev, mas sombrearia as rotas próprias do portal. Mesma
   pegadinha da feature 183 com `/figurinos`.

**Legado.** As rotas Jinja de `app/talent_portal` **continuam de pé e sem regressão** (paridade
verificada: login, first-access, forgot-password, `/portal/`, `/portal/historico`,
`/portal/profile`). Decomissioná-las é limpeza futura, fora do escopo desta entrega — conforme a
regra de `CLAUDE.md`, não apagar view antiga sem confirmação.

**Verificação.** `scripts/db/verify_191_portal_react.py` — 72/72 contra `manto_local`
(fluxos de conta, perfil/portfólio, avaliações com janelas e versionamento, histórico com
somatórios, paridade Jinja). Auditoria: 76/76. `npx tsc --noEmit` e `npm run build` limpos nos
três apps. Telas conferidas em viewport de 320px e 430px: sem rolagem horizontal, nenhum alvo de
toque &lt;44px, nenhum texto informativo &lt;12px.

---

### 192 — Detalhe do Evento: layout de duas colunas com paridade total da tela clássica
`main` (ajuste direto, sem branch de feature dedicada) · **2026-07-27** · **sem migration**

**Motivação.** A `/events/:id` em React era uma coluna única de ~1370 linhas num arquivo só,
com uma fração do que a tela clássica Jinja (`app/templates/event_detail.html`, 3.201 linhas,
ainda em produção em paralelo) entrega. Faltavam na versão React: menu "⋯ Ferramentas", bloco de
cópia rápida para WhatsApp, indicador de conflito de agenda do talento, medidas de figurino,
vínculo de ficha de figurino ao personagem, status de pagamento do cachê, equipe de apoio
separada dos personagens, materiais de ensaio, gastos extras vinculados, acréscimos/BV,
avaliações dos artistas, feedback da cliente e o log de atividades. Boa parte disso já existia
como cálculo inline na view Jinja — nunca tinha sido exposta pela API.

**Backend.** Nenhum endpoint antigo mudou de contrato; o JSON de leitura **ganhou campos**.
- `app/calendar/event_ops.py` (+~290 linhas): núcleo novo — `talent_availability` (extraído do
  loop inline de `event_detail`), `set_payment_status`, `link_figurino_sheet`,
  `clear_figurino_done`, `ensure_feedback_token`, `suggested_departure_time`,
  `add_ensaio_file`/`add_ensaio_link`/`delete_ensaio_material`.
- `app/api/agenda_read.py`: `serialize_event_detail` passou a incluir `event.description`,
  `event.google_html_link`, `event.travel` (cache do Maps + saída sugerida + `maps_url`),
  `materiais`, `ratings`, `client_feedbacks`; e, sob os gates já existentes, `acrescimos`,
  `gastos`, `mensagens`, `reembolsos_pendentes_total`, `feedback_link_pendente`. Cada cargo
  do `elenco` ganhou `talent` completo (medidas, WhatsApp com DDI, primeiro nome), `role_type`,
  `assigned_at`, `payment_status`, `availability`, `figurino_sheet_name`, `figurino_done_at`,
  `travel_cache` e `cache_cap`.
- `app/api/agenda_write.py`: 7 endpoints novos — `POST /api/roles/<id>/payment-status`,
  `POST /api/roles/<id>/figurino-sheet`, `DELETE /api/roles/<id>/figurino-done`,
  `POST /api/events/<id>/travel-estimate`, `POST /api/events/<id>/materials`,
  `DELETE /api/materials/<id>`, `POST /api/events/<id>/feedback-link`.

**Banco.** Sem migration — nenhuma coluna nova. Tudo já existia em `EventRole`
(`payment_status`, `figurino_sheet_id`, `assigned_at`), `CalendarEvent` (`description`,
`google_html_link`, `travel_*`, `feedback_token`), `EnsaioMaterial`, `EventRating`,
`ClientFeedback`, `SpecialExpense` e `EventAcrescimo`.

**Frontend.** `EventDetailPage.tsx` reescrita (1.367 → ~120 linhas) como composição de
`components/EventDetail/`: `parts.tsx` (Panel/DataRow/Stars/formatadores), `EventHeader.tsx`
(cabeçalho + menu Ferramentas + modal de exportar elenco + diálogo de exclusão),
`CastingSection.tsx`, `FigurinoSection.tsx`, `LogisticaSection.tsx`, `ComercialSection.tsx`,
`FinanceiroSection.tsx`, `FeedbackSection.tsx`, `ObservacoesSection.tsx` (+ `WhatsAppSummary` e
`LogsSection`). Hooks novos em `lib/eventDetail.ts` (todos gravam o evento devolvido no cache do
TanStack Query, como `casting.ts`) e os construtores das mensagens de WhatsApp. `KebabMenu`
ganhou `triggerLabel` e itens `disabled`/`title` em vez de um segundo componente de dropdown.
A busca de fichas de figurino reusa `useFigurinoSheets()` (`GET /api/figurino`), sem endpoint
novo.

**RBAC e regras de negócio.** Sem mudança de política — os gates novos reusam os existentes:
`_CAN_EDIT_EVENT` (status de pagamento, ficha de figurino, desmarcar figurino, estimar trajeto),
`_CAN_ENSAIO_MATERIAL` (materiais de ensaio) e Comercial/Superadmin (link de feedback, mesmo
gate de `feedback.gerar_link`). **Novo requisito de segurança**: a seção "Log de atividades" só
é renderizada para `SUPERADMIN` — para os demais papéis ela **não existe no DOM**, não é
escondida por CSS.

**Riscos e pegadinhas descobertas.**
1. `CalendarEvent.roles` **não tem `order_by`** — o Postgres devolvia os cargos em ordem
   arbitrária, e a ordem *mudava depois de um UPDATE*. Com os cards densos isso fazia a lista
   inteira pular de posição a cada mutação. `serialize_event_detail` agora ordena por `id`.
2. `api_set_payment_status` colidiu com o endpoint de mesmo nome em `financeiro_write.py`
   (Flask recusa o registro do blueprint com `AssertionError`) — renomeado para
   `api_set_role_payment_status`.
3. A descrição do evento vem do Google/Kommo **em HTML** (`<br>`, âncoras de e-mail). Colada
   crua no WhatsApp vira um paragrafão com tags à mostra; `descriptionToText()` converte para
   texto puro por regex (sem `innerHTML`/`querySelector`, proibidos pela constituição).
4. `/api/events/<id>` não é alcançável por `REVENDEDOR_EDUCAMANTO` puro — o guard global de
   `app/__init__.py` só libera o prefixo `/events/`, não `/api/...`. Comportamento pré-existente,
   descoberto ao escolher papéis para o script de verificação.
5. Materiais de ensaio novos vão por `app.storage.save_file` (local/S3) em vez do `file.save()`
   direto do fluxo Jinja; o serializador normaliza os dois formatos de `file_path`.

**Verificação.** `scripts/db/verify_190_event_detail.py` — 53/53 contra `manto_local`
(serialização dos blocos novos, RBAC de leitura por papel, e 200/400/403/404/401 dos 7
endpoints). Frontend: `npm run build` limpo e conferência no app real (evento 286): 16 seções,
duas colunas em 1280px, sem rolagem horizontal, log ausente do DOM ao impersonar `CASTING`,
mutações de figurino/pagamento/materiais devolvendo 200 com a lista estável.

---

### 191 — Calculadora de Orçamento: paridade de layout clássico + cálculo reativo
`main` (ajuste direto, sem branch de feature dedicada) · **2026-07-27** · **sem migration**

**Motivação.** A versão React de `/orcamento` (feature 190) portou a calculadora para duas
colunas de largura igual com um botão manual "Calcular orçamento" — isso dispersou os campos em
relação à tela clássica Jinja (`app/templates/orcamento/index.html`, ainda em produção em
paralelo) e tornou o fluxo do comercial mais lento (clicar em "Calcular" a cada ajuste). Dois
recursos da tela clássica nunca foram portados: o alerta de segurança "já agendado neste dia"
(evita vender o mesmo personagem duas vezes no mesmo dia) e o painel "Personalizar valores"
(definir o total final manualmente, por valor ou por multiplicador) — a infraestrutura de API
para ambos já existia (`usePersonagensNoDia`, campos `personalizado*` em
`CalcularOrcamentoInput`), só nunca tinha sido usada na tela.

**Backend.** Nenhuma mudança — nenhum endpoint, RBAC ou model tocado. Todo o trabalho reusou
`GET /api/orcamento/personagens-no-dia`, `GET /api/orcamento/historico` e
`POST /api/orcamento/calcular`, já existentes desde a feature 177/190.

**Banco.** Sem migration.

**Frontend.** Reescrita completa de `OrcamentoCalculadoraPage.tsx` (mesmo arquivo,
`PerformerTableRow` reaproveitado sem mudanças):
- Layout `lg:grid-cols-3`: coluna esquerda (1/3) = Dados do Evento + transporte condicional
  (Fora de SP) + alerta de agenda + link "Histórico de Orçamentos" com contador dinâmico
  (`useOrcamentoHistorico({}).data.entries.length`); coluna direita (2/3) = Equipe, Acréscimos,
  card "Ajustes Finos" (Nota Fiscal, duração extra, formato do orçamento, durações incluídas,
  "Personalizar valores") e o card de Resultado.
- **Cálculo reativo**: removido o botão "Calcular orçamento"; um `useEffect` observa um
  `payload` memoizado com todo o estado do formulário e dispara `calcular.mutate` com debounce
  de ~400ms a cada alteração — sem exigir clique. Os cards de resultado ficam com opacidade
  reduzida (`opacity-50`) enquanto uma requisição está em voo, em vez de somem, preservando o
  último valor visível (Princípio V — feedback visual obrigatório).
- **Alerta "Já na agenda neste dia"**: novo componente `AgendaNoDiaAlert`, usa
  `usePersonagensNoDia(eventDate)` (existia no hook, nunca usado em nenhuma página); valida a
  data com regex antes de habilitar a query, para não disparar a API com data parcial/inválida;
  renderiza abaixo do campo Data.
- **Painel "Personalizar valores"** (novo na UI — só o tipo já existia): checkbox que abre um
  toggle "Definir valor final" / "Mudar multiplicador" e 4 campos (1h–4h), `MoneyInput` no modo
  valor final, `Input` numérico no modo multiplicador.
- Substituído o `<select>` de "Formato do orçamento" por um toggle de dois `Button`
  (`variant="default"`/`"outline"` conforme seleção), mesmo padrão visual dos botões +/- do
  Coordenador — sem componente novo no design system.

**Impacto em RBAC e regras de negócio.** Nenhum — mesma tela, mesmo RBAC (`COMERCIAL`,
`SUPERADMIN`), nenhuma regra de cálculo mudou no backend.

**Riscos e pegadinhas.**
- O alerta de agenda e o contador do histórico dependem de dados existentes em `manto_local` —
  verificado manualmente logado como SUPERADMIN contra um evento real do dia (BLUEY + BINGO,
  27/07/2026): o alerta apareceu corretamente com os dois personagens.
- O modo "Personalizar valores" retorna erro de campo do backend quando os 4 valores ficam em
  zero ("Informe valores válidos para o orçamento personalizado.") — comportamento esperado do
  endpoint, não um bug novo; confirmado que o erro aparece e some corretamente ao preencher um
  valor.
- Sem verificação funcional automatizada de backend nesta entrada (nenhum endpoint mudou) — só
  `npx tsc --noEmit` (limpo) e verificação manual na UI real via preview.

---

### 190 — Paridade e Unificação do Módulo de Orçamentos e EducaManto (React)
`190-paridade-orcamento-educamanto` · **2026-07-27** · **sem migration**

**Motivação.** As 6 telas do módulo de Ferramentas (Calculadora de Orçamento, Config. de Preços,
Histórico de Orçamentos, Calculadora EducaManto, Pacotes EducaManto, Histórico EducaManto) já
existiam e funcionavam, mas haviam perdido densidade visual e paridade de recursos frente à
extinta versão Jinja: listas de `Card` soltos em vez de tabelas gerenciais, filtros avançados já
suportados pelo backend mas nunca expostos na UI (`date_from`/`date_to`/`min_val`/`max_val`/
`user_id`/`has_show` no histórico de Orçamento), e — a lacuna mais importante — **nenhum dos dois
históricos tinha ação "Recalcular"**, apesar do backend já guardar o estado bruto necessário
(`OrcamentoHistory.form_snapshot`, `EducaMantoQuote.snapshot`) sem nunca expô-lo em JSON. A meta
de negócio é unificar a experiência do EducaManto com a Calculadora de Orçamento normal como
ferramentas irmãs do mesmo ecossistema, incluindo paridade de "reabrir, editar e recalcular".

**Backend.** Dois endpoints de leitura, ambos aditivos/retrocompatíveis — nenhum endpoint
existente mudou de contrato, nenhuma lógica de negócio nova (reuso de `quote_ops` já existente).
- `app/api/orcamento_read.py`: `GET /orcamento/historico/<id>` passou a incluir também
  `form_snapshot` (estado bruto de entrada, já persistido, nunca antes exposto) ao lado do
  `quote` congelado que já existia.
- `app/api/educamanto_read.py`: **novo** `GET /educamanto/historico/<id>` — retorna
  `quote_ops.load_quote_snapshot(quote)` em JSON (mesmo dado já usado internamente para regerar o
  PDF), mesmo RBAC (`_require_use`) da listagem, sem restrição por dono (paridade com o endpoint
  de PDF por id, que também não restringe por dono).

**Banco.** Sem migration — nenhuma coluna nova, nenhum model alterado.

**Frontend.**
- Fundação em `@manto/ui`: `Table`/`TableRow`/`TableCell` (convenção densa extraída de
  `PagamentosPage`/`GastosRecorrentesPage`, feature 189), `Badge` (rótulo de tom único,
  complementar ao `MetricBadge` existente) e `CopyButton` (promovido de local em
  `PagamentosPage.tsx` para fonte única).
- `OrcamentoCalculadoraPage.tsx`: layout em duas colunas, "Limpar tudo", equipe em tabela
  (Coordenador com contador +/-, "+ Ator/Cantor"/"+ Especial"), nota informativa de BV, campo de
  duração extra (`duracao_custom`, já existia no tipo mas não estava exposto na UI), painel de
  resultados em cards 1h–4h, `Dialog` "Ver memória de cálculo"; lê `?recalcular_id=` e repopula
  todos os campos a partir de `form_snapshot` (mesmo padrão de pré-fill via query param de
  `EventCreatePage.tsx`).
- `OrcamentoConfigPrecosPage.tsx`: os 8 blocos de preço viraram tabelas (`PriceTable`) — Markup,
  Cachê Atores, Cachê Cantores, Técnico/Coordenador, Especiais (uma linha por variante); "Voltar
  à calculadora" no `PageHeader`.
- `OrcamentoHistoricoPage.tsx`: tabela gerencial com todos os filtros que o hook já suportava
  (texto, data, faixa de valor, vendedor, tipo com/sem show), badge de tipo, `Dialog` "Ver"
  (substitui a expansão inline anterior), **"Criar evento"** (`/events/new?orcamento_id=` — o
  pré-fill do lado do `EventCreatePage` já existia, só faltava o link) e **"Recalcular"**
  (`/orcamento?recalcular_id=`).
- `EducaMantoCalculadoraPage.tsx`: seletor de pacote virou dropdown (era pills), layout em duas
  colunas, cards "Sem Nota Fiscal"/"Com Nota Fiscal" recoloridos (verde/azul) com Custo Base e
  Comissão do Vendedor explícitos, detalhamento de custos dentro de um `AccordionRow`
  colapsável, atalhos no cabeçalho ("Editar pacote", "+ Novo pacote"); lê `?package_id=` (vindo
  de "Usar" na tela de Pacotes) e `?recalcular_id=` (repopula a partir do novo endpoint de
  detalhe — note que o texto do endereço não é persistido no snapshot, só o km calculado, então
  o campo de endereço fica vazio no recálculo mas o km/transporte já vêm preenchidos).
- `EducaMantoPackagesPage.tsx`: lista vertical virou grade de 2–3 colunas; cada card ganhou
  margens (1S/2S/1S-dias/2S-dias), desconto formatado ("5% após N dias") e uma mini matriz de
  custos; botão novo "Usar" (`/educamanto?package_id=`, disponível a todos que veem pacotes, não
  só a quem gerencia); "Duplicar" ganhou o rótulo "Criar cópia" pedido (mesma mutation).
- `EducaMantoHistoricoPage.tsx`: lista virou tabela; "Reabrir PDF" renomeado para "Baixar PDF";
  **"Ver"** novo (`Dialog` consumindo o endpoint de detalhe novo) e **"Recalcular"** novo
  (`/educamanto?recalcular_id=`).

**Rotas e endpoints.**
- **Novo:** `GET /api/educamanto/historico/<id>`.
- **Alterado (aditivo):** `GET /api/orcamento/historico/<id>` (campo `form_snapshot` a mais).
- Rotas de página inalteradas.

**RBAC e regras de negócio.** Sem mudança de permissões. "Recalcular" sempre roda o cálculo com
as configurações de preço **atuais** (não os valores congelados no histórico) — é a mesma
calculadora reaberta com os campos preenchidos, não uma reconstrução do valor histórico exato;
para ver o valor exatamente como foi cotado, a ação é "Ver" (mostra o snapshot congelado), não
"Recalcular".

**Riscos e pegadinhas.**
- O processo do backend local (`manto-backend-local`) não recarregou a nova rota
  `/api/educamanto/historico/<id>` automaticamente apesar do reloader do Werkzeug reportar
  "Restarting with stat" — só passou a responder (401 em vez de 404) após um restart manual do
  processo. Se uma rota nova parecer "não existir" mesmo com o código correto no disco
  (confirmado lendo `app.url_map` num processo novo), suspeite do processo de dev desatualizado
  antes de suspeitar do código.
- `EducaMantoQuote.snapshot` guarda `transporte.kmT`/`label`/`pessoas`/`total`, mas **não** o
  texto do endereço digitado — "Recalcular" no EducaManto restaura o km calculado, não o campo
  de endereço em si.
- `@manto/ui` não tem um componente `Table`/`Badge` genérico antes desta feature — telas com
  tabela usavam `<table>` nativo caso a caso; os novos `Table`/`TableRow`/`TableCell`/`Badge`
  ficam disponíveis para qualquer tela futura que precise de listagem densa.
- Verificação: `npx tsc --noEmit` limpo em `frontend/apps/internal`; `ruff check` limpo nos dois
  arquivos Python tocados; fluxo completo Calculadora → Salvar → Histórico → Recalcular → Criar
  evento exercitado no navegador contra `manto_local` para os dois módulos (Orçamento e
  EducaManto), incluindo o `Dialog` "Ver" em ambos os históricos.

### 189 — Módulo Financeiro de Alta Fidelidade e Consistência (React)
`189-financeiro-alta-fidelidade` · **2026-07-27** · **sem migration**

**Motivação.** As três telas financeiras em React (`/financeiro`, `/financeiro/pagamentos`,
`/gastos/recorrentes`) haviam perdido densidade de informação e fluxos operacionais frente à
versão Jinja congelada. Especificamente: o painel financeiro virou uma pilha vertical de cards
(sem grid 2/3 + 1/3, sem termômetro de break-even, sem barra do Fator R, com a DRE achatada e
sem hierarquia); a planilha de pagamentos perdeu a **cópia rápida de PIX/valor/descrição**, a
ordem de colunas clássica e — bug operacional principal — **não tinha ação em lote para "No
banco"**, embora o backend sempre tenha suportado; e `/gastos/recorrentes` era uma lista de
cards indiferenciados, sem as três seções por tipo, sem a coluna de status do mês de referência
e sem o botão `[Preencher]` proeminente que gera o `RecurringExpenseEntry`.

**Backend.** Nenhum endpoint novo de escrita; só enriquecimento de leitura (aditivo,
retrocompatível) e uma extração para não duplicar regra de negócio.
- `app/gastos/gastos_ops.py`: **duas funções novas** — `estimate_monthly_cost(conta)` (custo
  mensal estimado, normalizando frequência: semanal ×4, quinzenal ×2, anual ÷12; variável usa o
  teto da faixa) e `recurring_summary(contas)` (`somas` por tipo + `programado_pendente_total`).
  Ambas foram **extraídas de dentro da view Jinja** `app/gastos/routes.py::recorrentes` (onde
  viviam como `_estimate`/somas inline) — a view passou a chamá-las, fonte única com a API
  (Princípio I).
- `app/api/gastos_read.py`: `_recurring_dict` ganhou parâmetros opcionais `ref_year`/`ref_month`
  e passou a serializar os rótulos derivados do model (`expected_label`, `dia_label`,
  `vigencia_label`, `parcelas_summary`), além de `estimated_monthly`, `has_entries`,
  `occurrences` (0 = "fora do ciclo") e `entries` (só para `programado`). O payload da listagem
  ganhou `ref_year`, `ref_month`, `weekday_labels`, `somas` e `programado_pendente_total`.
- `app/api/financeiro_read.py`: `kpis` ganhou `margem_bruta`, `margem_ebitda`, `tax_rate`
  (alíquota do `SiteSetting`, para o rótulo "Impostos Provisionados (16% · eventos com nota)")
  e as faixas do Fator R (`fator_r_rate_low`/`fator_r_rate_high`); cada linha de `eventos[]`
  ganhou `receita` e `event_type` (a tabela React não tinha como exibir a coluna Receita).

**Banco.** Sem migration — nenhuma coluna nova. `RecurringExpense`/`RecurringExpenseEntry` e
`SpecialExpense` seguem inalterados; toda a informação nova é derivada.

**Frontend.**
- `FinanceiroDashboardPage.tsx` **reconstruída** no layout clássico em grid: coluna principal
  (2/3) com 4 KPIs (Ticket Médio, Custo Talento/Receita, Margem Bruta, EBITDA), **termômetro de
  break-even** e **alerta fiscal do Fator R** — ambos com barra de progresso Tailwind
  (`role="progressbar"` + `aria-valuenow`) e badge de proteção tributária —, a **DRE Gerencial
  com identação hierárquica** (linhas `(–)` recuadas, subtotais `=` em faixa destacada, EBITDA e
  Resultado Líquido com régua superior) e os 3 cards de A Receber/A Pagar/Pago. Coluna analítica
  (1/3) com Receita por Tipo (barras horizontais), Top Vendedores ranqueados, Auditoria de Input,
  Notas a Emitir, Tendência de 6 meses e Recebimentos Previstos. Tabela de Eventos no Período em
  largura total, agora com Receita e Tipo.
- `PagamentosPage.tsx`: ordem de colunas do Jinja restaurada (checkbox · vencimento · descrição
  detalhada com badge de tipo · favorecido em **bold** · valor · chave PIX com tipo · situação);
  **botão compacto de cópia** ao lado da descrição, do valor (formato cru `1234,56`) e da chave
  PIX, com feedback "✓" temporário e `aria-live`; **checkbox "selecionar tudo"**; ação em lote
  **"Marcar como no banco"** (o backend já aceitava `no_banco` em `bulk-action`); seletor de
  situação colorido por estado, com as opções que cada tipo realmente suporta.
- `GastosRecorrentesPage.tsx` **refeita** em três seções tabulares (Contas Variáveis, Débito
  Automático, Assinaturas/Cartão) + Pagamentos Programados, com resumo mensal no topo, seletor
  de mês de referência e formulário de criação completo (tipo, frequência, dia/dia-da-semana,
  vigência, faixa **ou** valor exato, cartão, PIX padrão, observações). Cada linha traz
  `[Preencher]` (Dialog de `@manto/ui` com `MoneyInput`), `[Pular mês]`, `[Pagar]`/`[Reabrir]`,
  `[Histórico]` (Dialog consumindo o endpoint novo), `[Editar]` (Dialog) e
  `[Desativar]`/`[Excluir]` com confirmação em Dialog.
- `lib/financeiro.ts` e `lib/gastos.ts`: tipos estendidos (zero `any`) + hook novo
  `useRecorrenteHistorico`.

**Rotas e endpoints.**
- **Novo:** `GET /api/gastos/recorrentes/<conta_id>/historico` — todos os lançamentos da conta,
  do mais recente para o mais antigo (equivale ao painel `?conta=<id>` da tela Jinja).
- **Alterados (aditivos):** `GET /api/financeiro/dashboard` e `GET /api/gastos/recorrentes`.
- Rotas de página inalteradas.

**RBAC e regras de negócio.** Sem mudança. O endpoint novo usa o mesmo gate
`gastos_ops.is_financeiro` (FINANCEIRO/SUPERADMIN) dos demais de recorrentes; a página Jinja
legada segue funcionando (`/gastos/recorrentes` e `/financeiro/` verificados em 200 após a
extração para `gastos_ops`).

**Riscos e pegadinhas.**
- **Os status de pagamento do backend são exatamente três**: `nao_pago` ("Não pago"), `pago` e
  `no_banco` (`_VALID_PAYMENT_STATUS` em `app/api/financeiro_write.py` e `_STATUS_LABELS` em
  `app/financeiro/routes.py`). Não existem `pendente` nem `agendado` — "pendente" é o rótulo de
  UI de `nao_pago`. `commission` e `recurring` **não têm** `no_banco`: em lote o backend
  devolve o item em `skipped`, e a UI já nem oferece a opção.
- **`text-amber`/`bg-amber-soft` não existem** no preset do design system
  (`@manto/ui/tailwind-preset` tem `green`, `red`, `blue`, `gold`, `accent` — não `amber`). A
  versão anterior de `GastosRecorrentesPage` usava essas classes no alerta do topo e elas nunca
  renderizaram cor nenhuma. Estados de atenção agora usam `gold`.
- `occurrences === 0` significa **"fora do ciclo"** (fora da vigência ou da frequência no mês),
  não "sem lançamento" — sem esse campo no payload a UI teria que reimplementar
  `RecurringExpense.occurrences_in_month`, que é regra de negócio real.
- O botão `[Excluir]` da conta só aparece com `has_entries === false`; com histórico o caminho é
  desativar (`delete_recurring` levanta `GastoStateError` → 409).
- Verificação funcional: `scripts/db/verify_189_financeiro_alta_fidelidade.py` (**51/51** contra
  `manto_local`) — novos campos do dashboard, `no_banco` individual **e** em lote com persistência
  conferida no banco, resumo/rótulos/`occurrences` das recorrentes, `preencher` gerando o
  `RecurringExpenseEntry` que aparece na planilha de pagamentos, e o histórico (200/404/403).
  Fluxo completo também exercitado no navegador contra `manto_local` (criar conta → `[Preencher]`
  com máscara BRL → linha vira "a pagar R$ 512,30" → item aparece na planilha de pagamentos).

### 188 — Refatoração e Paridade do Módulo de Formulários
`188-formularios-paridade-listagem` · **2026-07-27** · **sem migration**

**Motivação.** A migração para React deixou `/formularios` com menos informação que a tela Jinja
antiga: o painel superior com os **links públicos copiáveis** havia sumido, a listagem virou uma
pilha de cards sem **Data do evento**, o "Recebida em" perdeu a **hora**, e a "Situação" caiu para
texto cinza ("Sem cliente • Sem evento") em vez dos **badges coloridos**. Esta entrada restaura a
paridade e moderniza o editor de campos.

**Backend.**
- `app/api/formularios_admin_read.py`: **`client_name` promovido do detalhe para o
  `_response_summary`** — a coluna "Situação" da listagem precisa do nome para o badge
  "Cliente: `<nome>`". `_response_detail` deixa de duplicá-lo (herda do summary).
- `app/formularios/formularios_ops.py`: `list_responses` e `search_responses` passam a fazer
  `joinedload(FormResponse.client)`. Sem isso, ler `r.client.name` em até 200 linhas geraria
  N+1 queries.
- **Correção de bug Postgres-only** em `app/gastos/gastos_ops.py::search_events_by_date`:
  `func.date(CalendarEvent.start_at) == day.isoformat()` comparava um `date` com **string** e
  estourava `psycopg.errors.UndefinedFunction: operador não existe: date = character varying`
  → `GET /api/gastos/eventos?date=...` respondia **500 em produção**. Agora compara com o próprio
  `date`. O SQLite de dev aceitava a comparação (tipagem dinâmica), então o bug nunca aparecia
  localmente. Afetava o seletor "vincular evento" **desta** tela e o da tela de Gastos Extras
  (mesmo hook `useGastosEventos`).
- Nenhum endpoint novo, nenhuma mudança de RBAC.

**Banco.** Nenhuma alteração de schema.

**Frontend.**
- `FormulariosAdminPage.tsx` reescrita: **gerenciador de links públicos** (dois cards com URL
  somente-leitura, "Copiar link" com confirmação "✓ Copiado" + `aria-live`, "Abrir" em nova aba e
  atalho SUPERADMIN para o editor); **tabela densa** com as 6 colunas da tela antiga (Contratante,
  Formulário, Data do evento, Recebida em com `DD/MM/AAAA HH:mm`, Situação, Ver); badges de
  situação via `MetricBadge` (verde resolvido / âmbar pendente); busca + abas de tipo de
  formulário; detalhe e editor em `Dialog` de `@manto/ui` (antes eram painéis inline).
- **Novo** `components/FormFieldEditor.tsx`: editor de `FormFieldDefinition` com formulário real
  (rótulo, seção com `datalist`, tipo, opções, ajuda, placeholder, obrigatório) no lugar dos
  `window.prompt()`/`window.confirm()` anteriores.
- `lib/formulariosAdmin.ts`: `client_name` no `FormResponseSummary`; `FIELD_TYPES` e
  `optionsToText()` (converte o `options` JSON do backend em texto "uma opção por linha");
  `UpdateFieldInput` explícito.
- `EventCreatePage.tsx`: aceita **`?form_response_id=<id>`** e pré-preenche pré-contrato vinculado,
  data do evento e cliente associado — reusando `GET /api/formularios/respostas/<id>` (mesmo RBAC),
  sem endpoint novo.

**Princípio V (nenhum botão morto).** Todo disparador de mutation desta tela dá retorno visual:
`Button loading` em associar/desassociar/vincular/desvincular/salvar/excluir; nas linhas de
resultado da busca de cliente e nas setas ↑/↓ do editor, o estado usa `mutation.variables` para
que **só o item clicado** fique em spinner (e não a lista inteira); o `<select>` de evento — que é
o próprio gatilho da ação — trava e troca o rótulo para "Vinculando…" enquanto o vínculo está em
voo. "Copiar link" não é assíncrono: confirma inline com "✓ Copiado" + `aria-live`.

**RBAC e regras de negócio.** Inalterados. Respostas seguem em `_require_vendas()`
(COMERCIAL/FINANCEIRO/SUPERADMIN) e o editor em `_require_superadmin()`; a UI só espelha o
`can_edit_structure`/`is_superadmin` que o servidor já devolve.

**Rotas e endpoints.** Nenhum novo. `/formularios` mantém a rota; `/events/new` ganha o parâmetro
opcional `form_response_id` (o `orcamento_id` continua funcionando igual).

**Riscos e pegadinhas.**
- **`update_field` substitui, não faz merge**: omitir `help_text`/`placeholder`/`required` no PATCH
  **apaga** esses atributos. A versão anterior da tela mandava só `label` + `required` num
  `window.prompt()` e silenciosamente limpava ajuda/placeholder do campo. O editor novo sempre
  envia o payload completo.
- `field_type` e `section_name` são **imutáveis** após a criação (o backend nunca os altera) — o
  formulário de edição os desabilita e explica o porquê.
- Os links dos cards usam `window.location.origin` + `/catalogo/f/<slug>`, que só resolve no build
  de produção (onde `frontend/server.js` serve `apps/public` sob `/catalogo/*`). No dev server do
  `apps/internal` (:5173) o link abre um 404 da SPA — esperado, não é regressão.
- **`func.date(coluna) == <str>` é bomba-relógio neste repo**: passa no SQLite e explode no
  Postgres. Ao escrever qualquer filtro por dia, compare com o objeto `date` — e verifique contra
  `manto_local`, nunca contra o SQLite de `instance/` (regra do `CLAUDE.md`). Foi assim que o 500
  do `/api/gastos/eventos` apareceu: só ao exercitar o seletor de evento contra o Postgres local.
- Verificação funcional: `scripts/db/verify_formularios_listagem_paridade.py` (20/20 contra
  `manto_local`) — cobre `client_name` em listagem/busca/detalhe, `event_date`/`created_at`
  serializados e o RBAC dos três endpoints. O 500 do `/api/gastos/eventos` foi confirmado
  (e a correção validada) direto contra `manto_local`: 2026-08-22 → 3 eventos, 2026-08-15 → 1.

### 187 — Reestruturação do Módulo de Comissões
`187-comissoes-modulo-completo` · merge **2026-07-24** (`4c20e47`) · **sem migration**

**Motivação.** A tela `/financeiro/comissoes` misturava a visão do vendedor com a do financeiro,
dependia do cliente para restringir escopo e sofria de dessincronização ao marcar comissões como
pagas uma a uma.

**Backend.**
- Novo módulo de núcleo de negócio **`app/financeiro/comissoes_ops.py`** (385 linhas): dataclasses
  `CommissionEntry`, `CommissionKpis`, `CommissionMonthSummaryRow`, `PayoutResult`; funções
  `parse_month_strict`, `resolve_month`, `get_month_entries`, `get_month_summary_by_seller`,
  `get_month_kpis`, `pay_seller_month`. Exceções próprias `InvalidMonthError` e
  `SellerNotFoundError`.
- `GET /api/financeiro/comissoes` reescrito: devolve `month`, `can_manage`, `title`, `kpis`,
  `by_seller`, `entries` e (só para gestor) `sellers`. Continua chamando
  `_resync_pending_commissions()` de `app/financeiro/routes.py` para não duplicar a reconciliação.
- **Novo** `POST /api/financeiro/comissoes/pagar-mes` — liquidação em lote atômica por
  vendedor/mês, com `SELECT ... FOR UPDATE` (`with_for_update()`) sobre os registros elegíveis.
  Duas chamadas concorrentes (duplo clique / duas abas): a segunda espera a primeira commitar,
  relê o estado, encontra 0 elegíveis e reporta `changed_count = 0` — **idempotente, nunca paga
  duas vezes**. Registra `audit("payment", "commission_month", ...)`.
- Decisão explícita: `app/financeiro/routes.py` (Jinja legado) **não** foi tocado e **não**
  importa `comissoes_ops` — mantém sua própria cópia de `_bulk_set_commission_period`.

**Banco.** Nenhuma alteração de schema. `CommissionPayment` já tinha tudo que era necessário
(`status`, `paid_at`, `payable_from`, `original_id`, `amount` assinado).

**Frontend.**
- `ComissoesPage.tsx` reconstruída (~464 linhas alteradas): 3 cards de KPI, seletor de mês,
  **duas abas** (Resumo por Vendedor / Detalhamento de Vendas), accordion por vendedor, modal de
  confirmação com o valor somado no servidor, e **export CSV** do resumo.
- Três componentes novos em `@manto/ui`: **`AccordionRow`**, **`Dialog`** e **`Tabs`**.

**RBAC e regras de negócio.**
- **O servidor decide o escopo**: `seller_filter = requested_seller_id if can_manage else
  current_user.id`. Vendedor comum nunca recebe dados de outro, mesmo forçando `seller_id` na
  querystring.
- `can_manage` = `FINANCEIRO` ou `SUPERADMIN`. Título muda para **"Minhas Comissões"** quando
  falso, e nenhuma ação de pagamento é renderizada.
- O **responsável EducaManto** sem papel Financeiro continua sendo vendedor comum nesta tela.
- `pagar-mes` responde **403** para não-gestor, inclusive para o próprio `seller_id`.
- **Estornos** (`amount < 0`, `status='a_pagar'`) aparecem em **qualquer mês** até serem resolvidos
  (`_pending_reversals_query`, sem filtro de mês, deduplicado por `id`) e só são liquidados junto
  com as demais comissões do vendedor — nunca isoladamente.
- KPIs derivam do **mesmo** resumo que alimenta o botão "Pagar Mês", garantindo que batem centavo
  a centavo com o que pode ser efetivamente liquidado.

**Pegadinhas.** Mês inválido cai silenciosamente no mês corrente em `resolve_month` (leitura), mas
`pay_seller_month` usa `parse_month_strict` e **falha** — a escrita nunca adivinha o mês.

---

### 186 — Gerenciador de Catálogo: UX e fluxo Ficha ↔ Catálogo ↔ Venda
`186-gerenciador-catalogo-ux` · merge **2026-07-24** (`31310d3`) · **sem migration**

**Motivação.** A 185 entregou a estrutura Tema/Personagem funcional, mas "cega": a busca de elenco
mostrava só nome, o vínculo com a Ficha de Figurino só existia por um lado, e não havia forma de
tratar em lote o acervo antigo sem vínculo.

**Backend.**
- `GET /api/catalogo/elenco-busca` passou a servir também o lado da Ficha: gate ampliado para
  `COMERCIAL`, `FIGURINO` e `SUPERADMIN` (antes era só o fluxo comercial), incluindo `photo_url` e
  `figurino_sheet_id` de cada Personagem — dado interno, por isso fora da grade pública.
- **Novo** `POST /api/admin/catalogo/personagens/mover-em-massa` +
  `catalog_character_ops.move_characters(character_ids, target_item)`.
- `admin_catalogo_read` passou a expor o indicador de vínculo pendente por Personagem.

**Banco.** Nenhuma alteração. **Decisão de projeto**: o vínculo bidirecional reusa a coluna
existente **`catalog_characters.figurino_sheet_id`** — não há coluna espelho em `figurino_sheets`;
o "personagem vinculado" de uma ficha é derivado por busca inversa.

**Frontend.**
- **`CharacterAutocomplete`** — busca visual com miniatura, filtrada para **Personagens filhos
  ativos** (Temas pai nunca aparecem); placeholder quando não há foto; ao selecionar preenche nome
  e `figurino_sheet_id` na linha do elenco.
- **`CatalogTreeView`** (árvore hierárquica Tema → Personagens, com guia de recuo),
  **`CatalogCardGrid`**, **`KebabMenu`** e **`CatalogBulkActionBar`** (barra flutuante de ações em
  massa: Mover para… / Inativar / Excluir; "Mover" só existe para Personagens).
- `/admin/catalogo`: alternador **Cards ⇄ Árvore** persistido em `localStorage`
  (`manto_admin_catalogo_view`), seleção múltipla, e associação rápida "+ Vincular Ficha".
- `FigurinoFormPage`: campo **"Vincular a um Personagem do Catálogo"** com Desvincular.
- `FigurinoListPage`: indicador **"⚠ Sem personagem vinculado"** + modal de vínculo em 2 cliques.
- **US6 — deploy**: `frontend/server.js` novo (serve `apps/internal/dist` na raiz e
  `apps/public/dist` sob `/catalogo/*`, cada um com seu fallback de SPA), `base` condicional em
  `apps/public/vite.config.ts`, `basename` condicional em `apps/public/src/App.tsx`,
  `frontend/nixpacks.toml` passando a compilar os **dois** apps, e correção do link "/catalogo" no
  menu lateral.

**RBAC.** Gerenciador continua exclusivo de `SUPERADMIN`. A exceção é `elenco-busca`, aberta
também a `COMERCIAL` e `FIGURINO` — comercial escala evento e figurino vincula ficha sem ser
superadmin.

**Regras de negócio.** Um Personagem aponta para **no máximo uma** Ficha por vez: vincular pelo
lado da Ficha **substitui** o vínculo anterior, nunca duplica.

**Pegadinhas.** Um *Build/Start Command* customizado no painel do Railway tem precedência sobre o
`nixpacks.toml` — foi exatamente um build command com sintaxe de Turborepo/pnpm que causou o erro
"Missing script: build". Os dois campos precisam ficar vazios.

---

### 185 — Catálogo Vitrine Completo: Temas, Personagens e Vídeo
`185-catalogo-vitrine-completo` · merge **2026-07-24** (`17e6e11`, + fix `528e561`) ·
migration **`9f1c3a7b5e2d`**

**Motivação.** O catálogo só suportava fotos e tratava cada produto como uma unidade indivisível —
invisível para o cliente que um Tema é composto por atrações individuais também contratáveis.

**Banco (migration `9f1c3a7b5e2d` — head atual).**
- **Nova tabela `catalog_characters`**: `catalog_item_id` (FK → `catalog_items`, **ON DELETE
  CASCADE**), `name`, `slug` (unique, prefixado pelo slug do Tema), `photo_url`, `video_url`,
  **`figurino_sheet_id`** (FK → `figurino_sheets`, **ON DELETE SET NULL**), `position`,
  `is_active`, `created_at`; índice `ix_catalog_characters_catalog_item_id`.
- **Nova coluna `catalog_items.video_url`** (Drive/MP4/Vimeo).

**Backend.**
- Novo `app/admin/catalog_character_ops.py`: `unique_character_slug`, `create_character`,
  `update_character`, `delete_character`, `_validate_video_url`, `_validate_photo_extension`.
- Novo `app/catalogo/media.py` (normalização/detecção do tipo de vídeo).
- Endpoints novos: `POST /api/admin/catalogo/<item_id>/personagens`,
  `PATCH|DELETE /api/admin/catalogo/personagens/<character_id>`,
  `GET /api/admin/catalogo/tags`, `GET /api/catalogo/elenco-busca`.
  `GET /api/catalogo/<slug>` passou a devolver `video_url`, `video_kind` e o elenco de Personagens.

**Frontend.**
- **Público**: `VideoPlayer` (autoplay mudo em loop, botões próprios de som e tela cheia),
  `ProductGallery` com **transição animada de altura** entre foto horizontal e vídeo 9:16,
  `CharacterCard`/`CharacterGrid` para a seção **"Elenco Individual"**, `WishlistButton` por
  Personagem. Vídeo inválido é ignorado silenciosamente na vitrine.
- **Interno**: `ChipInput` (tags com Enter/vírgula, autocomplete das tags existentes),
  `AdminCatalogCharacterPanel` (CRUD de Personagens com foto, vídeo e dropdown de Ficha de
  Figurino), `ElencoBlock` do Novo Evento passando a auto-vincular a ficha do Personagem
  selecionado.
- Suíte E2E nova para catálogo público e admin; `verify_185.py` de verificação funcional.

**Regras de negócio.**
- URL de vídeo não reconhecida (não é Drive/MP4/Vimeo) é **recusada com erro no campo** no
  gerenciador.
- Excluir um Tema **apaga em cascata** seus Personagens; excluir uma Ficha **apenas desvincula**
  (`SET NULL`), sem apagar o Personagem.
- A lista de interesse do cliente aceita Tema completo **e** Personagem individual como itens
  distintos.

**Fix pós-merge (`528e561`).** Alvo de toque do botão "copiar link do Personagem" no mobile.

---

### 184 — Reconstrução do Formulário de Cadastro/Edição de Eventos
`184-eventos-formulario-completo` · merge **2026-07-24** (`1da7be6`) · **sem migration**

**Motivação.** `/events/new` no app React não tinha paridade de campos com a tela Jinja em
produção, forçando o vendedor a voltar para a tela antiga — risco real de dado divergente na tela
mais crítica do comercial. E a edição estava espalhada em várias ações soltas na tela de detalhe.

**Backend.**
- `app/calendar/event_ops.py` ampliado (+255 linhas): `update_event_core` e a reconciliação de
  elenco por `role_id`.
- `POST /api/events` e **`PATCH /api/events/<id>`** cobrindo os 7 blocos; `_build_create_event_data`
  / `_build_update_event_data` normalizam o corpo JSON. Validação central via `_validate_event_core`,
  devolvendo **`fields`** no envelope de erro para o formulário apontar o campo exato.
- `agenda_read.py` passou a serializar os campos que faltavam para pré-preencher a edição.
- Falha ao criar o evento no Google Calendar devolve **502** com mensagem amigável.

**Banco.** Nenhuma alteração — a feature foi de paridade e UX sobre o schema existente.

**Frontend.**
- `EventCreatePage.tsx` reescrita (982 linhas alteradas) e **`EventEditPage.tsx` nova** (489
  linhas), ambas montadas sobre **7 blocos** compartilhados em
  `src/components/EventFormBlocks/`: Cliente · Dados do Evento · Elenco · Valores · Pagamento ·
  Contrato · Observações.
- `eventFormSchema.ts` novo: validação `onBlur` imediata, banner de erro no topo **e** no rodapé,
  **auto-scroll suave até o primeiro campo inválido com foco**, e limpeza do destaque assim que o
  campo é corrigido.
- `ClientPicker` ganhou **cadastro rápido inline** (reaproveita cliente existente por telefone) e
  seletor de relação (Contratante/Assessora/Mãe-Pai/Familiar/Outros).
- `PendingAttachmentsPanel` novo: anexos escolhidos antes do evento existir sobem em **fase 2**,
  após a criação.
- Rota `/events/:id/edit` registrada no `App.tsx`; suíte E2E `event-form.spec.ts`.

**RBAC.** `_can_create_event()` / `_can_edit_event()` = `COMERCIAL` + `SUPERADMIN`, com paridade
verificada contra `_CAN_CREATE` / `_CAN_EDIT_EVENT` do Jinja. Acesso direto à URL de edição por
papel sem permissão (ex.: `ENSAIO`) é bloqueado no servidor.

**Regras de negócio confirmadas na tela.**
- Evento tipo **SHOW sempre gera ensaio**, independentemente do checkbox (o aviso é explícito).
- Percentual de desconto = `sale_value_gross − sale_value`, calculado em tempo real.
- *Faturado* exige vencimento; *Dividido no PIX* exige parcelas entre **2 e 12**.
- Fora de cortesia/permuta, os dois valores de venda são obrigatórios.
- Horário de fim não pode ser igual ao de início.
- Na edição, o elenco é **reconciliado** por `role_id` (não substituído), e agrupamento comercial
  / sincronização com o Google não são alterados pela feature.

---

### Contexto imediatamente anterior (para leitura do histórico)

| Feature | Entrega | Migration |
|---|---|---|
| **183** | Reestruturação do Banco de Figurinos — tags JSON na ficha, alerta "personagem sem ficha" com dispensa rastreável (`figurino_missing_dismissals`), impressão legada linkada da SPA | `7c2d9e4f1a3b`, `4e6f8a1c2d5b` |
| **182** | Revisão de mídia com Vimeo; correção do proxy Vite de `/uploads` | `aa1bb2cc3dd4` |
| **181** | Avaliações — fidelidade visual e RBAC | — |
| **180** | Módulo de Talentos completo (modo edição unificado em `/talents/:id?edit=1`) | — |
| **144** | Migração React SPA concluída (constituição v2.0.0) — fatias 145–177 | — |

**Correção pontual pós-187** — `6d6e234` (2026-07-25, branch `fix-figurino-nova-ficha-foto`):
completa o formulário de **Nova Ficha** de figurino (foto, textos de apoio, obrigatoriedade do
nome do personagem). Só frontend, sem impacto de schema, API ou RBAC.

---

## Convenções para as próximas entradas

1. **Append no topo** da seção "Registro", nunca no fim.
2. Sempre declarar **se houve migration** (e qual `revision`) — ou "sem migration", explicitamente.
3. Sempre declarar **impacto em RBAC**, mesmo quando for "nenhum".
4. Rotas novas ou alteradas precisam também ser refletidas em
   [`01_SISTEMA_E_BANCO.md`](01_SISTEMA_E_BANCO.md) §3 e, se tiverem tela,
   em [`02_MAPA_DE_PAGINAS_E_UX.md`](02_MAPA_DE_PAGINAS_E_UX.md).
5. Registrar **pegadinhas** descobertas na implementação — é a parte do documento que mais evita
   retrabalho.
