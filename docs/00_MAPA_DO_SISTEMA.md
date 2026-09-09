# 00 — Mapa do Sistema

> **Comece por aqui.** Este é o documento de entrada: curto de propósito. Ele responde *o que é o
> sistema*, *onde cada coisa mora*, *quais são as regras obrigatórias* e *qual arquivo abrir* para
> cada tipo de tarefa — para você não varrer 83 KB de documentação antes de escrever a primeira
> linha.
>
> Última revisão: **2026-09-08** · Estado do repositório: pós-feature **296** (revisão do harness;
> produção no **Render** desde 28/08/2026) · Head de migration: `b7d2e4f1a9c3` (confira com
> `flask db heads`).

---

## 1. O que é o sistema

ERP de uma produtora de eventos infantis e artísticos. A **agenda** é o centro: eventos sincronizados
do Google Calendar, dos quais penduram elenco (casting), figurino, financeiro (venda, comissão,
gastos, folha), clientes, catálogo público e — desde a feature 205 — um canal B2C de venda de
interações virtuais.

Backend **Flask** servindo **API JSON estrita** em `/api/*`. Frontend: **três SPAs React** num
monorepo npm workspaces, servidos por um único processo Node em produção.

O Manto **nunca escreve no Google Calendar por sincronização** — ele lê. As escritas no Google
acontecem só nos fluxos explícitos de criar/editar/excluir evento.

---

## 2. Topologia

| Camada | Onde | Papel |
|---|---|---|
| Factory Flask | `app/__init__.py` | config, 18 blueprints, guards, **7** threads de background (o laço do review-cleanup roda DUAS rotinas desde a 272: arquivos de revisão vencidos e retenção de `notifications`), rota `/uploads` |
| Schema | `app/models.py` (2.577 linhas, **68 tabelas**: 63 models + 5 associações) | fonte única do banco |
| API JSON | `app/api/` (52 módulos, **288 endpoints**) | `<dominio>_read.py` / `<dominio>_write.py` |
| Núcleo de negócio | `app/<dominio>/<algo>_ops.py` | funções puras — sem `request`/`render_template`/`flash` |
| Blueprints Jinja | `app/<dominio>/routes.py` | **legado**; ver §7 antes de confiar |
| SPA ERP | `frontend/apps/internal` (117 `.tsx`) | interface real do staff |
| SPA Portal | `frontend/apps/portal` (23) | Portal do Artista, sob `/portal/` |
| SPA Público | `frontend/apps/public` (28) | vitrine `/catalogo`, formulários, loja virtual |
| Pacotes | `frontend/packages/{ui,api-client,money}` (21) | design system, `apiFetch`/`assetUrl`, dinheiro |
| Servidor de produção | `frontend/server.js` | serve os 3 bundles + proxy reverso para o Flask |
| Hospedagem | Render — `render.yaml` (raiz) | `manto-backend` (python, disco persistente, healthcheck), `manto-frontend` (node, **sem** healthcheck), `manto-postgres`; detalhe em `docs/01` §5 |
| Deploy | push na `main` | auto-deploy nos dois serviços, ~60s, ~1 min de 502 na porta pública; regras em `CLAUDE.md` §2 e constituição §Operação |

**Regra de roteamento que quebra tudo se ignorada:** o Node só devolve ao Flask os prefixos de
`BACKEND_PREFIXES` (`frontend/server.js:192`) e os regexes de `BACKEND_PATTERNS` (`:237`). Rota fora
dessa lista cai no fallback da SPA e devolve `index.html` **com status 200** — a chamada "funciona",
o `JSON.parse` estoura e o erro vira lista vazia em silêncio.

---

## 3. Domínios: onde cada um mora

