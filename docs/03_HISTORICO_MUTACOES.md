# 03 — Histórico de Mutações

> **Documento vivo — APPEND ONLY.** Cada feature concluída adiciona uma entrada **no topo** da
> seção "Registro". Nunca reescrever entradas antigas (elas são o histórico); correções entram
> como nova entrada referenciando a anterior.
>
> Última atualização: **2026-07-27** · Estado do repositório: pós-feature **188**

Formato de cada entrada:

```
## <NNN> — <título>            (branch · data do merge · migration)
Motivação · O que mudou (Backend / Banco / Frontend) · Impacto em RBAC e regras de negócio ·
Rotas e endpoints novos/alterados · Riscos e pegadinhas
```

---

## Registro

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
