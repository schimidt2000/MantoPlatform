# 05 — Dívida Técnica

> **2026-10-20 (feature 310, pronta e aguardando deploy)**: itens 133 (limitador em memória por
> processo), 134 (História 9 desligada até a `INFINITEPAY_API_KEY`) e 135 (prova do proxy desligada até o
> `MANTO_PROXY_SECRET`), na baixa da 310 ao fim.
>
> **2026-09-08 (feature 296)**: §10 resolvida; pendências operacionais 21-33 registradas ao fim do §10.
>
> Achados de uma auditoria de leitura de 2026-08-06 sobre ~44k linhas de Python e ~46k de TypeScript,
> priorizados por **impacto**, não por elegância. Cada item tem `arquivo:linha` e uma ação concreta.
>
> **Como usar:** os itens **P0** e **P1** produzem número errado ou botão que não faz nada **hoje** —
> trate-os antes de qualquer refactor. Os itens da §9 são grandes demais para uma sessão e vêm com
> plano de fatiamento. Nenhum item aqui é hipótese: todos foram lidos no código.
>
> Notas de escala (19/10/2026, feature 306): `app/models.py` ~3.760 l. · `app/calendar/routes.py` ~4.600 l. ·
> `app/calendar/cancel_ops.py` ~3.330 l. (405 antes da 306) · `app/marketing/virtuais_ops.py` 2.366 l. ·
> `app/financeiro/routes.py` ~1.660 l. · `frontend/apps/internal/src/pages/GastosRecorrentesPage.tsx` 1.340 l.

---

## 1. Resumo priorizado

| # | Prio | Onde | Sintoma para o usuário | Tamanho |
|---|---|---|---|---|
| ~~1~~ | ~~P0~~ | ✅ **RESOLVIDO na feature 267** — eram **4** cópias, não 2 (os controles individuais também). Fonte única em `comissoes_ops.liquidar_periodo` | — |
| ~~2~~ | ~~P0~~ | ✅ **RESOLVIDO na feature 267** — `invalidarFinanceiro()` em `lib/financeiro.ts` | — |
| 3 | **P0** | `frontend/.../lib/gastos.ts:324` | histórico da conta recorrente não atualiza | 1 chave |
| 4 | **P0** | `frontend/.../lib/useAuth.ts:13` + `navigation.tsx:76` | "Ver como REVENDEDOR" cai numa tela que o servidor recusa | ~10 linhas |
| ~~5~~ | ~~P1~~ | ✅ **RESOLVIDO na feature 267** — `comissoes_ops.comissao_exibida_do_evento` serve a API e o gêmeo Jinja; lê a linha real, cai na regra canônica e zera evento cancelado | — |
| ~~6~~ | ~~P1~~ | ✅ **RESOLVIDO na feature 267** — `update_event_core` recebe `sincronizar_comissao` por injeção. *(`update_event_comercial` já sincronizava; este item estava parcialmente desatualizado)* | — |
| 7 | **P1** | `app/api/agenda_write.py:926` e `:995` | Figurino/Casting podem registrar pagamento de cachê e reembolso | ~4 linhas |
| 8 | **P1** | `app/api/orcamento_read.py` vs `clientes_read.py` (ambos `_require_vendas`) | `_require_vendas` com dois significados; FINANCEIRO passa ou não conforme o arquivo | ~30 linhas |
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
| ~~20~~ | ~~P5~~ | ✅ **RESOLVIDO na feature 296** — eram 8 fontes (4 de doc/skill + os 4 arquivos de deploy do Railway), todas apagadas ou reescritas; pendências operacionais novas ao fim do §10 | — |

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

> ✅ **Resolvido na feature 267** — e a contagem deste título estava errada: são **três**
> implementações, não quatro. `comissoes_ops.py:183` é recorte de **mês**, não cálculo (problema
> irmão, resolvido junto), e `financeiro/routes.py:120` é `_is_permuta`, sem relação com comissão —
> o DRE já consumia a regra canônica. Hoje a API e o gêmeo Jinja chamam
> `comissoes_ops.comissao_exibida_do_evento`.

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

**Ação:** trocar pelo gate financeiro explícito (`_can_manage_sale`, em `app/api/agenda_write.py`) e
justificar na docstring **pelo risco da ação**, não por paridade com o Jinja.

### 3.4 `_require_vendas` com dois significados

`app/api/orcamento_read.py` (`_require_vendas`) = `{COMERCIAL, SUPERADMIN}`; `clientes_read.py`,
`clientes_write.py:25`, `formularios_admin_read.py:24` = `{COMERCIAL, FINANCEIRO, SUPERADMIN}`. Lendo
`denied = _require_vendas()` dentro de uma view é **impossível** saber se FINANCEIRO passa.

**Ação:** mover os gates para um `app/api/rbac.py` único com nomes que digam o conjunto
(`require_comercial_ou_superadmin()`, `require_vendas_e_financeiro()`). Nenhum gate deve ser
redefinido por arquivo.

### 3.5 Impersonação respeitada só em metade do sistema

`session['impersonate_role']` é consultado em `app/api/agenda.py:138`, `agenda_write.py`
(`_can_create_event`/`_can_edit_event`),
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
| Precificação de orçamento dentro do módulo de calendário | `_compute_performer_caches`, `app/calendar/routes.py:2835` (~260 l. depois da 307, que lhe deu `data_evento` e a faixa de data especial); `app/orcamento/pricing.py:13` cita ela na docstring | mover para `app/orcamento/pricing.py` (ou um `pricing_elenco.py`) |
| Regra de auto-vínculo importada como **função privada** | ~~importada de `app/formularios/routes.py`~~ (a fase 3 do Jinja a levou para `formularios_ops.py`; a 298 a fez passar pelo núcleo `apply_event_link`). Resta o nome: `app/api/formularios_write.py` importa `_attempt_auto_link`; `calendar/sync.py` e `app/cli.py` usam `retry_auto_link_pending` | renomear para `tentar_vincular_evento()` / `reprocessar_vinculos_pendentes()` quando alguém tocar no envio público |
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
| ~~`docs/changelog.html`~~ | ✅ RESOLVIDO na 296 — movido para `docs/archive/changelog.html` | — |
| ~~`CLAUDE OLD.md`~~ | ✅ RESOLVIDO — arquivado em `docs/archive/CLAUDE_2026-07.md` (agosto); a constituição 2.1.0 foi para `docs/archive/constitution-2.1.0.md` na 296 | — |

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
| `flags: Record<string, boolean>` gateia 26 call sites sem tipagem — `data.flags.can_edit_cor` compila e esconde o botão em silêncio | `frontend/.../lib/agenda.ts:229` | `Record<EventFlag, boolean>` com a união fechada das 11 flags de `app/api/agenda_read.py` (`_role_flags`) |
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
| `calculate_quote` | **~540** | `app/orcamento/quote_ops.py:105` |
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
| A | `app/calendar/sync_ops.py` | `sync_events`, `_mark_month_synced`, `_detect_changes`, `_log_sync`, parsers de título (o corpo de `_cleanup_stale_events` já saiu para `app/calendar/sumico_ops.py` na feature 303; o nome ficou em `routes.py` como delegação de uma linha) |
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

`frontend/server.js` só devolve ao Flask os prefixos `/api`, `/uploads`, `/catalogo/midia`,
`/catalogo/og`, `/portal/photo`, `/google`, `/avaliar`, `/static` (mais o regex
`/figurinos/<id>/print`). `/cadastro` saiu da lista no hotfix cadastro-raiz (o Jinja do cadastro
foi **apagado**, não só desalcançado). Portanto:

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

## 10. Instruções concorrentes — ✅ RESOLVIDO na feature 296 (2026-09-08)

A auditoria de 06/08 achou três fontes de instrução contradizendo o `CLAUDE.md`; a revisão do harness
de 08/09 achou oito e fechou todas: as 4 skills genéricas soltas de março (`architecture.md`,
`autonomy.md`, `python-quality.md`, `ui-ux.md` — não carregavam por não terem `SKILL.md` e prescreviam
`src/`+repository, pytest/TDD, CSS vanilla e "Posso prosseguir?") saíram para
`~/.claude/archive/`; `CLAUDE OLD.md` já estava em `docs/archive/`; `DEVELOPMENT.md` foi reescrito
(branch `dev` morta e apagada; Railway só como história; migrations à mão); e `railway.json`,
`nixpacks.toml`, `frontend/railway.json` e `frontend/nixpacks.toml` — quatro arquivos de deploy que
não deployavam nada e que `scripts/validar_startcommand.py` ainda validava — foram apagados no mesmo
commit em que o validador passou a ler o `render.yaml`. As correções do próprio `CLAUDE.md` (typecheck
das três SPAs, `scripts/db/` gitignored, ponteiro para `docs/00`) entraram na reescrita. Nada em
`.claude/` era versionado (`.gitignore` tinha `.claude/`); desde a 296 só `settings.local.json` fica
fora.

### Pendências operacionais registradas na 296

