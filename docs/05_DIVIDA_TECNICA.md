# 05 — Dívida Técnica

> Achados de uma auditoria de leitura de 2026-08-06 sobre ~44k linhas de Python e ~46k de TypeScript,
> priorizados por **impacto**, não por elegância. Cada item tem `arquivo:linha` e uma ação concreta.
>
> **Como usar:** os itens **P0** e **P1** produzem número errado ou botão que não faz nada **hoje** —
> trate-os antes de qualquer refactor. Os itens da §9 são grandes demais para uma sessão e vêm com
> plano de fatiamento. Nenhum item aqui é hipótese: todos foram lidos no código.
>
> Notas de escala: `app/models.py` 2.577 l. · `app/calendar/routes.py` 3.910 l. ·
> `app/marketing/virtuais_ops.py` 2.325 l. · `app/financeiro/routes.py` 1.690 l. ·
> `frontend/apps/internal/src/pages/GastosRecorrentesPage.tsx` 1.392 l.

---

## 1. Resumo priorizado

| # | Prio | Onde | Sintoma para o usuário | Tamanho |
|---|---|---|---|---|
| 1 | **P0** | `app/financeiro/routes.py:1245` + `app/api/financeiro_write.py:213` | marcar comissão EducaManto como paga não faz nada | 2 linhas |
| 2 | **P0** | `frontend/.../lib/financeiro.ts:386` | Comissões, Gastos Recorrentes e Dashboard ficam com número velho após pagar | ~20 linhas |
| 3 | **P0** | `frontend/.../lib/gastos.ts:324` | histórico da conta recorrente não atualiza | 1 chave |
| 4 | **P0** | `frontend/.../lib/useAuth.ts:13` + `navigation.tsx:76` | "Ver como REVENDEDOR" cai numa tela que o servidor recusa | ~10 linhas |
| 5 | **P1** | `app/api/agenda_read.py:245` + `app/calendar/routes.py:1752` | comissão exibida no evento ≠ comissão que o Financeiro paga | ~40 linhas |
| 6 | **P1** | `app/calendar/event_ops.py:299` e `:490` | evento com venda preenchida depois nunca gera linha de comissão | ~5 linhas |
| 7 | **P1** | `app/api/agenda_write.py:926` e `:995` | Figurino/Casting podem registrar pagamento de cachê e reembolso | ~4 linhas |
| 8 | **P1** | `app/api/orcamento_read.py:30` vs `clientes_read.py:24` | `_require_vendas` com dois significados; FINANCEIRO passa ou não conforme o arquivo | ~30 linhas |
| 9 | **P1** | `app/api/` (12 cópias) | "Ver como" é respeitado na agenda e ignorado em clientes/financeiro/admin | ~40 linhas |
| 10 | **P2** | `app/financeiro/routes.py:120` | núcleo de cálculo dentro de arquivo de rotas Jinja | §9.2 |
| 11 | **P2** | `app/calendar/routes.py` | 39 símbolos privados exportados para 10 módulos | §9.1 |
| 12 | **P2** | `app/calendar/routes.py:349` + `app/talent_portal/routes.py` | ~2.600 l. de superfície Jinja inalcançável, mas viva pelo host do Flask | §9.3 |
| 13 | **P2** | `app/api/agenda_write.py:396` | evento agrupado é **inexcluível** pelo produto | ~60 linhas |
| 14 | **P3** | 18 arquivos | `_has_role` copiado byte a byte | ~40 linhas |
| 15 | **P3** | `app/api/financeiro_write.py:52` | `set_payment_status` duplicada linha a linha | ~150 linhas |
| 16 | **P3** | 6 pontos | `except Exception` sem log, contra regra explícita | ~12 linhas |
| 17 | **P4** | `app/calendar/routes.py:2424`, `:2365` | código morto puro | apagar |
| 18 | **P5** | `app/models.py` | 13 models centrais sem docstring; dois fusos sem anotação | §7 |
| 19 | **P5** | `app/api/` | 288 endpoints, **1** com contrato JSON documentado | §7 |
| 20 | **P5** | raiz + `.claude/skills/` | 3 fontes de instrução concorrentes e erradas | §10 |

---

## 2. P0 — bugs ativos

### 2.1 Comissão EducaManto não pode ser marcada como paga

`app/financeiro/routes.py:1245-1247` e `app/api/financeiro_write.py:213-215`.

O item agregado da Planilha de Pagamentos é montado pelo ciclo `coalesce(payable_from, sale_date)`
(`routes.py:1029` — regra da feature 109: comissão EducaManto entra pela data de **realização**). Mas
a marcação de pago filtra só por `sale_date`. Comissão vendida em janeiro com evento em março aparece
no ciclo de março e, ao ser marcada como paga, o filtro busca `sale_date` em março: **0 linhas
atualizadas**. O botão clica e nada muda.

**Ação:** usar `db.func.coalesce(CommissionPayment.payable_from, CommissionPayment.sale_date)` também
nos dois filtros. Melhor: extrair um `_ciclo_comissao()` que devolva a expressão, para as três
consultas não poderem divergir de novo.

### 2.2 Mutação de pagamento invalida um cache de quatro

`frontend/apps/internal/src/lib/financeiro.ts:386` (`useSetPaymentStatus`, `useBulkPaymentAction`) e
`:285` (`usePagarMesComissao`, problema simétrico).