| Domínio | Núcleo de negócio | API | Tela |
|---|---|---|---|
| Agenda / Eventos | ⚠️ `app/calendar/routes.py` (3.910 l.) + `event_ops.py`, `casting_ops.py`, `observation_ops.py` | `api/agenda.py`, `agenda_read.py`, `agenda_write.py` | `internal/pages/Agenda*`, `components/EventDetail/` |
| Sync Google | `app/calendar/service.py` (única porta do Google), `sync.py` (moldura) | — | — |
| Financeiro | ⚠️ `app/financeiro/routes.py` (1.690 l.) + `comissoes_ops.py`, `vendas_ops.py` | `financeiro_read.py`, `financeiro_write.py` | `FinanceiroDashboardPage`, `ComissoesPage`, `PagamentosPage` |
| Gastos | `app/gastos/gastos_ops.py` — **modelo a copiar** | `gastos_read/write.py` | `GastosExtrasPage`, `GastosRecorrentesPage` |
| Talentos | `app/talents/talent_ops.py`, `rating_ops.py`, `importer.py` | `talents_read/write.py`, `ratings_*` | `TalentsPage`, `TalentDetailPage` |
| Figurino | `app/figurino/figurino_ops.py`, `drive_service.py` | `figurino_read/write.py` | `FigurinoListPage` |
| Portal do Artista | `app/talent_portal/portal_ops.py`, `portal_rating_ops.py`, `portal_account_ops.py`, `portal_links.py` — **melhor código do repo** | `api/portal_*.py` | `apps/portal` |
| Catálogo | `app/catalogo/`, `app/admin/catalog_character_ops.py` | `catalogo_read.py`, `admin_catalogo_*` | `apps/public` + `AdminCatalogo*` |
| Loja Virtual | `app/marketing/virtuais_ops.py` (2.325 l.) | `virtuais_public/read/write/webhook.py` | `apps/public` `/catalogo/v/*` + `internal` |
| Marketing | `app/marketing/marketing_ops.py` | `marketing_read/write.py` | `MarketingPage` |
| Impressões 3D | `app/impressoes3d/impressoes3d_ops.py` | `impressoes3d_read/write.py` | `Acervo3D*`, `Fila3D*` |
| Orçamento | `app/orcamento/quote_ops.py`, `pricing.py`, `settings.py`, `transport.py` | `orcamento_read/write.py` | `OrcamentoCalculadoraPage` |
| EducaManto | `app/educamanto/pricing_ops.py`, `package_ops.py`, `quote_ops.py` | `educamanto_read/write.py` | `EducaManto*Page` |
| Clientes | `app/clientes/client_ops.py` | `clientes_read/write.py` | `ClientesPage` |
| Formulários | `app/formularios/formularios_ops.py` (auto-vínculo de evento em `:582`, de cliente em `attempt_auto_link_client`) | `formularios_write.py`, `formularios_admin_*` | `apps/public` `/f/*` + `FormulariosAdminPage` |
| Revisão de mídia | `app/revisao/review_ops.py`, `cleanup.py` | `revisao_read/write.py` | `Revisao*Page` |
| Feedback da cliente | `app/feedback/routes.py` (sem ops; ~167 l.) | `feedback_write.py` | `apps/public` `/avaliar/:token` |
| RH | `app/api/rh_read.py` (a lógica mora aqui; `app/rh/routes.py` é casca de 33 l.) | `rh_read.py` | `RhDashboardPage` |
| Pagamentos (operadora) | `app/integracoes/infinitepay_client.py` — **única fronteira**, único lugar com centavos | — | — |

⚠️ = o núcleo do domínio **não** está num `*_ops.py`, contrariando a arquitetura declarada. Ver §7.

Detalhamento de fluxos, invariantes e armadilhas por domínio: **`docs/04_GUIA_DE_DOMINIOS.md`**.

---

## 4. RBAC

**O modelo real:** o papel é uma **string comparada por uma função chamada no início da view** —
nunca um decorator. `SUPERADMIN` passa em tudo (`app/models.py:91`). São 247 checagens em 157 linhas
do backend.

Existe um **segundo mecanismo vestigial**: tabelas `permissions`/`role_permissions` +
`User.has_permission(code)` (`app/models.py:46, 89`). Ele é usado por apenas 2 códigos e 2 arquivos
(`app/rh/routes.py:12,32` e `app/api/rh_read.py:20,22`). O código `rh.view` **nunca é semeado**
(`seed.py` só cria `user.manage`), então `/rh` é SUPERADMIN-only de fato.