| # | Prio | Onde | O quê | Ação |
|---|---|---|---|---|
| 21 | **P1** | painel do Render, `manto-backend` | `AUDIT_AGENT_TOKEN` e `MARKETING_AGENT_TOKEN` não foram preenchidos na migração de 28/08: `/api/audit-agent/*` e `/api/marketing-agent/*` respondem 404 e as rodadas semanais (221, 256) estão paradas | o dono preenche no painel a partir de `.audit-agent-token`/`.marketing-agent-token` (locais), fora do horário — mudar env redeploya (janela de 502) |
| 22 | **P2** | `render.yaml`, bloco `manto-frontend` | sem `healthCheckPath` e sem `watchPatterns`: cada push (inclusive só de docs) rebuilda os dois serviços e abre ~1 min de 502 na porta pública | decisão do dono; `healthCheckPath: /` (o `server.js` responde a SPA) e `watchPatterns` excluindo `docs/`/`specs/` — cada um em commit isolado, fora do horário, Events abertos (comportamento de serviço sem disco não conferido) |
| 23 | **P2** | `app/models.py` × banco | drift antigo que `flask db check` acusa no `manto_local`: `remove_index ix_calendar_events_cancelled_at`, `remove_constraint UNIQUE(clients.phone)`, `add_fk` em `ensaio_materials` (event_id, user_id) e `talent_media.talent_id`, índices em `figurino_producoes` e `special_expenses` | decidir de que lado está a verdade item a item ANTES de qualquer migration que toque essas tabelas; nunca autogenerate (o `flask db upgrade` do start executaria em produção) |
| 24 | **P2** | pasta do repositório | sincronizada pelo Google Drive Desktop (`.tmp.drive*` na raiz): `.git/`, `instance/`, `.env`, tokens e `backups/*.dump` vão para a nuvem do dono | confirmar intenção; excluir `.git/`, `instance/` e `backups/` do sync |
| 25 | **P3** | `render.yaml:buildCommand` do frontend | `npm install` (o antigo `nixpacks.toml` usava `npm ci`, que exige lockfile em sincronia) | alinhar para `npm ci` em commit isolado, ou manter e registrar |
| 26 | **P3** | `.specify/templates/*.md` | adaptados à Manto no lugar (cabeçalho "ADAPTADO PARA A MANTO"); o `speckit.manifest.json` deixa de conferir para eles, e um `specify init --force` os sobrescreveria | reaplicar após qualquer atualização do Spec Kit; `overrides/` não é honrado por todas as skills |
| 27 | **P3** | `.claude/settings.json` | além dos `deny` (`flask db migrate`, `git add -A`, `git add .`, `git push --force`), nenhum portão da constituição é executado por máquina — typecheck, ruff e verify dependem do agente | avaliar hook de pré-commit local (fora do escopo da 296) |
| 28 | **P3** | Google Cloud Console | host registrado em `GOOGLE_OAUTH_REDIRECT_URI` de produção não conferido nesta revisão (`app.mantoproducoes.com.br` ou `manto-backend.onrender.com`) | conferir no painel do Render e no Console; então fixar no `.env.example` |
| 29 | **P3** | `docs/04_GUIA_DE_DOMINIOS.md` | última revisão 2026-08-06 (pós-216); as 80 features seguintes não passaram por ele | varredura por domínio na próxima feature que tocar cada um |
| 30 | **P3** | `docs/02_MAPA_DE_PAGINAS_E_UX.md` | cabeçalho virou changelog encadeado de ~30 linhas | trocar por uma linha "última atualização · última feature" e deixar o histórico no `docs/03` |
| 31 | **P4** | `.railway-db-url`, `scripts/db/backup-railway.ps1` | nomes herdados do Railway — apontam para o Postgres do Render desde 28/08 (7 consumidores + Tarefa Agendada leem o nome) | renomear só com todos os consumidores e a Tarefa Agendada na mesma passada |
| 32 | **P4** | ~282 branches `NNN-*` locais e remotas nunca apagadas | o alocador do Spec Kit lê branches: apagar branch sem pasta em `specs/` pode fazer um número voltar | apagar em lote só as que têm pasta correspondente em `specs/` |
| 33 | **P4** | `docs/planos.md`, `docs/EspecificacoesEducamanto.md` | conteúdo comercial dentro de `docs/` | mover para `docs/negocio/` quando alguém tocar neles |
| 34 | **P1** | `render.yaml` × `app/impressoes3d/video_ops.py` | **o `ffmpeg` virou dependência de fato e não está declarada.** Ele existe em `/usr/bin/ffmpeg` (5.1.9, com `libx264`) porque vem da imagem base do runtime Python do Render — se o Render trocar a imagem, ele some sem aviso e todo vídeo passa a ser entregue cru, do jeito que a feature 297 existe para evitar | o código já degrada com segurança (`ffmpeg_disponivel()` → entrega como veio e registra o motivo). O conserto de verdade é declarar: ou `imageio-ffmpeg` no `requirements.txt` (binário estático, ~40 MB), ou runtime Docker. Decisão do dono; enquanto isso, conferir `which ffmpeg` depois de cada mudança de runtime |
| 35 | **P3** | `specs/297-nfc-moldura-e-menu/spec.md` × `nfc_tag_messages` | a spec não define **retenção dos recados** das clientes. Hoje só somem por cascata quando a tag é apagada, e tag não é apagada por contrato | decidir prazo (ou "para sempre") quando houver acervo; o volume hoje é zero e a decisão não muda o modelo |
| 36 | **P3** | `app/marketing/virtuais_ops.py` (feature 205) | o vídeo da Loja de Interações Virtuais tem **o mesmo problema de peso** que a 297 resolveu nas tags NFC: sobe cru e é servido cru | `app/impressoes3d/video_ops.py` já é núcleo puro e agnóstico de domínio — reusar lá é uma feature curta |
| 37 | **P3** | `app/impressoes3d/nfc_ops.py`, pasta `instance/nfc_media/` | reinício de contêiner no meio de uma conversão deixa dois órfãos: o `.parcial` em escrita e o MESTRE do par incompleto. Foram 62 MB em dois reinícios em 09/09 | varrer no start, junto de `destravar_presas`: arquivo que nenhuma linha de `nfc_tag_deliveries` referencia é órfão (a regra já está escrita em `scratchpad/limpar_mestres.py`) |
| 38 | **P4** | `app/cli.py`, comando `nfc-reprocessar` | o resumo final imprime "liberou X MB" mesmo quando TODAS as entregas foram puladas — ele soma o tamanho de antes sem descontar o que não converteu | só somar o que de fato passou pela conversão |
| 39 | **P3** | painel do Render, env `BACKEND_URL` do `manto-frontend` (hotfix 263b) | o proxy fala com o backend pela **URL pública** (`https://manto-backend.onrender.com`): cada requisição proxyada faz TLS e passa pelo edge do Render duas vezes; no incidente de 10/09 o sintoma terminal foi "Client network socket disconnected before secure TLS connection was established". A rede privada existe (Connect → Internal do `manto-backend`, `http://<hostname-interno>:10000`, mesma região e workspace) | trocar só em commit próprio com sondagem: `changeOrigin` passa a mandar `Host: <interno>`, o Flask precisa continuar montando URL externa pelas constantes (não pelo `Host`) e `X-Forwarded-Proto` vira a única fonte de `https`; conferir cookie `Secure` e `url_for(_external=True)` antes |
| 40 | **P3** | `frontend/server.js`, `server.keepAliveTimeout` (5 s, default do Node) | o proxy do Render mantém conexões keep-alive com o Node; se o idle do edge for maior que 5 s, há corrida (o Node fecha enquanto o edge reutiliza) e o cliente vê 502 esporádico. Não medido — o hotfix 263b deixou de propósito | medir 502 no log do edge / nas linhas `[proxy]` depois do 263b; se houver, subir para ~65 s em commit isolado, fora do horário |
| 41 | **P2** | dados de produção (registrado na 298) | limpeza pendente, fora do escopo da 298: datas informadas impossíveis nos formulários (2029–2049), 24 comprovantes lançados sem valor (maio/junho), evento 309 e grupos 184/288 com recebido acima do valor | o dono decide caso a caso; enquanto isso a Home pinta a data suspeita de cinza e o cadastro pede conferência |
| 42 | **P3** | `app/formularios/destino_ops.py`, `_agrupar` (298) | "mesma cliente" é o telefone normalizado: celular antigo sem o 9º dígito não agrupa com o mesmo número com o 9º dígito (nem recebe a sugestão de evento) | normalizar o 9º dígito em `normalize_phone` exige migração de dados em `clients` e `form_responses` — só com o dono |
| 43 | **P3** | `app/calendar/routes.py`, rota Jinja de criação de evento (298) | só o `POST /api/events` checa "formulário já tem destino" **antes** do Google; a rota Jinja (viva pelo host do Flask, §9.3) usa o núcleo, que recusa depois de o evento já estar na Agenda | some com a remoção do Jinja (pausada); `/events` não passa pelo `server.js` |
| 44 | **P4** | `specs/266-costuras-funil/verify_266.py` | os cenários dos contadores (`count_status`, filtro `futuros_sem_evento`, `now_sp` dentro de `_status_condition`) testam a regra que a 298 substituiu e agora falham | não rodar esses cenários; a regra atual é coberta pelo `verify_298` (cenários 1–4 e 13) |
| 45 | **P3** | `app/financeiro/cobranca_ops.py` (`_severity_antiga`) + `PendingPayment` do TS (feature 299) | `severity` e o formato antigo das linhas de `pending_payments` só existem para o bundle em cache na janela de deploy (R26) | remover num deploy seguinte, com a 299 no ar há alguns dias |
| 46 | **P3** | `app/calendar/routes.py:1833-1850` (Jinja) | cópia antiga da regra de cobrança (soma por evento, parcelas não recebidas) na página Jinja do evento, que não passa pelo `server.js` | some com a remoção do Jinja (pausada); não corrigir de passagem |
| 47 | **P2** | `app/financeiro/vendas_ops.py`, `list_closed_sales` | `event_type != 'ENSAIO'` em SQL descarta o `NULL`: a venda sem tipo (ex.: evento 395, R$ 35 mil) some do funil `/vendas` | trocar por `or_(event_type.is_(None), event_type != 'ENSAIO')` com o dono — muda números do funil |
| 48 | **P3** | `received_map` (`/vendas`), "a receber" do Financeiro, `total_recebido` | continuam contando **por evento**, não pelo grupo (spec 299, Fora de escopo): o recebido do grupo vale só na Home e na página do evento | unificar só com o dono |
| ~~49~~ | ~~P2~~ | ✅ **RESOLVIDO na feature 303** — pertencer a grupo comercial (principal ou satélite) segura o evento: o sync confere a ausência no Google e mantém marcado o evento com venda, comprovante, contrato, escala ou grupo (`sumico_ops.preso_ao_evento`, FR-001) | — |
| 50 | **P3** | `payment_method` | duas grafias para o parcelado com datas (`parcelado` e `parcelado_datas`) | unificar com o dono |
| 51 | **P3** | Auditoria de Input e Financeiro × Home (299) | "sem valor" é `<= 0` lá e "abaixo de R$ 1,00" na Home — de propósito (`docs/04`, Agenda, invariante 12) | não unificar de passagem |
| 52 | **P3** | `app/api/dashboard_service.py`, `dashboard_cutoff` | com `release_date` vazio, o corte dos painéis de operação vira "hoje" (data do servidor), enquanto as listas comerciais usam `corte_dia_sp` (01/06/2026 como padrão) | alinhar ao `corte_dia_sp` quando alguém mexer nos painéis de operação |
| 53 | **P2** | produção, 30 dias depois do deploy da 299 (SC-008) | conferir que nenhum evento novo foi gravado com valor entre R$ 0,01 e R$ 0,99 | só leitura: `SELECT count(*) FROM calendar_events WHERE created_at >= '<data do deploy>' AND sale_value > 0 AND sale_value < 1` |
| 54 | **P4** | `specs/174-redesenho-fidelidade-visual/verify_174.py` | escolhe o "não-SUPERADMIN" com `.first()` sem ordem; quando cai num REVENDEDOR_EDUCAMANTO puro, o guard do perfil devolve 403 em `/api/dashboard` e o cenário 8 falha (visto na 299; na `main` passou por sorte) | filtrar por um papel que tem Home (COMERCIAL) ou ordenar |
| 55 | **P4** | `app/calendar/routes.py`, `app/financeiro/routes.py`, `app/models.py` (atualizada na 306) | a 306 corrigiu no lugar 7 dos 8 erros antigos de `ruff check` de `calendar/routes.py` (os 4 F841, o UP017 e os 2 I001 de import dentro de função). Ficam os estruturais, que o portão "ruff limpo nos arquivos tocados" só aceita por estarem registrados aqui: o I001 do bloco de import do topo de `calendar/routes.py` e de `financeiro/routes.py`, e os 5 E402 de `models.py` (a linha `logger = logging.getLogger(__name__)` no meio do bloco de import deixa os imports seguintes "depois de código") | reordenar o bloco do topo de cada `routes.py` em commit próprio e conferir que o app sobe antes do merge: o `--fix` muda a ordem dos imports de `app.*` (em `financeiro/routes.py` sobe `app.constants` para antes de `app.financeiro.comissoes_ops`), e esses arquivos têm imports cruzados. Em `models.py` basta descer a linha do `logger` para baixo dos imports |
| 56 | **P3** | telas internas fora do catálogo (registrado na 300) | painel e Kanban de Marketing, Fila 3D, ficha do talento, tags NFC e campanhas virtuais continuam pedindo o arquivo ORIGINAL para caixas pequenas — a 300 reverteu a decisão 7 da 270 **só** para as listas do catálogo | decisão do dono (16/09/2026): nelas a premissa da 270 ainda vale (poucas imagens por vez). Quando alguém reclamar de uma, é `assetUrl(url, { largura })` no ponto de render — não precisa de backend |
| 57 | **P3** | `/catalogo/midia/campanhas/<arquivo>` × `VARIANTE_CATALOGO` (`client.ts:84`) e `_FAMILIAS` (`og_ops.py:68`) | capa de campanha virtual **não tem miniatura possível hoje**: o endereço tem uma pasta a mais e não casa com o regex de variante, que só aceita um segmento. Passar `largura` ali devolve o original em silêncio | estender a regra para aceitar subpasta, **nos dois lados ao mesmo tempo** (o verify da 292 já compara o TS com o Python) |
| 59 | **P4** | `app/catalogo/og_ops.py`, escrita atômica da variante (observado na 300, código da 270) | **só no Windows**: seis pedidos simultâneos da MESMA variante ainda não gerada fazem um deles estourar `PermissionError` ao abrir a miniatura recém-gravada — `os.replace` sobre arquivo que outra thread está abrindo é proibido no Windows, ao contrário do POSIX. Rastreio em `send_file` (`catalogo/routes.py:74`). **Produção é Linux, onde não acontece**; a 300 não tocou neste código | se um dia importar (ou se alguém rodar o servidor no Windows), envolver o `send_file` da variante em retry curto, ou servir os bytes já em memória em vez de reabrir o arquivo. Enquanto isso, o `verify_300` aquece a variante antes de medir concorrência, e a geração a frio simultânea segue coberta pelo cenário 6 do `verify_270` |
| 58 | **P3** | `frontend/apps/internal` (registrado na 300) | o app interno carrega TODAS as telas num pacote só (1,3 MB, nenhum `lazy()`/`Suspense` no repositório inteiro) — pesa em qualquer tela, não só no catálogo | feature própria: `React.lazy` por rota no `App.tsx` + `Suspense` com o Skeleton que já existe; medir antes e depois |
| 60 | **P4** | `app/cli.py`, `warm-thumbnails`, família catálogo (observado na 300) | o laço de `CatalogCharacter` aquece só as larguras de card (320/480/640), não a de 128 — e a 300 passou a pedir 128 das fotos de personagem em três telas internas e na lista de desejos. **Hoje não pesa**: das 243 fotos de personagem da produção só 44 existem no disco (199 perdidas na migração do Railway), e as 44 foram aquecidas a 128 antes do deploy da 300 (18/09/2026). Foto de personagem NOVA gera sob demanda até o comando incluir 128 | incluir 128 no laço de personagem (`for w in (128, *larguras_card)`, como já é para talento e figurino) quando alguém mexer no comando |
| 62 | **P3** | `docs/00`, `docs/04`, `docs/05`, `docs/PLANO_*` — 22 citações (medido na 301) | citações `arquivo:linha` para `app/api/agenda_read.py` e `agenda_write.py` apontam para linha errada: `agenda_read.py:127` promete `_role_flags` e entrega o laço `by_day`; `:245`/`:247` prometem assinatura de função e entregam campos de talento; `agenda_write.py:926`/`:995` prometem os endpoints de pagamento e reembolso, que hoje estão ~600 linhas abaixo. **Já estavam erradas antes da 301** — conferido contra `e7aa940`, a linha citada também não batia lá; os blocos `RBAC:` da 301 (+13 linhas em cada arquivo) só aumentaram o desvio. Perigo concreto: a §3.3 mandava trocar um gate frouxo por `_can_manage_sale` citando `agenda_write.py:52`, e essa linha passou a cair justamente no gate condenado | citar **arquivo + nome do símbolo**, que não envelhece (foi o que a 301 fez nas 4 citações que ela própria deslocou). Um passe varrendo `docs/*.md` com o script de conferência contra HEAD resolve a classe inteira |
| 63 | **P2** | `app/talent_portal/portal_ops.get_agenda` (registrado na 302) | a chave `history` continua sendo montada e enviada no payload da agenda, mas **nenhuma tela a usa** desde a 302 — e ela não tem limite: o artista mais ativo do espelho tem 75 escalações passadas serializadas a cada abertura da Agenda, a média é 4,7. Ficou de propósito por **um ciclo de deploy**: `manto-backend` e `manto-frontend` sobem separados, e o bundle velho faz `agenda.history.map(...)`, que numa janela de servidor novo derruba a tela do artista no celular | depois de a 302 estar em produção e o bundle novo servido, remover `past` de `get_agenda` e a chave do tipo `PortalAgenda`. O Histórico completo continua em `GET /api/portal/historico` |
| 64 | **P3** | `app/calendar/event_ops.save_logistics` (achado na 302) | o aviso de alteração do portal (o botão **Ciente**) só nasce quando o valor **anterior existia** (`and old_makeup_time is not None`, e igual para saída). Como **nenhum** dos 64 eventos futuros tem logística preenchida, todo preenchimento que a 302 provoca é um PRIMEIRO preenchimento — e nenhum avisa ninguém. O artista vê na próxima vez que abrir o portal, sem ser notificado. Marcar ensaio também não avisa (`create_ensaio` não chama `notify_accepted_roles`) | decidir com o dono se o primeiro preenchimento deve disparar e-mail: mexe em envio para artista de verdade, então não é mudança para fazer de passagem |
| 65 | **P5** | docstrings de `portal_ops.get_agenda`, `app/api/portal_agenda.py`, `portal_ratings.py`, `portal_profile.py` e `portal_auth.py` (achado na 302) | todas citam a "view Jinja legada" do portal, ou a sessão compartilhada com ela. **O Jinja do portal não existe mais**: `app/talent_portal/routes.py` tem 82 linhas e serve só `/portal/photo`. Quase virou premissa de feature — quatro artefatos da 302 justificavam uma linha de regressão com "o Jinja legado tem consultas próprias", conclusão certa por razão falsa. É o mesmo mecanismo da regressão da 301 (documento velho obedecido com fidelidade). `docs/02` §C.1 **já foi corrigido** na 302; `docs/04` §5 ainda dá `routes.py` como tendo 974 linhas | uma passada nas cinco docstrings e no `docs/04` §5, quando alguém abrir esses arquivos |
| 66 | **P3** | `frontend/apps/portal/src/lib/format.ts` × `frontend/apps/internal/src/components/EventDetail/parts.tsx` (registrado na 302) | dois formatadores de faixa horária, um por app: o do portal dá `28 de jul, 20:00 às 23:00`, o do interno dá `05/07/2026 12:00 — 16:00`. A 302 **decidiu não unificar**, e o motivo é bom: promover um dos dois a `@manto/ui` promoveria o formato errado para o outro app. Fica registrado para ninguém "consertar" a duplicação sem ler isto | só unificar se os dois apps passarem a querer o mesmo formato — o que hoje não é verdade |
| 67 | **P3** | `calendar/event_ops.makeup_location_label` (Python) × `EventDetail/parts.makeupLocationLabel` (TypeScript), registrado na 302 | a tradução do local de maquiagem existe nas duas linguagens. A TS **precisa** existir: alimenta o `<select>` do formulário, que distingue preset de endereço livre. O texto do preset `"local"` diverge **de propósito** — "Local do evento" é opção de formulário, "No local do evento" é frase corrida que o artista lê no celular. O risco é alguém alinhar as duas achando que é bug, ou mudar uma e esquecer a outra | manter o comentário cruzado nos dois lados; se um dia o formulário morrer, a TS morre com ele |
| 68 | **P4** | `app/api/portal_figurino.py:24` (decisão registrada na 302) | a ficha de figurino recusa quem não está escalado com **403** e a mensagem "Você não está escalado neste evento", o que confirma a um estranho que o evento existe; o Princípio XIII manda **404**. O dono decidiu na 302 **não trocar**: mudaria o texto que o artista lê e não tinha relação com o pedido; o alcance é pequeno, porque só quem tem sessão de talento chega no endpoint | trocar junto de alguma feature que já mexa na tela da ficha, decidindo ao mesmo tempo o que ela passa a dizer |
| 61 | **P4** | `app/api/admin_catalogo_read.py:199` (detalhe do admin), `app/api/catalogo_read.py:216` (detalhe da vitrine) e `:290` (elenco-busca) — registrado na 300 | a listagem ordena o elenco por `(position, id)`; estes três ainda ordenam só por `position` sobre a ordem física do banco. Com dois personagens empatados em `position`, depois de um UPDATE que mude a ordem física (vincular ficha, trocar foto, ativar), a Árvore do gerenciador e o formulário de edição podem mostrar o par em ordens diferentes. **Não acontece hoje**: 0 de 458 no espelho | usar `(c.position, c.id)` nos três pontos, para uma regra só em todas as telas |
| 69 | **P2** | escritas no Google fora da devolução e do cancelamento (registrado na 303; o cancelar saiu na 306) | a trava `CALENDAR_SUPPRESS_EVENT_WRITES` cobre a devolução (303) e a remoção do show e dos ensaios no cancelamento (306, `cancel_ops._remover_do_google`). ~~cancelar~~ Criar, editar e excluir evento e ensaio (o "Cancelar ensaio" e a troca de tipo que sai de SHOW passam por `event_ops.delete_ensaio`, sem trava) e o convite, pelo `manto_local`, continuam escrevendo no calendário real, e o sync, a limpeza e o "Sincronizar" continuam lendo | estender a trava a `service.insert_event`/`update_event`/`delete_event`, com cenário próprio |
| 70 | **P3** | `service.fetch_events_for_month` (registrado na 303) | a lista do mês não pagina (`maxResults=2500`, sem `nextPageToken`): mês com mais itens que o teto deixa eventos fora da lista, e cada um vira consulta individual na limpeza | paginar com `nextPageToken` |
| 71 | **P4** | série recorrente no Google (303) | a série-mãe nunca vem na lista (`singleEvents=True`): fica no ramo "presente fora da lista" a cada ciclo, com uma linha de auditoria por dia | decidir se a série vira evento ou é ignorada |
| 72 | **P3** | devolução ao Google (303) | se alguém restaurar da lixeira o id velho **depois** da devolução, existem dois eventos no Google para o mesmo registro; o sync importa o velho como evento novo | detectar na reconferência ou ao importar |
| 73 | **P3** | `event_ops.update_ensaio` e `routes.edit_ensaio` | só capturam `RuntimeError` da escrita no Google: outra exceção derruba a edição | tratar como `_sincronizar_e_trocar_tipo` |
| ~~74~~ | ~~P3~~ | ✅ **RESOLVIDO na feature 312** — agendar e vincular ensaio e vincular presente 3D recusam o cancelado no núcleo; a Fila 3D e as pendências não o trazem | — | — |
| 75 | **P3** | lembrete diário de convite (`invite_reminders`, 303) | continua lembrando convite pendente de evento marcado "Sumiu do Google Agenda" | decidir com o dono se o lembrete pausa enquanto marcado |
| 76 | **P3** | `EventLog` gravado em horário de São Paulo: o desfazer do pagamento de comissão da 267c (`comissoes_ops.liquidar_item_de_comissao`, `created_at=now_sp()`) | o histórico trata sem-fuso como UTC e essas linhas saem 3 h antes da hora real. O cancelar saiu da lista na 306; o pedido e a recusa da 224 saíram na 315 (`solicitacao_ops` grava sem `created_at`) | deixar o default UTC, como a 303, a 306 e a 315 fazem |
| 77 | **P4** | `specs/205-loja-interacoes-virtuais/verify_205.py` antes da 303 | o V7.2 antigo chamava a limpeza com a lista vazia e apagava do espelho os eventos não virtuais do mês — o espelho de quem rodou o 205 antes da 303 pode estar sem eles | refresh do espelho |
| 78 | **P4** | `FaixaSumidosGoogle.tsx` (303) | sexta cópia do fechar-em-Esc-e-clique-fora (sino, `KebabMenu`, `FilterDropdown`…) | promover um hook `useFecharAoSair` para `@manto/ui` |
| 79 | **P3** | `sumico_ops.limpar_mes` (303) | sem teto de consultas por execução: lista de mês vazia ou cortada com o Google no ar faz uma consulta por evento, em série; no "Limpar eventos fantasma" pode passar dos 180 s do proxy (o Flask termina, a tela diz que não concluiu) | teto por execução, ou rodar a limpeza em segundo plano |
| 80 | **P3** | eventos "sem confirmação" (303) | o evento que fica inconclusivo ciclo após ciclo (403 persistente, por exemplo) só aparece no total do resumo — não há aviso próprio | aviso depois de N ciclos |
| 81 | **P4** | ensaio-filho (303) | o pai vazio apagado leva o ensaio do banco, mas não do Google; se o ensaio continuar lá, o sync o reimporta solto | apagar o ensaio no Google junto, ou não reimportar ensaio sem pai |
| 82 | **P4** | `_mark_talents_worked` (303) | liga "já trabalhou com a Manto" por evento marcado que pode não ter acontecido | excluir marcados da conta |
| 83 | **P3** | `service.update_event` (edição e ramo "já tinha voltado" da devolução, 303) | manda sempre `dateTime` (dia inteiro vira bloco com hora) e só manda `location` quando não é vazio (local apagado no sistema não é apagado no Google) | mandar `date` no dia inteiro e limpar o local |
| ~~84~~ | ~~P4~~ | ✅ **RESOLVIDO na feature 312** — `GET /api/events/cancelamentos` inventariado em `docs/01` §4.3 ("O cancelado fora das listas"), com o gate e os filtros; os outros da 224 já estão nas tabelas do cancelamento (§4.3) | — | — |
| 85 | **P4** | verifies de `scripts/db/` depois da 303 | `verify_cancelamento_evento.py` seguia válido até a 306, que o envelheceu (dívida 129); `verify_168_admin_config_react.py` quebra no `cleanup_past` (o dublê devolve lista, o endpoint lê `ResultadoLimpeza`); `verify_151_excluir_sync.py` **não pode rodar sem ajuste** — troca `routes.fetch_single_event`, que o "Sincronizar" deixou de usar, e a consulta iria ao Google real | ajustar os dois antes de rodá-los |
| 88 | **P2** | `VirtuaisCampanhasPage.tsx:90` → `/virtuais/campanhas/nova` (achado na 304) | o botão "Nova campanha" não cria nada: a rota cai em `VirtuaisCampanhaFormPage`, `Number("nova")` é `NaN`, a consulta fica desligada e a tela fica no esqueleto para sempre; `useCreateVirtualCampaign` nunca é usado e a tela não escolhe personagem. A campanha do Papai Noel nasceu por `specs/304-loja-natal-papai-noel/criar_campanha_noel.py` | tela curta de criação (título + personagem do catálogo) que manda para a edição; `catalog_character_id` precisa do id do `CatalogCharacter`, não da identidade de `useCatalogPersonagens` |
| 89 | **P4** | `Combobox`/`GoogleAddressInput` do `@manto/ui` na loja `/v*` (304) | desenham com os tokens globais (painel branco, tinta escura): sobre o verde do tema saem claros. Legíveis, mas fora da identidade — aparecem no endereço do presente e no seletor de presente com mais de 10 peças | aceitar `className` de cores no campo e na lista, ou um `variant` escuro |
| 87 | **P2** | `requirements.txt` (achado no deploy da 303) | só as dependências diretas têm versão; as transitivas sobem sozinhas a cada build do Render. Foi assim que o SQLAlchemy 2.1 (driver padrão psycopg 3) derrubou o deploy de 01/10; SQLAlchemy, alembic e oauthlib foram fixados na hora, o resto continua solto | gerar um lock (`pip-compile`/`uv pip compile`) a partir do `pip freeze` da produção e instalar por ele |
| 86 | **P3** | `sync_events` → `_notify_ensaio_team` (achado na 303) | o alerta de ensaio de evento novo importado do Google sai por thread **antes do commit**; a thread relê o evento por id numa sessão própria e, quase sempre, não o encontra (`AttributeError: 'NoneType' … start_at` no log) — o e-mail de "precisa de ensaio" de SHOW criado direto no Google provavelmente nunca sai | confirmar no log de produção; mandar depois do commit (o dono decide se quer esse e-mail) |
| 90 | **P3** | BV de evento que vira satélite (305, premissa 21) | agrupar à mão um evento que já tem BV deixa o BV fora da comissão e da DRE (o financeiro pula satélite) e o editor recusa satélite: o BV fica preso | mover o BV ao principal no agrupamento, ou recusar agrupar evento com BV |
| 91 | **P3** | BV não prende o evento na exclusão (305, premissa 24) | `pode_excluir` e o "vazio" da 303 não olham `event_acrescimos`: um evento com BV a pagar pode ser excluído e o BV some da Planilha | contar BV como dinheiro preso, como comprovante e cachê |
| 92 | **P3** | lucro do painel Financeiro sem BV (305, premissa 25) | o lucro por vendedor, a tendência e a tabela por evento do painel (e os gêmeos) não descontam o BV; a DRE e o card do evento já descontam | usar `_event_bv_total` nas três contas (sugerido para o 6b) |
| 93 | **P4** | id do acréscimo muda a cada salvamento (305, premissa 26) | o editor apaga e recria as linhas; a herança agora é pelo `id` que a tela mandou, e a Planilha aberta antes de salvar responde "Item não encontrado" ao marcar pago até recarregar; a 1b conta com o id | atualizar no lugar também no evento vivo: a 306 grava no lugar só no cancelado (`comercial_ops._gravar_no_lugar`, via `alterar_acrescimos_do_cancelado`); `substituir_acrescimos` ainda apaga e recria |
| 94 | **P3** | guarda 1:1 orçamento↔evento sem trava (305, premissa 27; vem da 273) | dois "Criar evento" do mesmo orçamento no mesmo segundo criam dois eventos (e dois BVs) | trava por `FOR UPDATE` na linha do orçamento |
| ~~95~~ | ~~P3~~ | ✅ **RESOLVIDO na feature 306** — o BV do cancelado entra na Planilha pelo que ficou (`cancel_ops.bv_da_planilha`): o pago ou no banco pelo valor pago, o a pagar pelo proporcional ao retido, que some quando dá zero. O evento recriado lista o BV dele pelo valor dele | — |
| 96 | **P4** | `specs/273-orcamento-para-evento/verify_273.py` (achado na 305) | 8/15 na `main` desde a 301: espera 404 onde a 301 responde 409 `orcamento_de_outro`, e os cenários 7–15 caem em cascata; o `verify_305` (cenário 27) o compara com essa linha de base | atualizar o verify à regra da 301 |
| 97 | **P4** | edição completa sem "sair sem salvar" (converge da 305) | `EventEditPage` tem sete links para o detalhe do evento (reembolsos, comprovantes, contratos, observações, o "Lançar o BV" do alerta, "‹ Evento", "Cancelar") que saem sem confirmação e descartam o digitado; nenhuma tela da SPA usa `useBlocker` | `useBlocker` do react-router com `formState.isDirty` + os estados locais, na página inteira |
| 98 | **P4** | acessibilidade do editor de acréscimos (converge da 305) | rótulos sem `htmlFor` (Tipo, Valor, Quem recebe, PIX — vem da main), erro sem `aria-describedby`, e o alerta do BV com `role="alert"` duas vezes na aba Comercial (Venda e Acréscimos) | ids por linha + `aria-describedby`; o alerta estático como `role="status"` |
| 99 | **P4** | alerta do BV sem valor em evento acima de 4h (converge da 305) | sem duração identificada (evento de 5h+ que não é a duração extra do orçamento), o alerta vem sem valor e o "Lançar o BV" abre em reais vazio — a pessoa calcula à mão | passar as horas da agenda ao `plano_dos_acrescimos` quando passam de 4h (a régua linear já existe) |
| 100 | **P4** | acréscimo negativo no editor React (2º converge da 305) | o valor em R$ é `MoneyInput`, que só lê dígitos: um acréscimo que não é BV com valor negativo (desconto) não se cria pela tela nova — o que já existe mantém o sinal; o servidor e o Jinja aceitam; nenhum no espelho | um alternador de sinal nas linhas que não são BV, se o desconto por acréscimo for uso de verdade |
| ~~101~~ | ~~P4~~ | ✅ **RESOLVIDO na feature 306** — `_delete_event_flow` e a limpeza do sync (`sumico_ops._apagar_vazio`) travam e releem o evento (`refresh(…, with_for_update=True)`) antes de `_delete_event`: a exclusão segue a mesma ordem evento → dependentes do PUT de acréscimos, e o evento que se descobre cancelado ali não se exclui | — |
| 102 | **P4** | `specs/266-costuras-funil/verify_266.py` (achado no 3º converge da 305) | 7/9 na `main` (2244e7b): o 7 espera o contador `total` no bloco de formulários do dashboard e o 8 quebra em `futuros_sem_evento` (`'list' object has no attribute 'id'`) — o bloco mudou na 298/299; o 6 (excluir cliente) passa | atualizar o verify ao bloco de hoje |

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
merge para `main` antes disso** — o Render faz deploy automático da `main`.