As mutações invalidam apenas `["financeiro-pagamentos", month]`. Mas o endpoint
`/api/financeiro/pagamentos/set-status` é **poliforme**: grava `CommissionPayment.status`
(`app/api/financeiro_write.py:81-99`) e `RecurringExpenseEntry.status` (`:102-124`). As telas
Comissões (`financeiro.ts:254`), Gastos Recorrentes (`gastos.ts:279`) e Dashboard Financeiro
(`financeiro.ts:188`) nunca são invalidadas. Com `staleTime: 30_000` e
`refetchOnWindowFocus: false` (`packages/api-client/src/queryClient.ts:20-21`), **o dado errado
persiste em tela**.

**Ação:** extrair `invalidarFinanceiro(queryClient)` em `lib/financeiro.ts` invalidando o conjunto
completo, e chamá-lo nas três mutações.

### 2.3 Histórico da conta recorrente nunca invalida

`frontend/apps/internal/src/lib/gastos.ts:324` invalida `["gastos-recorrentes"]`, mas o histórico usa
a chave **irmã** `["gastos-recorrentes-historico", contaId]` (`:299`) — não é prefixo, não é
alcançada. Com o `HistoricoDialog` aberto (`GastosRecorrentesPage.tsx:799`), pagar/pular/reabrir/
excluir não atualiza a lista.

**Ação:** renomear para `["gastos-recorrentes", "historico", contaId]` (vira filha e passa a ser
alcançada), estabelecendo de quebra a convenção hierárquica de chave para o resto do app.

### 2.4 "Ver como" leva a uma tela que o servidor recusa

`isRevendedorOnly` existe duas vezes com semânticas diferentes:
`frontend/apps/internal/src/lib/useAuth.ts:13` olha `user.roles` (papéis reais);
`lib/navigation.tsx:76` olha `effectiveRoles(user)` (respeita impersonação). Um SUPERADMIN com "Ver
como REVENDEDOR_EDUCAMANTO" tem a Home escondida na barra lateral (`navigation.tsx:87`), mas
`HomeOuAgenda` (`App.tsx:74`) usa a versão de `useAuth`, vê `[SUPERADMIN]`, devolve `false` e
renderiza a `DashboardPage` — cujo endpoint o servidor recusa sob o papel simulado. A própria
docstring de `App.tsx:66-70` diz que o objetivo era evitar "um painel vazio de erro".

**Ação:** apagar a cópia de `navigation.tsx:76` e exportar `effectiveRoles`/`isRevendedorOnly` de
`useAuth.ts` como fonte única, com a versão que respeita impersonação — é a que o servidor aplica em
`_role_flags` (`app/api/agenda_read.py:127-133`).

---

## 3. P1 — divergências de regra

### 3.0 ~~Avaliável mas invisível~~ — RESOLVIDO na feature 230

O portal exigia `invite_status="accepted"` para listar evento, enquanto a planilha de pagamentos
paga por **cargo atribuído** (`_pagamentos_query` não olha o convite) e a tela de avaliação já
aceitava qualquer escalação não recusada. Três definições diferentes de "esse trabalho é seu".

Consequências medidas antes da correção (espelho de 08/08/2026): 26 cargos **futuros** e 97
**passados** invisíveis no portal, ~39 talentos, R$ 36.910 que o financeiro paga e o artista não
via — incluindo cargo já **pago**. E o crachá de avaliar contava 11 eventos que nenhuma lista
mostrava.

A 230 fez o portal seguir a escala (`portal_ops.nao_recusada()`, fonte única das três consultas).
Convites continua listando só `pending`, que é o que precisa de resposta.

### 3.1 Quatro fórmulas de comissão

A regra completa está em `app/financeiro/routes.py:120` (9 ramos — ver `docs/04` §2). As outras três:

| Onde | O que ignora |
|---|---|
| `app/api/agenda_read.py:245` (`_compute_kpi`) | EducaManto (5% sobre lucro), zeramento da Loja Virtual, `receives_commission`; usa **2%** de padrão contra `DEFAULT_COMMISSION = 2.5` |
| `app/calendar/routes.py:1752` (dentro de `event_detail`) | idem |
| `app/financeiro/comissoes_ops.py:183` | filtro SQL, versão parcial por construção |

**Ação:** fazer `_compute_kpi` e `event_detail` chamarem `_event_commission(event, settings)`;
eliminar o literal `2` dos dois pontos em favor da constante única.

### 3.2 Comissão não nasce quando a venda é preenchida depois

`_sync_commission_payment` é chamada pelo handler Jinja (`app/calendar/routes.py:914`) e por
`_create_event_core` (`:3350`), mas **não** por `event_ops.update_event_comercial` (`:490`, usado por
`PATCH /api/events/<id>/comercial`) nem por `update_event_core` (`:299`). O paliativo
`_resync_pending_commissions` (`app/financeiro/routes.py:211`) itera apenas linhas já existentes com
status `a_pagar` — **não cria linha faltante**.

**Ação:** chamar `_sync_commission_payment` dentro das duas funções de `event_ops` (ou, melhor, mover
a chamada para um único ponto de commit do evento) e cobrir com script de verificação; depois remover
a chamada duplicada do handler Jinja.