| Papel | Escopo | Notas |
|---|---|---|
| `SUPERADMIN` | tudo | `has_permission()` sempre `True`; único que ultrapassa o teto de cachê |
| `CASTING` | escalar elenco, talentos, materiais de ensaio | |
| `FIGURINO` | fichas de figurino, peças, sync do Drive | |
| `COMERCIAL` | venda, clientes, orçamento, campanhas da Loja Virtual | |
| `FINANCEIRO` | comissões, planilha de pagamentos, gastos, folha, usuários | |
| `ENSAIO` | agenda + bloco de ensaio + painel próprio + EducaManto (uso) | `_CAN_ENSAIO_MATERIAL` em `app/calendar/routes.py:3627` |
| `REVENDEDOR_EDUCAMANTO` | agenda (leitura) + EducaManto | guard próprio em `app/__init__.py:426` |
| `MARKETING` | calendário editorial + espaços de revisão | |
| `ARTISTA_3D` | Acervo e Fila 3D + leitura de evento | precisa do elenco e do pré-contrato |

Fonte: `app/constants.py:231-243`. Tabela completa de gates por endpoint: `docs/01` §4.3.

**"Ver como" (impersonação).** `IMPERSONABLE_ROLES` = CASTING, FIGURINO, COMERCIAL, FINANCEIRO,
ENSAIO (`app/constants.py:254`). ⚠️ **Não é uniforme**: `session['impersonate_role']` é consultado em
agenda/dashboard/auth (`app/api/agenda.py:138`, `agenda_write.py:85`, `dashboard.py:23`,
`auth.py:38`) mas **ignorado** pelas ~12 cópias de `_has_role` em `app/api/`. Com "Ver como" ativo, a
agenda respeita o papel simulado e clientes/financeiro/admin não.

**Armadilha de nome:** `_require_vendas()` significa conjuntos **diferentes** conforme o arquivo —
`{COMERCIAL, SUPERADMIN}` em `app/api/orcamento_read.py:30`, `{COMERCIAL, FINANCEIRO, SUPERADMIN}`
em `clientes_read.py:24`, `clientes_write.py:25` e `formularios_admin_read.py:24`. Ler o nome do gate
não basta: abra o arquivo.

**RBAC de arquivo** (feature 216): `/uploads/<path>` despacha por primeiro segmento do caminho —
`UPLOADS_ROLE_BY_SUBFOLDER` (`app/__init__.py:66-71`) e `expenses` checado por **dono** no banco
(`_can_read_expense_receipt`, `app/__init__.py:94`). Devolve **404, não 403**, para não confirmar
existência.

**No frontend, RBAC nunca é decidido no cliente:** ou o payload traz a chave (bloco ausente = seção
não renderiza) ou traz `flags.<nome>` (11 flags geradas por `_role_flags`,
`app/api/agenda_read.py:136-161`).

**Terceiro padrão (feature 272): RBAC na emissão, escopo por dono na leitura.** As notificações
internas (`notifications`) são endereçadas por papel **quando o fato acontece**
(`notificacoes_ops.DESTINATARIOS_POR_KIND`) e gravadas como `user_id`; os endpoints
`/api/notificacoes*` não têm gate de papel — filtram sempre por `current_user.id` no servidor e
devolvem 404 (não 403) para id alheio. "Ver como" **não** troca a caixa: ela é da pessoa, não do
papel.

---

## 5. Convenções obrigatórias

**Python** — type hints em todas as funções; docstring Google style em classes e funções públicas;
funções de até ~30 linhas; constantes `UPPER_CASE` no topo; **nunca** `except Exception` sem logar
(o padrão adotado é `except Exception as exc:  # noqa: BLE001 — <motivo>` + `logger.warning`).
Routes só validam RBAC, chamam `*_ops` e serializam. `*_ops.py` nunca importam `flask.request`.

**Frontend** — só Tailwind + `@manto/ui`, zero CSS solto. Dinheiro sempre via `formatBRL`/`parseBRL`
de `@manto/money`. Arquivo servido pelo Flask sempre via `assetUrl()` de `@manto/api-client`.
Toda ação tem loading/erro/sucesso via TanStack Query; erro da API nunca apaga o que o usuário
digitou — aponte no campo (`ApiRequestError.fields`).