## Baixa da feature 236-cache-por-duracao (2026-08-14, branch)

- **Quitada**: teto/cachê de 1 hora aplicado silenciosamente a eventos com duração fora de
  1–4h na criação a partir de orçamento (`dur_idx` com fallback 0) — causa raiz do caso do
  Baile do Addan. A duração agora é validada e os cachês recalculados no servidor pela régua.
- **Nova (P3)**: o dublê `scripts/db/run-local-sem-google.py` não cobre todos os caminhos de
  escrita no Google (ex.: `api_create_event` faz import tardio) e o launcher de preview pode
  usar config em cache — criar evento em teste local pode tentar o Google real e falhar com
  502 (sem lixo, mas confunde a verificação).

## Baixa da feature 307-natal-papai-noel-calculadora (2026-10-15, branch)

| # | Prio | Onde | Sintoma | Ação |
|---|---|---|---|---|
| 103 | **P3** | `PerformersEditor.tsx:138-149` (compartilhado com o EducaManto) | o `<select>` nativo de especiais foi de 11 para 12 itens com "Ajudante do Noel" — violação **já existente** do Princípio XII.1 (NUNCA select nativo acima de 10), agravada pela 307; a troca pelo `Combobox` de `@manto/ui` mexe nas duas calculadoras e não coube no "para ontem" — **decisão do dono**: trocar na próxima fatia ou emendar a constituição | `Combobox` com miniatura no `PerformersEditor` (uma troca resolve as duas calculadoras) + conferência de tela nas duas |
| 104 | **P4** | `app/api/orcamento_read.py` `personagens-no-dia` (`quote_ops.py:736-765`) | o alerta "Já na agenda neste dia" agrupa por `character_name`: em 24/12, com vários Noéis escalados, todo orçamento de Noel acusa "venda em dobro" mesmo havendo artista livre | agrupar por talento (ou mostrar "N escalados") |
| 105 | **P4** | `OrcamentoCalculadoraPage.tsx` rehydrate (`?recalcular_id=`) | não restaura `incluir_duracao` (nem vai ao snapshot) nem `personalizado_criterio`/`cust_*` (estão no snapshot, faltam no tipo e no efeito): um orçamento "1 entrada de 30 min" reabre com as 4 durações | pôr `incluir_duracao` no snapshot e restaurar os três no efeito |
| 106 | **P4** | `calculate_quote` (~540 l.), `_compute_performer_caches` (~260 l.), `api_orcamento_settings_save` (~75 l.) | já excediam as 30 linhas do Princípio II; a 307 só acrescentou chamadas a helpers (`cache_na_faixa`, `markup_vigente`, `validar_datas_especiais`) — o 3b vai reescrever o núcleo em "por dia" e é a hora de quebrar | quebrar junto com o 3b, com o gabarito de paridade |
| 107 | **P4** | eventos de 24 e 25/12 criados antes do deploy da 307 | o vínculo 273 só preenche teto onde `cache_cap` é `NULL`: Noel 600 / coordenador 250 ficam nos eventos já criados | pós-deploy, consulta só de leitura (eventos com `start_at` em 24/25/12 e `orcamento_history_id`) e ajuste manual pelo superadmin |