### 3.3 RBAC largo demais em escrita financeira

`POST /api/events/<id>/payments` (`app/api/agenda_write.py:926`) e
`POST /api/events/<id>/reimbursements` (`:995`) usam `_can_edit_event()`, que resolve para
`_CAN_EDIT_EVENT = {CASTING, FIGURINO, COMERCIAL, FINANCEIRO, SUPERADMIN}`
(`app/calendar/routes.py:51`). Quem é só de Figurino ou só de Casting pode registrar comprovante de
pagamento de cachê e reembolso a cobrar da cliente. As próprias docstrings assumem que o gate veio do
dispatcher grosso do Jinja — nunca foi pensado para essas ações.

**Ação:** trocar pelo gate financeiro explícito (`_can_manage_sale`, `agenda_write.py:52`) e
justificar na docstring **pelo risco da ação**, não por paridade com o Jinja.

### 3.4 `_require_vendas` com dois significados

`app/api/orcamento_read.py:30` = `{COMERCIAL, SUPERADMIN}`; `clientes_read.py:24`,
`clientes_write.py:25`, `formularios_admin_read.py:24` = `{COMERCIAL, FINANCEIRO, SUPERADMIN}`. Lendo
`denied = _require_vendas()` dentro de uma view é **impossível** saber se FINANCEIRO passa.

**Ação:** mover os gates para um `app/api/rbac.py` único com nomes que digam o conjunto
(`require_comercial_ou_superadmin()`, `require_vendas_e_financeiro()`). Nenhum gate deve ser
redefinido por arquivo.

### 3.5 Impersonação respeitada só em metade do sistema

`session['impersonate_role']` é consultado em `app/api/agenda.py:138`, `agenda_write.py:85`/`:585`,
`dashboard.py:23` e `auth.py:38` — e **ignorado** pelas ~12 cópias de `_has_role` em `app/api/`
(`admin_catalogo_read:18`, `admin_catalogo_write:18`, `admin_config_read:21`, `admin_config_write:20`,
`admin_users_read:20`, `admin_users_write:20`, `catalogo_read:227`, `clientes_read:19`,
`clientes_write:20`, `financeiro_read:43`, `financeiro_write:39`, `formularios_admin_read:19`,
`orcamento_read:25`).

**Ação:** mover para `app/api_utils.py` um par `has_role(*names)` / `effective_roles()` com docstring
declarando explicitamente o tratamento da impersonação. **Se a divergência for intencional, ela
precisa estar escrita.**

---

## 4. P2 — inversões de arquitetura

Ver §9 para as duas grandes (calendar e financeiro). Aqui, a de tamanho tratável:

### 4.1 Evento agrupado é inexcluível

`_delete_event_flow` (`app/calendar/routes.py:3743`) recusa excluir líder de grupo e manda
"desagrupar antes"; `api_delete_event` traduz num 409 com a mesma mensagem
(`app/api/agenda_write.py:396`). Mas agrupar/desagrupar/renomear grupo existe **apenas** nos handlers
Jinja (`routes.py:1484`, `:1537`, `:1564`) — não há endpoint em `app/api/` nem tela no SPA. A leitura
de grupo, essa sim, continua ativa (`agenda_read.py:247`, `financeiro_read.py:392`).

**Ação:** decidir explicitamente — ou expor `POST /api/events/<id>/agrupar` +
`DELETE /api/events/<id>/grupo` com a UI correspondente, ou remover a regra de grupo do fluxo de
exclusão. **Documentar a decisão no docstring de `_delete_event_flow`.**

### 4.2 Dependências apontando para o lado errado

| Sintoma | Onde | Ação |
|---|---|---|
| Precificação de orçamento dentro do módulo de calendário | `_compute_performer_caches`, `app/calendar/routes.py:2682` (134 l.); `app/orcamento/pricing.py:13` cita ela na docstring | mover para `app/orcamento/pricing.py` (ou um `pricing_elenco.py`) |
| Regra de auto-vínculo importada como **função privada** | `app/api/formularios_write.py:19` importa `_attempt_auto_link` de `app/formularios/routes.py:246`; `calendar/sync.py:91` e `app/cli.py:56` importam `retry_auto_link_pending` | mover para `formularios_ops.py` como `tentar_vincular_evento()` / `reprocessar_vinculos_pendentes()` |
| Parser do Google Docs dentro de arquivo de rotas | `_sync_normalize`/`_sync_extract_name`/`_sync_extract_pieces`/`_sync_save_photo`, `app/figurino/routes.py:272-351` | mover para `drive_service.py` (I/O) ou `figurino_ops.py` (regra); deixar `sync_drive_stream` só orquestrando o SSE |
| View Jinja ignora o ops que existe | `list_talents` (`app/talents/routes.py:39`, 153 l.) faz query direta; `talent_ops.get_talent_profile` (`:202`) existe e não é usada | mover agregações para `talent_ops.list_talents_overview()` |
| Re-export só para não quebrar import antigo | `ensure_recurring_entries`/`recurring_alerts` moram em `gastos_ops.py:445`/`:482` mas 5 pontos importam de `app.gastos.routes` (`financeiro/routes.py:447` e `:1172`, `api/financeiro_read.py:211` e `:655`, `api/dashboard_service.py:458`) | trocar os 5 imports e remover o re-export (`routes.py:28`) — substituição mecânica, sem risco |