**Comentário explica o PORQUÊ** (a armadilha, a razão da escolha), nunca o óbvio. Tudo em pt-BR.

**Contrato de erro da API** — envelope único `{"error": {"message": str, "fields": {campo: msg}}}`
via `json_error` (`app/api_utils.py:16`). `api_login_required` devolve **401 JSON**, nunca redirect.

**Novo módulo em `app/api/`** só existe se for importado em `app/api/__init__.py` (linhas 12-68) —
sem isso a rota não é registrada e **não há erro nenhum**.

**Novo componente em `@manto/ui`** só existe se for exportado em `packages/ui/src/index.ts`.

---

## 6. Armadilhas transversais

As que quebram em silêncio. Leia esta seção inteira uma vez.

1. **Dois relógios no mesmo model.** `CalendarEvent.start_at/end_at` (`app/models.py:233-234`) são
   **horário de parede de São Paulo, naive** (convenção em `app/calendar/service.py:207-211`);
   `created_at/updated_at` (`:236-237`) são **UTC**. Mesmo tipo `db.DateTime`, zero anotação. A API
   serializa com `.isoformat()` — **o ISO não é um instante UTC**. No React use `lib/horaLocal.ts`
   (recorte de string); `new Date(iso).toISOString()` desloca +3h e regrava errado no banco **e no
   Google Agenda**.
2. **Terceiro relógio.** As tabelas `virtual_*` (feature 205) usam `now_sp()`
   (`app/constants.py:114`) até em `created_at`. Comparar `VirtualOrder.created_at` com
   `CalendarEvent.created_at` mistura relógios com 3h de diferença. `notifications.created_at`
   (feature 272) também é `now_sp()` — comparar com `audit_logs.created_at` (UTC) erra 3 h.
3. **`date.today()`/`utcnow()` em código de negócio é bug latente**: produção roda em UTC, então
   depois das 21h de Brasília o dia já virou. O relógio canônico é `now_sp()`.
4. **Dinheiro é `Numeric(12,2)`/`Decimal`**, `ROUND_HALF_UP` em 2 casas. JSON trafega reais decimais.
   Centavos só existem em `app/integracoes/infinitepay_client.py`. Bug Postgres-only conhecido:
   `float − Decimal`.
5. **`PATCH /api/events/<id>` é edição EM BLOCO**: reconcilia elenco e **substitui** clientes. Corpo
   incompleto apaga elenco e clientes. Para campo isolado use os endpoints estreitos da feature 215
   (`/basico`, `/comercial`, `/clients`, `/form-response`).
6. **O título do evento no Google é a fonte de verdade do elenco.** `parse_characters`
   (`app/calendar/routes.py:1935`) separa por `+`. Renomear no Google **apaga `EventRole`** e dispara
   e-mail de remoção ao talento.
7. **`parent_event_id` (ensaio → pai) ≠ `group_leader_id` (agrupamento comercial).** Nunca reutilizar
   um pelo outro. E `CalendarEvent.client_id` é denormalização — a verdade multi-cliente é
   `EventClient`.
8. **Cada SPA precisa do SEU proxy por prefixo de mídia** (`/uploads`, `/catalogo/midia`,
   `/catalogo/og`, `/portal/photo`). A entrada de um app não vale para o outro. Prefixo que colide com
   rota do React Router (`/figurinos`, `/formularios`) só entra por **regex escopado ao sub-path**.
9. **Cache do bundle.** `frontend/server.js` manda `no-cache` para HTML e `immutable` para
   `assets/*`. "Verifiquei em produção" ≠ "o usuário está com isso".
10. **Idempotência é por restrição de banco, não por confiança no fluxo**: `UNIQUE(order_id, kind)`
    para avisos, `UNIQUE(transaction_nsu)` para webhooks, `UNIQUE(user_id, due_date)` para
    salários. Siga o padrão — e quando a regra de negócio impede a restrição (os lançamentos
    recorrentes perderam a `UNIQUE(recurring_id, month_ref)` na 121, porque o pagamento programado
    gera 2 por conta/mês), serialize a geração com `pg_advisory_xact_lock` (hotfix 271).