## Baixa da feature 309-produtos-de-tabela (2026-10-20, branch)

- **Quitada em parte**: a engenharia reversa da 307 ("Papai Noel" 712 / "Ajudante do Noel" 423 como
  cachê para o preço da Visita bater) saiu da tabela — cachê 600 / 270 de volta, preço no produto.
  Os tetos 712/423 já gravados em vagas desde 16/10 são rebaixados pelo script
  `specs/309-produtos-de-tabela/rebaixar_tetos_noel_309.py` (dry-run; `--execute` só sem cachê e
  sem artista) — **rodar no pós-deploy** e conferir à mão o que ele listar como "conferir".
- #103 continua (o `<select>` de especiais do `PerformersEditor`); a 309 pôs o `Combobox` só no
  card de produtos.

| # | Prio | Onde | Sintoma | Ação |
|---|---|---|---|---|
| 108 | **P4** | `ProdutosCard.tsx` × `quote.produtos` | a linha do produto casa `aplicados[i]` com `selecionados[i]` pela posição e pela chave; se o servidor um dia reordenar ou filtrar os aplicados, a linha mostra "calculando…" para sempre | devolver no `quote` um índice/identificador do exemplar |
| 109 | **P4** | `calculate_quote` (~600 l. depois da 309), `_compute_performer_caches` (~300 l.) | a 309 acrescentou mais chamadas a helpers (`produtos.*`) às duas maiores funções do repositório (ver #106) | quebrar junto com o 3b, com o gabarito de paridade (`verify_309_golden.json` já serve de oráculo) |
| 110 | **P4** | `ProdutosConfigCard.tsx` | produto novo nasce com rótulo vazio e preço 0 — o 400 do servidor é a única trava (nada local), e o card não sabe quais faixas foram desligadas (`dias: []`): mostra "Preço em <faixa>" mesmo para faixa sem dias | validação local mínima (rótulo e preço) e esconder faixa sem dias |
| 112 | **P4** | `quote_ops.py` (`num_colaboradores`) × `routes.py` prefill — **pré-existente na main** | com "Nº de colaboradores" vazio a venda dimensiona a van por `num_going` (performers + coordenadores — e, desde a 309, as pessoas do produto), mas o snapshot grava `""` e o prefill lê `1`: o `transport_value` do Novo evento difere da venda (R$ 33,33 com 50 km e divisor 3; cresce com km e pessoas). A 309 só torna o caso padrão da Visita | gravar no snapshot o `num_colaboradores` efetivo (ou o prefill recompor `num_going` do snapshot); mexe no snapshot de todo orçamento — fatia própria com gabarito |
| 111 | **P4** | `GET /api/orcamento/opcoes` (`orcamento_read.py`) | devolve `settings` inteiro a todo COMERCIAL — desde sempre com os cachês da tabela, agora também com a composição e os cachês fixos dos produtos (decisão consciente da 309: a calculadora precisa dos produtos ativos; os cachês já eram visíveis) | se um dia a tabela de cachês virar segredo do superadmin, enxugar o `/opcoes` para o que a calculadora usa (produtos ativos sem `vagas[].cache`, dias das faixas) |

## Baixa da feature 306-dinheiro-do-cancelamento (2026-10-19, branch)

**Quitadas.** Riscadas no lugar: a 95 e a 101; o "cancelar" da 69; o cancelar da 76; 7 dos 8 erros da 55.
E mais quatro que nunca chegaram a ser numeradas (vinham da pesquisa da 303):
- O estorno da exclusão deixou de copiar a data da venda e ganhou o ramo `no_banco`:
  `cancel_ops.aplicar_estorno_comissao` estorna a comissão paga **ou no banco** no primeiro repasse aberto do
  vendedor, com o motivo "Exclusão do evento".
- O cachê do dia cancelado de um grupo saiu da base: `comissoes_ops._group_cost` soma só os satélites vivos
  (comissão EducaManto e CPV).
- Os handlers Jinja de comprovante, de reembolso e da aba Comercial recusam o evento cancelado para todo papel, o
  Superadmin inclusive (`_ACOES_RECUSADAS_NO_CANCELADO`, `app/calendar/routes.py`): o Jinja não refaz o cancelado.
- O rótulo de impostos da DRE antiga, que a spec ainda listava como dívida, saiu corrigido: com cancelado no
  período, "Impostos Provisionados" diz "+ imposto informado de N cancelamento(s)"
  (`templates/financeiro/dashboard.html`), como a DRE nova.

**Novas.**

| # | Prio | Onde | Sintoma | Ação |
|---|---|---|---|---|
| 113 | **P3** | `comissoes()` e `set_commission_status` (`app/financeiro/routes.py`, `/financeiro/comissoes` — Jinja vivo só pelo host do Flask, §9.3) | a tela Jinja de Comissões não ganhou nada da 306: sem os filtros (tipo e ciclo) e sem `no_banco` (lista só `a_pagar` e `pago`); o painel "Estornos pendentes" lista todo negativo a pagar de qualquer mês, e o estorno ou ajuste cujo `sale_date` cai no mês pedido aparece nas duas listas e entra duas vezes em `total_a_pagar`. `set_commission_status` ganhou só a guarda que recusa linha de evento cancelado (FR-047); segue sem trava e grava `paid_at` com `date.today()` (UTC) | some com a remoção do Jinja (pausada); não usar como modelo — a fonte é a tela React (`comissoes_ops`) |
| 114 | **P4** | `event_detail` Jinja (`app/calendar/routes.py`) × `comissoes_ops.comissao_exibida_do_evento` | na página Jinja do evento cancelado a comissão aparece 0 (P-28, escolha do plano): a função zera o cancelado, e o Jinja não lê a comissão do retido que a API manda no bloco `cancelamento` | some com a remoção do Jinja; não tirar o zero da função (o detalhe da API não a chama no cancelado) |
| 115 | **P3** | "pago" de gasto sem conferência de valor: `POST /api/financeiro/pagamentos/bulk-action`, o lote Jinja (`bulk_payment_action`) e o individual Jinja (`set_payment_status`), em `app/financeiro/routes.py` | só o individual da API manda `valor_esperado` e recebe 409 `valor_mudou` (`cancel_ops.marcar_status_da_devolucao`). O individual Jinja trava o evento mas não confere o valor; os dois lotes nem travam: com a Planilha aberta antes de um "Alterar devolução", o "pago" em lote cai sobre o valor novo da devolução sem ninguém ver | mandar no lote o valor que a tela mostrou (um `valor_esperado` por gasto) e passar os dois lotes por `marcar_status_da_devolucao` |
| 116 | **P3** | comprovante pelo Jinja num dia vivo de grupo com dia cortado (`_handle_edit_payment`/`_handle_delete_payment`, `app/calendar/routes.py`, vivos pelo host do Flask) | pela API a guarda vale no grupo inteiro: baixar ou excluir comprovante de qualquer dia de grupo com algum dia cancelado dá 409 `pago_abaixo_do_devolvido` quando o pago do grupo fica abaixo do já devolvido (`cancel_ops.gravar_comprovante_no_grupo` → `reaplicar_por_dinheiro`). O Jinja só recusa o dia cancelado: no principal vivo, excluir o comprovante passa e deixa o grupo abaixo da devolução do dia cortado | some com a remoção do Jinja; até lá, comprovante só pela tela nova |
| 117 | **P4** | estorno órfão da exclusão nos dias 1 a 5 (tela de Comissões) | com o repasse do mês anterior ainda aberto, o estorno nasce com a data desse ciclo (`primeiro_repasse_aberto`) e a tela o mostra duas vezes: no mês anterior, pelo `sale_date`, e no corrente, pelo resgate de órfão pendente (`comissoes_ops._estornos_do_mes`). A Planilha o mostra uma vez só | o resgate do mês corrente só é preciso para o órfão de antes da 306, que herdou a data da venda: pular o que já cai num ciclo aberto |
| 118 | **P2** | tipo de evento nulo fora da DRE (evento vivo) | `_compute_drg` (`app/financeiro/routes.py`), a DRE da API (`financeiro_read.py`) e a Tendência (`dre_ops.py`) filtram `event_type != 'ENSAIO'`, que no SQL descarta o `NULL`: a venda viva sem tipo não entra na receita. O retido dos cancelados vem de `cancel_ops.cancelados_do_periodo`, que não descarta o nulo — a assimetria foi aceita pela 306 (P-16) | a mesma troca da dívida 47 (`or_(event_type.is_(None), event_type != 'ENSAIO')`), com o dono: muda números da DRE |
| 119 | **P3** | parcelas nunca marcadas como recebidas (`EventInstallment.received`) | nada grava `received = True`: a coluna nasce falsa e `comercial_ops.substituir_parcelas` apaga e recria as parcelas sem ela. Os Recebimentos Previstos (`financeiro_read.py` e o gêmeo Jinja) listam até o sinal já pago de evento vivo; a 306 só tirou o cancelado da lista | decidir com o dono como a parcela se baixa (pelo comprovante ou por um "recebida" na tela); até lá, nenhum relatório deve confiar na coluna |
| 120 | **P4** | `/admin/desempenho` (`admin_config_read.api_admin_desempenho`) | a régua das vendas é outra que a do Dashboard Comercial (`vendas_ops.list_closed_sales`): conta pela data do evento (`start_at`), não pela data da venda; conta como venda o satélite, o ensaio e o evento sem valor; agrupa pelo nome do vendedor e usa o mês padrão em UTC (`datetime.utcnow()`). A 306 só tirou o cancelado e somou o retido à parte, mapeando o vendedor congelado de id para nome | alinhar à régua de `list_closed_sales`, com o dono — muda números da página |
| 121 | **P4** | desconto de comissão sem repasse futuro (1e-Q8 = B) | o ajuste negativo de quem não tem mais repasse (saiu da empresa, deixou de comissionar) fica `a_pagar`, à vista, para sempre, sem baixa. Decisão do dono: por enquanto nada, mas anotado para a negociação da saída | nada no código até o dono pedir; a lista é `commission_payments` com `amount < 0` e `status = 'a_pagar'` do beneficiário |
| 122 | **P3** | comissão paga × venda viva alterada depois do repasse (1b-Q12 = B) | `_sync_commission_payment` não mexe em linha paga: a venda que sobe depois do pagamento não paga a diferença ao vendedor | dono: item **1e** do backlog (a venda que sobe paga a diferença no próximo repasse; a que desce não desconta), que reaproveita a reconciliação no primeiro repasse aberto da 306 |
| 123 | **P3** | D20 — "Pago" sem prova de saída no Gasto Extra | o status "Pago" do gasto se marca à mão sem comprovante de saída; no caso 1246, três gastos foram marcados "Pago" com um PIX de **entrada** anexado como nota fiscal. Decisão do dono (29/09): não agora | exigir o comprovante de saída ao marcar "Pago", quando o dono pedir |
| 124 | **P4** | resíduo da trava (seção Travas do plano da 306) | um "pago" da Planilha (`liquidar_periodo`, `pay_seller_month`) cuja instrução começou antes de a reconciliação gravar uma linha nova do mesmo beneficiário não a vê: a linha fica aberta naquele ciclo e aparece na Planilha. Nada se perde | se incomodar, `pg_advisory_xact_lock` por beneficiário em `liquidar_periodo`, `pay_seller_month` e na trava das linhas de comissão do ato (T4) |
| 125 | **P4** | `POST /api/gastos` (`gastos_write.api_gastos_create`) | o comprovante é salvo (`gastos_ops.save_receipt`) antes de `create_expense` validar: no 400 de validação e no 409 `devolucao_travada` (devolução ligada a evento cancelado, novo na 306) o arquivo fica em `expenses/` sem gasto. Raro | remover o arquivo no `except`, como `cancel_ops.gravar_comprovante_no_grupo` faz com o comprovante do evento |
| 126 | **P3** | ensaio que o Google não apagou (cancelamento, "Cancelar ensaio", troca de tipo) | o cancelamento tira os ensaios do banco na transação do ato e do Google depois do commit (`cancel_ops._remover_do_google`). Se o Google recusa (e sempre no `manto_local`, onde a trava não deixa remover), o ensaio continua na agenda da empresa e o próximo sync o importa como ENSAIO novo, sem show: o título "🟧 ENSAIO" vira o tipo, e o pai não é ligado. A tela avisa e cita os ensaios. O "Cancelar ensaio" e a troca de tipo que sai de SHOW (`event_ops.delete_ensaio`) já tinham o mesmo risco: apagam do banco mesmo com o Google falhando. O show cancelado não volta, porque o sync não encosta em evento cancelado. Irmã da 81 (exclusão) | lembrar os ids do Google dos ensaios apagados e não reimportá-los (ou reconferir no sync seguinte), em vez de importar um órfão |
| 127 | **P4** | `MOTIVO_AJUSTE_CORTE_DE_DIA` (`app/constants.py`) | o corte de um dia refaz a comissão do principal que fica sempre que a cheia muda (`cancel_ops._seguir_o_corte`), também na EducaManto em que a venda não muda e só o custo cai (o cachê do dia cortado sai da base); a nota diz "Corte de dia: venda diminuiu" nos dois casos | texto neutro ("Corte de dia: comissão refeita"), mantendo o prefixo antigo reconhecido em `MOTIVOS_AJUSTE_COMISSAO`: a nota é a chave do motivo das linhas já gravadas, e a 1e lê o código dela |
| 128 | **P4** | skill `financeiro` (`.claude/skills/financeiro/SKILL.md`) | as "Convenções que mudam resultado" não sabem do cancelado: tratam toda linha negativa de comissão como estorno e não dizem que o cancelado entra pelo retido, no mês do cancelamento (`event_cancellations`), que o ajuste do cancelado fica ligado ao evento e nasce no primeiro repasse aberto, nem que a devolução à cliente não é gasto na DRE. A pergunta "quanto vendemos em outubro?" pela skill dá outro número que a DRE | apontar a skill para os invariantes do cancelamento no `docs/04` e pôr as três tabelas novas no mapa |
| 129 | **P4** | verifies não versionados de `scripts/db/` que a 306 envelheceu | `verify_cancelamento_evento.py` (224) cancela sem `modo` (hoje 400 `devolucao_modo`) e espera o estorno cheio da comissão paga; `verify_158_financeiro_comissoes.py` compara a API de Comissões com o `comissoes()` Jinja, que agora divergem (`no_banco`, dívida 113); `verify_estorno_comissao_mes.py` (224c) semeia o estorno do jeito antigo (sem evento, na data da venda); `verify_187_comissoes.py` e `verify_199_no_banco_comissao_recorrente.py` testam Comissões e o "no banco" de antes da 306. A pasta é gitignored: nenhum deles foi rodado contra a 306 nem está no `--regressao` do `verify_306` | não rodar sem reescrever; reescrever um quando a regra dele for tocada de novo, ou mover para o arquivo morto com o dono |
| 130 | **P4** | "Pagar Mês" de Comissões (`comissoes_ops.pay_seller_month`), herdado da 187 | junta `_pending_reversals_query` sem olhar o mês: pagar qualquer mês liquida o estorno órfão que a tela só mostra no mês corrente (achado do converge da 306, refutado como escopo — a 306 só estreitou o filtro ao órfão) | liquidar o órfão só pelo mês em que a tela o mostra |
| 131 | **P4** | passagem da venda com BV em satélite (observação sobre a dívida 90) | se a dívida 90 deixar um BV preso num satélite e esse dia virar o novo principal na passagem, o BV passa a contar na venda do grupo e é proporcionado pelo corte; a prévia não o mostra. Zero casos no espelho e na produção (contagem de 19/10) | some com a correção da 90 |

## Baixa da feature 311-aviso-prazo-pagamento (2026-10-20, branch)

**Quitada.** A data do aceite voltou à tela `/portal/termos` (a Jinja da 091 mostrava; a 191 perdeu).

**Criada.**

| # | Prioridade | Onde | O quê | Saída |
|---|---|---|---|---|
| 132 | **P3** | escalação e pagamento × `Talent.terms_accepted_at` | o termo (prazo de pagamento, uso de imagem) só é exigido para usar o portal; escalar e pagar não olham o aceite. No backup de 20/10, 128 de 309 ativos não tinham aceitado, e 30 deles já tinham trabalhado em evento | decisão do dono: avisar o casting ao escalar quem não aceitou, ou exigir o aceite antes do primeiro evento |

## Baixa da feature 312-cancelado-fora-das-listas (2026-10-20, branch)

**Quitadas.** 74 (ensaio e 3D no cancelado) e 84 (inventário de `/events/cancelamentos`).

**Criadas.**

| # | Prioridade | Onde | O quê | Saída |
|---|---|---|---|---|
| 133 | **P4** | Planilha de Pagamentos (`financeiro_write.py` `set-status` e `bulk-action`) | o status do cachê de uma vaga de evento cancelado ainda muda pela Planilha (fora da tela do evento, que a trava fecha) | decidir se o cachê do cancelado é editável pela Planilha (o cachê de cancelado já sai dela pela 306) |
| ~~134~~ | ~~P4~~ | ✅ **RESOLVIDO no converge da feature 312** — `figurino_ops.associate_missing_character` não grava em vaga de cancelado e `list_sheets` não a conta entre os faltantes | — | — |
| 135 | **P4** | listas internas sem o selo do cancelado | avaliações internas, as avaliações da ficha do talento e os comprovantes dos outros dias do grupo mostram o título do evento sem a situação (premissa 24 do plano 1c) | `event_situacao` onde a lista aparecer |
| ~~136~~ | ~~P4~~ | ✅ **RESOLVIDO com a 312 na `main`** — o retrato `main` (`c074657b`) × 313, rodado no pré-merge da 313 em 22/10, saiu idêntico (saída 0). Texto original: `verify_306.py` cenário 23 (retrato main × branch) | com a 312 em branch, o retrato acusa a mudança de contrato da ficha da cliente (`events[].cancelado` sai; `cancelamentos` e `event_situacao` entram — 239 diferenças, todas dessa chave). Volta a ficar verde quando a 312 estiver na `main` (a base do retrato) | nada a fazer depois do merge; registrar a base nova no `docs/03` |

## Baixa da feature 313-desconto-e-pix-na-calculadora (2026-10-21; em produção desde 22/10 ~04:58)

**Quitadas.** Nenhuma. A 100 (acréscimo negativo, que a equipe usava como desconto) continua — o desconto negociado
agora tem campo próprio, mas o acréscimo negativo segue aceito no servidor e no Jinja.

**Criadas.**

| # | Prioridade | Onde | O quê | Saída |
|---|---|---|---|---|
| 137 | **P4** | `app/orcamento/quote_ops.py` (núcleo do orçamento) | a conta do orçamento é float com `round(x, 2)` (o Princípio IX pede Decimal no backend); a 313 manteve assim de propósito — a paridade byte a byte com os 2.484 orçamentos do espelho e com a mensagem de hoje exige a mesma aritmética (plano §Complexidade). O BV, que vira dinheiro gravado, já é Decimal (305) | converter numa feature própria, com gabarito de paridade (`specs/313-…/gabarito_paridade.py`) e a lista dos centavos que mudam aprovada pelo dono |
| 138 | **P4** | memória de cálculo com BV em % (`quote_ops`, a linha do BV) | o BV que cai em meio centavo arredonda na linha (796,25 × 10% → 79,62) e no total por outro caminho (875,875 → 875,88): a memória não fecha por R$ 0,01 nessas colunas. Já era assim antes da 313 (a conta é a mesma; visto na tela aberta, T045) | a linha do BV = total arredondado − base arredondada, ou uma regra de arredondamento só, junto da 137 |
| 139 | **P5** | PDF do orçamento (`app/orcamento/pdf.py`, tabela INVESTIMENTO) | a primeira linha ("1 hora") encosta no traço do título da seção — no PDF de antes da 313 também (conferido num orçamento de 2026) | descer a tabela um respiro abaixo do traço |
| 140 | **P5** | seletor de tipo do acréscimo (`OrcamentoCalculadoraPage` → `AcrescimosEditor`) | "BV" aparece duas vezes: a tabela de preços do espelho já traz "BV" em `acrescimo_tipos` e a tela soma `acrescimo_tipo_bv` (vem de antes da 313) | deduplicar ao montar a lista (`new Set`) ou tirar "BV" de `acrescimo_tipos` nas Configurações |
| 141 | **P5** | BV em duas ou mais linhas (`quote_ops` × `orcamento_evento_ops.plano_dos_acrescimos`) | a calculadora mostra `bv_que_acompanha(Σ linhas)` e o evento grava a soma das linhas arredondadas uma a uma: pode diferir R$ 0,01 (converge da 313) | calcular o BV a repassar do quote linha a linha, como o evento |
| 142 | **P5** | `orcamento_evento_ops._linhas_v2` acima de 4h | casa as linhas do `valores_brl` com as da conta da extra pela posição; os dois filtros (`_linhas_do_snapshot` × `_linhas_do_snapshot_313`) só coincidem no snapshot que a calculadora gera — num forjado, o valor de uma linha vai para outra | um filtro só, ou casar por índice do acréscimo |
| 143 | **P5** | `deduzir_duracao` com o bruto = o final (gêmeo Jinja, bundle velho) | procura o cheio em todas as durações antes do final: se o final de uma duração for igual ao cheio de outra ("3 h pelo preço de 2 h"), deduz a duração errada — só muda o BV com acréscimo em R$ | dar preferência à duração gravada no evento quando houver |
| 144 | **P5** | a marca `versao_conta: 2` × `snapshot_v2` | o leitor refaz a conta com o `aplicar_acrescimos` de hoje e exige ± R$ 0,01: uma mudança futura de centavo nessa função, sem subir a versão, manda todo orçamento v2 para o caminho de antes sem aviso (cheio = final, o BV deixa de encolher) | qualquer mudança no núcleo sobe `VERSAO_CONTA` e trata a versão anterior; um cenário do verify segura a paridade |

## Baixa da feature 317-contratos-clicksign (2026-10-22, branch)

**Quitadas.** Nenhuma da lista; a 317 corrige de passagem as menções antigas à ClickSign "viva" em `docs/01`
e `docs/02` (a integração do CRM tinha saído na 021).

**Criadas.** (151–156; nasceram 148–153 na branch e foram renumeradas no merge em lote de 23/10.)

| # | Prioridade | Onde | O quê | Saída |
|---|---|---|---|---|
| 151 | **P3** | `render.yaml` / painel do Render | **`CLICKSIGN_ACCESS_TOKEN` nasce vazio em produção** (Princípio XIV): sem ele a integração fica desligada e a Home não mostra o painel (só ao Superadmin, com o aviso) | o dono cola o token "Plataforma Manto" no `manto-backend` no deploy (quickstart §3) |
| 152 | **P4** | `site_settings.clicksign_token` / `clicksign_sandbox` | colunas inertes desde a 021 (a 317 lê o token só da env); confundem quem lê o schema | migração destrutiva com ensaio, quando houver outra mexida em `site_settings` |
| 153 | **P4** | `app/contratos/sincronizar_ops.candidatos` | o vínculo depende do nome que os fluxos da ClickSign montam; mudar a personalização do nome no painel faz tudo cair em "A conferir" sem aviso | quando a Manto gerar o contrato pela API (feature própria, decisão 4 do dono), gravar o id da venda no `metadata` do envelope e casar por ele |
| 154 | **P5** | `ClicksignDocumento` × contratos de artista | o contrato de prestação de serviços artísticos é classificado e ignorado | ligar ao talento pelo telefone do signatário, se o dono quiser |
| 155 | **P5** | migration `d3c7a1e5b317` × `e8b4a1c7d310` (310) | as duas partem de `c5d2f7a9e306`; a que for mergeada por último precisa reencadear o `down_revision` | conferir `flask db heads` no merge |
| 156 | **P5** | `app/contratos/situacao_ops.contratos_da_home` | `sugestoes()` consulta por documento a conferir (poucos, mas é N consultas) | lote único por intervalo de datas se a lista crescer |

## Baixa da feature 318-pix-recebido-por-email (2026-10-22, branch — não mergeada)

**Criadas.** (157–161; nasceram 148–152 na branch e foram renumeradas no merge em lote de 23/10.)

| # | Prioridade | Onde | O quê | Saída |
|---|---|---|---|---|
| 157 | **P3** | InfinitePay fora da loja (cartão/link) | não manda aviso por e-mail; a 318 só vê o repasse manual ao MEI ("Prime Dreams"), que é paliativo ("É esta?" do Financeiro, sem nome, com taxa) | link de pagamento InfinitePay gerado pelo ERP para cada venda (`order_nsu` = venda), no webhook da 205/310 — depois da 310 |
| 158 | **P4** | `EventInstallment.received` | nenhum código marca a parcela como recebida; a 318 trata como "não coberta" a parcela que o recebido acumulado não cobre (mesma régua do vencimento) | marcar `received` pelo recebido do grupo, ou tirar a coluna |
| 159 | **P4** | `pix_recebidos` sem venda | o dono escolheu ignorar (sem fila); os R$ 209 mil "sem registro" de 21/10 continuariam sem tela | tela "PIX sem venda" para o Financeiro classificar (venda esquecida, aporte, empréstimo) |
| 160 | **P4** | resumo por conta (`pix_ops.resumo_por_conta`) | agrupa pelo mês do registro do pagamento (`created_at`), não do dinheiro; comprovante manual sem conta cai em "Sem conta informada" | data do pagamento no `EventPayment` e conta obrigatória no manual, quando o dono decidir |
| 161 | **P5** | `fetch_messages` (`imap_client.py`) | busca uma mensagem por vez (`FETCH` por id): 3 dias de avisos são segundos, mas o ensaio de 145 dias leva ~7 min | `FETCH` em lote (`1:n`) |

## Baixa da correção 316-tom-dos-textos (2026-10-22, branch)

**Quitadas.** Nenhuma (só texto).

**Criadas.**

| # | Prioridade | Onde | O quê | Saída |
|---|---|---|---|---|
| 145 | **P4** | `app/api/figurino_producao_write.py:223` × `app/figurino/producao_ops.py:875` | o endpoint decide o 403 por `"super admin" in exc.message.lower()`: a mensagem "Só um super admin aprova um pedido…" ficou fora da padronização para "Superadmin" porque trocar o texto viraria 400 | a exceção carrega um código (`ProducaoValidationError.code`), e o endpoint decide por ele, não pelo texto |
| 146 | **P5** | `lib/navigation.tsx` e títulos de módulo ("Banco de Talentos", "Calculadora de Orçamento", "Planilha de Pagamentos", "Calc. Orçamento", "Config. Preços") | nome de seção em Title Case convivendo com "Gerenciar catálogo" e "Exclusões e cancelamentos"; a 316 padronizou cartão e botão, não o menu | decisão de produto: um padrão para o menu inteiro, sidebar e título de página juntos |
| 147 | **P5** | mensagens da API com enum ou campo em texto (`"Status inválido (use: …)"`, `form_response_id inválido`, `Envie a lista completa em \`items\``), "Google Calendar" × "Google Agenda" (`agenda_write`, `event_ops`), cabeçalho do CSV de comissões (`lib/financeiro.ts`: "Status", "Qtd de Vendas") | ficaram fora da 316: as duas primeiras só aparecem com o frontend quebrado; o CSV pode ser lido por planilha externa pelo nome da coluna | tratar ao mexer em cada endpoint; o CSV só com o dono confirmando que nenhuma planilha depende do cabeçalho |
| 150 | **P5** | `app/email_service.py` (todos os e-mails menos o de gasto extra) | texto digitado por usuário (título de evento, nome, descrição) entra no HTML sem `escape`; um "&" ou "<" no título quebra a linha e um `<a>` colado vira link no e-mail. A 319 escapou só o aviso de gasto extra | escapar em `_info_row`/`_paragraph` exige rever quem já passa HTML pronto (negrito, links) |

## Baixa da feature 315-pedido-de-cancelamento (2026-10-22, branch)

**Quitadas.** A parte da 224 da **76** (o pedido e a recusa gravavam o `EventLog` em horário de São Paulo; saíram com
`cancel_ops.solicitar_exclusao` e `recusar_solicitacao`).

**Criadas.**

| # | Prioridade | Onde | O quê | Saída |
|---|---|---|---|---|
| 148 | **P5** | `app/api/agenda_write.py` (`api_solicitar_exclusao`, `api_recusar_solicitacao`) | as rotas velhas `/api/events/<id>/solicitar-exclusao` (POST e DELETE) seguem como segunda regra das views novas, para o bundle de antes do deploy; pelo caminho velho o corpo só com o motivo vale, e o pedido nasce sem devolução e com alcance nulo | tirar as duas regras velhas quando o bundle novo for o único (alguns dias depois do deploy); o `verify_312` 9b e o `verify_315` 17 e 26 usam o caminho velho e mudam junto |
| 149 | **P5** | `solicitacao_ops.responder_na_exclusao` × `api_delete_event` | a resposta "Evento excluído" sai depois do commit da exclusão, lida antes dela: uma recusa que commita entre a leitura e a trava do núcleo dá ao autor "recusado" e depois "excluído" (research R10) | só se aparecer na prática: ler o pedido depois da trava do núcleo, dentro de `_delete_event_flow` |

## Baixa da feature 310-pagamento-loja-virtual (2026-10-20, branch)

**Quitada.** O limite anti-abuso deixou de valer para a loja inteira: o limitador lia o IP da
infraestrutura do Render, e agora lê o do cliente (`X-Manto-Client-Ip` + `ip_do_cliente()`, `docs/01`
§3.13.4). A 88 ("Nova campanha") continua aberta, fora do escopo da 310.

**Criadas.** (162–164; nasceram 133–135 na branch e foram renumeradas no merge em lote de 23/10.)

| # | Prioridade | Onde | O quê | Saída |
|---|---|---|---|---|
| 162 | **P4** | `app/__init__.py` (`Limiter(key_func=ip_do_cliente, default_limits=[])`, sem `storage_uri`) | o Flask-Limiter guarda as contagens **em memória, por processo**: cada um dos 3 workers do gunicorn conta separado, e o limite efetivo de cada família fica até ~3× o nominal (reservar 20/min vira até ~60/min; o aviso, 60 → ~180). O próprio Flask-Limiter avisa no start ("in-memory storage… not recommended for production"). Aceito pela 310: a 310 corrigiu de quem é o balde (o cliente, não a loja inteira), não o tamanho | backend compartilhado (`storage_uri` num Redis, ou no Postgres) — serviço novo no Render, decisão do dono |
| 163 | **P3** | `INFINITEPAY_API_KEY` no painel do `manto-backend` (Render) | a **História 9 da 310** (link que vence junto com a reserva e aceita um pagamento só) está **desligada** até o dono colar a chave: sem ela o link nasce sem validade e a família ainda pode pagar um horário que já voltou para a vitrine — o pagamento atrasado vira venda ou devolução pela regra única, mas a devolução é trabalho manual no app. O código já suporta (`render.yaml` declara a chave com `sync: false`); o log do deploy diz `[infinitepay] … api_key=ausente (link sem validade)` | o dono cria a chave na InfinitePay e cola no painel do Render (nunca pelo chat); mudar env redeploya, então fora do horário |
| 164 | **P2** | `MANTO_PROXY_SECRET` nos painéis do `manto-frontend` e do `manto-backend` (Render) | a prova de que o IP do cliente veio do Node (revisão T059 da 310) fica **desligada** até o dono criar a variável com o MESMO valor nos dois serviços: sem ela o backend aceita `X-Manto-Client-Ip` sem prova, e quem chama `manto-backend.onrender.com` direto trocando o cabeçalho escapa de todo limite de taxa — o de login inclusive. O boot avisa `[proxy] MANTO_PROXY_SECRET ausente` | o dono cria um valor aleatório e cola nos dois painéis — frontend primeiro, backend depois (ao contrário, por alguns minutos todo mundo cai no mesmo balde); fora do horário |


## Baixa da feature 314-gastos-extras-filtros (2026-10-27, branch)

**Quitada.** A `/gastos` deixou de rolar para o lado e de cortar as ações (10 colunas com `min-w-[960px]` num
`max-w-6xl`). A exclusão em Gastos Extras saiu do `window.confirm` para o `ConfirmDialog` (Princípio V).

**Criadas.** (165–167.)

| # | Prioridade | Onde | O quê | Saída |
|---|---|---|---|---|
| 165 | **P5** | `GET /api/gastos` → `totals` (`gastos_ops.expense_totals`) | desde a 314 nenhuma tela lê `totals`: os cartões somam a lista já recortada na tela. O servidor ainda soma e manda o bloco à gestão | tirar `totals` do payload (e `expense_totals`) depois de confirmar que nenhum script externo o lê |
| 166 | **P5** | `GastoItemViews.tsx` (`handleReject`) | o motivo da rejeição ainda vem de `window.prompt`: sem o estilo da casa, sem campo, e no celular o diálogo nativo cobre a tela. A 314 só corrigiu o "Cancelar", que rejeitava assim mesmo | diálogo do `@manto/ui` com campo de motivo (opcional), `loading` no botão e erro no diálogo |
| 167 | **P5** | `CartaoFiltro.tsx` e cabeçalhos de tabela (`GastoItemViews.tsx`, `PagamentosPage.tsx`); linha de vínculo de evento (`GastoItemViews.tsx`) | (a) **Caixa**: rótulos de cartão-filtro e de coluna saem em CSS `uppercase` ("AGUARDANDO APROVAÇÃO"). O texto no código está em caixa de frase, mas o que se lê contraria a regra de caixa do XV. É o padrão de Pagamentos desde a 194, então entra junto da 146. (b) **Movimento**: só os grupos recolhidos (`AccordionRow`) animam. A linha "Vincular evento", a troca de lista quando se escolhe uma situação e o gasto que muda de grupo depois de uma ação aparecem sem transição (Princípio XI). A 314 manteve o comportamento antigo da tela nesses três pontos (converge G6/G11) | (a) decidir na mesma rodada da 146; (b) `AnimatePresence` + `useReducedMotion` na linha de vínculo e `layout` nas listas, conferindo o custo com 186 linhas |


## Baixa da feature 320-voltar-sem-perder-o-lugar (2026-10-27, branch)

**Quitada.** O comprovante de gasto extra deixou de usar o caminho cru (`receipt_url` sem
`assetUrl`): todo arquivo do app interno passa pelo `LinkDeArquivo`, que aplica a regra única.

**Criadas.** (168–171; eram 165–168 na branch — a 314 entrou antes com 165–167.)

| # | Prioridade | Onde | O quê | Saída |
|---|---|---|---|---|
| 168 | **P4** | listas do interno fora da 320 (Agenda já tinha; Eventos, Clientes, Figurinos, Pagamentos, Orçamentos…) | só catálogo (público e gerenciador) e banco de talentos guardam filtros no endereço e voltam na mesma rolagem; nas outras, voltar de um detalhe ainda cai no topo, e parte delas guarda filtro em `useState` | aplicar o mesmo par (`useSearchParams` + `useRestaurarRolagem`) tela a tela, quando o dono apontar a próxima |
| 169 | **P4** | links de página pública abertos do interno (formulário "Abrir" em `FormulariosAdminPage`, "Abrir página ↗" do personagem, `/gastos/recorrentes` no Dashboard, impressão de figurino) | no app instalado (iPhone pela Tela de Início) continuam abrindo "em outra aba" — uma janela sem botão de voltar, a mesma armadilha que a 320 tirou dos arquivos | abrir na mesma janela no modo app (`estaComoAppInstalado()`) com caminho de volta, como o item "Catálogo" do menu |
| 170 | **P5** | `frontend/apps/internal/e2e/` + `playwright.config.ts` (feature 180) | a suíte e2e parou na 186 (precisa de `E2E_USER_*` e ninguém roda); a 320 usou o Playwright por fora, num `verify_320_navegador.mjs` | decidir: reviver a suíte (usuário descartável como o `verify_320.py`) ou apagar |
| 171 | **P5** | build do `public` e do `portal` | o `VisualizadorDeArquivo` sai do `index.ts` do `@manto/ui`, e o Vite emite o chunk do pdf.js (366 kB) e o worker (1,4 MB) também nesses dois apps, que não abrem PDF — arquivo no `dist`, nunca baixado | subpath de export (`@manto/ui/visualizador`) se o tamanho do deploy incomodar |

## Baixa da feature 322-o-que-o-casting-fecha (2026-10-28, branch)

**Quitada.** Nenhuma.

**Criadas.** (172–174.)

| # | Prioridade | Onde | O quê | Saída |
|---|---|---|---|---|
| 172 | **P4** | `specs/273-orcamento-para-evento/verify_273.py` | o verify da 273 dá **8/15 na `main`** (mesmo número com e sem a 322): o cenário 6 espera 404 para orçamento de outro comercial e recebe 409 (a 301 mudou a regra), o 7 recebe 409 no `POST /api/events` e os 8, 10, 13, 14 e 15 caem em cascata (`'ev_criado'`). Verify velho, não regressão | atualizar os cenários 6 e 7 à regra da 301/305 e rodar de novo |
| 173 | **P5** | eventos anteriores à 322 | sem retroativo (decisão do dono): personagem de evento já criado não tem `perfil_vendido`, e nenhuma vaga antiga leva "adicionado pelo sistema"/"inserido pelo comercial". No espelho de 20/10, 87 dos 147 personagens futuros nem vieram de orçamento. O "Aplicar" do vínculo 273 preenche o tipo dos personagens casados | se o dono quiser, um script dry-run → `--execute` que relê o orçamento ligado e grava o tipo |
| 174 | **P5** | Portal do Artista, e-mail de convite, tela de figurino | o perfil vendido só aparece na página do evento (escopo da 322); o artista convidado não lê "Cantor · com maquiagem" no convite | estender `perfil` ao `portal_ops` e ao e-mail de convite quando o dono pedir |