---

## 5. P3 — duplicação

| O quê | Cópias | Ação |
|---|---|---|
| `_has_role` (3 linhas) | **18** arquivos (13 em `app/api/` + `clientes/routes.py:29`, `feedback/routes.py:38`, `financeiro/routes.py:33`, `formularios/routes.py:90`, `revisao/review_ops.py:57`) | `has_role(*names)` em `app/api_utils.py` (versão `current_user`) + `user_has_role(user, *names)` em `app/utils.py` (versão explícita, para os ops puros) |
| `set_payment_status` | `app/financeiro/routes.py:1206` (108 l.) ↔ `app/api/financeiro_write.py:52` (139 l.), árvore idêntica de 6 tipos de item | `financeiro_ops.aplicar_status_pagamento(item_type, item_id, status, *, sufixo_auditoria)`. **Corrigir já** o docstring de `financeiro_write.py:3`, que afirma "Reusa, sem duplicar" |
| `_bulk_set_commission_period` | `routes.py:1416` ↔ `financeiro_write.py:200`, corpos idênticos | idem |
| "é venda da Loja Virtual?" | 4 (`vendas_ops.py:192`, `calendar/routes.py:2138`, `comissoes_ops.py:166` SQL, inline em `agenda_read.py:46` e `:606`) | manter `vendas_ops.is_loja_virtual` (Python) e `_sem_loja_virtual` (SQL); os outros delegam |
| Validador de senha do portal | 3 (`talent_portal/routes.py:52`, `:183`, `portal_account_ops.py:36`) com mensagens diferentes | fonte única `PASSWORD_RULES`; ver §9.3 |
| `_not_rejected` | 3 (`talent_portal/routes.py:286`, `portal_ops.py:95`, `portal_rating_ops.py:68`) | idem |
| `brl()` no frontend | **13** páginas, assinaturas já divergentes (`number` vs `number \| null`, fallback `'—'` vs `'R$ 0,00'`) | exportar `formatBRLPrefixado` de `@manto/money` e apagar as 13 |
| `formatDate`/`formatDateTime` | **16** lugares, apesar de `formatShortDate` existir em `@manto/ui` (`lib/date.ts:35`) | trocar pelos de `@manto/ui`, acrescentando `formatShortDateTime` lá |
| `const INPUT` / `const LABEL` | **25** arquivos, com alturas já divergentes (h-9, h-10, h-11) contra o `<Input>` h-11 do design system (`packages/ui/src/components/input.tsx:16-24`) | promover `apps/portal/src/components/FormField.tsx:11` para `@manto/ui` e substituir; h-9 vira variante `size="sm"` |
| `PaymentStatus` | declarado 2× no mesmo app com conjuntos **diferentes**: `lib/agenda.ts:108` (4 valores) e `lib/financeiro.ts:317` (3) | renomear para `RolePaymentStatus` e `PlanilhaPaymentStatus`, citando o módulo Python de cada um |

---

## 6. P4 — código morto e instruções mortas

| Item | Onde | Ação |
|---|---|---|
| `travel_estimate` (51 l.) | `app/calendar/routes.py:2424` — perdeu o decorator, sem chamador; a que roda é `_fetch_travel_data` (`:2377`) | apagar e corrigir a referência de `agenda_read.py:444` |
| `_is_outside_sp` | `app/calendar/routes.py:2365` — sem referência no repositório inteiro | apagar |
| `Modal.tsx` local | `frontend/apps/internal/src/components/Modal.tsx:15` afirma que "não existe equivalente em `@manto/ui`" — **falso desde a 187**; e o Modal local não prende foco nem usa portal | migrar os 4 consumidores (`CatalogBulkActionBar`, `AdminCatalogoListPage`, `FigurinoListPage`, `GastosExtrasPage`) para `Dialog` e apagar |
| `docs/changelog.html` (70 KB) | declarado congelado, mas continua em `docs/` e cai em qualquer `Glob('docs/*')` | mover para `docs/archive/` ou apagar (o conteúdo está coberto pelo 03) |
| `CLAUDE OLD.md` (23 KB) | raiz, **mesmo título de primeira linha** do vigente | mover para `docs/archive/CLAUDE_2026-07.md` ou apagar |

---

## 7. P5 — documentação que custa caro

### 7.1 `app/models.py` — o arquivo mais lido e o menos navegável