11. **Campos JSON moram em `db.Text`** com uma property `*_list`/`*_items` tolerante que devolve `[]`
    em JSON corrompido. **Nunca** `json.loads` direto na coluna.
12. **Valores congelados por design**: `OrcamentoHistory.result_snapshot`, `EducaMantoQuote.snapshot`,
    `EventAcrescimo.amount_brl`, `VirtualOrder.price_*`, `CommissionPayment.event_title`. Mudar o
    preço depois **não** altera o histórico. É intencional.
13. **`SiteSetting` é singleton `id=1`** — 45 dos 47 acessos usam `.query.get(1)`.
14. **`CatalogItem` tem DOIS FKs vindos de `CatalogCharacter`** desde a 209 (`catalog_item_id` e
    `own_item_id`, `app/models.py:1915`) — sem `foreign_keys` explícito o mapper quebra no boot com
    `AmbiguousForeignKeysError` (`app/models.py:1853`).
15. **Migrations são escritas à mão** (Alembic, head único; `flask db migrate` é proibido — o drift
    antigo entraria e derrubaria o start). O Render roda `flask db upgrade && python seed.py` no
    start (`startCommand` do `render.yaml`); **papéis novos vêm por `seed.py`, não por
    migration**.
16. **`Dialog` centraliza por flex, nunca por `translate`** (`packages/ui/src/components/dialog.tsx:45-58`)
    — o Framer Motion escreve `transform` inline e vence a classe.
17. **`BACKEND_URL` precisa do esquema** (`https://manto-backend.onrender.com`); sem ele o `http-proxy`
    estoura `TypeError` síncrono e mata o processo. É envVar `sync: false` do `manto-frontend`
    (`render.yaml`). Backend vivo se prova por um endpoint `/api/` — nunca pelo `/health` público,
    que cai no fallback da SPA (`docs/01` §5.3).
18. **Rota pública nova precisa entrar no proxy.** O Node só devolve ao Flask `BACKEND_PREFIXES` e
    `BACKEND_PATTERNS` (`frontend/server.js`); rota fora da lista cai no fallback da SPA com 200 (§2).
    Entra no mesmo commit da rota.
19. **Cookie de sessão é mudança de DUAS partes.** Trocar `SESSION_COOKIE_DOMAIN` exige inscrever o
    domínio antigo em `Config.SESSION_COOKIE_DOMINIOS_OBSOLETOS` (`app/config.py`). Desligar a
    variável não recolhe o cookie já gravado: ele viaja na frente do host-only, o Werkzeug lê o
    primeiro, e a pessoa fica em 401 para sempre — e todo teste de agente passa, porque cliente
    limpo não tem o órfão (feature 295).
20. **Contratos imutáveis — URLs gravadas fora do software.** `/nfc/<code>` está gravado em tags NFC
    físicas já entregues (`NFC_PREFIX`, `frontend/server.js`); `/avaliar/<token>` e `/cadastro`
    circulam em mensagens já enviadas. Renomear prefixo quebra coisa que já saiu daqui, sem sintoma
    no código.
21. **Campo novo do payload é opcional no React.** Backend e bundle ficam em versões diferentes por
    minutos em todo deploy (e por horas quando o cache morde): `data.campo_novo.x` derruba a árvore
    inteira (tela branca). Tipar `campo?:` e sair com `null`. `tsc` limpo não pega isso.
22. **`onError` de `<img>` não pega 404 vindo do cache** (o evento não borbulha e dispara antes do
    commit): use `<Foto>` de `@manto/ui`, que decide num `useEffect` por `complete && naturalWidth
    === 0`. E hook criado com id de `useState` fica preso ao valor antigo dentro do próprio
    `onSuccess` — passe o id por argumento.
23. **"Vídeo corrompido" quase nunca é corrupção: meça o peso primeiro** (feature 297). Os dez
    vídeos das tags NFC eram arquivos crus de câmera — 4K, até 76 Mbps, 147 MB para 16 segundos —
    íntegros, H.264 válido, servidos com `206` correto. O que falhava era a decodificação: dez
    players 4K na mesma tela esgotam o navegador, e nenhuma cliente em 4G carrega isso. Antes de
    suspeitar de codec, MIME ou proxy, rode `ffprobe` e olhe resolução, bitrate e tamanho.