| Achado | Linha | Ação |
|---|---|---|
| **Dois relógios em colunas do mesmo tipo, sem uma linha de comentário**: `start_at`/`end_at` naive-SP vs `created_at`/`updated_at` UTC | `:233-237` | comentar cada bloco de datas declarando o fuso e abrir a docstring de `CalendarEvent` com a regra |
| 13 models sem docstring — e são os 13 **mais centrais**: `Role`(34), `Permission`(46), `User`(52), `Talent`(102), `CalendarEvent`(217), `FigurinoSheet`(363), `EventRole`(458), `EventLog`(497), `EventContract`(532), `EventPayment`(549), `SiteSetting`(691), `SalaryHistory`(749), `ImportState`(1263) | — | docstring de invariantes, começando por `CalendarEvent`, `EventRole`, `Talent` e `SiteSetting` |
| Sem docstring de módulo e sem índice: 130 KB / 68 tabelas | `:1` | docstring com índice de domínios por faixa de linha + as 3 convenções transversais (fuso, `Numeric(12,2)`, JSON em `Text` com property `*_list`) |
| Banners de seção só a partir da linha 1162; as primeiras 1.160 linhas são um bloco indiviso | `:1162` | aplicar os mesmos banners `── Domínio ──` na primeira metade. **Reordenar não muda schema nem exige migration** (`TalentMedia`:653 junto de `Talent`; `FigurinoSheet`:363 junto do bloco de figurino) |
| `@login_manager.user_loader` enterrado a 1.105 linhas de `User`, e é o único `def` sem type hints do bloco | `:1157` | mover para logo abaixo de `class User`, com `-> User \| None` |
| `SiteSetting` singleton `id=1` sem docstring; 45 de 47 acessos usam `.query.get(1)`, um usa `.first()` (`email_service.py:543`) | `:691` | docstring declarando o singleton + ponteiro para o schema de `pricing_config` em `app/orcamento/settings.py`; padronizar num helper `get_settings()` |
| `Permission`/`role_permissions`/`has_permission` **vestigiais** (2 códigos, 2 arquivos) sem nada dizendo isso | `:46` | marcar como legado na docstring ou remover se `/rh` migrar para papéis |
| 12 `def` sem anotação de retorno; docstrings remanescentes em inglês | `:386` e outros | corrigir |
| Campos cujo significado só se descobre no consumidor: `acrescimo_value`(288) × tabela `EventAcrescimo`(1585) — qual é a fonte de verdade?; `cache_cap`(472) é **teto**; quatro colunas `payment_status` sem lista de valores declarada (só `RecurringExpenseEntry`:1124 declara `STATUSES`); `Talent.has_visa`(139) "deprecated" sem desde quando | — | anotar o consumidor canônico e declarar as constantes de STATUSES |

### 7.2 `app/calendar/routes.py` — o maior arquivo do sistema, sem mapa

- **Sem docstring de módulo** (`:1` é um `import`), quando todos os outros arquivos do domínio têm.
- **`sync_events` (`:2149`, 146 l.) — a função mais crítica do domínio — não tem nenhuma docstring.**
  Ficam sem explicação: o early-return de `source == 'platform'`, o wipe de roles de `ENSAIO`, a
  reconciliação por nome normalizado, o disparo de `send_removal_email` e o commit por item.
- `parse_characters` (`:1935`) codifica a invariante central (o título é a fonte de verdade do
  elenco) e não tem docstring, enquanto as vizinhas de uma linha têm.
- `_EVENT_ACTIONS` (`:1592`) mapeia `'update_comercial'` e `'update_sale'` para o mesmo handler, sem
  dizer que uma é alias legado.
- A ordem "primeiro Google, depois banco" (`:3573-3592` e `agenda_write.py:563-573`) não está
  documentada em nenhum dos dois caminhos, e não há compensação.

**Ação mínima e barata, hoje:** cabeçalho de módulo declarando (1) que o arquivo é a camada de ops de
fato, com a lista dos símbolos exportados; (2) que só `/google/connect` e `/google/callback` são
alcançáveis; (3) o mapa de seções por faixa de linha (já está em `docs/04` §1 — copiar para lá).

### 7.3 Contrato JSON: 288 endpoints, 1 documentado

Não há OpenAPI, schema nem tipo compartilhado Python↔TS. Em 44 mil linhas de `app/api/` existem **8**
ocorrências de `Returns:`; **1** view tem contrato completo. Do outro lado, **478 interfaces
TypeScript escritas à mão** sem geração nem validação em runtime: se o backend renomear um campo, o
TS continua compilando e a tela mostra `undefined`.

**Ação:** adotar como obrigatório o formato de `app/api/maps_read.py:21-34` (linha `RBAC:` +
`Query params:` + `Returns:` com o shape literal), começando pelos 10 endpoints mais consumidos. No
frontend, curto prazo: um comentário em cada tipo de contrato apontando o módulo Python que o
serializa (já feito em `lib/agenda.ts:5`, ausente em `financeiro.ts`, `gastos.ts`, `talents.ts`,
`orcamento.ts`). Médio prazo: validar com zod as ~10 respostas mais críticas.

### 7.4 Outros itens de documentação

| Item | Onde | Ação |
|---|---|---|
| **37 `window.confirm()` sobrevivem** (36 no painel interno, 1 no portal) apesar de o Princípio V pedir confirmação em diálogo. O alerta nativo não respeita o tema, não formata valor, não tem estado de carregando nem lugar para o erro da API — e no celular nasce colado no topo, fácil de tocar errado. A trilha já existe desde a 228: `ConfirmDialog` do `@manto/ui` (promovido de `GastosRecorrentesPage`, adotado na exclusão em lote de Pagamentos) | `EventDetail/FinanceiroSection.tsx` (3), `AdminCatalogoListPage.tsx` (6), `TalentDetailPage.tsx`, `RevisaoSpacePage.tsx`, `PortalProfilePage.tsx`… | trocar por `ConfirmDialog` **por tela**, priorizando o que apaga dinheiro ou registro (contrato, comprovante, reembolso, exclusão de personagem/produto). Nenhuma migração em massa: cada troca precisa de `pending` e `error` ligados na mutation certa |
| `flags: Record<string, boolean>` gateia 26 call sites sem tipagem — `data.flags.can_edit_cor` compila e esconde o botão em silêncio | `frontend/.../lib/agenda.ts:229` | `Record<EventFlag, boolean>` com a união fechada das 11 flags de `app/api/agenda_read.py:136-161` |
| `@manto/ui` sem README — **não existe um único `.md` em `frontend/`**. Reflexo: `DenseCard` em 2 arquivos, `CopyButton` em 2, `Table` em 11 contra **8 páginas com `<table>` cru** | `packages/ui/src/index.ts` | `frontend/packages/ui/README.md` com uma linha por componente: o que é, quando **não** usar, props obrigatórias. As distinções já existem nas docstrings |
| Metade dos módulos de `lib/` sem docstring de módulo, incluindo os maiores (`financeiro.ts` 478 l., `gastos.ts` 442, `orcamento.ts` 388, `adminCatalogo.ts` 384) | — | cabeçalho de 4-6 linhas no padrão de `lib/impressoes3d.ts:1`: domínio, endpoints, RBAC do servidor, chaves de cache |
| Sem convenção de chave de cache: 3 estilos convivendo (literais inline repetidas 9×, constantes com nomes inconsistentes, chaves hierárquicas) | `lib/adminCatalogo.ts:147` | fixar `[dominio, recurso, ...params]` + uma constante `<DOMINIO>_KEYS` por módulo; documentar em `frontend/CONVENCOES.md` junto com a regra do invalidate por prefixo |
| `app/constants.py`: docstring fala só de RBAC, mas `RoleName` está na linha 231 de 260; 6 dos 9 papéis sem comentário de escopo | `:231` | reescrever a docstring descrevendo os blocos reais e dar uma linha de escopo por papel |
| `except Exception` sem log (regra explícita do CLAUDE.md) | `app/api/agenda_write.py:567`, `calendar/sync.py:93` e `:116`, `talents/routes.py:499`, `figurino/routes.py:385`, `revisao/cleanup.py:37` | `logger.exception`/`logger.warning` nos 6. Em `cleanup.py:37` logar o **caminho**: é a única pista de por que o disco não esvazia |
| Sem ESLint no monorepo (nenhuma config, nenhuma dependência), apesar de **10** `// eslint-disable-next-line` no código — cada um marcando uma dependência de efeito omitida de propósito | `frontend/package.json:16` | instalar eslint + typescript-eslint + react-hooks + jsx-a11y com um `npm run lint`, e revisar os 10 disables caso a caso |

---

## 8. Funções grandes demais (limite do CLAUDE.md: ~30 linhas)

| Função | Linhas | Onde |
|---|---|---|
| `calculate_quote` | **470** | `app/orcamento/quote_ops.py:58` |
| `api_financeiro_dashboard` | 352 | `app/api/financeiro_read.py:185` |
| `create_app` | 321 | `app/__init__.py:341` |
| `NovaContaForm` (componente) | 315 | `frontend/.../GastosRecorrentesPage.tsx:154` |
| `event_detail` | 305 | `app/calendar/routes.py:1615` |
| `dashboard()` | 305 | `app/financeiro/routes.py:409` |
| `serialize_event_detail` | 265 | `app/api/agenda_read.py:502` |
| `EditarDialog` (componente) | 216 | `frontend/.../GastosRecorrentesPage.tsx:577` |
| `_handle_update_comercial` | 205 | `app/calendar/routes.py:712` |
| `ContaRow` (componente) | 193 | `frontend/.../GastosRecorrentesPage.tsx:915` |
| `list_talents` | 153 | `app/talents/routes.py:39` |
| `sync_events` | 146 | `app/calendar/routes.py:2149` |
| `api_set_payment_status` | 139 | `app/api/financeiro_write.py:52` |

Agregado: 39 das 288 views de `app/api/` passam de 30 linhas (5 das 10 piores no Financeiro).
`dashboard()` e `set_payment_status` (108 l.) não têm sequer docstring — e `dashboard()` é a
**definição operacional de todos os KPIs do Financeiro** (ticket médio `:470`, break-even `:476`,
Fator R `:481`). Priorize docstring nas 4 funções acima de 100 linhas sem docstring:
`financeiro/routes.py:409`, `calendar/routes.py:1615` e `:712`, `talents/routes.py:39`.

---

## 9. Grande demais para uma sessão

Estes quatro itens **não cabem** num turno e não devem ser tentados de uma vez. Cada um vem com o
corte sugerido — cada fatia é independente, verificável e mergeável sozinha.

### 9.1 `app/calendar/routes.py` (3.910 linhas)

Composição medida: 946 l. de views Jinja (20 funções), 691 de handlers `_handle_*` (23), **1.007 de
núcleo compartilhado com a API** (32) e 866 de privados auxiliares (35). 39 símbolos privados são
importados por 10 módulos, com **imports tardios** que não aparecem em análise estática.

**Fatie assim, nesta ordem** (cada fatia = 1 sessão):