24. **O `ffmpeg` existe no contêiner do Render mas NÃO está no `render.yaml`** (`/usr/bin/ffmpeg`,
    5.1.9, com `libx264`): ele vem da imagem base do runtime Python. Todo código que depende dele
    checa `video_ops.ffmpeg_disponivel()` e degrada com segurança. Dívida 34 do `docs/05`. Na
    máquina de desenvolvimento o ffmpeg é LGPL e **não** tem `libx264` — só `libopenh264`; por isso
    `video_ops.encoder_disponivel()` escolhe em vez de fixar.

---

## 7. Antes de refatorar: onde a arquitetura declarada não vale

O repositório está no meio de uma migração Jinja → API+SPA e há **três estágios** convivendo. A regra
"o núcleo está em `*_ops.py`" **falha exatamente nos dois domínios mais importantes**:

- `app/calendar/routes.py` (3.910 linhas) exporta **39 símbolos privados** consumidos por 10 módulos
  (`app/api/agenda_write.py` sozinho importa 25). `event_ops.py` importa 8 de lá.
- `app/financeiro/routes.py` (1.690 linhas) exporta `_event_commission`, `_commission_beneficiary`,
  `_is_permuta`, `_resolve_period`, `_compute_drg` para `vendas_ops.py` e `financeiro_read.py`.

Os imports são **tardios (dentro das funções)** para quebrar ciclo — renomear um `_helper` ali quebra
a API em silêncio e **não aparece em análise estática de topo**.

Além disso, boa parte da superfície Jinja está **inalcançável em produção** (fora de
`BACKEND_PREFIXES`) mas ainda registrada: 18 das 20 rotas de `calendar_bp` e 20 das 21 rotas de
`app/talent_portal/routes.py`. Onde há duplicação Jinja↔API, **as duas implementações estão vivas
via acesso direto ao host do Flask** e já divergem.

Inventário completo, com o que é morto, o que é duplicado e como fatiar: **`docs/05_DIVIDA_TECNICA.md`**.

---

## 8. Por onde começar, por tipo de tarefa

| Tarefa | Leia, nesta ordem |
|---|---|
| **Qualquer tarefa** | este arquivo (§4, §5, §6) |
| Campo novo no evento | `docs/04` §Agenda → `app/models.py` (`CalendarEvent`, 217-361) → `app/api/agenda_read.py:502` (`serialize_event_detail`) → `internal/src/lib/agenda.ts` → `components/EventDetail/` |
| Endpoint novo | `docs/01` §3 (inventário) → módulo `app/api/<dominio>_{read,write}.py` → **registrar em `app/api/__init__.py`** |
| Regra de comissão / DRE | `docs/04` §Financeiro (a regra completa está lá, em 9 pontos) → `app/financeiro/routes.py:120-350` |
| Mexer no sync do Google | `docs/04` §Agenda → `app/calendar/sync.py` (moldura) → `sync_events` em `app/calendar/routes.py:2149` |
| Tela nova no ERP | `docs/02` (telas vizinhas) → rota em `internal/src/App.tsx` → item em `lib/navigation.tsx` (`isVisible`) → módulo em `lib/` → página em `pages/` |
| Componente compartilhado | `packages/ui/src/components/` → **exportar em `packages/ui/src/index.ts`** |
| Loja Virtual / pagamento | `docs/04` §Loja Virtual → `app/marketing/virtuais_ops.py` → `app/integracoes/infinitepay_client.py` |
| Portal do Artista | `app/talent_portal/portal_ops.py` (o padrão a copiar) — **não** `app/talent_portal/routes.py` |
| Entender uma decisão antiga | `docs/03` (índice) → `Read` com `offset` só na entrada da feature |
| RBAC de um endpoint | docstring de **topo** do módulo (é onde a intenção está escrita) → `docs/01` §4.3 |
| Shape do JSON de um endpoint | não há atalho nem OpenAPI: ache o serializer (`serialize_*`/`_*_dict`) no `_read.py` e cruze com a interface TS em `frontend/apps/*/src/lib/` |

---

## 9. Como se verifica trabalho aqui