| Fatia | Extrair para | Conteúdo |
|---|---|---|
| A | `app/calendar/sync_ops.py` | `sync_events`, `_cleanup_stale_events`, `_mark_month_synced`, `_detect_changes`, `_log_sync`, parsers de título |
| B | `app/calendar/event_create_ops.py` | `_create_event_core`, `_validate_event_core` e satélites |
| C | `app/calendar/finance_ops.py` | `_add_payment_record`, `_add_contract_record`, `_add_invoice_record`, `_add_reimbursement_record` e pares |
| D | `app/calendar/group_ops.py` | agrupar/desagrupar/renomear grupo (**e só então** decidir o item 4.1) |
| E | — | apagar as 18 rotas mortas e os 23 handlers `_handle_*`, **depois** de migrar as lacunas de paridade (acréscimos, notas fiscais, parcelas) |

**Regra de segurança para cada fatia:** promova o símbolo a nome público com docstring de contrato,
mantenha um alias privado em `routes.py` durante a transição, e só remova o alias quando o `grep` do
nome antigo voltar vazio.

**Pré-requisito da fatia E:** as regras que **só** existem no Jinja precisam existir na API antes —
`EventAcrescimo`, `EventInvoice` e `EventInstallment` só têm implementação de escrita em
`_handle_update_comercial` (`:712`). Junto com as views vão 4.992 linhas de template
(`event_detail.html` 3.201, `event_create.html` 1.210, `calendar_list.html` 253, `calendar_day.html`
176, `ensaio_detail.html` 152) e os `url_for('calendar.*')` remanescentes em
`financeiro/dashboard.html`, `financeiro/comissoes.html`, `vendas/pipeline.html` e
`orcamento/historico.html`.

### 9.2 `app/financeiro/routes.py` (1.690 linhas) — **começar por aqui**

É o item de maior retorno: destrava todo o resto do Financeiro, e é menor que 9.1.

1. Extrair `app/financeiro/financeiro_ops.py` com as 6 funções que já são importadas de fora:
   `_event_commission` (`:120`), `_sync_commission_payment` (`:153`), `_resync_pending_commissions`
   (`:211`), `_resolve_period` (`:301`), `_salary_cost` (`:327`), `_compute_drg` (`:351`) — puras e
   tipadas, com a regra de 9 ramos escrita na docstring (está em `docs/04` §2).
   Os imports locais que hoje existem só para quebrar ciclo (`routes.py:126`, `:157`, `:447`;
   `vendas_ops.py:239`, `:261`, `:308`) somem junto.
2. Só então unificar as 4 fórmulas de comissão (item 3.1) e deduplicar `set_payment_status` (§5).

### 9.3 Superfícies Jinja inalcançáveis, mas vivas

`frontend/server.js:176` só devolve ao Flask os prefixos `/api`, `/uploads`, `/catalogo/midia`,
`/catalogo/og`, `/portal/photo`, `/google`, `/cadastro`, `/avaliar`, `/static` (mais o regex
`/figurinos/<id>/print`). Portanto:

- **`calendar_bp`**: 18 das 20 rotas sem caminho de acesso (vivas só `/google/connect` e
  `/google/callback`).
- **`app/talent_portal/routes.py`** (974 l.): **1 rota viva** — `portal_photo` (`:78`). As outras 20
  seguem registradas (`app/__init__.py:532`) e continuam acessíveis batendo direto no host do Flask,
  com **validação mais fraca** que a da API: `profile()` (`:544-554`) aceita foto checando só a
  extensão, sem o limite de tamanho que `portal_ops.update_photo` (`:280`) aplica.
  Bug latente já presente nessa cópia: `media_delete` (`:624-625`) usa `.lstrip("/uploads/")`, que
  remove **caracteres** do conjunto `{/,u,p,l,o,a,d,s}` e não o prefixo — funciona por acaso porque o
  caminho seguinte começa com `t`. A versão viva (`portal_ops._delete_local_upload`, `:526`) usa
  `removeprefix` corretamente.

**Ação (1 sessão para o portal, que é o caso limpo):** remover as 20 rotas Jinja do portal e os
templates de `app/templates/portal/`, deixando só `portal_photo`. O ERP (9.1 fatia E) é maior e vem
depois.

### 9.4 `app/marketing/virtuais_ops.py` (2.325 linhas)

Coeso por **feature**, balde por **camada**: 9 seções marcadas e ~6 responsabilidades técnicas
distintas (CRUD de campanha, retry genérico, Google Calendar, webhook, e-mail, gravação de arquivo em
disco, 10 serializadores). A qualidade interna é alta — **não reescreva, só mova**.

| Novo arquivo | Conteúdo |
|---|---|
| `virtuais_ops.py` | campanhas + estoque de horários |
| `virtuais_pedido_ops.py` | reserva, efetivação, webhook, devolução |
| `virtuais_producao_ops.py` | fila de produção + vídeo (`salvar_video_entrega`, `:1839`) |
| `virtuais_serializers.py` | os 10 serializadores (`:2021-2286`) |
| `app/utils.py` | `executar_com_retry`/`deve_tentar_novamente`/`retry_esgotou` (`:550-605`) — são **genéricos**, não específicos da loja |

**Preserve os nomes públicos** e reexporte a partir de `virtuais_ops.py` durante a transição.

### 9.5 O que NÃO refatorar agora

**`app/models.py`.** É o arquivo de maior raio de impacto do repositório e não há teste que cubra a
quebra. O retorno imediato e barato é o da §7.1 (docstring de módulo com índice, banners de seção,
docstring nos 13 models). Se um dia for dividido, `app/models/__init__.py` reexportando preserva todos
os imports.