**Não existe suíte de testes.** Não há `tests/`, não há `pytest` (`pyproject.toml` declara isso).
O que faz as vezes de teste são os `specs/NNN-nome/verify_NNN.py` (versionados; os anteriores à 266
em `scripts/db/`, que é gitignored), rodados contra a cópia local do Postgres de produção
(`manto_local`) com `DATABASE_URL` de `.local-db-url`, `FLASK_ENV=development` e
`MANTO_SEM_THREADS=1` — o espelho traz credenciais reais (`docs/01` §5.4). Esqueleto e os cinco
modos de um verify passar verde sem testar nada: `DEVELOPMENT.md` §Escrever um verify e a skill
`manto-verify`.

Typecheck do frontend: `cd frontend && npm run typecheck` — cobre os **três** apps
(`frontend/package.json`). Não use `npx tsc --noEmit` app a app: esquece o portal. `tsc` limpo não
é verificação de UI: abra a tela (skill `manto-conferir-tela` — inputs no Browser pane não chegam
ao react-hook-form sem o setter nativo + `dispatchEvent`; Radix ignora `.click()`).

Produção é PostgreSQL. Verificação contra o SQLite vazio de `instance/` não pega bugs Postgres-only.

---

## 10. Mapa dos documentos

| Documento | Contém | Custo |
|---|---|---|
| `00_MAPA_DO_SISTEMA.md` | este arquivo: topologia, RBAC, convenções, armadilhas, por onde começar | ~5k tokens |
| `01_SISTEMA_E_BANCO.md` | schema por domínio, inventário de endpoints, tabela de gates de RBAC, build/deploy e operação no Render (§5) | ~25k |
| `02_MAPA_DE_PAGINAS_E_UX.md` | uma entrada por tela: objetivo, acesso, UX, API consumida, vínculos | ~25k |
| `03_HISTORICO_MUTACOES.md` | **índice** de features + as mais recentes (append-only) | ~4k o índice |
| `docs/historico/*.md` | entradas arquivadas por faixa de feature — leia só por `offset` | — |
| `04_GUIA_DE_DOMINIOS.md` | fluxos, invariantes e armadilhas por domínio (última revisão 2026-08-06) | ~12k |
| `05_DIVIDA_TECNICA.md` | achados priorizados, com arquivo:linha e ação concreta; pendências operacionais | ~9k |
| `render.yaml` (raiz) | **não é doc, é o que roda**: blueprint de produção; prevalece sobre qualquer texto | — |
| `CONTINGENCIA_RENDER.md` | registro histórico da migração Railway → Render (28/08/2026); não é runbook | ~2k |
| `PLANO_REMOCAO_JINJA.md`, `PARADA_REMOCAO_JINJA.md`, `PLANO_EXTRACAO_CALENDAR.md` | planos **pausados** por decisão do dono; leia a PARADA antes de retomar | — |
| `archive/` | morto: `CLAUDE_2026-07.md`, `constitution-2.1.0.md`, `changelog.html` (congelado) | — |
| `planos.md`, `EspecificacoesEducamanto.md` | conteúdo comercial (pacotes/planos), não é doc de sistema | — |

**Fonte única por tipo de fato** (para as cópias não divergirem): contrato de API e schema só no 01;
infra/deploy/operação só no 01 §5 (o `render.yaml` prevalece sobre o texto); fluxo de tela só no 02;
motivação/decisão/pegadinha histórica só no 03; fluxo e invariante de domínio só no 04; dívida só no
05. Regras de trabalho do agente: `CLAUDE.md`; princípios: constituição; procedimento: `DEVELOPMENT.md`.
Citação `arquivo:linha` se confere contra HEAD na hora de escrever — arquivo que muda na mesma
rodada (`.gitignore`, `render.yaml`) se cita pela entrada/chave, não pela linha.

Arquivos de leitura cara, para planejar o orçamento de token: `app/models.py` ≈ 39k tokens ·
`app/calendar/routes.py` ≈ 49k · `app/financeiro/routes.py` ≈ 21k · `app/marketing/virtuais_ops.py`
≈ 28k. Nenhum deles tem índice interno — prefira `Grep` e `Read` com `offset`.