---

## 10. Instruções concorrentes (remover antes de qualquer coisa)

Três fontes de instrução com aparência de autoridade contradizem o CLAUDE.md. São o item de menor
esforço e maior efeito da lista, porque envenenam **toda** sessão futura.

| Arquivo | Problema | Ação |
|---|---|---|
| `.claude/skills/architecture.md` | Prescreve `src/<feature>/{models,service,repository}.py` com classes `OrderRepository`/`OrderService` injetadas por construtor e a regra "API → Service → Repository". **Contradiz frontalmente** a arquitetura real (`app/<blueprint>/<dominio>_ops.py` com funções puras, sem repository) e usa `total: float` para dinheiro, quando o projeto exige `Decimal` | apagar ou reescrever para o padrão real. Uma skill genérica dentro de um projeto com arquitetura própria e forte é **uma instrução errada com aparência de autoridade**, e mais específica (ativável) que o CLAUDE.md |
| `.claude/skills/autonomy.md:11` | Exige bloco "PLANO DE IMPLEMENTAÇÃO" com pergunta "Posso prosseguir?", execução um arquivo por vez e "criar testes (TDD)". Contradiz o CLAUDE.md (`:19-20`, "vá direto ao ponto", "NÃO execute rotinas extras de auto-verificação") e **pressupõe uma suíte de testes que não existe** | alinhar ao CLAUDE.md ou apagar |
| `CLAUDE OLD.md` (23 KB, raiz) | Mesmo título de primeira linha do vigente; indistinguível numa busca | arquivar |
| `DEVELOPMENT.md:14` | "Nunca commitar direto no `main`. Todo desenvolvimento vai para `dev`" — não existe branch `dev` como tronco; o fluxo real é branch de feature → merge em `main` → deploy automático | atualizar ou absorver no CLAUDE.md |

### Correções no próprio CLAUDE.md

| Linha | Problema | Correção |
|---|---|---|
| `:55` | `npx tsc --noEmit` "dentro de `apps/internal` ou `apps/public`" — esquece `apps/portal`, que é buildado em produção | `cd frontend && npm run typecheck` (cobre os três, `frontend/package.json:18`) |
| `:54` | A regra **NÃO-NEGOCIÁVEL** de verificação aponta para `.\scripts\db\run-local.ps1`, e `/scripts/db/` é **gitignored** (`.gitignore:41`) | registrar a condição na própria regra: "`scripts/db/` não é versionado (contém caminhos e credenciais locais)" e documentar o conteúdo esperado dos scripts — isso importa mais que a linha de comando |
| — | O CLAUDE.md nunca diz que o frontend tem **três** SPAs nem que existem `frontend/packages/{ui,api-client,money}` | apontar para `docs/00_MAPA_DO_SISTEMA.md` |

---

## 11. Ordem sugerida de ataque

1. **§10** — apagar/corrigir as instruções concorrentes (minutos, e evita dano recorrente).
2. **§2** — os quatro P0. São 2 linhas, 20 linhas, 1 chave e 10 linhas. Impacto imediato no usuário.
3. **§9.2** — extrair `financeiro_ops.py`. Destrava o resto do Financeiro.
4. **§3.1** — unificar as 4 fórmulas de comissão apontando para `_event_commission`.
5. **§5** — deduplicar `set_payment_status` e unificar `_has_role` (resolve §3.5 de quebra).
6. **§9.3** — limpar as 20 rotas Jinja do portal (caso limpo, 1 sessão).
7. **§9.4** — fatiar `virtuais_ops.py` preservando nomes públicos.
8. **§7.1 e §7.2** — as docstrings de `models.py` e o cabeçalho de `calendar/routes.py`. Baratas e é o
   que mais reduz o custo de leitura das próximas sessões.
9. **§9.1** — as fatias A→E de `calendar/routes.py`, uma por sessão.


---

## Baixas e novidades da feature 235-educamanto (2026-08-13)

**Dívidas quitadas pela reestruturação do EducaManto:**
- Fórmula duplicada em JavaScript no template Jinja do EducaManto (e divergente do Python no
  gross-up do transporte e no headcount) — **morta**: templates removidos, cálculo só em
  `app/educamanto/pricing_ops.py`.
- Geração aceitava `sem_nota`/`com_nota` prontos do cliente sem recálculo — **corrigida**:
  `POST /api/educamanto/orcamento/gerar` recalcula tudo no servidor (snapshot v2).
- `EducaMantoPackage.commission_rate` (campo morto que a UI exibia como "% s/ lucro") —
  **removido** na migration `b7e3a91d5c24`.
- "Desconto especial de 5% à vista" era só texto no PDF — **virou cálculo real** (tela e PDF).

**Pendência nova (P1 — gate de deploy da 235):** valores `PROVISORIO` em
`app/educamanto/pdf_textos.py` (custos de técnicos, áreas X/Y do som), custos de
iluminação/cenário por musical (colunas zeradas) e a divisão personagens×produção dos musicais
além de Uma Aventura Animal; textos das responsabilidades aguardam revisão do dono. **Não fazer
merge para `main` antes disso** — Railway faz deploy automático do main.
