# 01 — Sistema e Banco de Dados

> **Documento vivo.** Atualizado obrigatoriamente ao fim de cada feature (ver regra em
> `CLAUDE.md` → "REGRA OBRIGATÓRIA DE DOCUMENTAÇÃO VIVA").
>
> **Não comece por aqui.** O documento de entrada é `docs/00_MAPA_DO_SISTEMA.md` (topologia, RBAC,
> convenções e "qual arquivo abrir para cada tarefa"). Este 01 é a referência de **schema (§2),
> endpoints (§3), RBAC (§4) e deploy (§5)** — consulte por seção, não do começo ao fim.
>
> Última atualização: **2026-10-21** · **313-desconto-e-pix-na-calculadora** (EM PRODUÇÃO desde 22/10/2026 ~04:58; sem migration; o desconto
> negociado e o PIX que vale o maior em `/orcamento/calcular`, a ordem da conta da Q7 marcada por `versao_conta: 2` no
> snapshot, o cheio e o final no prefill, no Novo evento e no vínculo 273, `duracoes_do_desconto` no 400 — §3.13,
> "Feature 313"; nenhum gate muda, §4.3). Antes: **2026-10-20** · **312-cancelado-fora-das-listas** (sem migration; o cancelado sai do Dia, da busca, das
> fichas, dos seletores, das filas e do painel do grupo; a trava `exigir_evento_vivo` e as recusas de vínculo com `codigo:
> "cancelado"`; `GET /api/events/cancelamentos` também para o FINANCEIRO, com `mes`/`devolucao`; o card `cancelamentos` no
> pipeline; `casting.cancelados_a_avisar`; a avaliação pública 410 — §4.3, "O cancelado fora das listas"). Antes: **2026-10-20** · **306b-motivo-editavel** (sem migration; `PATCH /api/events/<id>/motivo-cancelamento`, §3.3; `pode_editar_motivo_do_cancelado` e a flag
> `can_edit_motivo_cancelado`, §4.3). Antes: **2026-10-20** · **306-dinheiro-do-cancelamento** (EM PRODUÇÃO desde 20/10/2026 ~09:30; migration
> **`c5d2f7a9e306`** — head: as tabelas `event_cancellations`, `event_cancellation_bvs` e
> `event_cancellation_elenco`, §2.2; o ajuste e o `no_banco` das comissões, a categoria "Multa de
> cancelamento" e a devolução de cancelado travada, §2.6; a cobrança desconta a devolução, §3.2;
> `PATCH /api/events/<id>/devolucao`, `POST /api/events/<id>/multas`, o cancelar reescrito e o
> cancelar do marcado liberado, §3.3; o retido na DRE, no Comercial e na Planilha, §3.6; Gastos
> Extras, §3.7; o bloqueio `cancelamentos` na exclusão de usuário, §3.11; kinds `evento.cancelado`
> e `evento.cancelado_escala`, §3.13.5; a regra única do cancelado, o gate e o 409 de cada porta e
> os 18 códigos de 409, §4.3; a trava `CALENDAR_SUPPRESS_EVENT_WRITES` passa a cobrir a remoção do
> Google no cancelamento, §2.4.1 e §5.4). Antes: **2026-10-20** · **309-produtos-de-tabela** (EM PRODUÇÃO desde 20/10/2026 ~09:15, a pedido do dono; sem migration — head
> continua `a7c3e91f4d28`; blocos `produtos` e `produtos_estimativa` no `pricing_config` e "Papai Noel"/
> "Ajudante do Noel" de volta a 600/270, §2.10; `produtos` no payload, `quote` e `snapshot` de
> `/orcamento/calcular`, validação do bloco em `/orcamento/settings`, teto das vagas do produto no
> prefill/criação/vínculo, §3.13). Antes: **2026-10-16** · **307-natal-papai-noel-calculadora** (EM PRODUÇÃO desde
> 16/10/2026 ~01:25; sem migration — head continua `a7c3e91f4d28`; bloco `datas_especiais` no `pricing_config`, §2.10;
> `data_especial` no quote de `/orcamento/calcular` e validação do bloco em `/orcamento/settings`,
> §3.13; gate de `orcamento_write` na tabela, §4.3). Antes: **2026-10-14/15** · **305-bv-do-orcamento-no-evento**
> (sem migration; em produção desde 15/10 ~02:49). Antes: **2026-09-30** · Em branch: **303-sync-nao-apaga-venda** (migration
> **`a7c3e91f4d28`** — head: coluna `calendar_events.google_missing_since` e o índice parcial
> `ix_calendar_events_google_missing_since`, §2.2; `GET /api/events/sumidos-google`, `POST
> /api/events/<id>/devolver-ao-google` e as mudanças de `/sync`, `PATCH`, `cancelar`, `DELETE`,
> agenda e detalhe, §3.3; números novos do `cleanup_past`, §3.11; produtor `evento.sumiu_google`,
> §3.13.5; `em_confirmacao` e avaliação de cancelado no portal, §3.15; gates e a trava
> `CALENDAR_SUPPRESS_EVENT_WRITES`, §4.3). Antes: **2026-09-11** · **298-formulario-vira-evento**
> (migration **`e5a1c7d93b20`**: encerramento em `form_responses` e a tabela
> `form_response_dismissed_events`, §2; bloco `formularios` do `/api/dashboard` reescrito, §3.2;
> endpoints de destino do formulário e guarda de 409 antes do Google, §3.14; RBAC, §4.3). Antes:
> **2026-09-08** · **296-revisao-harness** (sem migration; §5 reescrita para o
> Render — serviços, disco, backup, acesso ao servidor, `/health` público; `railway.json`/`nixpacks.toml`
> removidos, o validador lê o `render.yaml`). Antes: **2026-09-03** · Em branch: **292-fotos-que-somem** + **293-atualizacao-cadastral**
> (sem migration; `<Foto>` com fallback de 404, variante por largura em `figurino_photos`, `pillow-heif`
> convertendo HEIC, os 9 caminhos de upload cru passando por `save_file`, `MANTO_SEM_THREADS`, e os
> comandos `midia-orfa`/`fix-heic`/`campanha-fotos`). Antes: **272-notificacoes-internas** (tabela
> `notifications`, migration **`b7d2e4f1a9c3`** — head; endpoints `/api/notificacoes*`; o e-mail de
> resposta de formulário da 266 saiu). Antes: **270-miniaturas-catalogo** (variantes de miniatura por
> largura — sem migration) e **261-nfc-entregas-video** (entregas anexadas
> a tags NFC; migration **`e08e454c4780`** — head: tabela `nfc_tag_deliveries`; endpoints
> `POST`/`DELETE /api/3d/nfc/<id>/entregas*` e `GET /api/nfc/<code>/entregas/<id>/media`
> público; ver §2.2.1 e §3.13.2b). Anterior:
> Última atualização: **2026-08-21** · Feature **258**: `POST /api/clientes/quick-create`
> aceita `cpf`, `cnpj` e `address` (opcionais, só na criação — telefone já cadastrado devolve a
> ficha existente intocada), usados pelo cadastro manual da tela de Clientes. Antes:
> Última atualização: **2026-08-21** · Hotfix **257** em produção: os cinco POSTs de anexo do
> evento (`payments`, `contracts`, `reimbursements`, `invoices`,
> `reimbursements/<id>/collect`) ganharam o `db.session.commit()` que faltava — respondiam 2xx
> sem gravar; e `GET /api/audit-agent/<token>/orphan-attachments` (somente leitura) lista os
> arquivos órfãos que o bug deixou no volume. Antes:
> Última atualização: **2026-08-21** · Em branch: **256-auditor-marketing** (auditor de marketing
> semanal; migration **`c4d1e7b2a9f3`** — head: 7 tabelas `marketing_*` + `marketing_posts.permalink` +
> `clients.lead_origin/utm_*`; endpoints `/api/marketing-agent/<token>/{context,run,report}` por env
> `MARKETING_AGENT_TOKEN` e `GET /api/marketing/desempenho` (MARKETING/SA); ver bloco "Agente de
> marketing" abaixo do agente auditor financeiro). Anterior:
> Última atualização: **2026-08-18** · Em branch: **239-backlog-agosto** (rodada de 11 itens do
> backlog de agosto/2026 — ver `specs/239-backlog-agosto/`). Schema: `event_roles` ganhou
> `does_transport` (Boolean, nullable — "leva o carrinho de transporte fora de SP") e
> `cache_cap_note` (Text, nullable — a conta do teto em valores, só para superadmin); migrations
> **`d1c7b93a2f60`** → **`e2d8ca4b3071`** (head atual; confirme com `flask db heads`). Endpoints
> novos `POST`/`DELETE /api/roles/<id>/transporte` (gate `_can_edit_event()`; o `POST` recusa com
> 400 fora de `event.is_outside_sp`). Regras de negócio novas: **teto com carrinho** —
> `teto_efetivo = max(cache_cap + parcela_do_veículo_quando_marcado, valor_já_salvo)`, a parcela
> somada **dentro** do `max` (nunca por cima, para não virar catraca a cada "Salvar") —
> `casting_ops.valor_transporte_papel`/`set_transporte`; **vaga "Técnico de Som (Presença)"**
> travada sem valor no servidor (`assign_role`/`add_role` forçam `cache_value=None`) e fora de
> todos os somatórios de dinheiro (custo de evento, KPI, DRE, dashboard, planilha de pagamentos);
> **troca de tipo de evento** reage automaticamente ao entrar/sair de SHOW
> (`event_ops.aplicar_troca_de_tipo`), com o título novo empurrado ao Google **antes** da parte
> destrutiva (cancelar ensaios, remover vagas de som) — falha do Google nessa troca vira **409**
> `EventTypeChangeBlocked` e a troca é desfeita, nada é removido. Ver §2.2 (regras) e §3.3
> (endpoints/payload) para o detalhe completo. Scripts retroativos em `scripts/db/`
> (`cleanup_presenca_239.py`, `cleanup_show_nao_show_239.py`, `cleanup_titulos_239.py`) — só
> `--dry-run` até aqui, execução real fica para depois do deploy.
>
> Última atualização: **2026-08-14** · Em branch: **235-educamanto** (EducaManto por responsabilidades: pacotes por nível viram musicais, snapshot v2 recalculado no servidor, Jinja do EducaManto desligado; migration **`b7e3a91d5c24`**). Na main: Última atualização: **2026-08-14** · Feature **237-solicitar-ficha** (branch): kind novo `ficha` em `figurino_producoes` (sem migração; fluxo curto sem aprovação = manutenção), `POST /api/figurino/producoes/solicitar-ficha` (login, gate `pode_abrir`), e transição para `pronto` de kind=ficha exige `figurino_sheet_id`. Antes: **236-cache-por-duracao** (branch): criação de evento aceita `duracao` inteira ≥ 1 (fim do fallback que dava cachê de 1h a durações fora de 1–4h); com `orcamento_history_id`, `cache_value`/`cache_cap` são RECALCULADOS no servidor pela duração real — >4h usa a régua (base de 4h ÷ 4 × horas + adicionais fixos). Anterior: · Estado do repositório: pós-feature **225c (Pedido de
> Compra — terceiro `kind` de `figurino_producoes`, fluxo `solicitado → aprovado → comprado →
> recebido`, **sem migration**; nav: "Revisão" saiu de Produção e foi para Marketing, e nasceu
> `/compras`. Endpoint mudado: `GET /api/figurino/producoes/responsaveis?tipo=compra`)**. Antes
> dela, **235 (o mesmo
> personagem em vários temas — a identidade é a ficha de figurino, e duas linhas de
> `catalog_characters` com o mesmo `figurino_sheet_id` são o mesmo personagem em temas
> diferentes; migration `f4a8d61c9e27`: `figurino_sheets.quantity`, quantos figurinos iguais
> existem, 0 válido. Endpoints novos: `GET /api/admin/catalogo/personagens` e
> `POST /api/admin/catalogo/<id>/personagens/reaproveitar`). Antes dela, 234 (fotos do catálogo:
> `apply_photos` sempre regrava `position` — antes só regravava quando havia capa explícita, e uma
> edição que só reordenava era descartada em silêncio; `photo_order` passa a aceitar tokens
> `new:<i>` para intercalar foto nova entre as antigas; sem schema). Antes dela, 233 (convite
> automático ao escalar + `get_figurino` na regra `nao_recusada()`; sem schema). Antes dela, 232
> (avaliação por
> partes volta a ser o caminho padrão — só frontend, sem endpoint novo). Antes dela, 231 (confirmações
> pendentes — migration `e3f7c25a8b90`: `event_roles.invite_reminder_at`/`invite_reminder_count`
> e `site_settings.invite_reminder_run_at`; `GET /api/dashboard` ganhou `casting.unconfirmed`).
> Antes dela, 230 (portal segue a
> escala: `get_agenda`/`get_historico` passaram de `invite_status="accepted"` para
> `portal_ops.nao_recusada()`, e `_role_summary` expõe `invite_status`; sem schema). Antes dela, 229
> (avaliar do histórico da Agenda, só frontend). Antes dela, 228 (`ConfirmDialog` no `@manto/ui`,
> frontend) e 227 (foto do portal e figurino do coordenador: `GET
> /api/portal/events/<id>/figurino` ganhou `is_coordinator` e `talent_name`, e a agenda do portal
> ganhou `has_figurino`). Nenhuma das quatro tem schema ou migration** · Head de
> migration: **`e2d8ca4b3071`** (*explicação do teto do cachê, feature 239 — encadeada em
> `d1c7b93a2f60` → `c8f4d92e17ab`*) — confirme com `flask db heads`; este cabeçalho é a **única**
> menção ao head neste documento. (Nota: este campo ficou parado em `e3f7c25a8b90`, da feature 231,
> por várias rodadas — 235, 236, 237, 238 e catalogo-fase-1 já não estavam refletidas aqui antes
> desta correção; §2.11 tem a mesma ressalva.)
>
> **Edição por recorte (215).** `PATCH /api/events/<id>` (feature 184) é **edição em bloco**: ele
> reconcilia elenco e **substitui** os clientes. Para editar um dado isolado use os endpoints
> estreitos da 215 (`/basico`, `/comercial`, `/clients`, `/form-response`) — cada um grava só o seu
> conjunto de campos. Nunca reaproveite o PATCH em bloco para salvar um campo solto: o corpo
> incompleto apaga o elenco e os clientes que não vieram nele.
>
> **Contrato de horário (210, não-negociável).** `CalendarEvent.start_at`/`end_at` são **horário de
> parede de São Paulo**, gravados naive (`service.py::parse_event_datetime`) e serializados com
> `.isoformat()` — o ISO que a API devolve **não tem fuso e não é um instante UTC**. No React, para
> preencher formulário ou comparar datas, use `lib/horaLocal.ts` (recorte de string); passar por
> `new Date(iso).toISOString()` desloca +3h e regrava o evento errado no banco e no Google Agenda.
>
> **Cache do frontend (210d).** `frontend/server.js` declara `Cache-Control: no-cache` para HTML e
> `public, max-age=31536000, immutable` para `assets/*`. Sem isso o `serve-handler` não manda
> cabeçalho nenhum, o navegador guarda o `index.html` por heurística e o usuário fica no bundle
> antigo mesmo com o deploy no ar — "verifiquei em produção" ≠ "o usuário está com isso".
>
> **RBAC do detalhe do evento (210c).** `pagamentos` e `reembolsos` são do bloco **`show_comercial`**
> (COMERCIAL/FINANCEIRO/SUPERADMIN) — paridade com o Jinja, onde os painéis ficavam dentro de
> `{% if show_comercial %}`. Só `kpi` e `gastos` são exclusivos de `show_financeiro`. As ações
> destrutivas (editar valor/excluir comprovante e reembolso) continuam SUPERADMIN, no endpoint.
>
> **Consumo de rota do Flask pelo React (210b).** Use **sempre** `/api/*`. O servidor do frontend
> só repassa ao Flask os prefixos de `BACKEND_PREFIXES`/`BACKEND_PATTERNS` (`frontend/server.js`);
> qualquer outro caminho cai no fallback da SPA e devolve o `index.html` **com status 200** — a
> chamada "funciona", o JSON estoura e o erro vira lista vazia em silêncio. Prefixo que colide com
> rota do React Router (`/formularios`, `/figurinos`) só entra por regex restrito ao sub-path.
>
> Hotfix 210: sem migration e sem endpoint novo. `POST /api/orcamento/calcular` e
> `GET /api/orcamento/historico/<id>` passaram a incluir `quote.memoria` (detalhamento linha a
> linha do cálculo; ausente em orçamentos salvos antes da 210). Rota React nova:
> `/orcamento/:id` (orçamento gerado — WhatsApp, PDF, e-mail), declarada depois das rotas fixas
> de `/orcamento/*`.
>
> Rotas novas da 207: `GET /api/agenda/search?q=` (busca textual; nome/telefone da cliente só
> para vendas), `POST /api/admin/catalogo/personagens/<id>/adotar-foto` (SUPERADMIN),
> `DELETE /api/clientes/avaliacoes/<id>` (SUPERADMIN, auditado). Mudanças de payload:
> `GET /api/avaliar/<token>` ganhou `google_review_url`; `GET /api/clientes/avaliacoes` ganhou
> `can_delete`; `GET /api/admin/settings` ganhou `google_review_url`; no detalhe do evento a
> chave `logs` passou a ser condicional a SUPERADMIN. Sanitização de descrição do catálogo com
> `nh3` (novo em requirements.txt). Proxies (vite + server.js) ganharam
> `/figurinos/print-event/<id>`.

---

## 1. Visão geral da arquitetura

A Plataforma Manto é um ERP para gestão de eventos, talentos, figurino, financeiro, catálogo e
agenda da Manto Produções.

```
┌──────────────────────────────┐        ┌──────────────────────────────┐
│ frontend/apps/internal (SPA) │        │ frontend/apps/public (SPA)   │
│ staff autenticado            │        │ visitante anônimo            │
│ React 18 + Vite + TS         │        │ React 18 + Vite + TS         │
└──────────────┬───────────────┘        └──────────────┬───────────────┘
               │  fetch  credentials:"include"         │
               └──────────────┬────────────────────────┘
                              ▼
               ┌──────────────────────────────┐
               │ Flask — blueprint `api_bp`   │  url_prefix = /api
               │ app/api/*.py (JSON estrito)  │
               └──────────────┬───────────────┘
                              ▼
               ┌──────────────────────────────┐
               │ app/<blueprint>/<dom>_ops.py │  núcleo de negócio (funções puras)
               └──────────────┬───────────────┘
                              ▼
               ┌──────────────────────────────┐
               │ app/models.py (SQLAlchemy)   │  → PostgreSQL (Render)
               └──────────────────────────────┘
```

**Regra de dependência** (Princípio de arquitetura da constituição): a camada só pode depender da
camada abaixo. Rotas (API e Jinja legado) **não** contêm regra de negócio — apenas validam RBAC,
chamam `*_ops` e serializam.

| Camada | Stack |
|---|---|
| Backend | Python 3 · Flask · Flask-Login · Flask-Migrate (Alembic escrito à mão) · SQLAlchemy |
| Banco | PostgreSQL (produção no Render — serviço `manto-postgres`, `render.yaml`; cópia local `manto_local`); SQLite só faz o app subir |
| Frontend | React + TypeScript + Vite + Tailwind CSS + shadcn/ui + Framer Motion + TanStack Query |
| Pacotes internos | `@manto/ui` (design system), `@manto/api-client` (`apiFetch`/`assetUrl`), `@manto/money` (`formatBRL`/`parseBRL`) |
| Integrações | Google Calendar API (OAuth 2.0), Google Sheets API (service account), Google Maps Distance Matrix, ClickSign (API v3, só leitura + aviso — feature 317, §3.13.6), InfinitePay, Vimeo/Drive (mídia) |
| Storage | `app/storage.py` — `instance/uploads/` local e o disco persistente do `manto-backend` em produção (`USE_S3=false`; não há S3/R2) |

### 1.1 Escopo migrado vs. legado

- **React + API (completo)**: tudo que staff autenticado usa (`apps/internal`), as superfícies
  públicas anônimas (`apps/public`) e o **Portal do Artista** (`apps/portal`) — este último
  concluído pela feature 191 (fatia 176 entregou 5 telas; a 191 fechou conta, perfil, avaliações
  e histórico).
- **Jinja legado paralelo**: os `routes.py` dos blueprints já migrados continuam existindo
  (padrão strangler-fig), **incluindo `app/talent_portal`**. Decomissioná-los é limpeza futura.
- **A raiz não é mais Jinja (feature 206)**: `GET /` no Flask responde 301 para
  `https://app.mantoproducoes.com.br`, onde o `frontend/server.js` serve os três bundles e faz
  proxy reverso do que ainda é do backend (§5.2.1). O React é a interface primária de fato — o
  Flask só é alcançado por `/api`, mídia e a ficha de impressão.

---

## 2. Schema e Models (PostgreSQL)

Fonte única: `app/models.py` (~2,6k linhas). **~68 tabelas** — 63 models + 5 tabelas de associação
(`user_roles`, `role_permissions`, `catalog_item_categories`, `marketing_post_temas`,
`virtual_campaign_acervo`). *Números aproximados de propósito: contagem exata em prosa envelhece a
cada feature. Confira com `grep -c __tablename__ app/models.py`.*

### 2.1 Identidade, acesso e RBAC

| Tabela | Model | Colunas relevantes | Relacionamentos |
|---|---|---|---|
| `users` | `User` | `email` (unique, nullable), `name`, `password_hash`, `has_access`, `is_active`, `must_change_password`, `birth_date`, `profile_photo`, `receives_commission`, `pix_key`, `pix_key_type` | M:N `roles` via `user_roles`; 1:N `salary_histories` |
| `roles` | `Role` | `name` (unique) | M:N `permissions` via `role_permissions` |
| `permissions` | `Permission` | `code` (unique, ex.: `user.manage`) | — |
| `user_roles` | *(association)* | PK composta (`user_id`, `role_id`) | FK → `users.id`, `roles.id` |
| `role_permissions` | *(association)* | PK composta (`role_id`, `permission_id`) | FK → `roles.id`, `permissions.id` |

> `User.has_permission(code)` retorna `True` incondicionalmente para `SUPERADMIN`.
> Usuários "apenas pagamento" (`has_access=False`) têm `email`/`password_hash` nulos.

### 2.2 Agenda e Eventos (núcleo do sistema)

| Tabela | Model | Destaques | FKs |
|---|---|---|---|
| `calendar_events` | `CalendarEvent` | `google_event_id` (unique), `google_html_link`, `title`, `start_at`/`end_at`, `event_type` (`SHOW`/`CORP`/`R&I`/`ENSAIO`…), `source` (`google_calendar`\|`platform`), `sale_value`, `sale_value_gross`, `sale_date`, `with_invoice`, `is_cortesia_permuta`, `commission_rate`, `confirmed_at`, `feedback_token` (unique), `needs_rehearsal`, `group_name`, `makeup_time`/`makeup_location`, `departure_time`/`departure_location`, `travel_time_minutes`, `travel_distance_km`, `is_outside_sp`, `payment_method`, `payment_installments`, `payment_due_date`, `transport_value`, `acrescimo_value`, `invoice_file`, `invoice_due_date`, **`cancelled_at`/`cancellation_reason`** (feature 224 — preenchido = evento cancelado: sai da agenda e das métricas de venda e de casting, mas o registro fica porque é a ele que a devolução ao cliente se refere; desde a **306** o retido (pago − devolvido do grupo) entra na DRE, no Comercial e na comissão pelo mês do cancelamento (`cancel_ops.resumo_cancelado`), e o cancelado não se exclui; índice parcial `ix_calendar_events_cancelled_at`), **`deletion_requested_at`/`deletion_request_reason`** (pedido do Comercial aguardando o Superadmin; zerados ao recusar ou ao atender), **`google_missing_since`** (feature 303 — `DateTime` nullable, horário de parede de São Paulo como `cancelled_at`: quando o sync percebeu que o evento sumiu do Google Agenda e o manteve porque tinha dinheiro preso; `NULL` = não marcado; "marcado" = preenchida **e** `cancelled_at` nulo; só `sumico_ops.marcar`/`desmarcar` escrevem; não muda venda, comissão nem escala; índice parcial `ix_calendar_events_google_missing_since`) | `seller_id`→`users`, `client_id`→`clients`, `confirmed_by_id`→`users`, `cancelled_by_id`→`users`, `deletion_requested_by_id`→`users`, `parent_event_id`→`calendar_events` (ensaios), `group_leader_id`→`calendar_events` (agrupamento comercial), `orcamento_history_id`→`orcamento_history` |
| `event_roles` | `EventRole` | `character_name`, `role_type` (`character`\|`extra`), `cache_value`, `cache_cap`, **`cache_cap_note`** (Text, nullable — feature 239: a conta do teto EM VALORES, ex. "Ator cara-limpa: base 2h R$ 300 + noturno R$ 50 = R$ 350"; só sai pela API para superadmin), `travel_cache`, **`does_transport`** (Boolean, nullable — feature 239: marcador puro "leva o carrinho de transporte fora de SP", mesma semântica `True`\|`NULL` de `needs_makeup`/`is_singer`; não guarda valor), `payment_status`, `invite_status` (`pending`\|`accepted`\|`rejected`), `figurino_done_at`, `event_changed_at`, `needs_makeup`, `is_singer`, `dismissed_at` | `event_id`→`calendar_events`, `talent_id`→`talents`, `figurino_sheet_id`→`figurino_sheets`, `dismissed_by`→`users` |
| `event_observations` | `EventObservation` | observações de evento (texto/foto) | `event_id` |
| `event_contracts` | `EventContract` | arquivo + flag assinado | `event_id` |
| `event_payments` | `EventPayment` | comprovantes de pagamento com valor | `event_id` |
| `event_installments` | `EventInstallment` | parcelas (`due_date`) | `event_id` |
| `event_invoices` | `EventInvoice` | notas fiscais (`issue_date`) | `event_id` |
| `event_acrescimos` | `EventAcrescimo` | acréscimos tipados (`BV`, `Taxa de urgência`, `Outro`…) | `event_id` |
| `event_clients` | `EventClient` | múltiplos clientes por evento com tipo de relação (`Contratante`, `Assessora`, `Mãe/Pai`, `Familiar`, `Outros`) | `event_id`, `client_id` |
| `event_reimbursements` | `EventReimbursement` | reembolso de despesa da cliente | `event_id`, `created_by_id`, `collected_by_id` |
| `event_cancellations` | `EventCancellation` | **Feature 306** — o dinheiro congelado no ato do cancelamento, **uma linha por evento** (`UNIQUE(event_id)`, a segunda barreira do clique duplo: estourar vira 409 `ja_cancelado`). `regime` (`venda`\|`satelite`\|`dia`\|`virtual`; cancelado **sem** linha é `legado`, o de antes do deploy, e esse valor nunca é gravado), `refund_mode` (`tudo`\|`parte`\|`nada`; nulo em `satelite` e `virtual`), `sale_value`, `commission_full`, `commission_rate` (`Numeric(6,3)`), `commission_cost` (a base de custo da comissão EducaManto no ato), `commission_seller_id` (o beneficiário) e `seller_id`, `with_invoice`, `retained_tax` (NULL = não se aplica), `sale_handed_over` (o antigo 1º dia que passou a venda), `sale_value_before`/`_after` e `sale_value_gross_before`/`_after` (a venda do principal antes e depois do corte, no `dia`), `created_at`/`updated_at` em `now_sp()`, `updated_by_id`. Só a `venda` congela comissão e BV; **pago e devolvido não ficam aqui**: são lidos ao vivo, do grupo, por consulta (`cancel_ops.ids_do_grupo`), porque o Superadmin ainda corrige comprovantes e devolução. Regimes e modos em `app/constants.py` (`REGIME_*`, `MODO_*`); só `cancel_ops` escreve. Índice `ix_event_cancellations_group_leader_id` | `event_id`→`calendar_events` (**CASCADE**), `group_leader_id`→`calendar_events` (**SET NULL**; o principal, no `satelite` e no `dia`), `commission_seller_id`/`seller_id`→`users` (**sem `ondelete`**: bloqueiam a exclusão do usuário, §3.11), `updated_by_id`→`users` (SET NULL) |
| `event_cancellation_bvs` | `EventCancellationBv` | **Feature 306** — cada BV do evento no ato: `original_amount` (o BV cheio, `amount_brl` no ato), `recipient`, `pix`, `paid_at_cancellation` (já estava pago ou no banco, lido sob a trava) e `paid_amount` (o valor que conta enquanto o BV está pago ou no banco; só `cancel_ops.marcar_status_do_bv` escreve, e ele volta a NULL no desfazer). `UNIQUE(acrescimo_id)`; linha com `acrescimo_id` NULL é órfã e nenhum leitor a soma. Índice em `cancellation_id` | `cancellation_id`→`event_cancellations` (**CASCADE**), `acrescimo_id`→`event_acrescimos` (SET NULL) |
| `event_cancellation_elenco` | `EventCancellationElenco` | **Feature 306** — a lista do elenco do ato, para a multa: **uma linha por escalação** (vaga × dia), sem a vaga recusada e sem a de presença (`cancel_ops.elenco_do_ato`). `character_name`, `cache_reference` (só referência: nunca entra em custo, DRE nem multa). A linha nunca é apagada por mudança na escala; "na vaga" = `role_id` não nulo com o mesmo talento. No "todos", as linhas de todos os dias moram no congelado do principal; no corte e na passagem, no do dia; a Loja Virtual não tem lista. `UNIQUE(special_expense_id)` (uma multa por linha); índices em `cancellation_id`, `talent_id`, `role_id` e `day_event_id` | `cancellation_id`→`event_cancellations` (**CASCADE**), `talent_id`→`talents` (**sem `ondelete`**: artista com multa não some), `role_id`→`event_roles` (SET NULL), `day_event_id`→`calendar_events` (**CASCADE**, NOT NULL), `special_expense_id`→`special_expenses` (SET NULL) |
| `event_logs` | `EventLog` | trilha por evento (`actor_name`, `actor_role`, `message`) | `event_id` |
| `ensaio_materials` | `EnsaioMaterial` | materiais de ensaio (upload/link) | `event_id`, `user_id` |
| `audit_logs` | `AuditLog` | trilha global de auditoria (usada por `app.utils.audit`) | — |
| `notifications` | `Notification` | notificações internas por destinatário (feature 272): `kind`, `severity` (`info`\|`urgent`), texto pronto (`title`/`body`/`link_path`), referência fraca (`entity_type`/`entity_id`, sem FK), `dedupe_key`, `read_at` (NULL = não lida). `UNIQUE(user_id, dedupe_key)` é a trava de idempotência; índice **parcial** `(user_id, id) WHERE read_at IS NULL` serve o polling. `created_at` em `now_sp()`. Emissão/leitura em `app/notificacoes/notificacoes_ops.py` | `user_id` (CASCADE) |
| `sync_logs` | `SyncLog` | histórico de sincronização com o Google Calendar | — |
| `import_state` | `ImportState` | estado da importação de planilhas | — |

**Semântica importante de `CalendarEvent`**
- `parent_event_id` = vínculo **Ensaio → evento pai**.
- `group_leader_id` = **agrupamento comercial** (evento satélite → evento principal). São coisas
  distintas — nunca reutilizar um pelo outro.
  Desde a **306** o principal pode mudar: cancelar só o 1º dia passa a venda ao dia vivo mais cedo
  (`group_ops.passar_venda`), e o antigo 1º dia, cancelado, vira dia do novo principal. O dia
  cancelado continua no grupo (não se desagrupa nem se solta).
- `cancelamento` (backref de `EventCancellation`, `uselist=False`) = o dinheiro congelado no ato
  (feature 306); `None` no evento vivo e no cancelado `legado`. ⚠️ `EventCancellation` tem duas FKs
  para `calendar_events` e três para `users`: toda relação declara `foreign_keys=`, senão o
  `configure_mappers` levanta `AmbiguousForeignKeysError` e o `create_app()` não sobe.
- `is_educamanto` (property) = título começa com `(EDU` (`EDUCAMANTO_TITLE_PREFIX`).
- `event_requires_client(event)` (em `app/constants.py`): eventos com início ≥ **2026-06-29**
  (`CLIENT_REQUIRED_FROM`) exigem cliente para salvar a venda; anteriores são grandfathered.

**Feature 239 — regras de negócio novas do Casting/Agenda.**

- **Carrinho de transporte fora de SP** (`app/calendar/casting_ops.py`). `EventRole.does_transport`
  marca quem leva um veículo no evento (só existe com `event.is_outside_sp` — e, desde o hotfix
  239b, também quando a classificação é **desconhecida** (`NULL`): marcar grava
  `is_outside_sp=True` e tenta a estimativa de trajeto; só `False` recusa. A classificação vem de
  `_lookup_sp_status`: CEP → ViaCEP; senão **Geocoding do Google** (`maps.cidade_do_endereco`);
  senão texto; e é refeita nas edições React quando o endereço muda ou estava desconhecida
  (`event_ops.reclassificar_fora_de_sp`). Gate de quem marca =
  `_can_edit_event()`, mesmo de quem escala). O valor **nunca** é gravado à parte: o teto do cachê
  sobe pela parcela e o que se paga fica todo em `cache_value` (um número só), então planilha de
  pagamentos, custo do evento, KPI e DRE seguem sem qualquer mudança de código.
  `valor_transporte_papel(event)` calcula a parcela de **um** veículo (cada marcado tem direito à
  parcela de um, mesmo com vários carros no orçamento) numa cascata: 1) recálculo do orçamento que
  gerou o evento (`_parcela_veiculo_do_orcamento`, só a rodagem — **nunca**
  `event.transport_value` cheio, que já inclui o adicional fora-SP por pessoa somado dentro do
  `cache_cap` de todo mundo e pagaria esse adicional duas vezes); 2) `travel_distance_km × 2 ×
  tarifa do carro` quando não há orçamento; 3) zero. Em `assign_role`, o enforcement é
  `teto_efetivo = max(role.cache_cap + parcela_transporte, old_cache_value or 0)` — a parcela entra
  **dentro** do `max`, nunca somada por cima dele: somá-la depois faria cada "Salvar" render mais
  um degrau do tamanho da parcela (catraca que a revisão adversarial pegou antes do merge — ver
  `docs/03`). `app/api/agenda_read.py::_serialize_role` espelha a mesma fórmula em
  `cache_cap_efetivo`, para a tela nunca mostrar um teto diferente do que o servidor vai realmente
  aplicar.
- **"Técnico de Som (Presença)" nunca tem valor** (`casting_ops.e_vaga_de_presenca`, testa
  `character_name == PRESENCE_CHARACTER and role_type == "extra"`). `assign_role`/`add_role`
  forçam `cache_value=None`/`travel_cache=None` para essa vaga no servidor (a UI não tem campo de
  dinheiro nela, mas a trava real é aqui) e ela sai de **todos** os somatórios de dinheiro: custo de
  evento (`app/api/agenda_read.py::_compute_kpi`, `app/financeiro/routes.py::_event_cost`),
  planilha de pagamentos (`_pagamentos_query`), dashboard de performance (`money_total`) e o
  dashboard financeiro (`financeiro_read.py`). Continua visível no casting como **somente leitura**
  (quem recebe o PIX do som é a outra vaga, "Técnico de Som" — Nivaldo); designar quem vai
  fisicamente ao evento é tarefa do painel de Ensaio.
- **Troca de tipo do evento** (`app/calendar/event_ops.py::aplicar_troca_de_tipo`, chamada por
  `update_event_core` e `update_event_basics`, fonte única). Entrar em SHOW recria as vagas de som e
  liga `needs_rehearsal` (mesma regra da criação). Sair de SHOW **cancela/remove tudo
  automaticamente**: ensaios já agendados (inclusive no Google Calendar, via `delete_ensaio`),
  as duas vagas automáticas de som (mesmo preenchidas) e desliga `needs_rehearsal` — tudo registrado
  em `EventLog` com o que existia, e devolvido como `warnings` não-bloqueantes na resposta do PATCH.
  **A ordem é obrigatória**: o título com o prefixo `(TIPO)` novo (`event_ops.build_gc_title`) vai
  ao Google **antes** da parte destrutiva rodar (`_sincronizar_e_trocar_tipo`) — é o prefixo que o
  `sync_events` lê de volta para saber o tipo, então aplicar a automação antes do push arriscava
  apagar ensaio de verdade e o sync seguinte reimpor SHOW num evento que já não tem mais ensaio
  nenhum. Se o push falhar numa troca com automação (entrando ou saindo de SHOW), a troca inteira é
  desfeita (`_desfazer_troca_de_tipo`) e o endpoint devolve **409** `EventTypeChangeBlocked` — o
  resto do salvamento (data, local, descrição, valores) fica gravado, só a troca de tipo é
  revertida. Troca sem automação (ex.: CORP → R&I) continua best-effort, como toda sincronização.
- **Nomes de equipe nunca no título** (`RESERVED_TITLE_NAMES` em `app/calendar/routes.py`:
  Coordenador, Técnico de Som, Técnico de Som (Presença), Maquiador). Denylist normalizada
  (sem acento/caixa) aplicada em três pontas: `ElencoBlock.tsx` (não gera o nome no título),
  `parse_characters`/`_strip_reserved_title_segments` (o sync do Google ignora esses segmentos,
  inclusive numa edição manual do título feita direto na Agenda), e a reconciliação de roles a
  partir do título **migra** o role reservado para `role_type="extra"` em vez de apagá-lo — apagar
  dispararia e-mail de "você foi removido" para quem estava escalado sem ninguém tê-lo removido de
  verdade (achado da revisão adversarial, ver `docs/03`).

### 2.2.1 Impressões e Acervo 3D (features 200, 201, 202, 255 e 261)

| Tabela | Model | Destaques | FKs |
|---|---|---|---|
| `acervo_3d_items` | `Acervo3DItem` | catálogo de peças base: `name`, `photo_url` (**NOT NULL** — foto JPG/PNG de preview), `nfc_prefix` (feature 255 — não-nulo habilita a peça para tags NFC; é o prefixo do código, ex. `01`), `is_active`, `created_at` | — |
| `nfc_tags` | `NfcTag` | tag NFC física embutida numa peça entregue (feature 255): `code` (**UNIQUE**, imutável, `<prefixo>-<6 chars aleatórios sem ambiguidade>` via `secrets`), `sequence` (nº humano por item — **UNIQUE `(item_id, sequence)`** — rótulo físico da equipe), `is_active`, `notes`, `access_count`, `last_accessed_at`, `created_at`; índices em `code`, `item_id`, `event_id`, `client_id`. **Nunca é apagada** | `item_id`→`acervo_3d_items`, `event_id`→`calendar_events` e `client_id`→`clients` (ambos **ON DELETE SET NULL** — `client_id` é a cliente DIRETA, p/ campanha/brinde sem show; tem precedência sobre a contratante do evento na exibição) |
| `acervo_3d_files` | `Acervo3DFile` | arquivos 3D da peça (**1:N**, feature 201 — o modelo vem fatiado em partes): `file_path`, `original_name` (nome enviado, ex.: `corpo.stl`), `position`, `created_at` | `item_id`→`acervo_3d_items` (**ON DELETE CASCADE**) |
| `event_3d_gifts` | `Event3DGift` | presente 3D vinculado a um evento (1:N): `status` (`pendente`\|`imprimindo`\|`finalizado`\|`entregue`), `deadline_date`, `quantity`, `notes`, `created_at`/`updated_at`; índices em `event_id`, `item_id` e `status` | `event_id`→`calendar_events` (**ON DELETE CASCADE**), `item_id`→`acervo_3d_items` |
| `event_3d_dismissals` | `Event3DDismissal` | dispensa da pendência "show sem presente" (feature 202): `dismissed_at`, `dismissed_by`. `event_id` é **UNIQUE** — uma dispensa por evento | `event_id`→`calendar_events` (**ON DELETE CASCADE**), `dismissed_by`→`users` |

**Semântica importante**
- **Foto obrigatória** (sem ela a peça não é selecionável visualmente — Princípio X.2) e
  **pelo menos um arquivo 3D** (sem arquivo ela não é imprimível). Na **edição**, não enviar
  foto significa *manter a atual*; os arquivos 3D são **cumulativos** (`files` acrescenta,
  `remove_file_ids[]` remove) e o servidor recusa deixar a peça com zero arquivos.
- Só evento com `event_type == 'SHOW'` (`EVENT_TYPE_SHOW`, em `app/constants.py`) aceita presente
  3D — a API recusa com 400 em qualquer outro tipo, e o detalhe do evento só serializa a chave
  `presentes_3d` nesse caso.
- **A pendência nasce do evento (feature 202)**: todo SHOW com `start_at >= hoje` e **nenhum**
  `Event3DGift` é uma tarefa aberta na Fila de Impressão — um show novo entrando na agenda já
  aparece lá, sem depender de alguém lembrar de cadastrar. Só olha para frente: show passado não
  tem mais o que imprimir e afogaria a fila em linhas mortas.
- `Event3DDismissal` é o "este show não leva presente": tira a tarefa da lista sem inventar um
  presente fantasma. É reversível (DELETE) e **descartada automaticamente** quando alguém vincula
  um presente ao evento — se leva presente, a decisão anterior deixou de valer.
- `GIFT_3D_STATUSES` (`app/constants.py`) é a fonte única do ciclo de vida. `entregue` é estado
  final: sai da Fila de Impressão.
- `CalendarEvent.presentes_3d` é o backref (`cascade="all, delete-orphan"`) — excluir o evento
  leva junto os vínculos, mas **nunca** as peças do Acervo.
- Peça do Acervo com evento vinculado **não pode ser excluída** (400 com orientação de inativar):
  preserva o histórico de quantas vezes o modelo já foi impresso.
- Núcleo de negócio em `app/impressoes3d/impressoes3d_ops.py`. *(Nomenclatura: a proposta original
  era `app/3d_impressions/3d_ops.py`, impossível em Python — identificador não pode começar com
  dígito. As URLs públicas mantêm o `3d`.)*
- **Tags NFC (feature 255)** — contrato central: a URL gravada na tag física
  (`app.mantoproducoes.com.br/nfc/<code>`) é **imutável e eterna**; todo o conteúdo da página é
  decidido pelo servidor a cada acesso (gancho `campaign: null` no payload para campanhas
  futuras sem regravar tags). Geração automática: `add_event_gift`/`update_event_gift` chamam
  `nfc_ops.sync_event_gift_tags(event, item)` na MESMA transação — alvo é a soma das
  `quantity` dos presentes do par `(evento, item)`; cria só a diferença positiva e **nunca
  apaga** (reduzir quantidade/remover presente não toca nas tags). Lote avulso e edição
  (evento/situação/notas) em `app/impressoes3d/nfc_ops.py`; não existe DELETE de TAG em camada
  nenhuma — desativar (`is_active=False`) faz a página pública responder o payload genérico,
  **indistinguível de código inexistente** (sempre 200, mesmo shape — requisito de privacidade).
- **Entregas da tag NFC — `nfc_tag_deliveries` (feature 261)**: tabela (não coluna) do que a
  página pública mostra além do produto — hoje só vídeo ("Um vídeo especial para você"), mas o
  schema já é extensível para foto/link futuros sem migração nova. Colunas: `tag_id` (FK
  `nfc_tags.id`, `ondelete=CASCADE` — apagar a tag levaria as entregas, embora tag nunca seja
  apagada na prática), `kind` (`String(20)`, só `"video"` por ora), `title` (nullable — `None` ⇒
  a página usa a copy padrão), `file_path` (nullable — só o NOME do arquivo, nunca o caminho
  completo nem URL), `link_url` (nullable, gancho para entrega futura por link direto),
  `is_active`, `sort_order`. **1 vídeo ativo por tag por ora**: `nfc_ops.add_delivery` substitui
  a entrega anterior do mesmo `kind` (apaga arquivo + linha antigos) em vez de acumular —
  comportamento de hoje, não limite do schema. Arquivo mora em `Config.NFC_MEDIA_FOLDER`
  (`instance/nfc_media/`, env-overridable), **irmã de `UPLOAD_FOLDER`, nunca dentro dela** —
  mesmo motivo da feature 205 (`VIRTUAL_VIDEO_FOLDER`): a rota `/uploads/<path>` exige login
  (`app/__init__.py:733`) e a página `/nfc/<code>` é pública, sem sessão; o arquivo só sai por
  `GET /api/nfc/<code>/entregas/<id>/media`, que revalida tag ativa + entrega ativa a cada
  requisição (`conditional=True` → suporte a `Range`/`206`, essencial pro vídeo tocar no
  celular). Extensão aceita SEMPRE por `app.storage.extension_of` sobre o nome do arquivo
  (nunca `Content-Type`): `NFC_DELIVERY_VIDEO_EXTENSIONS` = `.mp4`/`.mov`/`.webm`/`.m4v`
  (`app/constants.py`); limite `NFC_DELIVERY_VIDEO_MAX_BYTES` = 250 MB (espelha
  `VIRTUAL_VIDEO_MAX_BYTES` da 205). Nome no disco é sempre `<uuid4>.<ext>` — nunca o nome
  original enviado (evita path traversal e colisão).

### 2.3 Talentos e Casting

| Tabela | Model | Destaques | FKs |
|---|---|---|---|
| `talents` | `Talent` | `full_name`, `artistic_name`, `phone`, `email_contact`, `birth_date`, `status` (`pending`\|`active`, indexado), `source`, `tags`, `skills`, medidas (`height_cm`, `clothing_size_top/bottom`, `shoe_size`), `passport_status`, `rg`, `cpf` (unique, nullable — estrangeiro grava `NULL`), `is_foreigner`, `pix_key`/`pix_key_secondary`, fotos (`photo_face_path`, `photo_full_path`, `doc_photo_path`), CNH, dados de carro, `notes`, `warning_level`, credenciais do portal (`password_hash`, `password_reset_token`, `terms_accepted_at`), confirmação de email da 219 (`email_verified_at`, `email_verify_token` **unique**, `email_verify_sent_at`) | 1:N `media_items` |
| `email_bounces` | `EmailBounce` | devoluções de email lidas por IMAP (feature 219). `message_id` **unique** = idempotência da varredura; `email`, `kind` (`caixa_cheia`\|`endereco_invalido`\|`dominio_invalido`\|`bloqueado`\|`outro`), `is_permanent` (`Action: failed` vs `delayed`), `status_code` (RFC 3463), `diagnostic`, `occurred_at`, `resolved_at`/`resolved_by_id`. **Só grava endereço que casa com talento/usuário** — devolução de contato alheio é descartada. Índices em `email`, `talent_id`, `resolved_at` | `talent_id`, `user_id`, `resolved_by_id` |
| `talent_media` | `TalentMedia` | mídia do portfólio do talento | `talent_id` |
| `event_ratings` | `EventRating` | avaliação de talento por evento | `event_id`, `talent_id` |
| `event_sub_ratings` | `EventSubRating` | notas por critério/sujeito | `rating_id`, `subject_talent_id` |
| `event_rating_versions` | `EventRatingVersion` | versionamento das avaliações | `rating_id` |

### 2.4 Figurino

| Tabela | Model | Destaques | FKs |
|---|---|---|---|
| `figurino_sheets` | `FigurinoSheet` | `character_name`, `character_name_norm` (lowercase sem acentos), `photo_filename`, `pieces` (JSON `[{name, qty}]`), **`quantity`** (feature 235 — quantos figurinos IGUAIS existem; padrão 1, 0 = ficha de figurino ainda não produzido; **não confundir com o `qty` de dentro de `pieces`**, que é "2 luvas" dentro de UM figurino), `tags` (JSON `["anjo","natal"]`, feature 183), `notes`, campos de sync do Drive (`drive_file_id` unique, `drive_url`, `thumbnail_url`, `last_synced_at`) | referenciada por `event_roles.figurino_sheet_id` e `catalog_characters.figurino_sheet_id` |
| `figurino_missing_dismissals` | `FigurinoMissingDismissal` | descarte de alerta "personagem sem ficha"; guarda os `event_role_ids` cobertos (JSON) — um `EventRole` novo faz o alerta reaparecer | `dismissed_by`→`users` |

Properties úteis: `pieces_list`, `pieces_count`, `tags_list`, `photo_url` (aceita URL absoluta,
caminho `/uploads/figurino_photos/...` ou fallback para `thumbnail_url` do Drive).

#### 2.4.1 Produção de Figurinos (feature 225) e Pedido de Compra (225c)

`figurino_sheets` descreve o figurino **pronto**; `special_expenses` registra o dinheiro **depois**
que saiu. Estas três tabelas são o que existe no meio — o trabalho de produzir.

| Tabela | Model | Destaques | FKs |
|---|---|---|---|
| `figurino_producoes` | `FigurinoProducao` | `title`, `description`, `status` (`solicitado`\|`aprovado`\|`em_producao`\|**`comprado`**\|`pronto`\|**`recebido`**\|`cancelado`), **`kind`** (`producao`\|`manutencao`, 225b \| **`compra`**, 225c), **`severity`** (`impede_uso`\|`pode_esperar`, só em manutenção), `quantity`, `due_date`, `estimated_cost`, `approved_at`, `done_at`, `cancelled_at`, `cancellation_reason`, `google_event_id` (o compromisso do prazo na agenda) | `event_id`→`calendar_events` (**SET NULL**), `figurino_sheet_id`→`figurino_sheets` (**SET NULL**), `requested_by_id`→`users`, `responsible_id`/`approved_by_id`→`users` (**SET NULL**) |
| `figurino_producao_anexos` | `FigurinoProducaoAnexo` | `kind` (`foto`\|`orcamento`), `file_path`, `original_name`, `caption`; `supplier_name`/`amount` só em `orcamento` (para comparar propostas) | `producao_id`→`figurino_producoes` (**CASCADE**), `uploaded_by_id`→`users` (SET NULL) |
| `figurino_producao_logs` | `FigurinoProducaoLog` | histórico narrativo no formato de `EventLog` (`actor_name`, `actor_role`, `message`) + `photo_path` e `status_from`/`status_to` | `producao_id`→`figurino_producoes` (**CASCADE**) |

`special_expenses.figurino_producao_id` (**SET NULL**) é o vínculo com o dinheiro.

**Invariantes.**

- **`SET NULL` para fora, `CASCADE` para dentro.** Excluir o evento não apaga o pedido; apagar o
  pedido não apaga o gasto (o dinheiro saiu de verdade). Anexos e histórico, sim, vão junto.
- **`total_gasto` conta só gasto `aprovado`** — mesmo recorte da DRE.
- **`prazo_efetivo`** cai na data do evento quando ninguém informou `due_date`.
- **O compromisso no Google carrega `extendedProperties.private.manto_kind`**, e `sync_events`
  pula todo item que a tenha (`_is_manto_task_item`). Sem isso o prazo viraria um `CalendarEvent`
  fantasma: o calendário é o mesmo dos shows e o sync importa tudo que encontra.
- **`CALENDAR_SUPPRESS_INVITES`** (`config._suppress_calendar_invites`) impede um processo local
  de escrever na agenda real — `manto_local` traz o token de produção e o calendário é fixo. A
  trava irmã da feature 303, **`CALENDAR_SUPPRESS_EVENT_WRITES`**
  (`config._suppress_calendar_event_writes`; escape `CALENDAR_ALLOW_LOCAL_EVENT_WRITES=true`), cobre
  **só** duas escritas: a devolução de evento marcado ao Google e, desde a feature 306, a remoção
  do Google no cancelamento (os dias e os ensaios do ato, `cancel_ops._remover_do_google`;
  travada, o ato cancela no sistema e só avisa na tela) — ver §5.4.
- **O fluxo depende do tipo** (225b): `FIGURINO_PROD_FLUXOS` define a ordem por `kind` e
  `producao_ops._transicoes_do_fluxo` **deriva** as transições dela — nunca escrever duas
  tabelas. Manutenção pula `aprovado`; nem SUPERADMIN consegue aprovar uma.
- **Manutenção exige `figurino_sheet_id` e `severity`.** É sempre sobre uma peça que existe, e a
  gravidade é o que decide se ela pode ir para o próximo evento.
- **`alertas_por_ficha()` é a fonte única do aviso**, consumida por `figurino_ops.list_sheets`
  (lista de Figurinos) e por `agenda_read` (elenco do evento) — uma consulta por tela, não uma
  por ficha. Manutenção resolvida sai do dicionário e o aviso some sozinho.
- **`kind="compra"` é o Pedido de Compra (225c)** — mesma tabela, terceiro fluxo:
  `solicitado → aprovado → comprado → recebido`. **Sem migration**: `kind` e `status` são
  `String(20)` sem CHECK, e todo o resto (prazo, responsável, histórico, anexos, vínculo com
  Gasto Extra, convite na agenda) já existia. Ficha e evento são **opcionais** — a compra pode
  não ter nada a ver com figurino (tinta de cenário, material de escritório).
- **`comprado` está em `FIGURINO_PROD_ABERTOS`**: o dinheiro saiu, mas a coisa não chegou, e é
  esse intervalo que se perde hoje. O estado final feliz de cada tipo é o **último do fluxo**
  (`_fluxo_de(p)[-1]`) — é dele que sai o carimbo de `done_at`, para não ser preciso listar
  estados finais em dois lugares.
- **`pode_executar_pedido(user, p)`** abre a execução ao **responsável pela própria compra**,
  além de FIGURINO/SA. Sem isso um pedido entregue ao Comercial travaria em "aprovado" para
  sempre. Vale **só** em `kind="compra"`; produção e manutenção continuam sendo da oficina.
- **Aprovar continua sendo só de SUPERADMIN**, inclusive na compra — é o único ponto em que
  alguém olha o dinheiro antes de sair.
- **`responsaveis_elegiveis(kind)`**: em compra devolve a equipe interna inteira (`pode_abrir`);
  nos outros tipos, só FIGURINO/SUPERADMIN.
- **Compra sem dono avisa só o SUPERADMIN** (`equipe_figurino(kind)`) e entra na caixa de
  entrada do setor apenas para quem aprova (`resumo_setor`) — mandar tinta de cenário para a
  costureira transformaria o aviso em ruído.

### 2.5 Catálogo (vitrine pública + gerenciador interno)

| Tabela | Model | Destaques | FKs |
|---|---|---|---|
| `catalog_items` | `CatalogItem` | **Tema** — `wp_product_id` (unique, dedupe da importação WordPress), `name`, `slug` (unique), `short_description_html`, `tags` (JSON), `is_active`, `imported_at`, **`video_url`** (feature 185 — Drive/MP4/Vimeo) | M:N `categories`; 1:N `images`, `characters` |
| `catalog_characters` | `CatalogCharacter` | **Personagem filho** (feature 185) — `name`, `slug` (unique, prefixado pelo slug do Tema), `photo_url`, `video_url`, `position`, `is_active`. Cada linha é uma **aparição**: duas linhas com o MESMO `figurino_sheet_id` são o mesmo personagem em temas diferentes (feature 235 — a ficha é a identidade), e duas no mesmo tema são dois performers do mesmo figurino (caso "Astronauta 1"/"Astronauta 2"). Sem ficha, o personagem existe só dentro do tema dele | `catalog_item_id`→`catalog_items` (**ON DELETE CASCADE**), **`figurino_sheet_id`→`figurino_sheets` (ON DELETE SET NULL)**, **`own_item_id`→`catalog_items` (UNIQUE, ON DELETE SET NULL)** |
| `catalog_item_images` | `CatalogItemImage` | `url`, `original_url`, `position` (**posição 0 = capa**, usada no Open Graph), `file_size_bytes` | `item_id` |
| `catalog_categories` | `CatalogCategory` | `name` (unique), `slug` (unique) | — |
| `catalog_item_categories` | *(association)* | PK composta | `item_id`, `category_id` |

> **`catalog_characters.own_item_id` (feature 209, `app/models.py:1915`)** aponta para o `CatalogItem`
> que **é** a página própria deste personagem (caso "Coelho Branco" dentro do tema Alice). `NULL` = o
> personagem só existe no elenco do Tema; preenchido = ele tem página própria de catálogo. É UNIQUE —
> um item só pode ser página de um personagem. Relacionamento `own_item` com backref `as_character`.
>
> ⚠️ **Com isso `CatalogItem` passou a ter DOIS FKs vindos de `CatalogCharacter`**
> (`catalog_item_id` e `own_item_id`). Sem `foreign_keys` explícito nos relacionamentos o mapper
> quebra no boot com `AmbiguousForeignKeysError` — ver o comentário em `app/models.py:1853`.

> **`catalog_characters.figurino_sheet_id` é a coluna que materializa o vínculo bidirecional
> Catálogo ↔ Figurino** (feature 186). Não existe coluna espelho do lado de `figurino_sheets` — o
> "personagem vinculado" de uma ficha é derivado por busca inversa nessa mesma coluna.

### 2.6 Financeiro

| Tabela | Model | Destaques | FKs |
|---|---|---|---|
| `commission_payments` | `CommissionPayment` | `event_title` (**cópia**, sobrevive à exclusão do evento), `sale_date`, `payable_from` (EducaManto: só entra no ciclo após a realização), `amount` (`Numeric(12,2)`, **pode ser negativo** = estorno ou ajuste), `status` (`a_pagar`\|`no_banco`\|`pago`\|`cancelado`), `paid_at`, `notes`. **Feature 306**: linha paga ou no banco nunca é reescrita; quando o valor devido muda depois dela (cancelamento com retido, correção da venda do cancelado, corte de dia, exclusão), nasce um **ajuste** — linha nova `a_pagar`, positiva ou negativa, com `original_id` na liquidada, `sale_date` = `payable_from` = o primeiro repasse aberto do beneficiário (`DIA_DO_REPASSE` = 5) e o motivo no prefixo de `notes` (`MOTIVOS_AJUSTE_COMISSAO`, `app/constants.py`). O ajuste continua ligado ao evento; só a exclusão deixa a linha sem evento (o estorno **órfão**). Índices em `seller_id`, `event_id`, `status` | `event_id`→`calendar_events` (nullable), `seller_id`→`users`, `original_id`→`commission_payments` (auto-referência do estorno e do ajuste) |
| `salary_history` | `SalaryHistory` | `salary`, `payment_type` (`semanal`\|`quinzenal`\|`comissao`), `start_date`, `end_date` (`NULL` = vigente) | `user_id` |
| `salary_payments` | `SalaryPayment` | `due_date`, `amount`, `payment_status`, `paid_at`, `month_ref` (`YYYY-MM`); **UNIQUE (`user_id`,`due_date`)**; `advance_amount`/`advance_proof` são legado migrado para `salary_advances` | `user_id`, `salary_history_id` |
| `salary_advances` | `SalaryAdvance` | adiantamentos (N por pagamento) — reduzem o líquido a pagar, **não** o custo de salário do balanço | `salary_payment_id` |
| `special_expenses` | `SpecialExpense` | gastos extras com fluxo de aprovação e reembolso a funcionário. `CATEGORIES`: Figurino, Escritório, Marketing, Manutenção, **Devolução a cliente** (224, `CATEGORY_DEVOLUCAO`), **Multa de cancelamento** (306, `CATEGORY_MULTA_CANCELAMENTO`) e Outros — categoria fora da lista vira "Outros" na primeira edição em Gastos Extras. `disbursement_type` ∈ `reembolso`\|`fornecedor`\|`cliente`. **Feature 306**: a devolução e a multa do cancelamento nascem **aprovadas** pelo `cancel_ops`, nunca por `create_expense`. A devolução se reconhece pela categoria, pelo evento e pela aprovação (`cancel_ops.filtro_devolucao`), não pelo `disbursement_type`; a de evento cancelado sai dos gastos extras da DRE (já está descontada no retido) e fica **travada** em Gastos Extras (§3.7). A multa é uma por escalação, `fornecedor`, a pagar ao artista (nome e `Talent.pix_key`), ligada ao dia, e conta como gasto do mês da `expense_date` (o dia do ato, ou o do lançamento depois dele) | `created_by_id`, `approved_by_id`, `reimburse_user_id`, `event_id` |
| `recurring_expenses` | `RecurringExpense` | contas recorrentes | `created_by_id` |
| `recurring_expense_entries` | `RecurringExpenseEntry` | parcelas geradas da conta recorrente | `recurring_id`, `filled_by_id` |

### 2.7 Clientes, Formulários, Feedback e Orçamento

| Tabela | Model | Destaques | FKs |
|---|---|---|---|
| `clients` | `Client` | cadastro comercial; identidade = `phone` normalizado (`NOT NULL UNIQUE`, só dígitos com DDI). `source` ∈ `kommo_import` \| `manual` \| `whatsform_import` (feature 193) | 1:N `events` |
| `form_responses` | `FormResponse` | respostas dos formulários públicos de pré-contrato (`form_type` ∈ `comum` \| `corporativo`) **e** o histórico do WhatsForm importado na feature 193. **Feature 298**: encerramento em `closed_reason` (`desistiu` \| `repetido` \| `preenchido_errado` \| `teste` \| `outro`), `closed_note` (≤ 300, obrigatória em `outro`), `closed_by_id`, `closed_at` (UTC ingênuo, como `created_at`); índice parcial `ix_form_responses_sem_destino` (`created_at` onde `event_id IS NULL AND closed_at IS NULL`). Invariante: `closed_at IS NOT NULL ⇒ event_id IS NULL` | `client_id`, `event_id` (ambos indexados e nullable); `closed_by_id` (`users`, `SET NULL`); `client_link_source` (feature 266: `auto_phone` \| `manual` \| `NULL`, espelha `event_link_source`; 298: `evento` quando a cliente veio do evento ligado) |
| `form_response_dismissed_events` | `FormResponseDismissedEvent` | **Feature 298**: sugestão "parece ser este evento" descartada — o par nunca volta (definitivo, decisão do dono). `UNIQUE(form_response_id, event_id)`; **sem backref** de propósito (as exclusões de evento e de formulário contam com o `ON DELETE CASCADE`) | `form_response_id` e `event_id` (`CASCADE`), `dismissed_by_id` (`SET NULL`) |
| `form_field_definitions` | `FormFieldDefinition` | editor de campos dos formulários (ordem, tipo, obrigatoriedade) | — |
| `client_feedbacks` | `ClientFeedback` | avaliação pública da cliente via `feedback_token` do evento | `event_id` |
| `orcamento_history` | `OrcamentoHistory` | histórico da calculadora de orçamento (vira `calendar_events.orcamento_history_id`) | `user_id` |

#### Estado do banco de leads (pós-feature 193)

A base comercial tem **duas origens históricas** consolidadas na mesma tabela `clients`, mais o
cadastro manual do dia a dia:

Números de **produção**, medidos após a carga de 2026-07-28:

| `clients.source` | Volume | Origem |
|---|---|---|
| `kommo_import` | 5.492 | CSV do Kommo CRM (feature 094) |
| `whatsform_import` | 665 | Histórico do WhatsForm (feature 193) |
| `manual` | 41 | Cadastro pela ficha do cliente |
| **Total** | **6.198** | |

`form_responses` foi para **1.473** linhas (1.374 `comum` + 99 `corporativo`): as 28 respostas
nativas do formulário do Manto mais as **1.445 respostas históricas do WhatsForm**
(2023-09-04 a 2026-07-09), carregadas pelo script CLI
`scripts/db/import_whatsform_history.py`.

> A mesma carga rodou antes contra `manto_local` (cópia mais antiga) e criou **693** clientes em
> vez de 665: a produção já tinha mais clientes cadastrados, então 28 linhas casaram com cliente
> existente em vez de criar duplicata. Diferença de volume entre os dois ambientes é esperada —
> o que não muda é o total de 1.445 respostas.

Pontos que valem para quem for ler esses dados:

- **Deduplicação em 2 níveis** — telefone normalizado (`normalize_phone` de
  `app/clientes/importer.py`, fonte única) e, na sequência, CPF/CNPJ com comprimento válido
  (11/14 dígitos). Documentos truncados/digitados errado ficam gravados em `cpf` mas **não**
  deduplicam. Das 1.445 respostas, 767 caíram em cliente que já existia (majoritariamente base
  Kommo) e 665 criaram cliente novo.
- **Cliente existente nunca é sobrescrito** — a carga só preenche colunas que estavam nulas
  (`email`, `cpf`, `cnpj`, `company`, `address`, `phone_display`): 415 clientes foram
  completados assim. `name` jamais é alterado.
- **32 respostas ficam com `client_id` nulo** (13 novas da carga + 19 anteriores): a linha não
  tinha telefone normalizável e `clients.phone` é `NOT NULL UNIQUE`. Elas aparecem normalmente
  em `/formularios` e podem ser associadas à mão pela tela.
- **Padrão B2B dos corporativos** — `contact_name`/`clients.name` das planilhas corporativas
  seguem `"Nome do Responsável (Empresa)"` (ex.: `Priscila da Silva (OCESP)`), com o WhatsApp de
  quem preencheu, não o telefone fixo da empresa. A razão social completa fica em
  `clients.company`.
- **`created_at` é histórico**, não a data da carga — tanto nas respostas quanto nos clientes
  criados por ela, para a base refletir a linha do tempo real de captação.
- **`FormResponse.data`** foi montado no mesmo formato da feature 123
  (`[{"secao", "campos": [[chave, rótulo, valor], …]}]`), com as colunas de controle do
  WhatsForm (`Response`, `Time`, `Delivered to`) removidas e as chaves-sistema (`cpf`, `cnpj`,
  `endereco_contratante`, `endereco_empresa`) preservadas — então
  `formularios_ops.fill_client_from_response` continua funcionando nessas respostas.

### 2.8 EducaManto

| Tabela | Model | Destaques | FKs |
|---|---|---|---|
| `educamanto_musicals` | `EducaMantoMusical` | feature 235 (rename de `educamanto_packages`, ids preservados): 1 linha por musical; `num_personagens`/`num_producao` derivados dos itens (Cara Limpa+Bonecos+Papai Noel / item Produção — 4ª rodada) e `num_ensaios (≥2)`; alimentação por pessoa (`custo_alimentacao_1s/2s`) e ensaio por pessoa (`custo_catering_ensaio_pp`, `custo_ajuda_ensaio_pp`); som/iluminação NÃO ficam aqui (tabela única `pricing_config['educamanto_som_luz']`); cenário sem custo/coluna (removido na 4ª rodada); `commission_rate` (campo morto) removido | 1:N `items` |
| `educamanto_musical_items` | `EducaMantoMusicalItem` | rename de `educamanto_items` (`package_id`→`musical_id`); itens sempre inclusos — Som/Catering apresentação/Caterings de ensaio/Transporte viraram colunas ou regra na migração | `musical_id` |
| `educamanto_quotes` | `EducaMantoQuote` | `snapshot` versionado: **v2** = `{version: 2, configs: [...]}` com entradas + resultado **recalculado no servidor**; sem `version` = v1 (legado por pacote, re-render intacto) | `user_id` |

### 2.9 Revisão de Mídia

| Tabela | Model | Destaques | FKs |
|---|---|---|---|
| `review_spaces` | `ReviewSpace` | espaço de revisão | `created_by` |
| `review_assets` | `ReviewAsset` | asset com status de aprovação | `space_id`, `uploaded_by` |
| `review_asset_versions` | `ReviewAssetVersion` | versionamento (replace) | `asset_id`, `uploaded_by` |
| `review_reviewers` | `ReviewReviewer` | revisores atribuídos ao espaço | `space_id`, `user_id` |
| `review_comments` | `ReviewComment` | comentários com resolução | `asset_id`, `user_id`, `resolved_by` |

### 2.9.1 Gestão de Marketing e Frequência (feature 204, temas múltiplos na 204b)

| Tabela | Model | Destaques | FKs |
|---|---|---|---|
| `marketing_posts` | `MarketingPost` | card do Kanban de planejamento: `title`, `status` (`ideia`\|`producao`\|`revisao`\|`agendado`\|`publicado`), `deadline_date`, `publish_date`, `platform` (lista fixa `MARKETING_PLATFORMS`), `drive_folder_url` (texto — o acervo bruto segue no Drive), `notes`, `created_at`/`updated_at`; índices em `status` e `publish_date` | `assignee_id`→`users`, `review_space_id`→`review_spaces` (**UNIQUE**) — **ON DELETE SET NULL** |
| `marketing_post_temas` | (tabela de associação, sem model próprio) | **N:N** entre post e Tema (feature 204b) — um post pode falar de vários Temas ao mesmo tempo (ex.: Reels que junta "15 Anos" e "Debutante"). PK composta `(post_id, catalog_item_id)` | `post_id`→`marketing_posts`, `catalog_item_id`→`catalog_items` — os dois **ON DELETE CASCADE** |
| `marketing_frequency_goals` | `MarketingFrequencyGoal` | regra de frequência ("15 Anos a cada 15 dias"): `name`, `target_interval_days`, `created_at` | `catalog_item_id`→`catalog_items` (**ON DELETE SET NULL**, opcional) |

**Semântica importante**
- **`assignee_id`/`review_space_id` são `SET NULL` de propósito**: apagar um usuário ou um espaço
  de revisão **não pode** apagar o planejamento de marketing junto. `review_space_id` é **UNIQUE** —
  o vínculo com a Revisão de Mídia é 1:1 por definição. Já `marketing_post_temas` é **CASCADE** dos
  dois lados: a linha de associação não faz sentido sem o post nem sem o Tema.
- **Um post pode ter 0, 1 ou vários Temas** (`MarketingPost.temas`, relationship N:N via
  `marketing_post_temas`, `lazy="joined"`). A API expõe `catalog_item_ids`/`catalog_items`
  (plural) em vez do antigo `catalog_item_id`/`catalog_item` singular.
- **A meta não guarda estado de cumprimento.** `last_posted_date`, `next_due_date`, `days_late` e
  o status derivado (`on_track`/`delayed`) são **calculados na leitura** por
  `marketing_ops.goal_health()` a partir dos posts publicados — nada de job noturno, e mover um
  card para "publicado" conserta a saúde da meta na hora.
- **Casamento meta ↔ post, em dois modos**: com `catalog_item_id` na meta, casa se **qualquer um**
  dos Temas do post for o Tema da meta (`MarketingPost.temas.any(...)` — um post multi-Tema conta
  para cada meta que ele toca); sem Tema na meta, casa pelo `name` da meta contido no título do
  post (`ILIKE`, com os curingas escapados) — serve para assunto que não existe no catálogo (ex.:
  "Bastidores"). Só entram posts com `status = 'publicado'` **e** `publish_date` preenchida.
- Meta **sem nenhum post publicado** é `delayed` com `never_posted = True`: nunca ter postado é o
  atraso máximo, não "em dia".
- **Regra de negócio do `publish_date`**: marcar um post como `publicado` sem data preenche a data
  de hoje automaticamente (`_autofill_publish_date`) — sem isso o post não contaria para a
  frequência. Sair de "publicado" **não** apaga a data.
- Excluir um post **não** exclui o `ReviewSpace` vinculado: materiais e comentários da revisão têm
  vida própria. Núcleo de negócio em `app/marketing/marketing_ops.py`; a criação do espaço reusa
  `review_ops.create_space` (Princípio I).

### 2.10 Configuração global

`site_settings` (`SiteSetting`, **linha única id=1**) concentra: identidade visual
(`logo_path`, cores), `default_commission_rate`, `educamanto_seller_id`,
`educamanto_commission_rate` (% do responsável EducaManto sobre o **lucro** do evento — feature
223; `NULL` = 5%, o antigo `EDUCAMANTO_COMMISSION_RATE` do código, que virou só o piso de
fábrica; `event.commission_rate` continua sobrepondo os dois),
`infinitepay_handle`/`infinitepay_webhook_token` (conta que recebe as vendas da Loja de
Interações Virtuais e o segredo que autentica o aviso de pagamento — editáveis em Configurações
desde a 224f; **nulos, nenhuma reserva passa do checkout**. O token é gerado pelo sistema e
nunca sai pela API: a leitura devolve só `infinitepay_webhook_configured`), `tax_rate`,
`fator_r_threshold`, `manto_address`, `departure_margin_minutes`, `google_maps_api_key`,
`clicksign_token`/`clicksign_sandbox` (**inertes** desde a 021 — o token da 317 vem só da env), os
`clicksign_webhook_id`/`_secret`/`_secret_anterior(_ate)` e `clicksign_sync_at`/`_cursor`/`_pendente`
da feature 317 (§3.13.6), `email_notifications_enabled`, `ratings_fully_anonymous`,
`release_date`, `google_token` (OAuth persistido para sobreviver a redeploy), `pricing_config`
(JSON da calculadora — schema em `app/orcamento/settings.py`; desde a **307** tem o bloco
`datas_especiais` `{<chave>: {rotulo, dias["MM-DD"], markup[4], cache{especial: [4]},
coordenador[4], piso[4], nota_mensagem}}`, com a faixa `natal` (24 e 25/12) garantida na carga;
`_migrate` injeta "Ajudante do Noel" salvo se estiver em `especiais_excluidos` e descarta
sobrescrita de especial que não existe na tabela. Desde a **309** tem o bloco `produtos`
`{<chave>: {rotulo, descricao, ativo, preco, por_faixa{<faixa>: {preco}}, vagas[{label, tipo
especial|ator|coordenador|maquiador, cache: null|R$, needs_makeup}], inclui_noturno}}` (preço FIXO
por visita, fora do markup; `cache: null` = pela tabela vigente na data do evento; labels de
coordenador/maquiador forçados a "Coordenador"/"Maquiador") e `produtos_estimativa {fator_cache,
markup}` (produto sem preço numa faixa: Σ cachês × fator × markup, marcado "estimativa"); os dois
produtos padrão "Visita Mágica — Papai Noel" (2.500; natal 5.000; vagas Papai Noel com make,
Coordenador, Maquiador) e "… + Ajudante" (3.600; natal 6.500; + Ajudante do Noel) entram pelo
`setdefault` só quando a chave está AUSENTE; `_migrar_309` normaliza o bloco na defensiva e DESFAZ a
engenharia reversa da 307 — "Papai Noel" `[712, 800, 850, 900]` → `[600, 650, 675, 700]` e "Ajudante
do Noel" `[423, 480, 510, 540]` → `[270, 320, 345, 370]`, só quando estiverem exatamente nesses
valores; a troca 600→712 de `_migrar_307` foi removida: cachê é cachê, o preço da Visita vem do
produto), `calendar_sync_cache`, `calendar_auto_sync_at`, `whatsapp_form_number`.

### 2.11 Migrations

- Alembic via Flask-Migrate, **sempre escritas à mão** (`migrations/versions/`).
- Head atual: **rode `flask db heads`** — head único. O head vigente no momento desta revisão está
  **só no cabeçalho deste documento** — versionar o head em dois lugares foi o que produziu a
  divergência corrigida em 2026-08-06 (esta seção declarava `b7d4f81a6e0c`, da 204b, enquanto o
  head real já era `e7a1c94f20b3`, da 209). **A mesma divergência se repetiu**: entre a 209 e esta
  revisão (239) a cadeia recente abaixo não foi atualizada a cada feature (235, 236, 237, 238 e
  catalogo-fase-1 têm migration própria e não aparecem listadas) — só o cabeçalho do documento
  vinha sendo corrigido. Não confie na lista "Cadeia recente" para o head; confie só no cabeçalho.
- Cadeia recente (histórico até a 209; **não é exaustiva a partir daí** — ver nota acima):
  `27acb021e8d6` → `aa1bb2cc3dd4` (review asset status) → `7c2d9e4f1a3b`
  (figurino_missing_dismissals) → `4e6f8a1c2d5b` (figurino_sheet tags) → `9f1c3a7b5e2d`
  (catalog characters) → `c8d2f4a6b013` (impressões 3D) → `d9e3a5b7c124` (multi-arquivos)
  → `e4f7b2c9a350` (pendência 3D por evento) → `a3c7e1d59f42` (marketing) → `b7d4f81a6e0c`
  (marketing multi-Tema) → … → `c8f4d92e17ab` (catalogo-fase-1) → `d1c7b93a2f60`
  (`event_roles.does_transport`, feature 239) → `e2d8ca4b3071` (`event_roles.cache_cap_note`,
  feature 239, **head atual**).
- Features **186**, **187**, **199** e **203** não geraram migration (reusaram colunas existentes).
- Os papéis `ARTISTA_3D` e `MARKETING` **não** vêm por migration: papéis são linhas de `roles`
  semeadas por `seed.py` (mesmo tratamento de `REVENDEDOR_EDUCAMANTO`), e o Render roda
  `flask db upgrade && python seed.py` no start.
- Produção aplica `flask db upgrade && python seed.py` no start (`startCommand` do `render.yaml`).

---

## 3. Mapeamento de APIs e Endpoints

Blueprint único `api_bp` com `url_prefix="/api"` (`app/api/__init__.py`). Cada módulo de rotas é
importado por efeito colateral. Autenticação por **cookie de sessão HttpOnly** (Flask-Login) —
o frontend sempre usa `credentials:"include"` via `apiFetch`. Erros seguem o envelope
`json_error(msg, status, fields=...)` de `app/api_utils.py`.

### 3.1 Autenticação e sessão — `app/api/auth.py`
| Método | Rota | Observação |
|---|---|---|
| POST | `/api/auth/login` | |
| POST | `/api/auth/logout` | |
| GET | `/api/auth/me` | devolve papéis, `impersonating`, `is_educamanto_responsavel` |
| POST/DELETE | `/api/auth/impersonate` | "Ver como" — só superadmin **real** (`_require_real_superadmin`) |

### 3.2 Dashboard e RH
`GET /api/dashboard` (`dashboard.py` + `dashboard_service.py`) · `GET /api/rh/dashboard`.

> **Feature 239**: `GET /api/dashboard` ganhou `portal_url` (raiz do Portal do Artista, mesma
> fonte de `_portal_url()` em `app/email_service.py`; `null` quando a env `PORTAL_URL` não está
> setada). O card "Confirmações pendentes" usa para incluir o link do portal na mensagem de
> cobrança pelo WhatsApp — sem a env, o link é omitido em vez de sair quebrado.

> **Feature 266**: ganhou `formularios` — os cinco contadores de `formularios_ops.count_status()`
> (`total`, `sem_evento`, `sem_cliente`, `ambiguos`, `futuros_sem_evento`), **a mesma fonte dos
> cartões de `/formularios`**, para os dois números não poderem divergir. Gate: o mesmo
> `show_comercial` (COMERCIAL ∪ FINANCEIRO ∪ SUPERADMIN); fora dele a chave vem `null` e a seção
> não renderiza. Embutido aqui, e não consumido de `GET /api/formularios/respostas`, por dois
> motivos: aquele endpoint carrega 200 respostas inteiras para devolver 5 inteiros, e o
> `_require_vendas` dele lê `current_user.roles` **cru** — ignora impersonação, então um SUPERADMIN
> em "Ver como CASTING" continuaria vendo o card.

> **Feature 298**: o bloco `formularios` deixou de ser os cinco contadores. Agora é
> `{contagens, pode_criar_evento, motivos_encerramento, a_chegar[], ja_passou[]}`, montado por
> `destino_ops.listar_sem_destino()`: os formulários que chegaram desde o corte (meia-noite de SP da
> `release_date`, ou 01/06/2026) sem evento e sem encerramento, **uma linha por telefone**
> (representada pelo que chegou por último), com `severidade` (`vermelho` 0–7 dias · `amarelo` 8–30
> e todo "já passou" · `cinza` > 30 dias ou data suspeita), `dias_ate_a_data` pelo "hoje" de SP,
> marcas `repetido`/`outro_com_evento`/`data_suspeita` e `sugestao` (evento livre da cliente a até 3
> dias). `contagens` são as partições por destino (`sem_destino`, `com_evento`, `encerrados`,
> `historico`, que somam `total`) mais `corte` — a mesma fonte dos cartões de `/formularios`.
> `pode_criar_evento` = papel efetivo em `_CAN_CREATE` (respeita "Ver como"). Contrato:
> `specs/298-formulario-vira-evento/contracts/dashboard-formularios.md`; todos os campos são
> opcionais no tipo TS.

> **Feature 299**: o bloco `comercial` deixou de ser só `{pending_payments}`. Agora é
> `{corte, pode_editar_venda, pending_payments[], cobrancas_resumo, sem_valor}`, montado por
> `app/financeiro/cobranca_ops.py` — núcleo novo e puro, **fonte única da Home e da página do
> evento**. O grupo é uma venda só: valor do principal, recebido de todos os eventos do grupo
> (cancelados inclusive; desde a **306** o saldo, a quitação, o sinal e a parcela descoberta contam o
> recebido **menos** as devoluções à cliente aprovadas do grupo, que saem à parte em `devolvido` —
> `pending_payments[]` e o `cobranca` do detalhe ganham a chave; o `recebido` mostrado continua o
> bruto); vencimento = data combinada > 1ª parcela que o recebido não cobre > 2 dias
> antes do 1º evento vivo e sem 🟧/🟠 (os dois últimos nunca antes da data da venda); folga de
> centavos de R$ 1,00; sinal pendente só sem data combinada e sem cronograma. `pending_payments`
> continua sendo a lista de cobranças, com as chaves antigas (bundle em cache) mais `cliente`,
> `data_evento`, `vencimento(_origem)`, `dias_ate_vencimento`, `sinal_pendente`, `severidade`
> (`vermelho` ≤ 2 dias · `amarelo` 3–30 ou sinal pendente · `cinza` > 30), `selo` em pt-BR, `nota`
> e `grupo_comercial`; `severity` passa a ser derivada da cor. `sem_valor` traz
> `a_acontecer[]`/`ja_aconteceu[]` (vazio, zero ou abaixo de R$ 1,00, desde a data de início, fora
> cortesia, ensaio, 🟧/🟠, Loja Virtual e outro evento de grupo; régua da 298) com `por_cor` e
> `para_agir`; `cobrancas_resumo` traz `por_cor`, `para_agir` e `total_em_aberto`. Falha interna
> **nunca** vira `comercial: null`: a lista que falhou vem `null` e a tela mostra o aviso; `null` no
> bloco continua significando "sem permissão". `formularios` ganhou `para_agir`. Contrato:
> `specs/299-sem-valor-cobrancas/contracts/dashboard-comercial.md`.

### 3.3 Agenda e Eventos — `agenda.py` (leitura) / `agenda_write.py` (escrita)
| Método | Rota |
|---|---|
| GET | `/api/agenda`, `/api/agenda/day/<date_str>`, `/api/talents`, `/api/events/<id>`, `/api/events/new/options`, `/api/events/new/prefill` |
| GET | `/api/events/<id>/casting-options` *(feature 215)* |
| GET | `/api/events/sumidos-google` *(feature 303 — a faixa: `{pode_ver, total, limit, items: [{id, title, start_at}]}`; quem não vê recebe 200 vazio)* |
| POST | `/api/events/<id>/devolver-ao-google` *(feature 303 — só Superadmin; responde o detalhe + `devolucao_google: {resultado}`; erros com `codigo`)* |
| POST | `/api/events/<id>/cancelar` *(feature 224; corpo, resposta e recusas reescritos na 306 — ver "Feature 306" abaixo)* |
| GET | `/api/events/<id>/impacto-exclusao` *(224; a 306 soma as chaves do ato e a prévia `?devolucao=`)*, `/api/events/cancelamentos` *(224; a 306 soma `resumo` a cada cancelado; a 312 abre ao FINANCEIRO e filtra por `mes` e `devolucao` — §4.3)* |
| PATCH | `/api/events/<id>/devolucao` *(feature 306 — "Alterar devolução" do cancelado; só Superadmin real; responde `{ok, resumo}`)* |
| PATCH | `/api/events/<id>/motivo-cancelamento` *(feature 306b — "Editar motivo" do cancelado; Superadmin ou Comercial pelo papel real; corpo `{motivo}`; o texto vale para os dias do grupo cancelados com o mesmo motivo e troca o antigo no `EventLog` e no `AuditLog` `event_cancelled`; 409 `nao_cancelado`, 400 `fields.motivo`; responde `{ok, motivo, eventos}`)* |
| POST | `/api/events/<id>/multas` *(feature 306 — multa ao elenco depois do ato; só Superadmin real; responde `{ok, resumo, gastos}`)* |
| POST | `/api/events`, `/api/events/<id>/confirm`, `/api/events/<id>/observations`, `/api/events/<id>/sync`, `/api/events/<id>/roles`, `/api/events/<id>/invoices`, `/api/events/<id>/contracts`, `/api/events/<id>/payments`, `/api/events/<id>/reimbursements` |
| POST | `/api/roles/<id>/assign`, `/api/roles/<id>/invite`, `/api/roles/<id>/figurino-done`, `/api/roles/<id>/dismiss`, `/api/roles/<id>/restore` |
| POST | `/api/roles/<id>/payment-status`, `/api/roles/<id>/figurino-sheet` *(feature 192)* |
| POST\|DELETE | `/api/roles/<id>/transporte` *(feature 239 — marca/desmarca o carrinho de transporte; `POST` recusa com 400 só quando `event.is_outside_sp` é `False` — desconhecido vira `True` ao marcar (hotfix 239b); `DELETE` não tem essa guarda para permitir limpar marcação de evento que deixou de ser fora de SP)* |
| POST | `/api/events/<id>/travel-estimate` *(desde o hotfix 239b também reclassifica dentro/fora de SP)*, `/api/events/<id>/materials`, `/api/events/<id>/feedback-link` *(feature 192)* |
| POST | `/api/contracts/<id>/toggle-signed`, `/api/reimbursements/<id>/collect` |
| PATCH | `/api/events/<id>`, `/api/events/<id>/logistics`, `/api/payments/<id>` |
| PATCH | `/api/events/<id>/basico`, `/api/events/<id>/comercial`, `/api/events/<id>/form-response` *(feature 215)* |
| PUT | `/api/events/<id>/clients` *(feature 215)* |
| PATCH | `/api/events/<id>/orcamento` *(feature 273: vincula/desvincula orçamento; aplica fora de SP, equipe e — sem venda — valores de 1h a 4h; 409 `event_id` se o orçamento está preso a outro evento vivo, 409 `orcamento_de_outro` se o vínculo atual é de outro vendedor; `POST /api/events` responde o mesmo 409 `event_id`)* |
| DELETE | `/api/events/<id>`, `/api/roles/<id>`, `/api/observations/<id>`, `/api/contracts/<id>`, `/api/payments/<id>`, `/api/reimbursements/<id>` |
| DELETE | `/api/roles/<id>/figurino-done` (desmarcar), `/api/materials/<id>` *(feature 192)* |

> **`GET /api/events/<id>` é o payload único da tela de detalhe** (feature 192): além dos blocos
> antigos, traz `event.description`/`google_html_link`/`travel`, `materiais`, `ratings`,
> `client_feedbacks` e — sob os gates comercial/financeiro já existentes — `acrescimos`,
> `gastos`, `mensagens`, `reembolsos_pendentes_total` e `feedback_link_pendente`. Cada item de
> `elenco` inclui `talent` completo (medidas de figurino, WhatsApp com DDI), `role_type`,
> `payment_status`, `availability` (conflito de agenda) e a ficha de figurino vinculada.
> Os cargos são ordenados por `id` — `CalendarEvent.roles` não tem `order_by` e o Postgres
> reordenava a lista a cada UPDATE.
> **RBAC das escritas novas**: `_CAN_EDIT_EVENT` (payment-status, figurino-sheet,
> figurino-done DELETE, travel-estimate, **transporte** — feature 239) · `_CAN_ENSAIO_MATERIAL`
> (materials) · Comercial/Superadmin (feedback-link).
>
> **Payload do detalhe do evento — adições da feature 239.** Cada item de `elenco` ganhou
> `is_presence` (sempre presente, define a anatomia do card — vaga de presença não recebe NENHUM
> campo de dinheiro no payload), `does_transport`, `transporte_valor` (parcela de UM veículo, o
> mesmo número em todos os papéis do evento) e `cache_cap_efetivo` (o teto já calculado pelo
> servidor, `max(cache_cap + parcela quando marcado, cache_value)` — a tela não refaz essa conta).
> `cache_cap`/`cache_cap_note` **só saem para superadmin** (antes `cache_cap` ia para
> `show_casting` inteiro); o casting comum continua sem ver o número do teto, só o aviso de que
> passou dele. O evento ganhou `data.maquiagem` (`{precisa, fechado}` — decisão 17: `fechado` exige
> vaga extra com nome ~"maquiad" **e** talento atribuído) e `venda.orcamento_history_id`, que só
> vem preenchido quando quem lê consegue de fato abrir o orçamento (superadmin, ou o comercial
> dono daquele orçamento) — demais papéis (ex.: FINANCEIRO) recebem `null` e o React omite o link
> "Orçamento de origem" na aba Comercial.
> **⚠️ A parte "o comercial dono daquele orçamento" foi SUPERADA pela feature 301 (21/09/2026)**:
> não há mais checagem de dono aqui — `venda.orcamento_history_id` e `venda.orcamento` saem para
> quem tem o módulo de Orçamento (COMERCIAL ou SUPERADMIN), seja o orçamento de quem for. O que
> depende de autoria é a chave `pode_gerir`, que diz se a pessoa pode mexer no vínculo. FINANCEIRO
> continua com `null` e só `tem_orcamento`. A regra vigente está em §3.13. `characters` (usado por telas legadas) passou a vir da
> tabela `EventRole` (fonte de verdade) quando o evento já tem roles de personagem, caindo para o
> parse do título só em evento sem nenhuma — decisão 6, para o texto livre do título nunca mais ser
> a única fonte de quem é personagem.
>
> **Feature 305 — o BV do orçamento no evento.** `GET /api/events/new/prefill` ganha
> `acrescimos_do_orcamento` (`{personalizado, linhas: [{tipo, descricao, is_bv, percentual,
> valores_brl: {"1".."4", custom}}]}`, o BV cheio por duração). `POST /api/events` aceita
> `bv_recipient`/`bv_pix` e **ignora a lista `acrescimos`** (em toda criação); com orçamento cujo
> BV vai nascer, sem os dois → **400** com `fields` e a mensagem do PIX, **antes do Google**. O BV
> nasce em reais, na proporção da venda (`orcamento_evento_ops.gravar_acrescimos_do_orcamento`).
> `PATCH /api/events/<id>/orcamento` aceita os mesmos dois campos (400 depois da autoria da 301) e o
> `relatorio_orcamento` ganha `acrescimos_criados`, `bv_total`, `acrescimos_ignorados`.
> `PUT /api/events/<id>/acrescimos`: item com `id?` (herança só da mesma linha), `descricao`
> ausente = mantém, `value` número (a tela nova manda número) ou texto pt-BR; recusa a lista inteira
> com **400** e `fields` `items.<i>.<campo>` (BV sem quem recebe/PIX; valor ilegível ou ambíguo —
> "1.500" sem vírgula, "1,309.52", ≥ 10¹⁰; BV sem valor, zero ou negativo; o mesmo `id` duas vezes
> → `items.<i>.id`; BV pago removido ou retipado), sem apagar nada; sincroniza a comissão; a troca
> de quem recebe ou do PIX num BV pago vai ao `AuditLog` (`entity_type="event_bv"`, PIX mascarado).
> O detalhe ganha `acrescimos[].descricao`/`bv_pix`, `venda.orcamento.bv` e
> `venda.bv_do_orcamento_pendente` (`{valor, percentual, duracao}`; só para evento criado/ligado
> depois de `CORTE_ALERTA_BV` — com a constante vazia, nenhum). `PATCH …/comercial` devolve
> `aviso_bv`; a edição completa põe os avisos do BV em `warnings`; o `relatorio_orcamento` do vínculo
> ganha `bv_acompanhou` (a B10 quando o "Vincular e aplicar" põe a venda num evento que já tinha BV).
> `POST /api/financeiro/pagamentos/set-status` com `item_type="bv"` aceita `valor_esperado` (o
> valor que a Planilha mostrou; opcional): diferente do gravado, ao marcar pago ou no banco → **409**.
> No PUT de acréscimos, a linha BV em R$ aceita `valor_visto` (o valor que o editor abriu): o BV a
> pagar com outro valor (a venda o mudou depois) → 400 na linha. O `acrescimos_do_orcamento` do
> prefill ganha `nota_do_orcamento` e `divisor_da_nota` (a tela compara líquidos, como o servidor).
>
> **Hotfix 215b — taxa e vendedor da comissão.** `PATCH /api/events/<id>/comercial` e
> `PATCH /api/events/<id>` recusam com **403** (`fields.commission_rate` / `fields.seller_id`) a
> mudança que quem pede não pode fazer, comparando com o que está gravado
> (`event_ops.taxa_e_vendedor_negados`): a **taxa** só o Superadmin muda; o **vendedor** já gravado
> só Financeiro e Superadmin trocam — a Comercial preenche o vazio. Reenviar o valor de sempre
> passa. O detalhe ganha `venda.pode_mudar_taxa` e `venda.pode_trocar_vendedor`, que a tela usa
> para travar os campos. Paridade com `_handle_update_comercial` (Jinja).
>
> **Feature 299 — valor da venda e cobrança do grupo.** `POST /api/events` e
> `PATCH /api/events/<id>` aceitam `valor_a_definir` (não gravado): com ele, sem cortesia, a venda
> grava `NULL` e os erros de valor não saem. Sem ele, valor vazio, zero ou abaixo de R$ 1,00 → 400
> em `sale_value`/`sale_value_gross`, com a exceção do valor simbólico que o evento já tinha, campo a
> campo (`event_ops.erros_de_valor_de_venda`). No outro evento de um grupo, a edição completa não
> valida nem grava nada da venda. `PATCH /api/events/<id>/comercial` recusa o valor novo entre
> R$ 0,01 e R$ 0,99 (vazio = "a definir"). `PATCH /api/events/<id>/orcamento` trata valor abaixo de
> R$ 1,00 como "sem venda". No detalhe, `cobranca` sai do mesmo núcleo da Home: `outstanding` =
> saldo do grupo, `due` = vencimento, `enabled` só no principal ou avulso, a qualquer momento (299b),
> fora cortesia, simbólico e sem valor. Chaves novas, opcionais: `valor`, `recebido`, `quitado`,
> `cortesia`, `sem_valor`, `valor_simbolico`, `sinal_pendente`, `vencimento_origem`, `escopo`,
> `grupo_tamanho`; a cortesia nunca é `quitado` (a página diz "cortesia ou permuta").
> `venda` ganha `sem_valor`/`a_definir`/`valor_simbolico`; `pagamentos` ganha `outros_do_grupo`.
> A comissão que nasce quando o valor chega depois (evento cadastrado e vendido num mês anterior)
> entra no ciclo do mês do valor (`payable_from`). Contratos: `specs/299-sem-valor-cobrancas/contracts/`.
>
> **Feature 303 — evento que sumiu do Google Agenda.** Contrato completo, com a tabela de erros e
> os textos fixos: `specs/303-sync-nao-apaga-venda/contracts/api-endpoints.md`. O que muda aqui:
> `POST /api/events/<id>/sync` confere o próprio evento no Google antes de mexer — ausência
> confirmada → **409** "Este evento não está mais no Google Agenda. Nada foi alterado." (marcado ou
> não; nada é tocado), sem resposta → 502 como antes, presente e marcado → a marca sai (histórico
> com quem clicou) e sincroniza. `PATCH /api/events/<id>` e `…/basico` de evento marcado não
> escrevem no Google e nunca dão 409 por isso. `DELETE /api/events/<id>` de
> evento marcado → **409** `codigo: "sumiu_do_google"` (a recusa mora em `_delete_event_flow`; a
> rota Jinja `POST /events/<id>/delete` recusa pela mesma regra). **Corrigido na 306**: o
> `POST …/cancelar` de evento marcado deixou de dar 409 — o ato tira a marca
> (`sumico_ops.desmarcar`, motivo `MOTIVO_CANCELADO`, que dá o aviso do sino como lido) antes de
> gravar `cancelled_at`, e não tenta remover do Google o dia marcado, que já não está lá; o impacto
> responde `acao: "cancelar"` para todo marcado. A mensagem do `DELETE` passou a oferecer as duas
> saídas: devolver ao Google Agenda ou cancelar. Toda
> exclusão passa a limpar o histórico do ensaio-filho e os avisos do sino do evento. Resumo da
> agenda (mês, dia, busca): `situacao?` (`cancelado` > `sumiu_do_google` > `exclusao_solicitada`)
> e `situacao_desde?`. Detalhe: `event.situacao?`, `event.sumiu_do_google?: {desde}` (só marcado e
> não cancelado) e `event.google_html_link` nulo em evento marcado ou cancelado.
>
> **Feature 306 — o dinheiro do cancelamento.** Contrato completo, com o corpo, a resposta e a
> ordem das recusas de cada porta: `specs/306-dinheiro-do-cancelamento/contracts/api.md`. Gate e
> 409 de cada porta, e os 18 códigos: §4.3. O que muda aqui:
> - **`POST /api/events/<id>/cancelar`**: corpo `{motivo, devolucao: {modo, valor?, nome?, pix?,
>   observacao?}, imposto_retido?, bvs?: [{acrescimo_id, recebedor, pix}], multas?: [{role_id,
>   valor, talent_id?}], alcance?, novo_principal_id?, venda_nova?, venda_esperada?}`, com `modo` em
>   `tudo`, `parte` ou `nada`; sai `bv_negociado`, e o corpo antigo sem `modo` leva 400
>   `devolucao_modo`. Resposta `{ok, resumo, aviso, google_removido, gasto_id, dias_cancelados,
>   venda_passou_para, ensaios_cancelados, avisados: {email, ensaio, casting}}` (`google_removido` e
>   `gasto_id` ficam um ciclo). Os 400 de campo saem todos de uma vez e **depois** da trava, porque
>   dependem do pago, do regime e da nota relidos nela. O núcleo (`cancel_ops.cancelar_evento`)
>   trava, grava e commita; o Google (os dias e os ensaios) e os e-mails ao elenco saem depois do
>   commit. Grupo: no 1º dia, `alcance` escolhe entre `todos` (o principal em `venda`, os outros
>   dias em `satelite`) e `so_este_dia` (a venda passa ao dia vivo mais cedo, `novo_principal_id`,
>   com `venda_nova`); um dia que não é o 1º se cancela sozinho pelo corte (`dia`, com `venda_nova`:
>   a venda do grupo diminui). Sai a 409 de líder. Venda da Loja Virtual é `virtual`, sem devolução
>   nem multa.
> - **`GET …/impacto-exclusao`** ganha `regime`, `sumiu_do_google`, `pago`, `ja_devolvido` e
>   `max_devolucao` do **grupo** (`total_recebido` continua o do próprio evento), `com_nota`,
>   `imposto_aliquota`, `bvs[]`, `comissao {beneficiario, cheia, paga, a_pagar}`, `grupo?`,
>   `venda_do_grupo`, `ensaios[]`, `cache_pago`, `faltam_dias` e `comprovantes_sem_valor`; cada
>   item de `elenco[]` (uma escalação, sem quem recusou e sem a vaga de presença) ganha `role_id`,
>   `day_event_id`, `talent_id`, `talent_pix_informado` e `talent_email_informado`, com o PIX só
>   para `show_financeiro`. Com `?devolucao=` (e `&venda_nova=`) é a **prévia**: a mesma conta da
>   execução, sem trava e sem gravar, que responde só `{efeito}`. `devolucao_sugerida` e
>   `is_group_leader` ficam um ciclo.
> - **Detalhe** (`GET /api/events/<id>`): `event.cancelamento` (o `ResumoCancelado`,
>   `cancel_ops.serializar_resumo_cancelado`) só com `show_comercial`; comissão, BVs, imposto,
>   taxa e PIX só com `show_financeiro`; `limites_devolucao {piso, teto, atual, refaz_retido}` e
>   `elenco[]` só com `flags.can_edit_venda_cancelado`. Flags novas `can_edit_venda_cancelado` e
>   `can_edit_pagamentos` (`agenda_read.flags_do_detalhe`). No cancelado, `kpi` não sai, `bv_pix` só
>   sai com a flag de correção e `venda.pode_mudar_taxa`/`pode_trocar_vendedor` exigem a flag; os
>   `gastos` são os dos dias do ato (`cancel_ops.dias_dos_gastos`). No vivo, o KPI e os gastos
>   contam só os dias vivos. Novos: `cobranca.devolvido` e `group.satellites[].cancelado`.
> - **`PATCH …/devolucao`** `{devolucao_total, nome?, pix?, observacao?, imposto_retido?}` →
>   `{ok, resumo}`: no `venda` e no `legado`, o novo total devolvido do grupo; no `dia`, o total
>   daquele dia. **`POST …/multas`** `{multas: [{elenco_id, valor}]}` → `{ok, resumo, gastos}`: um
>   Gasto Extra aprovado por escalação, com a data do lançamento; vazio ou 0 é ignorado, e nada com
>   valor > 0 dá 400 `fields.multas`.
> - **O Superadmin corrige o cancelado** e o retido, a comissão e o BV do retido se refazem na mesma
>   transação: `PATCH …/comercial` (o gancho de comissão vira despachante —
>   `cancel_ops.recongelar_do_comercial` no cancelado, `_sync_commission_payment` no vivo), `PUT
>   …/acrescimos` (grava no lugar pelo `id`, `comercial_ops.alterar_acrescimos_do_cancelado`; lista
>   não vazia sem nenhum `id` num evento com acréscimos → 400 "Recarregue a página"; BV novo em % →
>   400) e os três comprovantes (`cancel_ops.gravar_comprovante_no_grupo`, que trava o grupo também
>   no vivo e, no `POST`, recusa antes de salvar o arquivo). As três respondem o detalhe, com
>   `event.cancelamento`.
> - **Jinja gêmeo**: a tela antiga do evento recusa no cancelado, com aviso e para todo papel,
>   `update_comercial`, `update_sale` e as ações de comprovante e de reembolso
>   (`_ACOES_RECUSADAS_NO_CANCELADO`, `app/calendar/routes.py`); agrupar, desagrupar e excluir
>   recusam o cancelado; na Planilha antiga, o BV passa por `marcar_status_do_bv` e a devolução de
>   cancelado trava o evento; `set_commission_status` recusa linha de evento cancelado.
> - **Escala**: no cancelado, tirar o artista da vaga não manda o e-mail de remoção
>   (`casting_ops._manda_email_de_remocao`) — o ato já avisou o elenco. Vale para a API e o Jinja.

### 3.4 Talentos — `talents_read.py` / `talents_write.py`
`GET /api/talents/directory`, `/api/talents/character-suggestions`, `/api/talents/<id>`,
`/api/talents/<id>/ratings` · `PATCH /api/talents/<id>` ·
`POST /api/talents/<id>/{approve,reject,notes,photo}` · `DELETE /api/talents/<id>/photo`.
**Feature 274** (sem migration): `POST /api/talents/<id>/reset-senha` manda ao talento o link de
redefinição de senha do portal (gate `_can_edit_talent`; 400 quando o cadastro não tem e-mail;
grava `AuditLog`), e `GET /api/talents/<id>` ganha o bloco `portal`
(`tem_senha`, `reset_pendente`, `reset_expira_em` **em horário de São Paulo**) apenas para quem
gere talento. O token nasce em `portal_account_ops.emitir_token_de_reset`, fonte única deste
caminho e do "Esqueci minha senha" do artista — enviar de novo invalida o link anterior.
Avaliações: `GET /api/ratings` · `POST /api/ratings/modo-anonimo`.
Fila de emails devolvidos (feature 219, gate `_can_edit_talent`):
`GET /api/talents/bounces` (agrupada por endereço, `?resolvidos=1` inclui as fechadas) ·
`POST /api/talents/bounces/resolve` (resolve **por endereço**, não por mensagem).
Alimentada pela thread `email-bounce` (30 min, claim atômico em `import_state`), que lê a caixa do
remetente por IMAP em modo somente leitura — ver `app/integracoes/imap_client.py`.

### 3.5 Figurino — `figurino_read.py` / `figurino_write.py`
`GET /api/figurino` · `POST /api/figurino` · `PATCH|DELETE /api/figurino/<id>` ·
`POST|DELETE /api/figurino/<id>/photo` · `POST /api/figurino/<id>/photo/rotate` ·
`POST /api/figurino/faltantes/dispensar` · `POST /api/figurino/faltantes/associar`.

### 3.5.1 Produção de Figurinos e Pedido de Compra — `figurino_producao_read.py` / `_write.py` (features 225 e 225c)

| Método | Rota | Gate | Nota |
|---|---|---|---|
| GET | `/api/figurino/producoes` | interno | Filtros `status`, **`tipo`**, `abertos`, `responsavel`, `evento`, `ficha`, `busca`. Devolve `flags` (`can_create`/`can_execute`/`can_approve`), `kind_labels`, `status_abertos` |
| POST | `/api/figurino/producoes` | interno | Abre pedido (`kind`: `producao`\|`manutencao`\|`compra`) |
| GET | `/api/figurino/producoes/<id>` | interno | Detalhe + `anexos`, `logs`, `gastos` e `transicoes` válidas. **`flags.can_execute` é avaliado PARA ESTE pedido** (o responsável por uma compra recebe `true`) |
| PATCH | `/api/figurino/producoes/<id>` | `pode_executar_pedido`, ou quem abriu enquanto ninguém assumiu (e, em compra, enquanto está `solicitado`) | `responsible_id` só é aceito de quem executa — **ou de quem abriu, se for compra** |
| DELETE | `/api/figurino/producoes/<id>` | FIGURINO/SA | Gastos vinculados sobrevivem |
| POST | `/api/figurino/producoes/<id>/status` | `pode_executar_pedido`; **aprovar só SA** | `motivo` obrigatório ao cancelar. Falta de permissão volta **403**, não 400 |
| POST | `/api/figurino/producoes/<id>/comentarios` | interno | Nota no histórico |
| POST\|DELETE | `/api/figurino/producoes/<id>/anexos[/<anexo_id>]` | `pode_executar_pedido` | multipart: `file`, `kind` (`foto`\|`orcamento`), `supplier_name`, `amount` |
| POST\|DELETE | `/api/figurino/producoes/<id>/gastos[/<gasto_id>]` | `pode_executar_pedido` | Vincula/desvincula `SpecialExpense` existente |
| GET | `/api/figurino/producoes/<id>/gastos-vinculaveis` | interno | Gastos do mesmo evento + categoria Figurino |
| GET | `/api/figurino/producoes/responsaveis` | interno | Usuários FIGURINO/SUPERADMIN, com `tem_email`. **`?tipo=compra`** devolve a equipe interna inteira |

"interno" = qualquer papel menos `REVENDEDOR_EDUCAMANTO` sozinho (`producao_ops.pode_abrir`).
As mutações devolvem `{producao, warning?}` — `warning` é falha do Google Agenda, **nunca** erro:
o pedido foi salvo.

### 3.6 Financeiro — `financeiro_read.py` / `financeiro_write.py`
| Método | Rota | Nota |
|---|---|---|
| GET | `/api/vendas/pipeline` | **Dashboard Comercial** (feature 196 — o payload plano do "pipeline" da 156 deixou de existir). Aceita `period` (`este_mes`/`mes_anterior`/`30d`/`custom`+`start`/`end`) e `seller_id`. Devolve `kpis` (`total_vendido`, `ticket_medio`, `eventos_fechados`, `comissao_prevista`, `desconto_concedido`), `eventos[]` (venda, cliente, contrato, cobrança, vendedor — **sem custo e sem lucro**), `can_filter_seller`, `scope_label` e `sellers` (só gestor). Núcleo em `app/financeiro/vendas_ops.py`. **Feature 205**: vendas da Loja Virtual (`event_type='VIRTUAL'`) saem do funil por padrão e voltam com `?incluir_loja_virtual=1`; o consolidado do canal vem em `loja_virtual` **só para gestor** (`can_filter_seller`) |
| POST | `/api/virtuais/pedidos/<id>/avisos/<kind>/reenviar` | **Feature 205f**: reentrega um aviso automático que falhou (FR-039c). Só age sobre aviso já registrado e **falhado** — reenviar um entregue dá 400, para não mandar um segundo e-mail à família. Gate: `COMERCIAL`/`SUPERADMIN` |
| GET | `/api/financeiro/dashboard` | DRE / KPIs — **feature 189**: `kpis` inclui `margem_bruta`, `margem_ebitda`, `tax_rate` (alíquota do `SiteSetting`, rótulo dos impostos provisionados) e as faixas do Fator R (`fator_r_rate_low`/`fator_r_rate_high`); cada item de `eventos[]` inclui `receita` e `event_type`. **Feature 205**: a receita virtual continua na cascata da DRE (Fator R e break-even exatos) mas sai de `ticket_medio` e `a_receber_clientes`; `paineis.loja_virtual` traz o consolidado do canal e `?incluir_loja_virtual=1` reincorpora o canal aos indicadores de evento (FR-055) |
| GET | `/api/financeiro/comissoes` | **feature 187** — KPIs + `by_seller` + `entries` + `can_manage` + `sellers` |
| GET | `/api/financeiro/pagamentos` | planilha de pagamentos |
| POST | `/api/financeiro/comissoes/pagar-mes` | **feature 187** — liquidação em lote atômica |
| POST | `/api/financeiro/pagamentos/set-status`, `/bulk-action` | Status válidos: **`nao_pago` \| `pago` \| `no_banco`** (`_VALID_PAYMENT_STATUS`) — não existem `pendente`/`agendado`. **Feature 199**: os 3 status valem para TODOS os tipos de item (`cache`/`salary`/`expense`/`bv`/`commission`/`recurring`), inclusive `bulk-action`; `_build_commission_items`/`_build_recurring_items` (`app/financeiro/routes.py`) passaram a incluir `no_banco` no filtro de leitura — antes esses itens sumiam da planilha ao virar `no_banco` |
| POST | `/api/financeiro/pagamentos/salary/<sp_id>/advance`, `/salary/advance/<adv_id>/delete` | |
| GET | `/api/financeiro/pagamentos/export` | CSV |

**Feature 306 — o cancelado nos relatórios e na Planilha** (gates sem mudança; contrato em
`specs/306-dinheiro-do-cancelamento/contracts/api.md` §17–§19). O cancelado sai das métricas do
mês do evento, e o **retido** (pago − devolvido do grupo; só `venda` e `legado` com dinheiro) entra
pelo **mês do cancelamento**, por uma fonte só: `cancel_ops.cancelados_do_periodo`.
- `GET /api/financeiro/dashboard`: `dre.{realizado,projetado,total}.retido_cancelamentos` e
  `.n_cancelados` sempre (o retido entra no Realizado e no Total, nunca no Projetado);
  `paineis.cancelamentos` sempre (`{quantidade, pago, devolvido, devolucao_a_pagar, retido,
  comissao_retido, bv_retido, imposto, efeito_resultado, itens[]}`); a barra "Retido de
  cancelamentos" em `receita_por_tipo` (`dre_ops.ROTULO_RETIDO`); `monthly_trend[].retido?`,
  `top_sellers[].retido?` e `notas_fiscais[].cancelado?`/`retido?`. Os gastos extras do período e a
  tendência saem de `app/financeiro/dre_ops.py`, a mesma fonte do Jinja, **sem** a devolução de
  evento cancelado (já está no retido).
- `GET /api/vendas/pipeline`: `kpis.retido_cancelamentos?`, `n_cancelados?` e `comissao_retido?`; o
  retido entra em `total_vendido` do vendedor congelado e a comissão do retido em
  `comissao_prevista` do beneficiário congelado.
- `GET /api/financeiro/comissoes`: `status` pode ser `no_banco` ("No banco"); cada linha ganha
  `tipo?` (`comissao`, `ajuste` ou `estorno`), `original_id?`, `evento_cancelado?`, `ciclo?` e
  `motivo?` (o código lido do prefixo da nota, `MOTIVOS_AJUSTE_COMISSAO`); `kpis.total_no_banco?`
  (`total_month` = pago + no banco + a pagar); quem só tem `no_banco` aparece em `by_seller`.
- `GET /api/financeiro/pagamentos`: o item `bv` sai com `amount = cancel_ops.bv_da_planilha` (no
  cancelado, o BV do retido) e some quando ele é `None`; o item `commission` ganha
  `commission_lines?` (`{id, tipo, event_id, event_title, amount, ciclo, status}`).
- `POST /api/financeiro/pagamentos/set-status`: o `bv` passa por `cancel_ops.marcar_status_do_bv`, a
  função única das duas Planilhas — trava o evento e o acréscimo, compara `valor_esperado` com
  `bv_da_planilha` (409 `valor_mudou`, com `atual`; 409 `bv_nao_esta_a_pagar`) e guarda o valor pago
  em `event_cancellation_bvs.paid_amount`. O `expense` que é devolução de cancelado passa por
  `cancel_ops.marcar_status_da_devolucao`: trava o evento e o gasto e confere `valor_esperado` (409
  `valor_mudou`). A tela manda `valor_esperado` no BV e na devolução; `bulk-action` segue sem
  conferência de valor (`docs/05`).
- `GET /api/admin/desempenho` (rota em §3.11): o cancelado sai do mês do evento; entram
  `vendas[].retido?`, `vendas[].cancelados?` e `totals.retido?`, pelo nome do vendedor congelado.
  `GET /api/clientes/<id>`: `total_sales` inclui o retido, `event_count` não conta cancelado e cada
  item de `events[]` ganha `cancelado`; "Com evento" e "Recorrentes" (`/metricas`) e a lista não
  contam cancelado. `GET /api/dashboard`: a Performance ignora o cancelado.

**Agente auditor financeiro — `audit_agent.py` (feature 221).** Endpoints para o auditor
semanal que roda FORA do servidor (Claude Code na máquina do dono): `GET
/api/audit-agent/<token>/file/<path>` (download read-only de comprovante; escopo
`payments/expenses/invoices/contracts` + allowlist de extensão; `safe_join`) e `POST
/api/audit-agent/<token>/report` (envia o relatório por e-mail — destinatários restritos a
usuários internos ativos). `GET /api/audit-agent/<token>/orphan-attachments` (hotfix 257): arquivos das pastas
`payments`/`contracts`/`invoices` sem linha no banco, com data de envio, tamanho e eventos
candidatos — somente leitura, não re-vincula nada. Token via env `AUDIT_AGENT_TOKEN` (painel do Render, `sync: false` — **ausente desde a migração de
28/08/2026**, ver `docs/05`); inválido/ausente → **404** (molde do webhook InfinitePay; 404 aqui é
configuração, não bug de rota). Nenhum endpoint escreve no banco. Pipeline do auditor em
`scripts/auditor/` (ver `specs/221-agente-auditor-financeiro/spec.md`).

#### Agente de marketing (feature 256) — `app/api/marketing_agent.py` + `app/marketing/desempenho_ops.py`

Mesmo molde do agente auditor financeiro (token de ambiente, 404 para token errado/ausente), mas
este agente **escreve** — e só o que `desempenho_ops` permite:

- `GET /api/marketing-agent/<token>/context?window_start&window_end&card_holder_email` — posts
  publicados (90 dias, com `permalink`), metas (`goal_health`), clientes novos por mês
  (`client_metrics`), gastos de Marketing do mês corrente/anterior (com `batch`), clientes com
  utm na janela e seus eventos. 403 se o titular não for usuário interno ativo.
- `POST /api/marketing-agent/<token>/run` — ingestão idempotente por `run_id`: registra a
  rodada e os arquivos (`sha256` único), faz upsert das fotografias de post, campanhas e conta,
  vincula posts aos cards (permalink > data > nenhum) e mantém o **Gasto Extra de reembolso por
  plataforma × mês civil** (`sync_ad_spend`: created / updated / frozen_ok / frozen_divergent /
  skipped_manual / skipped_currency). `mode=local` só em `FLASK_ENV=development`.
- `POST /api/marketing-agent/<token>/report` — envia o HTML por e-mail (destinatários restritos a
  usuários internos ativos; `send_audit_report_email(..., preheader=…)`) e marca `report_sent`.
- Env **`MARKETING_AGENT_TOKEN`** (painel do Render, serviço `manto-backend`, `sync: false`) = arquivo
  local `.marketing-agent-token`. Sem o env, tudo responde 404 (interruptor geral — 404 aqui é
  configuração, não bug de rota). **Ausente no painel desde a migração de 28/08/2026**: a rodada
  semanal está parada (`docs/05`).

Schema (migration `c4d1e7b2a9f3`): `marketing_agent_runs`, `marketing_import_files`,
`marketing_post_metrics` (única por plataforma+post+`snapshot_date`), `marketing_campaign_metrics`
(única por plataforma+campanha+`period_start`+`period_end`), `marketing_account_metrics`
(plataforma+dia), `marketing_ad_spend_batches` (plataforma+`month_ref`, 1:1 com
`special_expenses`), `marketing_ad_spend_lines`; `marketing_posts.permalink`;
`clients.lead_origin/utm_source/utm_medium/utm_campaign` (preenchidos pelo importador do Kommo).

Leitura para a tela: `GET /api/marketing/desempenho?weeks=4|12|26` ou `?start&end` (gate
MARKETING/SUPERADMIN, `marketing_read.py`). `GET /api/gastos` passa a devolver `marketing_batch`
(null nos gastos comuns). `PATCH /api/marketing/posts/<id>` aceita `permalink` (http(s), sem
querystring).

Núcleo de negócio de comissões: `app/financeiro/comissoes_ops.py`
(`resolve_month`, `get_month_entries`, `get_month_summary_by_seller`, `get_month_kpis`,
`pay_seller_month`). O Jinja legado `app/financeiro/routes.py` **não** importa deste módulo
(decisão explícita da 187).

### 3.7 Gastos — `gastos_read.py` / `gastos_write.py`
`GET /api/gastos`, `/api/gastos/eventos`, `/api/gastos/funcionarios`, `/api/gastos/recorrentes` ·
`GET /api/gastos/recorrentes/<id>/historico` (**feature 189**) ·
`POST /api/gastos` (+ `/<id>/aprovar`, `/rejeitar`, `/vincular-evento`) · `PATCH|DELETE /api/gastos/<id>` ·
recorrentes: `POST /api/gastos/recorrentes` (+ `/<id>/toggle`, `/preencher`, `/pular`),
`PATCH|DELETE /api/gastos/recorrentes/<id>`,
`POST /api/gastos/recorrentes/entry/<id>/{pagar,reabrir}`, `DELETE .../entry/<id>`.

**Feature 306 — a devolução de cancelado travada.** As seis portas de gasto avulso (`POST
/api/gastos`, `…/aprovar`, `…/rejeitar`, `PATCH`, `DELETE` e `…/vincular-evento`) mantêm o gate e
a ordem de hoje e, depois deles, travam o evento da devolução (no vínculo trocado, os dois, por id)
e relêem o gasto. Devolução à cliente ligada a evento cancelado → **409** `codigo:
"devolucao_travada"` (`gastos_ops.GastoLockedError`), com o `event_id` e, em `fields`, o campo que
chegou diferente do gravado (`amount`, `expense_date`, `category` ou `event_id`; `status` no
aprovar e no rejeitar; `id` no excluir): valor, data, categoria e vínculo só mudam pelo "Alterar
devolução" (§3.3). Nome, PIX e descrição ficam livres, e `approved_with_edits` nunca acende. O
caminho inverso também é 409: criar devolução ligada a evento cancelado, ou mudar a categoria ou o
vínculo de um gasto para que vire uma. Criar com `disbursement_type: "cliente"`, ou converter para
ele, → **400** `fields.disbursement_type` ("Devolução à cliente nasce pelo cancelamento do
evento"). `GET /api/gastos` ganha `locked` e `event_cancelled` em cada gasto, e `categories` traz
"Multa de cancelamento".

**`GET /api/gastos/recorrentes` (payload, feature 189).** Além de `grupos`/`month_ref`/
`is_current_month`/`type_labels`/`frequency_labels`/`alerts`, devolve `ref_year`, `ref_month`,
`weekday_labels`, `somas` (estimativa mensal por tipo, só contas ativas) e
`programado_pendente_total`. Cada conta em `grupos[<tipo>]` traz, além das colunas do model, os
rótulos derivados `expected_label`, `dia_label`, `vigencia_label`, `parcelas_summary` (só
`programado`), `estimated_monthly`, `has_entries` (bloqueia exclusão), `occurrences`
(cobranças no mês de referência; **`0` = fora do ciclo/vigência**) e `entries` (todas as
parcelas — só `programado`).

**`GET /api/gastos/recorrentes/<id>/historico` (feature 189).** Todos os
`RecurringExpenseEntry` da conta, do `month_ref` mais recente para o mais antigo:
`{conta_id, conta_name, entries[]}`. Gate `gastos_ops.is_financeiro`; 404 para conta inexistente.
Equivale ao painel `?conta=<id>` da tela Jinja legada.

**Núcleo de negócio (`app/gastos/gastos_ops.py`).** `estimate_monthly_cost(conta)` normaliza a
frequência para custo mensal (semanal ×4, quinzenal ×2, anual ÷12; conta variável usa o teto da
faixa; `programado` retorna 0) e `recurring_summary(contas)` monta `somas` +
`programado_pendente_total`. Fonte única: a view Jinja `app/gastos/routes.py::recorrentes` e o
endpoint da API chamam as mesmas funções (feature 189 — antes a lógica vivia inline na view).

### 3.8 Clientes — `clientes_read.py` / `clientes_write.py`
`GET /api/clientes/`, `/api/clientes/search`, `/api/clientes/<id>`, `/api/clientes/avaliacoes`,
`/api/clientes/metricas` · `POST /api/clientes/quick-create` · `PATCH|DELETE /api/clientes/<id>`.

**Feature 220**: `GET /api/clientes/<id>` inclui `form_history[]` (`{id, form_type_label,
event_date, created_at, event_id, event_title}`) — festas registradas em formulário, inclusive as
anteriores à agenda de 2026 (fonte: `client_ops.list_client_form_history`). Novo
`GET /api/clientes/metricas` → `{new_by_month: [{month, total, formulario, kommo, manual}] (12m,
cronológico; Kommo conta por kommo_created_at), recurring_clients, clients_with_event}`
(`client_ops.client_metrics`).

**`GET /api/clientes/avaliacoes`** (feature 197) — cada item de `feedbacks[]` e `attention[]` vem
com o relacionamento aninhado: `{id, score, comment, tags[], submitted_at, event: {id, title,
event_date} | null, client: {id, full_name} | null}`, mais o bloco `kpis: {media_geral,
total_avaliacoes, percentual_5_estrelas}` calculado sobre o recorte filtrado. `client.full_name`
cai para `ClientFeedback.client_name` (nome digitado no formulário público) quando o evento não
tem cliente vinculada — nesse caso `client.id` é `null`. O núcleo continua em
`client_ops.summarize_feedback`, que carrega evento+cliente com `joinedload` (evita N+1) e casa a
tag pelas **duas** formas do JSON (escapada e literal) com `ESCAPE '!'` — o `LIKE` do PostgreSQL
consome a barra invertida de `\uXXXX` como escape, e por isso o filtro por tag não funcionava.

### 3.9 Catálogo público (anônimo) — `catalogo_read.py`
`GET /api/catalogo`, `/api/catalogo/categorias`, `/api/catalogo/categoria/<slug>`,
`/api/catalogo/<slug>` · **`GET /api/catalogo/elenco-busca`** (autenticado —
`COMERCIAL`/`FIGURINO`/`SUPERADMIN`; devolve Temas + Personagens com `photo_url` e
`figurino_sheet_id`; alimenta a busca visual de elenco e o vínculo pelo lado da Ficha).

### 3.10 Gerenciador de catálogo — `admin_catalogo_read.py` / `admin_catalogo_write.py`
| Método | Rota |
|---|---|
| GET | `/api/admin/catalogo`, `/api/admin/catalogo/<item_id>`, `/api/admin/catalogo/tags`, **`/api/admin/catalogo/personagens`** (feature 235 — personagens por identidade, com os temas de cada um), **`/api/admin/catalogo/categorias`** (feature 300 — só a lista de categorias, para o seletor do formulário de edição; antes ele chamava a listagem inteira, 458 produtos com todo o elenco, para desenhar 39 opções. SUPERADMIN, mesmo gate do `POST` no mesmo caminho) |
| POST | `/api/admin/catalogo`, `/api/admin/catalogo/categorias`, `/api/admin/catalogo/<item_id>/toggle-ativo` |
| PATCH/DELETE | `/api/admin/catalogo/<item_id>` |
| POST | `/api/admin/catalogo/<item_id>/personagens` · **`/api/admin/catalogo/<item_id>/personagens/reaproveitar`** (feature 235 — `{"figurino_sheet_id"}`: põe no elenco deste tema um personagem que já existe; 400 se a ficha já estiver no tema) |
| PATCH/DELETE | `/api/admin/catalogo/personagens/<character_id>` |
| POST | **`/api/admin/catalogo/personagens/mover-em-massa`** (feature 186) |

Ops: `app/admin/catalog_ops.py`, `app/admin/catalog_character_ops.py`
(`unique_character_slug`, `create_character`, `update_character`, `delete_character`,
`move_characters`, validação de `video_url` e de extensão de foto).

### 3.11 Administração — usuários e configuração
`admin_users_read/write.py`: `GET /api/admin/users`, `/api/admin/users/<id>` ·
`POST /api/admin/users` (+ `/<id>/salary`, `/grant-access`, `/reset-password`) ·
`PATCH /api/admin/users/<id>`, `/<id>/pix` · `DELETE /api/admin/users/<id>` ·
**`PATCH`/`DELETE /api/admin/users/<id>/salary/<salary_id>`** (feature 218 — corrigir/excluir faixa
do histórico salarial; **só SUPERADMIN**, enquanto registrar salário é SUPERADMIN ou FINANCEIRO).
As duas devolvem `payments_resynced`: o núcleo (`user_ops._rechain_salary_history` +
`_resync_salary_payments`) reencadeia os `end_date` e realinha os `SalaryPayment` **não pagos** ao
valor corrigido, reatando só a FK dos já pagos e preservando os `SalaryAdvance`.

`DELETE /api/admin/users/<id>` ganhou o bloqueio `cancelamentos` (feature 306): quem é vendedor ou
beneficiário congelado de um cancelamento (`event_cancellations.seller_id`/`commission_seller_id`,
FKs sem `ondelete`) não se exclui. Mesmo status e formato dos outros bloqueios: `400 {error:
{message, blockers}}` (`user_ops.UserDeletionBlockedError`).

`admin_config_read/write.py`: `GET /api/admin/settings`, `/logs`, `/desempenho`, `/sync-status`,
`/migrar-arquivos/status`, `/importar-catalogo/status` · `PATCH /api/admin/settings` ·
`POST /api/admin/sync/run`, `/portal-announcement`, `/migrar-arquivos/start`,
`/importar-catalogo/start`.

`POST /api/admin/sync/run` com `action: "cleanup_past"` (feature 303): cada linha de `results[]`
traz `removed`, `marcados`, `movidos`, `desmarcados`, `inconclusivos` e `falhas` (números), com
`ok` falso quando há falha ou erro de consulta (`err`); a `message` diz as seis somas no texto fixo
do contrato da 303. `sync_now` não muda (não limpa).

### 3.12 Revisão de mídia — `revisao_read.py` / `revisao_write.py`
`GET /api/revisao`, `/api/revisao/reviewer-options`, `/api/revisao/<space_id>`,
`/api/revisao/<space_id>/asset/<asset_id>`, `/api/revisao/asset/<id>/comments` ·
`POST /api/revisao`, `/<space_id>/upload`, `/asset/<id>/replace`, `/asset/<id>/finalize`,
`/asset/<id>/comment`, `/comment/<id>/resolve` · `PATCH /api/revisao/<space_id>/reviewers`,
`/api/revisao/asset/<id>/status` · `DELETE` de espaço, asset e comentário.

### 3.13 Orçamento e EducaManto
Orçamento: `GET /api/orcamento/{opcoes,personagens-no-dia,distancia,settings,historico,historico/<id>}` ·
`POST /api/orcamento/{calcular,salvar,settings,settings/especiais}` ·
`GET /api/orcamento/historico/<id>/pdf` · `POST .../enviar-email` · `DELETE .../historico/<id>` e
`/settings/especiais/<nome>`.
`GET /api/orcamento/historico/<id>` retorna, desde a feature 190, também `form_snapshot` (estado
bruto de entrada do formulário) além do `quote` congelado — usado pela tela de histórico para a
ação "Recalcular" (mudança aditiva, retrocompatível).
**Feature 262 (sem migration)**: payload de `/calcular`, `form_snapshot` e `quote` ganham
`deslocamento_responsavel: "manto"|"cliente"` ao lado de `fora_sp` — chave ausente ≡ `"manto"`
(comportamento antigo). No modo `"cliente"` o veículo sai da conta (só adicionais fora-SP/show),
a mensagem/PDF ganham a frase de responsabilidade, `_build_orcamento_prefill` grava
`transport_value` sem o veículo e o carrinho (`casting_ops.valor_transporte_papel`) vale zero.
**Feature 307 (sem migration) — data especial pela data do evento.** `POST /calcular` resolve
`settings.faixa_especial(event_date)` (recorte `MM-DD` ∈ `datas_especiais.<faixa>.dias`): com
faixa, o markup é o dela (receptivo e show), os especiais com sobrescrita levam o cachê da faixa,
o coordenador usa a lista `coordenador` (com e sem show) e todo outro performer sobe ao `piso`
(`pricing.cache_na_faixa`, fonte única com o teto das vagas) — tudo ANTES de brinde, noturno,
técnico, maquiador, transporte, acréscimos e NF, que seguem iguais. O `quote` ganha
`data_especial: {chave, rotulo, markup[4], nota_mensagem} | null` (a nota vai junto porque o PDF e o
orçamento congelado não releem a tabela) e `markup_used` passa a ser o markup aplicado; a memória
marca "cachê da data especial"/"piso da data especial" e a linha "× Markup" leva o detalhe
`"<rótulo> · DD/MM"`; mensagem e PDF trazem a nota em itálico após a frase de deslocamento. Sem
faixa (data vazia, snapshot antigo, EducaManto — que remove `event_date` em `_totais_contratacao`)
a conta é byte a byte a de antes (fora "Papai Noel"/"Ajudante do Noel", que mudaram na tabela
normal). `GET /orcamento/opcoes` (`_require_vendas`) e `GET /orcamento/settings` devolvem
`settings` inteiro já migrado — `datas_especiais` e os especiais com "Ajudante do Noel" — e a
calculadora lê os dias de lá para a dica com a data vazia: **não enxugar o bloco do `/opcoes`**.
`POST /settings` aceita `datas_especiais` validado no núcleo (`settings.validar_datas_especiais` →
`SettingsValidationError`; 400 `"Datas especiais inválidas."` com `fields`): `datas_especiais` →
"bloco inválido"; `datas_especiais.<faixa>` → "faixa inválida" (chave `^[a-z0-9_]{1,30}$`);
`.rotulo` → "informe o rótulo" / "rótulo com mais de 60 caracteres"; `.dias` → "informe os dias
(DD/MM)" / "dia inválido: <MM-DD>" / "dia repetido: <DD/MM>" / "<DD/MM> já está na faixa <outra>"
(lista vazia = faixa desligada); `.markup` → "4 valores entre 1 e 6 (coeficiente)" (gravado com 2
casas HALF_UP); `.coordenador`/`.piso` → "4 valores em R$" (≥ 0 por `parse_brl`, finito); `.cache`
→ "sobrescritas inválidas"; `.cache.<nome>` → "especial desconhecido: <nome>" / "4 valores em R$
maiores que zero (remova a sobrescrita para usar o piso)" — zero é recusado porque a sobrescrita
passa por fora do piso e viraria cachê zero na venda E no teto da vaga; `.nota_mensagem` → "nota
com mais de 200 caracteres" (quebras de linha viram espaço). O bloco enviado substitui o salvo e
corpo inválido não grava nada. Desligar a faixa é `dias: []`; **remover a chave `natal` não
desliga** — a carga seguinte (`_migrar_307`) recria a faixa padrão com 24 e 25/12. "Ajudante do
Noel" é injetado na tabela normal salvo se estiver em `especiais_excluidos`; sobrescrita de
especial que não existe na tabela (excluído ou renomeado) é descartada na carga, e `DELETE
/settings/especiais/<nome>` tira a sobrescrita do especial das faixas. O teto das vagas
(`_compute_performer_caches(snapshot, horas_extra, data_evento)`) honra a faixa pela data do
**evento** na criação (`_create_event_core`) e no vínculo 273 (`orcamento_evento_ops.data_do_evento`)
e pela data do orçamento no prefill.
**Feature 309 (sem migration) — produtos de tabela.** `POST /calcular` aceita `produtos: [{chave}]`
ao lado de `performers` (lista, repetição permitida, ausente = conta de hoje; chave desconhecida ou
produto apagado → 400 `fields.produtos` 'O produto "X" não está mais na tabela de preços…'). Fonte
única `app/orcamento/produtos.py`: o preço do produto (`preco` ou `por_faixa.<faixa>.preco` pela
faixa da 307; sem preço na faixa → estimativa `Σ cachês das vagas × fator_cache × markup`, marcada)
entra DEPOIS de "= Após markup" e ANTES de brinde, noturno, técnico, maquiador, transporte,
acréscimos e NF — igual nas 4 colunas e fixo na régua >4h (`produtos.total_na_duracao`, também no
prefill e em `_total_da_duracao`/`fator_regua`); o coordenador do produto não é cobrado em dobro
(`split_coordenadores`: `total = max(qty, inclusos)`, só `total − inclusos` na fórmula); UM
Maquiador por orçamento (`incremento_make`); noturno só com `inclui_noturno: false`; personalizado
"valor final" vence tudo e "multiplicador" não multiplica o produto. O `quote` traz SEMPRE
`produtos: [{chave, rotulo, descricao, preco_aplicado, faixa_chave, estimado, vagas[labels]}]`,
`produtos_total`, `coordenadores_inclusos`, `avisos: [str]` (deduplicados) e `valor_unico: bool` (só
produto, sem avulso e sem coordenador da fórmula — a tela e o PDF rotulam "Preço de tabela" por ela;
vazios/false sem produto — a presença das chaves é o sinal de backend novo para o React), linhas
`tipo: "produto"` + "= Após produtos" na
`memoria`, os personagens do produto em `team_lines`, o bloco "🎅 *rótulo* (descrição): *R$ X*" na
`message` (só produto = UM valor: `show_1h` apenas, `total_custom` null, PIX único — e, quando NF,
transporte, BV ou noturno por fora mudam o total, ou há dois exemplares, o bloco "Total da visita" com
VALOR TOTAL e logística); o `snapshot` grava `produtos` com preço E vagas congelados e `produtos_total`
(0 no personalizado "valor final": o produto não está dentro do digitado — régua do evento linear; no
multiplicador a régua não reaplica % nem NF). Acima de 4h, `acrescimos_do_orcamento` refaz as linhas
UMA a uma (fixa × h ÷ 4; % sobre a base da duração com o produto fixo — `produtos.base_na_duracao`). Sem produto a conta é byte a byte a
de antes (gabarito `specs/309-…/verify_309_golden.json`). `GET /orcamento/opcoes` e `GET
/orcamento/settings` devolvem `produtos` e `produtos_estimativa` já migrados (**não enxugar**).
`POST /settings` aceita `produtos` e `produtos_estimativa` (ramo DEPOIS de `datas_especiais`;
`settings.validar_produtos` → 400 `"Produtos de tabela inválidos."` com `fields`): `produtos` →
"bloco inválido"; `produtos.<chave>` → "produto inválido" (`^[a-z0-9_]{1,30}$`); `.rotulo` →
"informe o rótulo" / "rótulo com mais de 60 caracteres"; `.descricao` → "descrição com mais de 120
caracteres" (parênteses externos são tirados — mensagem, PDF e tela já os põem); `.preco` → "preço
em R$ maior que zero e até 100.000"; `.por_faixa.<faixa>.preco` → idem (faixa inexistente é
DESCARTADA com aviso em `avisos` do 200, não 400); `.vagas` → "de 1 a 10 vagas"; `.vagas.<i>.label`
→ "informe o nome da vaga"; `.vagas.<i>.tipo` → "tipo de vaga desconhecido: <tipo>"; `.vagas.<i>.cache`
→ "cachê em R$ maior que zero e até 100.000, ou vazio para usar a tabela"; `.vagas.<i>.needs_makeup`
→ "verdadeiro ou falso" (só em especial/ator; nos demais o campo é ignorado); label de especial fora
da tabela → aviso (a vaga nasce sem teto); `produtos_estimativa.fator_cache` → "fator maior que
zero"; `.markup` → "markup entre 1 e 6 (coeficiente)". Chave `produtos` AUSENTE no corpo = mantém o
salvo; corpo inválido não grava nada. Teto das vagas: `_compute_performer_caches` emite primeiro as
vagas `character` dos produtos a partir das vagas CONGELADAS do snapshot (flat nas 4 colunas, cachê
pela tabela vigente na data do evento — 600 / 270 / 250 / 250; 1.000 / 650 / 500 / 250 na faixa —,
`cap_notes` "cachê da tabela · produto …", `origem: "produto"`; produto apagado ou especial fora da
tabela → `cache_Nh: null` com nota, nunca 0; snapshot sem vagas congeladas de um produto apagado →
fantasma sem vagas, nunca exceção), depois `performers`, depois extras (coordenadores do produto → da
fórmula → Técnico → UM Maquiador — nunca 0: a vaga do produto sem make contada vale a 1ª maquiagem, e um
cachê FIXO digitado na vaga maquiador do produto é honrado); prefill = criação (pareamento posicional) e
o vínculo 273 casa por nome — os itens de coordenador são consumidos em sequência (os primeiros às
vagas existentes, as sobras viram vagas novas), porque desde a 309 o do produto (250 flat) e o da
fórmula (show/régua) diferem. `resumo_do_orcamento` conta os personagens e as makes do produto. O
EducaManto remove `produtos` em `_totais_contratacao`. CLI pós-deploy:
`specs/309-produtos-de-tabela/rebaixar_tetos_noel_309.py` (dry-run; `--execute` rebaixa pela
DIFERENÇA da coluna — 712→600, 800→650, 423→270… — lendo a base na nota do teto da 239 (cobre 762 =
712 + noturno, fora de SP e 2h–4h) só em "Papai Noel"/"Ajudante do Noel" sem cachê e sem artista, em
eventos desde 16/10/2026; nome diferente ou base fora da lista só no relatório).
**Feature 313 (sem migration) — desconto negociado, PIX que vale o maior e a ordem da conta.** Chaves e tipos em
`specs/313-desconto-e-pix-na-calculadora/data-model.md`; o contrato em `contracts/api.md`. `POST /calcular` aceita
`desconto_pct` (0 ≤ d < 100) **ou** `desconto_valor` + `desconto_duracao` (`"1h".."4h"|"extra"`: o valor final de uma
duração; o servidor acha o % exato sobre o cheio dela e ignora `desconto_pct`; igual ao cheio ± R$ 0,005 = sem
desconto). 400 com `fields.desconto_pct` (fora da faixa, não numérico) ou `fields.desconto_valor` (só um dos dois, ≤ 0,
acima do cheio, duração que o resultado não mostra — esta com `duracoes_do_desconto: [...]` no objeto de erro, para a
tela trocar o seletor). **A ordem da conta** (uma função, `quote_ops.aplicar_acrescimos(base, acrescimos, nota)`): base
(apresentação + transporte + produto) → acréscimos em R$ **uma vez** → os % que não são BV sobre a base → o BV em %
sobre tudo isso (o BV em R$ entra uma vez, no passo do BV) → a nota → o desconto, o último passo, sobre o total. Acima
de 4h, `_preco_extra`: a base de 4h ÷ 4 × horas (produto fixo), os acréscimos pela mesma função — sem parte fixa fica
o `round(bruto_4h ÷ 4 × h, 2)` de antes. O snapshot novo leva `versao_conta: 2`, `bases`, `brutos` e o desconto
digitado (`desconto_pct_digitado`/`desconto_valor`/`desconto_duracao`) e o aplicado (`desconto_aplicado`, o que os
leitores leem); `total_1h..4h` do `OrcamentoHistory` passam a ser o **final**. Snapshot sem a marca (todo orçamento de
antes) segue o caminho de antes em toda leitura — histórico, PDF, prefill, evento, 305 (`snapshot_v2` cruza `bases` ×
`brutos` e, inválido, também cai no de antes). O `quote` ganha `bruto_*`, `base_4h`, `desconto_pct`/`_texto`/`_modo`,
`pix_pct = max(5, d)` e `pix_*` (sobre o **cheio**: vale o maior), `bv_*`/`bv_pix_*` (o BV a repassar com o desconto e
no PIX, por `bv_que_acompanha`; `null` sem BV); o texto do % é `texto_do_percentual` (uma casa, **para baixo**, vírgula,
sem ",0"). Mensagem e PDF: "de R$ X por R$ Y" + "_(desconto de N% aplicado)_" por duração; com d ≥ 5% o PIX diz "o
mesmo valor — o desconto de N% já está aplicado", abaixo disso o bloco de 5% de sempre; sem desconto, byte a byte a de
antes. A memória ganha "Desconto (N%)" e "BV a repassar a quem indicou" só com desconto. `GET /historico` traz
`desconto_pct` por item. **Prefill** (`_build_orcamento_prefill`, só orçamento v2): `bruto_1h..4h`, `bruto_custom`,
`desconto_pct`, `extra_por_horas: {"5".."24": {bruto, total}}` (no personalizado, a régua sobre o cheio de 4h) e, em cada
`acrescimos_do_orcamento.linhas[]`, `valores_final` (o que a linha vale com o desconto; `valores_brl` segue o cheio).
**Evento**: a tela manda `sale_value_gross` = cheio e `sale_value` = final; o BV gravado (305) e `deduzir_duracao`
usam o **cheio** da duração como denominador (cheio primeiro, depois o final); o vínculo 273
(`aplicar_valores_do_orcamento`) grava o mesmo par. O EducaManto tira `desconto_*` do payload em `_totais_contratacao`.
**Feature 273 (sem migration)**: cada item de `GET /api/orcamento/historico` traz `event_id` /
`event_title` do evento **não cancelado** que aponta para ele (uma consulta para a página inteira);
`DELETE .../historico/<id>` responde **409 + `event_id`** enquanto houver evento vivo vinculado — a
FK `calendar_event.orcamento_history_id` não tem `ondelete`, e apagar estourava `IntegrityError`;
eventos **cancelados** que ainda apontem para o orçamento são soltos (FK nula + `EventLog`) antes
de apagar.
O vínculo posterior é `PATCH /api/events/<id>/orcamento` (§3.3), que aplica ao evento o que o
orçamento vendeu (`app/calendar/orcamento_evento_ops.py`).

**Feature 301 (sem migration) — escopo do histórico, escrito aqui para não se perder de novo.**
O histórico de orçamentos é **do time inteiro**: quem passa em `_require_vendas()` de
`orcamento_read.py` (COMERCIAL ou SUPERADMIN) lista, abre, recalcula, baixa o PDF e reenvia o
e-mail de **qualquer** orçamento, seja de quem for. Não há checagem de dono na listagem nem no
detalhe (`_get_entry` confere só existência), e `GET /api/orcamento/historico` devolve
`user_name` e `pode_excluir` por linha, mais `users` sempre populada para o filtro por vendedor;
a chave `is_superadmin` **saiu** do payload. Sobra **uma** trava de autoria: o
`DELETE .../historico/<id>`, por `_get_entry_para_excluir` — e nele a autoria é resolvida
**antes** da guarda 409 de evento vivo, de propósito (quem não é autor leva 404 e não confirma a
existência do registro, Princípio XIII). Reenviar o orçamento **de outra pessoa** grava uma linha
em `audit_logs` (`entity_type="orcamento"`), com commit próprio e em `try/except`: o e-mail já
saiu, então falha de auditoria não vira falha de envio.

Isso restaura o que o commit `6b191e4` (20/05/2026) havia decidido e a migração 177 desfez sem
querer, ao copiar de um contrato desatualizado — a restrição viveu dois meses e contaminou a aba
Comercial do evento (239) e o vínculo orçamento↔evento (273). **Quem reescrever o módulo não deve
reintroduzir o filtro por `user_id`.**

EducaManto (feature 235 — contrato novo por responsabilidades): `GET /api/educamanto/{historico,musicals,textos,distancia,personagens-no-dia}` ·
`POST /api/educamanto/calcular` (uma configuração; **breakdown só na resposta de SUPERADMIN** — corte no servidor), `/musicals`, `/musicals/<id>/duplicate`, `/orcamento/gerar` (**recalcula tudo no servidor**, snapshot v2, PDF por configuração) ·
`PATCH|DELETE /api/educamanto/musicals/<id>` · `GET /api/educamanto/musicals/<id>` (só superadmin) · `GET /api/educamanto/orcamento/<id>/pdf`.
`GET /api/educamanto/musicals?gestao=1` (Comercial+Superadmin) devolve custos/margens **apenas** para superadmin. Os endpoints `/packages*` morreram com os pacotes. As rotas Jinja `/educamanto/*` viraram redirects 301 para o SPA.
**Novo na feature 190**: `GET /api/educamanto/historico/<id>` — snapshot bruto (`d1`, `d2`,
`ensemble`, `acrescimo`, `transporte`, `client_name`, `packages`) de um orçamento salvo em JSON
(mesmo dado já usado para regerar o PDF, agora também exposto para "Ver" e "Recalcular"); mesmo
RBAC de uso do EducaManto (`_require_use`), sem restrição por dono.

### 3.13.1 Google Maps — `maps_read.py` (feature 195)
`GET /api/maps/address-autocomplete?q=<termo>&session_token=<opcional>` — proxy do **Google Places
Autocomplete**, restrito ao Brasil (`components={"country": ["br"]}`) e em pt-BR. Devolve
`{"items": [{"description": "Rua Tuiuti - Tatuapé, São Paulo - SP, Brasil", "place_id": "…"}]}`,
no máximo 5 itens, descartando predições sem `description`.

- **RBAC**: qualquer usuário autenticado do staff (`api_login_required`). Não expõe nenhum dado do
  sistema — só o retorno público do Google. As telas que o consomem já têm RBAC próprio.
- **Segurança da chave (Princípio X.4)**: a `SiteSetting.google_maps_api_key` (com fallback para a
  env `GOOGLE_MAPS_API_KEY`) **nunca** vai para o navegador — o React só fala com este endpoint.
- **Economia de quota (Princípio X.5)**: termo com menos de 3 caracteres devolve `{"items": []}`
  com 200, **sem** chamar o Google; o cliente ainda aplica debounce de 350ms.
- **Erros**: `503` se a chave não está configurada ("Configure a API Key em Admin →
  Configurações"), `502` se o Google falha (o erro real vai para o log via `logger.warning`, o
  usuário vê "Não foi possível buscar endereços no Google Maps agora").
- A regra vive em `app/maps.py` → `address_autocomplete()`, mesmo módulo de `distance_km_ida()`
  (feature 076) — fonte única da integração com o Maps.

> **`GET /api/events/new/options` mudou (aditivo)**: cada item de `assignable_talents` passou a
> incluir `photo_face_path`, que alimenta o avatar circular do combobox de pré-escala e de
> coordenador. `figurino_sheets` já trazia `photo_url`. O Jinja legado ignora a chave extra.

### 3.13.2 Impressões 3D — `impressoes3d_read.py` / `impressoes3d_write.py` (feature 200)

| Método | Rota | O que faz |
|---|---|---|
| `GET` | `/api/3d/acervo` | Catálogo de peças com `usage_count` (nº de eventos que já usaram a peça). `?ativos=1` esconde as inativas. |
| `POST` | `/api/3d/acervo` | Cadastra peça (**multipart**): `name`, `photo` (JPG/PNG) e um ou mais `files` (`.stl`/`.3mf`/`.zip`) — **todos obrigatórios**; falta de qualquer um devolve 400 com o campo em `fields` (`name`/`photo`/`files`). |
| `PATCH` | `/api/3d/acervo/<id>` | Edita nome/`is_active`, troca a foto (upload novo apaga a antiga) e **acrescenta** arquivos via `files` / **remove** via `remove_file_ids[]` (**multipart**). 400 se a operação deixaria a peça sem nenhum arquivo. |
| `DELETE` | `/api/3d/acervo/<id>` | Exclui a peça e seus arquivos. **400** se houver evento vinculado. Com **`?force=true`** (só `SUPERADMIN`, senão **403**) apaga mesmo assim, removendo antes os `Event3DGift` da peça — o presente some dos eventos e da Fila de Impressão. A cascata é explícita no ops: `Event3DGift.item_id` não tem `ondelete`. Auditoria registra de quantos eventos desvinculou (feature 213). |
| `GET` | `/api/3d/fila` | Fila de Impressão, **dois blocos**: `items` (presentes com `status != 'entregue'` de eventos SHOW, ordenados por prazo — sem prazo vai para o fim) e `sem_presente` (SHOWs futuros ainda sem presente vinculado). `?dispensados=1` inclui os marcados como "não leva presente". |
| `POST` | `/api/events/<id>/3d-dismissal` | Marca o SHOW como "não leva presente 3D" (idempotente). 400 em evento não-SHOW. |
| `DELETE` | `/api/events/<id>/3d-dismissal` | Desfaz a dispensa, devolvendo o show às pendências (idempotente). |
| `POST` | `/api/events/<id>/3d-gifts` | Vincula peça ao evento (JSON: `item_id`, `quantity`, `deadline_date`, `notes`, `status`). **400** em evento não-SHOW. |
| `PATCH` | `/api/events/<id>/3d-gifts/<gift_id>` | Edita status/quantidade/prazo/observações/peça. É o endpoint do seletor rápido de status da Fila. |
| `DELETE` | `/api/events/<id>/3d-gifts/<gift_id>` | Remove o vínculo (a peça do Acervo continua existindo). |

- **RBAC**: todos os endpoints acima exigem `ARTISTA_3D` **ou** `SUPERADMIN`
  (`require_3d_access()` em `impressoes3d_read.py`, chamada no início de cada view — função, não
  decorator, conforme §4.3). Sem sessão → 401; papel errado → 403.
- **Inteligência de negócio da Fila**: cada item traz aninhados o `event`, a lista de `roles`
  (personagens contratados, com o talento escalado) e `form_response` — o extrato do formulário
  de pré-contrato **já normalizado** (as duas formas históricas de `FormResponse.data`,
  `[chave, rótulo, valor]` e `[rótulo, valor]`, viram um formato único) e **filtrado só aos
  campos preenchidos**. É assim que o Artista 3D lê idade e quantidade de aniversariantes sem
  abrir evento por evento.
- **`GET /api/events/<id>` mudou (aditivo)**: eventos SHOW passaram a serializar `presentes_3d`
  (lista de presentes) e **todo** evento ganhou a flag `can_manage_3d` em `flags`. Quem não é
  Artista 3D lê a lista, mas a UI de edição não aparece. A chave `presentes_3d` **não existe** em
  evento não-SHOW — a ausência é o sinal para o React não renderizar a seção.
- **Uploads**: `app.storage.save_file` nas subpastas `acervo_3d_photos` (a foto passa pela
  compressão automática do Pillow) e `acervo_3d_files` (arquivos brutos, sem compressão). Como o
  caminho salvo é um UUID, `Acervo3DFile.original_name` guarda o nome enviado — é o que diz qual
  parte do modelo é qual (`corpo.stl`, `argola.3mf`).
- **Feature 255**: `POST`/`PATCH` do Acervo aceitam o campo opcional `nfc_prefix` (normalizado:
  trim, MAIÚSCULAS, sem `-`; string vazia = desabilitar; ausente no PATCH = não alterar) e
  `serialize_acervo_item` devolve `nfc_prefix`. Criar/editar presente 3D dispara a geração
  automática de tags (ver §2.2.1) — sem mudança de contrato nos endpoints de presente.

### 3.13.2b Tags NFC — `nfc_read.py` / `nfc_write.py` (feature 255; entregas na 261; espelho admin da mídia na 265)

| Método | Rota | O que faz |
|---|---|---|
| `GET` | `/api/nfc/<code>` | **PÚBLICO, sem login** (padrão `catalogo_read.py`). Resolve o código gravado na tag física. **Sempre 200, mesmo shape**: tag ativa → `{product: {name, photo_url}, campaign: null, deliveries: [...], instagram_url}` + incrementa `access_count`/`last_accessed_at` (melhor-esforço, falha não derruba a resposta); inexistente **ou** desativada → `{product: null, campaign: null, deliveries: [], instagram_url}` — indistinguíveis de propósito. Lookup case-insensitive. `instagram_url` vem de `MANTO_INSTAGRAM_URL` (`app/constants.py`). `deliveries` (feature 261) é `[{kind, title, media_url, width, height}]` das entregas ativas **e com conversão PRONTA** (feature 297 — entrega em fila ou que falhou não existe para o mundo lá fora); `media_url` já no formato `/api/nfc/<code>/entregas/<id>/media`, pronto para `assetUrl()`; `width`/`height` deixam a página reservar a altura do palco antes de o vídeo carregar. A feature 297 acrescentou ao payload `spotify_url` (`MANTO_SPOTIFY_URL`), `intro_video_url` (o vídeo de abertura, `null` quando não cadastrado) e `aceita_recado` — os três viajam **também no payload vazio**, porque o menu genérico precisa dos botões externos e qualquer diferença viraria oráculo de existência. TODO o conteúdo da página é do servidor. |
| `GET` | `/api/nfc/<code>/entregas/<id>/media` | **PÚBLICO, sem login** (feature 261). Serve o arquivo da entrega — espelha `GET /api/virtuais/pedidos/<token>/video` (feature 205): `send_file(conditional=True)` (suporte a `Range`/`206`). Código inexistente, tag desativada, entrega de outra tag, entrega inativa **e entrega ainda em conversão** (feature 297) devolvem o **mesmo 404 genérico** — nenhum vaza mais que o outro. |
| `GET` | `/api/3d/nfc` | Lista de gestão (ordem: item + `sequence`), cada linha com `item` aninhado, `event` resumido, `client` (vínculo direto), `client_name`/`client_direct` resolvidos (**cliente direta → contratante do evento**, `client_of_event` de `agenda_read.py`) e `video_delivery` (feature 261: `{id, kind, title, file_name, created_at}` ou `null`). |
| `POST` | `/api/3d/nfc/lote` | Gera lote avulso (JSON `{item_id, quantity}` 1–999), tags sem evento (estoque). 400 com `fields` se o item não tem `nfc_prefix`. |
| `PATCH` | `/api/3d/nfc/<id>` | Edita **só** os mutáveis: `event_id` e `client_id` (`null` desassocia; sentinela = não alterar; independentes entre si), `is_active`, `notes`. `code` e `sequence` são imutáveis por contrato. |
| `POST` | `/api/3d/nfc/<tag_id>/entregas` | **Feature 261.** Multipart `file` + `kind` (só `"video"` por ora) + `title` opcional. Substitui a entrega ativa do mesmo `kind`, se houver (apaga arquivo + linha antigos). 400 com `fields` se faltar arquivo, extensão fora da allowlist ou acima de 250 MB. Devolve `{tag: ...}` (mesmo shape de `GET /api/3d/nfc`). |
| `DELETE` | `/api/3d/nfc/<tag_id>/entregas/<id>` | **Feature 261.** Remove a entrega (linha + arquivo do disco). Sem confirmação no servidor — a UI confirma antes de chamar. |
| `GET` | `/api/3d/nfc/<tag_id>/entregas/<id>/media` | **Feature 265 — espelho ADMIN da mídia.** Mesmo `send_file(conditional=True, max_age=86400)` do público, mas: gate `ARTISTA_3D`/`SUPERADMIN`, busca por `tag_id` (não por código), serve **inclusive tag desativada** (auditável por dentro) e **NUNCA incrementa `access_count`** — o incremento mora só em `resolve_code`, que este endpoint não chama. É o `src` de todos os players do ERP (`adminNfcVideoUrl` em `apps/internal/src/lib/nfc.ts`); revisar pela URL pública inflava a métrica das clientes. 404 genérico para entrega inexistente/de outra tag. Sem `audit()` (leitura) e sem limiter próprio (autenticado). |

| `POST` | `/api/3d/nfc/<tag_id>/entregas/<id>/reprocessar` | **Feature 297.** Devolve o vídeo à fila de conversão. JSON `{com_moldura?}` — omitido mantém a escolha atual da entrega. Parte do MESTRE sem moldura; nas entregas anteriores à 297 (que não têm mestre) parte do próprio arquivo entregue. `409` com `fields` se já estiver `pendente`/`processando`. |
| `PUT`/`DELETE` | `/api/3d/nfc/moldura` | **Feature 297.** Cadastra (multipart `file`) ou remove a moldura PNG **única do sistema**, gravada na borda de todo vídeo enviado com a caixinha marcada. `400` com `fields` para extensão fora de `.png` e para **PNG sem transparência real** (`imaging.tem_transparencia_real`) — moldura opaca cobriria o vídeo inteiro. Nome fixo `moldura.png` em `nfc_media/sistema/` (molde de `logo_path`). |
| `GET` | `/api/3d/nfc/moldura` | **Feature 297.** Serve a moldura para a prévia no ERP; `max_age` de 5 min porque o arquivo é sobrescrito no lugar. |
| `PUT`/`DELETE` | `/api/3d/nfc/abertura` | **Feature 297.** Cadastra ou remove o vídeo de abertura da página pública. Passa pela MESMA conversão dos vídeos de tag (sem moldura): é servido a todo mundo que encosta o celular numa luminária. Nome fixo `abertura.mp4`. |
| `GET` | `/api/3d/nfc/<tag_id>/recados` | **Feature 297.** Recados que as clientes escreveram nessa tag: `{items: [{id, message, author_name, created_at, read_at}], unread_count}`. Conteúdo privado de quem recebeu a peça. |
| `POST` | `/api/3d/nfc/<tag_id>/recados/lidos` | **Feature 297.** Marca todos como lidos; devolve `{marcados}`. |
| `POST` | `/api/nfc/<code>/recados` | **Feature 297 — PÚBLICO, sem login**, `@limiter.limit("10 per hour")`. JSON `{message, author_name?}`. `400` com `fields` para texto vazio ou acima de 1000 caracteres. **Responde `201` mesmo para código inexistente ou tag desativada, sem gravar nada** — a leitura já é indistinguível por contrato (SC-006 da 255) e uma escrita que respondesse diferente viraria oráculo de quais códigos existem. Notifica o sino em transação própria, melhor-esforço. |
| `GET` | `/api/nfc/abertura/video` | **Feature 297 — PÚBLICO, sem login.** Serve o vídeo de abertura (`send_file(conditional=True, max_age=3600)`); `404` no envelope quando nenhum foi cadastrado. Três segmentos, então não conflita com `GET /api/nfc/<code>`. O `?v=` é ignorado — existe só para furar cache do navegador. |

- **RBAC**: os `/api/3d/nfc*` (tag, entregas, mídia admin, moldura, abertura e recados) exigem
  `ARTISTA_3D` ou `SUPERADMIN` (`require_3d_access`, reuso da feature 200). **Não existe DELETE de
  tag** — tag física entregue é eterna; entregas (vídeo/foto/link) SÃO removíveis — são conteúdo
  anexado, não a tag. As duas únicas rotas públicas de ESCRITA do domínio são o recado (acima) e
  nada mais.
- **Onde o vídeo mora**: `Config.NFC_MEDIA_FOLDER` (padrão `instance/nfc_media`), irmã de
  `uploads`, nunca dentro — mesmo racional de `VIRTUAL_VIDEO_FOLDER` (§3.13, feature 205). Ver
  §2.2.1 para o schema completo de `nfc_tag_deliveries`. **Desde a feature 297 há três subpastas**
  (todas dentro de `nfc_media`, para entrarem sozinhas no backup de mídia): `entrada/` guarda o
  arquivo cru entre o envio e o fim da conversão; `mestres/` guarda a versão 1080p **sem** moldura,
  que é a origem de todo reprocessamento; `sistema/` guarda os dois arquivos únicos da plataforma,
  `moldura.png` e `abertura.mp4`. O arquivo ENTREGUE continua na raiz, com os nomes de sempre.
- **Conversão de vídeo (feature 297)**: todo vídeo enviado é convertido para 1080 de largura,
  H.264 + AAC com índice no início, ~15 MB por 30 s. Roda numa thread de fundo (`nfc-video`,
  `app/__init__.py`), **um vídeo por vez**, com `nice -n 19` e uma linha de execução só — o
  contêiner tem UMA CPU, dividida com os três workers do gunicorn. O claim entre workers é um
  `UPDATE ... WHERE processing_status = 'pendente'` na própria linha da entrega. O `ffmpeg` vem da
  imagem base do runtime Python do Render e **não está declarado no `render.yaml`** (dívida em
  `docs/05`): sem ele, o vídeo é entregue como veio e o motivo fica em `processing_error`.
- **Serving da página**: `frontend/server.js` serve `/nfc/*` com o bundle da vitrine **sem
  reescrever a URL** (`NFC_PREFIX`, mesmo mecanismo de `CADASTRO_PREFIX`); o React Router roda
  sem o basename `/catalogo` (`isRootSurface` em `apps/public/src/App.tsx`).

### 3.13.3 Marketing e Frequência — `marketing_read.py` / `marketing_write.py` (feature 204, multi-Tema na 204b)

| Método | Rota | O que faz |
|---|---|---|
| `GET` | `/api/marketing/posts` | Planejamento completo. `?status=` (validado — status inválido devolve 400) e `?responsavel=<user_id>` filtram. Ordena por prazo mais apertado (sem prazo vai para o fim). Devolve também `statuses` e `plataformas` — a interface monta as colunas do Kanban e o seletor a partir do servidor. |
| `GET` | `/api/marketing/posts/<id>` | Detalhe de uma postagem (mesmo payload da lista). |
| `POST` | `/api/marketing/posts` | Cria postagem (JSON). Campos: `title` (obrigatório), `status`, `deadline_date`, `publish_date`, `platform`, `drive_folder_url`, `notes`, `assignee_id`, `catalog_item_ids` (**lista** de ids do catálogo, feature 204b — ausente/`[]` = sem Tema). |
| `PATCH` | `/api/marketing/posts/<id>` | Edição **parcial** (campo ausente = não alterar; `null` = limpar). É o endpoint da troca de coluna do Kanban. |
| `DELETE` | `/api/marketing/posts/<id>` | Exclui a postagem — o `ReviewSpace` vinculado **sobrevive**. |
| `POST` | `/api/marketing/posts/<id>/create-review` | **Ponte com a Revisão de Mídia**: cria um `ReviewSpace` com o título do post (via `review_ops.create_space`), vincula 1:1 e devolve `{review_space_id, post}` para o frontend redirecionar a `/revisao/<id>`. **400** se já houver espaço vinculado. |
| `GET` | `/api/marketing/goals` | Metas com a saúde calculada: `last_posted_date`, `last_post_id`, `next_due_date`, `days_since_last_post`, `days_late`, `never_posted` e `status` (`on_track`\|`delayed`), mais `delayed_count` no topo. |
| `POST` | `/api/marketing/goals` | Cria meta (`name`, `target_interval_days` 1–1825, `catalog_item_id` opcional). |
| `PATCH` | `/api/marketing/goals/<id>` | Edita a meta; a resposta já vem com a saúde recalculada. |
| `DELETE` | `/api/marketing/goals/<id>` | Exclui a meta (as postagens seguem intactas). |
| `GET` | `/api/marketing/opcoes` | Opções dos `Combobox`: `temas` (Temas **ativos** do catálogo com `cover_url`), `usuarios` (ativos e com acesso, com `photo_url`) e `plataformas`. Existe porque `/api/admin/catalogo` é exclusivo de `SUPERADMIN` — `MARKETING` precisa dos Temas sem ganhar acesso à gestão do catálogo. |

- **RBAC**: todos exigem `MARKETING` **ou** `SUPERADMIN` (`require_marketing_access()` em
  `marketing_read.py`, chamada no início de cada view — função, não decorator, conforme §4.3).
  Sem sessão → 401; papel errado → 403.
- **Validação com campo culpado**: `MarketingValidationError(field, message)` vira
  `json_error(msg, 400, fields={campo: msg})` — o React destaca o campo exato (Princípio V).
  Casos cobertos: título vazio, status fora do fluxo, plataforma fora da lista fixa,
  `drive_folder_url` que não começa com `http(s)` (um `javascript:` iria para um `target="_blank"`),
  data fora de `AAAA-MM-DD`, Tema/responsável inexistentes, intervalo de meta fora de 1–1825.
- **`publish_date` automática**: `PATCH {"status": "publicado"}` sem data preenche hoje — é o que
  faz o post contar para as metas de frequência (ver §2.9.1).

### 3.13.4 Loja de Interações Virtuais — `virtuais_*.py` (feature 205, parcial: US1)

Canal B2C que vende chamadas de vídeo de 10 min e vídeos gravados com Personagens do catálogo.
Núcleo em `app/marketing/virtuais_ops.py`; cliente da operadora em
`app/integracoes/infinitepay_client.py`.

| Método | Rota | O que faz |
|---|---|---|
| `GET` | `/api/virtuais/campanhas` | Lista campanhas com vendidos, faturado, horários restantes e capacidade de vídeo consumida. |
| `POST` | `/api/virtuais/campanhas` | Cria campanha (JSON ou multipart com `cover`). Nasce em `rascunho`. |
| `GET` | `/api/virtuais/campanhas/<id>/admin` | Detalhe completo + `slots` + `available_gift_items` (o Acervo 3D ativo inteiro, para o seletor). |
| `PATCH` | `/api/virtuais/campanhas/<id>` | Edição parcial (campo ausente = não alterar). |
| `POST` | `/api/virtuais/campanhas/<id>/publicar` | `{"status": "publicada"\|"pausada"\|"rascunho"}`. Publicar exige preços, capa, prazo e termos — falta de qualquer um vira **400** com o campo culpado. |
| `PUT` | `/api/virtuais/campanhas/<id>/acervo` | `{"item_ids": [...]}` — substitui a seleção inteira. Peça inativa é recusada. |
| `POST` | `/api/virtuais/campanhas/<id>/horarios` | `{date, start, end}` → `{created, skipped}`. **Idempotente**: reexecutar a mesma janela devolve tudo em `skipped`. Teto de 500 slots por chamada. |
| `DELETE` | `/api/virtuais/horarios/<id>` | Remove horário **livre**; reservado/vendido devolve **409**. |
| `GET` | `/api/virtuais/campanhas/<slug>` | **Público.** Landing. Rascunho → 404; pausada → **410**. |
| `GET` | `/api/virtuais/campanhas/<slug>/horarios` | **Público.** Só horários disponíveis e futuros; nunca revela quem reservou. |
| `POST` | `/api/webhooks/infinitepay/<token>` | **Público, com segredo no path** (`SiteSetting.infinitepay_webhook_token`). Só valida o segredo e delega. Segredo errado → **404** (403 confirmaria a existência do endereço). Processamento entra na US3. |

- **RBAC**: os endpoints administrativos exigem `COMERCIAL` **ou** `SUPERADMIN`
  (`require_virtuais_access()` em `virtuais_read.py`, chamada no início de cada view conforme §4.3).
- **Dinheiro**: todas as colunas são `Numeric(12,2)` e o JSON trafega **reais decimais**
  (`"150.00"`), nunca centavos. A InfinitePay exige centavos inteiros, e a conversão vive
  exclusivamente em `infinitepay_client.py` — que recusa `float` com `TypeError` de propósito
  (Princípio IX).
- **Indisponível ≠ não pago**: `consultar_pagamento()` levanta `InfinitePayIndisponivel` em
  timeout/5xx/resposta ilegível (timeout 10s conexão, 30s leitura). Confundir os dois faria uma
  queda da operadora liberar produto ou cancelar venda paga.
**Reserva e soft lock (US2)** — acrescentados na 205b:

| Método | Rota | O que faz |
|---|---|---|
| `POST` | `/api/virtuais/campanhas/<slug>/reservar` | **Público.** Cria o pedido, trava o horário por 15 min e devolve o link de pagamento. `400` validação (com campo culpado) · `409` horário/vaga tomada (vem com a lista atualizada) · `429` limite anti-abuso · `502` operadora fora (a reserva já foi desfeita). |
| `GET` | `/api/virtuais/pedidos/<public_token>` | **Público.** Resumo do pedido: situação, horário, valor e dica do telefone. Nenhum dado de criança. |
| `GET` | `/api/virtuais/enderecos/autocomplete` | **Público, com teto por origem.** Variante sem login de `/api/maps/address-autocomplete`; reusa `app.maps.address_autocomplete`. |

- **Concorrência**: toda mudança de posse do slot passa por `with_for_update()`. Dois visitantes
  simultâneos entram em fila no banco; o segundo recebe 409. Coberto por `verify_205.py` V2.7/V2.8
  com **duas conexões reais**.
- **Anti-abuso**: uma reserva ativa por telefone (devolve o pedido existente para a família
  retomar) e teto por origem na janela da campanha. `origin_hash` é SHA-256 com sal de IP +
  User-Agent — **nunca o IP cru**.
- **Um relógio só**: `constants.now_sp()` (naive São Paulo) governa horário de slot, soft lock,
  janela do anti-abuso e os `created_at` das tabelas `virtual_*`. Misturar com `datetime.utcnow()`
  custa 3 horas de erro — foi bug real, pego na tela.
- **Varredura**: `_start_virtual_sweep` em `create_app()`, thread daemon no padrão de
  `_start_calendar_sync`, com claim atômico (`virtual_sweep_at`) para não rodar em dois workers.
  Antes de liberar um horário vencido, reconsulta a cobrança; se paga, não libera.
**Efetivação da venda (US3)** — acrescentada na 205c:

| Método | Rota | O que faz |
|---|---|---|
| `POST` | `/api/webhooks/infinitepay/<token>` | **Público, com segredo no path.** Só valida o segredo e delega a `processar_notificacao_pagamento()`. Segredo errado → `404` (e a tentativa fica registrada). Todos os demais casos → `200`. |
| `GET` | `/api/virtuais/devolucoes?status=` | Devoluções a executar no painel da operadora. |
| `PATCH` | `/api/virtuais/devolucoes/<id>` | `{"status": "concluida"}` depois de devolver o dinheiro. |
| `POST` | `/api/virtuais/pedidos/<id>/sala` | Tenta obter a sala que ficou pendente no Google. |

- **O aviso não decide nada.** `processar_notificacao_pagamento()` registra a notificação (a
  unicidade de `transaction_nsu` barra a reentrega), trava o slot, **reconsulta a cobrança** e só
  então decide. Desfechos possíveis: `efetivado`, `duplicado`, `recusado`, `conflito`, `retido`,
  `orfao` — todos gravados em `virtual_payment_notifications`.
- **A efetivação é atômica**: evento (`event_type='VIRTUAL'`, `source='platform'`, `sale_value`),
  ficha, `EventRole` pré-escalado, `VirtualMediaDelivery`, presente 3D na fila existente e baixa de
  estoque nascem juntos. Falha → rollback e notificação como `retido`.
- **Sala do Meet** vem da Calendar API (`conferenceData` + `conferenceDataVersion=1`) e fica em
  `VirtualOrder.meet_url`. **Não confundir** com `CalendarEvent.google_html_link`, que abre o
  Calendar e exige login. Criação pendente → `meet_pending=True`, venda válida, pendência
  sinalizada.
- **Sincronização blindada**: `sync_events` e `_cleanup_stale_events` ignoram eventos `VIRTUAL`.
  Edição ou remoção feita direto no Google vira log `virtual_divergente`, nunca propagação — um
  pedido pago não pode ser desfeito por alguém mexendo no calendário.
**Fila de produção, vídeo e validação dupla (US4/US5)** — acrescentados na 205d:

| Método | Rota | O que faz |
|---|---|---|
| `POST` | `/api/virtuais/pedidos/<token>/verificar` | **Público.** Confere o telefone da compra e abre a sessão de acesso. `401` com `attempts_left`; `429` com `blocked_until` após 5 erros. |
| `GET` | `/api/virtuais/pedidos/<token>/completo` | **Público, sob sessão.** Ficha da criança, presente, endereço e o endereço do vídeo. |
| `GET` | `/api/virtuais/pedidos/<token>/video` | **Público, sob sessão.** Serve o arquivo com `Range` (`206`). |
| `GET` | `/api/virtuais/producao` | Fila de Produção, com filtros de campanha, data e status. |
| `PATCH` | `/api/virtuais/producao/<id>` | `pendente` \| `gravando` \| `finalizado` — nenhum outro. |
| `POST` | `/api/virtuais/producao/<id>/video` | Recebe o vídeo, finaliza a entrega e avisa a família. |

- **RBAC da fila**: `require_producao_access()` — `COMERCIAL`, `CASTING` ou `SUPERADMIN`.
- **Onde o vídeo mora**: `Config.VIRTUAL_VIDEO_FOLDER` (padrão `instance/virtual_videos`), **irmão
  de `uploads`, nunca dentro**. A rota `/uploads/<path>` serve qualquer coisa que caia lá e, com
  `USE_S3=true`, `save_file` devolveria URL de bucket público. `video_path` é caminho interno e
  **nunca** sai em payload (FR-038e).
- **Validação dupla**: o resumo do pedido mostra só situação, horário e valor; nome, idade, dicas,
  endereço e vídeo exigem o telefone da compra. A sessão vive no cookie e expira por 30 min de
  inatividade. A **sala** é exceção deliberada — aparece com o pedido pago, porque uma etapa a mais
  antes de uma chamada de 10 minutos custaria a experiência.
- **Vídeo gravado não tem sala**: `conferenceData` só é pedido na modalidade `ao_vivo`, e
  `meet_pending` idem — senão a fila alertaria sobre uma sala que nunca existirá.
- **Segregação financeira (FR-052–055): implementada** na feature 205e. `app/api/financeiro_read.py`
  trata `incluir_loja_virtual` e `resumo_loja_virtual` tanto no pipeline de vendas quanto na DRE
  (`:155`, `:172`, `:276`, `:282`, `:332`, `:521`). Ver §3.6.

### 3.13.5 Notificações internas — `notificacoes_read.py` / `notificacoes_write.py` (feature 272)

RBAC: só `@api_login_required`; **nenhum gate por papel** — o RBAC aconteceu na emissão (quem foi
endereçado) e a leitura filtra sempre por `Notification.user_id == current_user.id`. "Ver como" não
troca a caixa. REVENDEDOR_EDUCAMANTO nem chega aqui (guarda de perfil restrito da 078 → 403).

- `GET /api/notificacoes/nao-lidas` → `{unread_count}` — **o endpoint do polling** (60 s por aba
  visível; `refetchOnWindowFocus`): um COUNT no índice parcial, zero join.
- `GET /api/notificacoes?antes_de=<id>&limite=30&somente_nao_lidas=1` → `{items, next_before,
  unread_count}` — keyset por `id`, nunca offset; `limite` 1..100.
- `POST /api/notificacoes/<id>/lida` → `{id, read_at, unread_count}` — idempotente; id alheio → 404.
- `POST /api/notificacoes/lidas` `{ate_id}` → `{marcadas, unread_count}` — `ate_id` obrigatório
  (400 sem ele): "marcar todas" nunca engole o aviso que chegou depois de a lista ser desenhada.

Produtores da v1 (`notificacoes_ops.notificar_*`, textos junto do catálogo de `kind`): resposta de
formulário público (`formularios_write._notificar_comercial`, regime best-effort depois do fato —
**substituiu o e-mail da 266**; `send_form_response_email` foi removida), avaliação da cliente
(`feedback_write`, mesma transação do fato; nota ≤ 2 = `urgent`) e recusa de convite pelo talento
(`portal_ops.reject_invite`, mesma transação; `urgent` se o evento é em ≤ 7 dias; chave por dia).
Efeitos colaterais: `GET /api/formularios/respostas/<id>` marca lidas as notificações daquela
resposta **para quem abriu** (um GET que escreve, de propósito); `delete_response` apaga as da
resposta. Retenção (lida > 30 d, não lida > 180 d) no laço do review-cleanup e em `flask
notificacoes-limpar [--execute]`.

Produtor da feature 303: `notificar_evento_sumiu_google` (kind `evento.sumiu_google`, entidade
`calendar_event`, `urgent`, COMERCIAL e SUPERADMIN), chamado por `sumico_ops.marcar` na mesma
transação da marca; `dedupe_key` com o carimbo da marca (um aviso por sumiço, aviso novo se sumir
de novo). Toda saída da marca dá o aviso como lido para todos; a exclusão do evento apaga os avisos
dele (`_delete_event`).

Produtores da feature 306, chamados pelo ato do cancelamento (`cancel_ops._avisar_no_sino`) na
transação do ato, com a `dedupe_key` pronta (`cancel_ops._chave_do_sino`, sempre pelo evento da URL:
dois atos no mesmo grupo dão dois avisos) — o `notificacoes_ops` não importa o cancelamento. Nenhum
dos dois avisa o Superadmin, que é quem cancela:
- `notificar_evento_cancelado` (kind `evento.cancelado`, ENSAIO, `info`, entidade
  `calendar_event`): só quando algum dia cancelado tinha ensaio; um por pessoa por ato, com os
  ensaios que caíram no corpo e link para o evento; chave `evento.cancelado:<id da URL>`.
- `notificar_cancelamento_na_escala` (kind `evento.cancelado_escala`, CASTING): um por dia
  cancelado com escalados, contando pessoas e não vagas ("tire o artista da escala e avise cada um
  pelo WhatsApp"); `urgent` quando o dia é em até 7 dias, como a recusa de convite; link para a aba
  Produção do dia (`/events/<dia>?aba=producao`); chave `evento.cancelado_escala:<id da URL>:<dia>`.

Os ensaios que o ato apaga levam junto os avisos do sino deles (`event_ops._apagar_ensaio_no_banco`,
o mesmo caminho do botão e da troca de tipo). O e-mail de remoção ao elenco, um por talento com
e-mail, sai depois do commit.

**Feature 298**: formulário que ganha destino (ligado a evento por qualquer caminho, ou encerrado)
tem os avisos marcados como lidos **para todos** (`notificacoes_ops.marcar_lidas_por_entidade`, sem
filtro de usuário, na transação do fato); reabrir não reacende; formulário que já chega ligado não
gera aviso. Correções únicas pós-deploy, dry-run por padrão e com `MANTO_SEM_THREADS=1`:
`flask formularios-avisos-resolvidos [--execute]` (FR-019: avisos acesos de formulário com destino,
em lote via `marcar_lidas_por_entidades`) e `flask formularios-cliente-do-evento [--execute]`
(FR-020: formulários desde o corte ligados a evento com cliente e ainda sem cliente).

### 3.13.6 Contratos da ClickSign — `contratos_read.py` / `contratos_write.py` / `clicksign_webhook.py` (feature 317)

A Manto **lê** a conta ClickSign (PRIME DREAMS LTDA, API v3) e liga cada contrato de cliente à venda
(principal do grupo ou avulso). Fluxo e regras de domínio em `docs/04` §Contratos da ClickSign.

- **Cliente HTTP** `app/integracoes/clicksign_client.py` (sem Flask; `Authorization: <token>` puro,
  JSON:API, `page[size]` ≤ 50, `filter[status|created|modified]` com `AAAA-MM-DD,AAAA-MM-DD`; respeita
  `X-Rate-Limit-Remaining`). Exceções: `ClicksignRecusou` (4xx) × `ClicksignIndisponivel` ("não sei":
  timeout, 5xx, 429) × `ClicksignTravada`. Pré-condição da conta: **"E-mail do usuário da API"**
  preenchido em Configurações › API (sem ele, todo GET dá 403).
- **Núcleo**: `app/contratos/contratos_ops.py` (puro: leitor do nome, classificação, escolha da venda,
  documento vigente, situação, régua), `sincronizar_ops.py` (passada incremental, vínculo, anexo do PDF
  assinado, ligar/desligar/descartar/cobrança) e `situacao_ops.py` (leitura em lote para evento, Home e
  `/vendas`).
- **Tabelas** (migration `d3c7a1e5b317`, aditiva): `clicksign_documentos` (um envelope; UNIQUE
  `envelope_id`; `event_id` = principal, SET NULL; `vinculo` ligado/a_conferir/descartado/fora;
  `contrato_anexo_id` → `event_contracts`), `clicksign_desvinculos` (par documento × venda que a
  comercial desligou; CASCADE), `clicksign_cobrancas` (quem cobrou e quando; CASCADE).
- **Config** (`app/config.py`): `CLICKSIGN_ACCESS_TOKEN` (só env, `render.yaml` `sync: false`; vazio =
  integração desligada, aviso na subida), `CLICKSIGN_API_BASE` (default produção), trava
  `_suppress_clicksign()` (`CLICKSIGN_SUPPRESS_CALLS` / `CLICKSIGN_ALLOW_LOCAL_CALLS`; banco local =
  travado), `CLICKSIGN_SYNC_ENABLED`/`CLICKSIGN_SYNC_INTERVAL` (1800 s), `CLICKSIGN_AVISO_SINCRONO`
  (costura do verify).
- **Thread** `_start_clicksign_sync` (atrás de `MANTO_SEM_THREADS`; dorme 90 s; lock
  `site_settings.clicksign_sync_at`; repete se `clicksign_sync_pendente`).

| Método | Rota | O que faz |
|---|---|---|
| `POST` | `/api/webhooks/clicksign` | **Público, assinado.** `Content-Hmac: sha256=<hex>` = HMAC-SHA256 do corpo bruto com `site_settings.clicksign_webhook_secret` (ou o `_anterior` por 24 h), `compare_digest`; inválido ou sem segredo → **404**; corpo > 64 KB → 413; `60/min`. Válido → **200** e uma passada incremental fora da requisição. **O conteúdo do aviso não é lido** — só a reconsulta à ClickSign decide. |
| `GET` | `/api/contratos/a-conferir` | Lista completa de documentos a conferir, com motivo e vendas sugeridas. |
| `POST` | `/api/contratos/<id>/cobranca` | Registra o "Cobrar contrato" (a tela copia a mensagem). 201 `{ultima_cobranca}` · 409 `nao_cobravel` (assinado, vencido, satélite, venda cancelada, não vigente). |
| `POST` | `/api/contratos/<id>/ligar` | `{event_id}` → liga à venda do evento (sempre o principal). 409 `ja_ligado` / `tipo_fora` / `cancelado` (trava 312 no núcleo, `exigir_evento_vivo`). |
| `POST` | `/api/contratos/<id>/desligar` | Volta a "a conferir" e grava o par em `clicksign_desvinculos` (não religa sozinho). 409 `nao_ligado`. |
| `POST` | `/api/contratos/<id>/descartar` | "Não é de nenhuma venda": sai da conferência para sempre. 409 `ja_ligado`. |

Leitura embutida: `GET /api/events/<id>` ganha o bloco `contrato` (dentro de `show_comercial`, num
savepoint — falha vira `null`) e `mensagens.contrato_canal`/`contrato_prazo`; `GET /api/dashboard`
ganha `comercial.contratos` (`None` na volta cedo de falha das vendas); a coluna Contrato de `/vendas`
(`contract_status_map`) passa a ler a situação da venda com a integração ligada (FR-019).

**Comandos** (Shell do Render, `MANTO_SEM_THREADS=1`): `flask clicksign-sincronizar [--desde AAAA-MM-DD]
[--ate] [--aplicar]` (sem `--aplicar` lê, conta e desfaz) e `flask clicksign-webhook --listar |
--registrar <url https pública> | --remover <id> [--aplicar]` (grava `clicksign_webhook_id` e o segredo;
recadastrar guarda o anterior 24 h). Roteiro em `specs/317-contratos-clicksign/quickstart.md` §3.

### 3.14 Superfícies públicas (sem login)
**Catálogo — item avulso × tema (fase 1, migration `c8f4d92e17ab`).** `catalog_items.figurino_sheet_id`
guarda a ficha do item quando ele se contrata SOZINHO. INVARIANTE: item com elenco (um tema) tem
esse campo `NULL` — num tema a ficha é de cada `CatalogCharacter`. Endpoints:
`POST /api/admin/catalogo/<id>/figurino` (vincula/desvincula; 400 em tema) ·
`POST /api/admin/catalogo/<id>/virar-avulso` (tema de 1 personagem → avulso herdando a ficha).
O tipo do item não é coluna: `kind` = `"tema"` se tem elenco, senão `"avulso"`.

`GET /api/cadastro/check-cpf` · `POST /api/cadastro` (devolve `id`, `email` e `verify_token`) ·
`POST /api/cadastro/confirmar` (token do link; consome o token) ·
`POST /api/cadastro/reenviar` (autenticado pelo par `id` + `verify_token`; corrige **só** o email
e reenvia — feature 219) ·
`GET /api/formularios/<form_type>/schema` · `POST /api/formularios/<form_type>` ·
`GET|POST /api/avaliar/<token>` (feedback da cliente) ·
`GET /api/virtuais/campanhas/<slug>` e `.../horarios` (feature 205).
Admin dos formulários: `formularios_admin_read/write.py`
(`/api/formularios/respostas*`, `/api/formularios/editor/*`). O `_response_summary` de
`GET /api/formularios/respostas` e `…/respostas/search` inclui **`client_name`** (nome do cliente
vinculado ou `null`) — a coluna "Situação" da tela `/formularios` mostra o badge
"Cliente: `<nome>`" sem abrir o detalhe; `list_responses`/`search_responses` fazem `joinedload`
do cliente para não gerar N+1.

**Feature 220**: `GET /api/formularios/respostas` aceita `?filtro=sem_evento|sem_cliente|
ambiguos|futuros_sem_evento` (`formularios_ops.STATUS_FILTERS`; `futuros_sem_evento` ordena por
`event_date` asc) e devolve sempre `counts` (`formularios_ops.count_status`, 1 query com `FILTER`)
para os cartões da tela. O vínculo automático (`_attempt_auto_link`) só vincula com **data +
telefone confirmados**; `formularios_ops.ensure_event_client` garante a linha em `event_clients`
(e o `client_id` denormalizado) em todo vínculo manual/associação com cliente conhecido.

**Feature 298 — o formulário vira evento** (contratos em `specs/298-formulario-vira-evento/contracts/`):
- `GET /api/formularios/respostas?filtro=` aceita as partições por destino (`sem_destino`,
  `com_evento`, `encerrados`, `historico`; filtro antigo cai em "todas", sem erro); `counts` são as
  partições + `corte` (AAAA-MM-DD, SP); `truncado` avisa quando o filtro passa de 200. O resumo
  ganha `destino`, `tipo_rotulo`, `closed_reason`/`closed_reason_label`/`closed_note`/
  `closed_by_name`/`closed_at`; `created_at` e `closed_at` saem com `+00:00`.
- O detalhe ganha `motivos_encerramento` (`[{codigo, rotulo, pede_frase}]` — a tela não tem cópia),
  `sugestao`, `divergencia_cliente` (recalculada a cada leitura) e `flags` (`pode_encerrar`,
  `pode_reabrir`, `pode_criar_evento`).
- Novos, em `formularios_admin_write`: `POST …/<id>/encerrar` `{motivo, frase}` (400 com `fields`,
  409 destino já dado, 422 formulário do histórico) · `…/reabrir` (409 "Este formulário não está
  mais encerrado.") · `…/manter-entre-repetidos` (encerra como `repetido` os outros sem destino do
  mesmo telefone, uma `audit()` por formulário; 422 sem telefone) · `…/sugestao/<event_id>/confirmar`
  (404 sugestão que não vale mais; 409) · `…/sugestao/<event_id>/descartar` (`ON CONFLICT DO
  NOTHING`: idempotente e definitivo) · `…/usar-cliente-do-evento` (409 sem evento com cliente; o
  evento nunca muda). Em `formularios_admin_read`: `GET …/para-evento` (o formulário traduzido para o
  cadastro — `contracts/pre-evento.md`; 409 se já tem evento; só leitura, não apaga aviso).
- `POST …/vincular-evento` **não sobrescreve mais**: 409 "Este formulário já tem destino." e a
  resposta vira `{response, divergencia_cliente, event_id, event_title}`.
- **Núcleo único de vínculo**: tela, sugestão, criar evento, aba Comercial, edição do evento, envio
  público e reprocessamento do sync passam por `formularios_ops.apply_event_link` — desfaz o
  encerramento, leva a cliente nos dois sentidos sem trocar ninguém quando divergem, grava
  `event_link_locked` só em decisão humana e apaga o aviso para todos.
- `POST /api/events` com `form_response_id` bloqueia o formulário (`FOR UPDATE`) **antes** do Google
  e responde 409 sem tocar a agenda se ele já tem evento; `PATCH /api/events/<id>` e
  `…/form-response` respondem 409 com a mesma mensagem (antes: silêncio no primeiro, outra frase no
  segundo).
- Envio público (`POST /api/formularios/<tipo>`): a cliente pelo telefone vem antes do vínculo de
  evento (preserva `auto_phone` e o preenchimento da ficha); formulário que já chega ligado não
  gera aviso.

`GET /api/gastos/eventos?date=YYYY-MM-DD` (seletor de vínculo de evento, consumido tanto por
Gastos Extras quanto pelo detalhe de resposta em `/formularios`) respondia **500 no Postgres** até
a feature 188 — `gastos_ops.search_events_by_date` comparava `func.date(start_at)` com uma string.
Corrigido para comparar com o objeto `date`.

### 3.15 Portal do Artista (API completa, UI em React — feature 191)

O portal é um SPA próprio (`frontend/apps/portal`), servido em produção sob `/portal/*` pelo
mesmo serviço estático dos demais bundles (`frontend/server.js`). As rotas Jinja de
`app/talent_portal` continuam registradas em paralelo (strangler-fig, ver §3.16) — a UI React é
o caminho oficial desde a 191.

**Sessão.** Chave própria `session["talent_id"]`, separada do Flask-Login do staff. Os dois
logins fazem `session.clear()`, então as sessões são mutuamente exclusivas: um cookie de talento
não autentica na API de staff e vice-versa (auditado em
`scripts/security/overnight_security_audit.py`).

**RBAC.** "É o dono do recurso" — toda consulta parte do `talent_id` da sessão; nenhum endpoint
aceita um id de talento vindo do cliente. Não há papéis dentro do portal.

**Autenticação e conta**
`POST /api/portal/auth/login`, `/logout` · `GET /api/portal/auth/me` (devolve
`must_change_password`, `terms_accepted`, `terms_accepted_at` — horário de parede de São Paulo em
ISO ingênuo, `null` sem aceite, desde a 311 — e `pending_steps`) ·

> `must_redirect_to_classic` **saiu do payload do login na 206**. Virou sempre `false` na 191
> (troca de senha e aceite de termos passaram a ser telas React, guiadas por `pending_steps`) e
> foi removido junto com `portal_ops.needs_classic_portal_flow`, que já era código morto — o
> talento entra sempre no portal React.

`POST /api/portal/auth/first-access` (senha temporária por e-mail) ·
`POST /api/portal/auth/forgot-password` (silencioso — nunca revela se a conta existe; cobre
também talento sem senha ainda, feature 259 — o link também serve pra definir a primeira) ·
`GET /api/portal/auth/reset-password/<token>` (valida o token) ·
`POST /api/portal/auth/reset-password` · `POST /api/portal/auth/change-password` ·
`POST /api/portal/auth/accept-terms`.

**Agenda, convites e figurino**
`GET /api/portal/agenda` · `POST /api/portal/invites/<role_id>/{accept,reject}` ·
`POST /api/portal/roles/<role_id>/ack-change` ·
`GET /api/portal/events/<event_id>/figurino`.

Cada escalação de `GET /api/portal/agenda` e de `GET /api/portal/historico` sai do **mesmo**
serializador (`portal_ops._role_summary`) e carrega, desde a feature 302, mais duas chaves:

- **`role_type`** — `"character"` ou `"extra"`. É o **código do modelo**, não o rótulo pronto
  (mesma convenção de `payment_status` e `invite_status`): a tela escolhe entre "Personagem:" e
  "Função:".
- **`before_event`** — o bloco "Antes do evento", ou **`null`** quando não há nada a mostrar.
  Shape: `{makeup: {time, location} | null, departure: {time, location} | null, rehearsals: [{start_at, end_at, location}]}`.
  `makeup`/`departure` só existem quando há **horário** — local sem hora é resíduo do formulário
  interno, que pré-preenche "Local de saída". `makeup.location` sai **traduzido**
  (`"manto"` → `Manto Produções`, `"local"` → `No local do evento`, outro → verbatim, por
  `calendar.event_ops.makeup_location_label`): o código do banco nunca chega ao artista.
  `rehearsals` é **lista sempre** (um evento pode ter mais de um ensaio), ordenada por início, sem
  ensaio cancelado, sem ensaio **já realizado** e **sem a `description` do ensaio** — aquele campo
  guarda endereço, não observação. O bloco vai em `pending_invites` e `upcoming`; no `history` é
  sempre `null`.
- **`em_confirmacao`** (feature 303) — booleano, verdadeiro quando o evento está marcado "Sumiu do
  Google Agenda" e não cancelado. Vai o código, nunca o motivo: a tela escreve "Evento em
  confirmação — entre em contato com a produção". Em `pending_invites`, `upcoming` e `history` da
  agenda e em `items` do histórico; opcional no TypeScript, como as duas acima.

> **`history` continua no payload da agenda de propósito**, embora a tela tenha parado de usá-lo na
> 302. `manto-backend` e `manto-frontend` são serviços separados no `render.yaml` e não trocam de
> contêiner juntos: na janela de servidor novo com bundle velho, `agenda.history.map(...)` derruba
> a tela do artista. Remover é tarefa de um ciclo de deploy depois (`docs/05`). Pelo mesmo motivo
> ao contrário, `role_type` e `before_event` nascem **opcionais** no TypeScript.

`GET /api/portal/events/<id>/figurino` **não mudou de payload** na 302 (a tela é que passou a
desenhar `title` e `start_at`, que já vinham). O módulo ganhou a declaração de RBAC no topo, que
era o único dos cinco do portal sem ela.

**Perfil e portfólio**
`GET|PATCH /api/portal/profile` (PATCH parcial: só as chaves enviadas mudam) ·
`POST /api/portal/profile/{photo,document}` ·
`POST /api/portal/profile/media/{photo,link}` · `DELETE /api/portal/profile/media/<media_id>`
(limite de 3 fotos de atuação, links ilimitados).

**Histórico e avaliações**
`GET /api/portal/historico` (lista + somatórios pago/pendente/total) ·
`GET /api/portal/ratings/pending` · `GET|POST /api/portal/events/<event_id>/rate` (nota geral) ·
`POST /api/portal/events/<event_id>/rate/detail` (sub-notas).
Janelas: **7 dias** para avaliar e **30 dias** para editar, contadas do mais recente entre o fim
do evento e `EventRole.assigned_at` (feature 085). Nota abaixo de 4 exige comentário. Toda edição
que muda conteúdo grava a versão anterior em `EventRatingVersion` (feature 181). Evento cancelado
(feature 303): `rateable_event_ids` e `editable_event_ids` de `ratings/pending` nunca o trazem
(`rated_event_ids` não muda), e `GET|POST …/rate` e `POST …/rate/detail` respondem **400** "Este
evento foi cancelado e não recebe avaliação." — depois do 404 de quem não está escalado.

**Núcleo de negócio** (fonte única, reusada pelo Jinja legado): `app/talent_portal/portal_ops.py`
(agenda, convites, figurino, uploads, perfil, portfólio, histórico),
`portal_account_ops.py` (credenciais e termos) e `portal_rating_ops.py` (avaliações).

### 3.16 Rotas Jinja legadas ainda registradas
`app/__init__.py` registra, além de `api_bp`: `auth_bp` (`/auth`), `rh_bp` (`/rh`),
`admin_bp` (`/admin`), `calendar_bp`, `talents_bp`, `financeiro_bp`, `figurino_bp`,
`portal_bp`, `orcamento_bp`, `educamanto_bp`, `gastos_bp`, `revisao_bp`,
`clientes_bp`, `formularios_bp`, `feedback_bp`, `catalogo_bp`. (`cadastro_bp` foi apagado no
hotfix cadastro-raiz — o formulário público é 100% React e só `/api/cadastro/*` fica no Flask.)

Rotas legadas que **ainda têm uso real** (não são só resíduo):
- `GET /figurinos/<id>/print` e `GET /figurinos/print-event/<event_id>` — impressão de ficha.
  Só a **primeira** é linkada pelo React (`FigurinoListPage.tsx`) e, por isso, só ela está no
  proxy de `server.js`; a `print-event` continua sendo link interno de página Jinja.
- `GET /catalogo/midia/campanhas/<path:filename>` — capa das campanhas da Loja de Interações
  Virtuais, **sem login** (feature 224b). Serve só de `virtual_covers`. Existe porque quem abre
  a landing é a família comprando: pela rota geral `/uploads/*` (que é `login_required`) ela
  caía na tela de login do staff e a capa não carregava. Fica sob `/catalogo/midia/` porque esse
  prefixo já é repassado pelo `frontend/server.js` e proxiado pelos três vite configs — e é
  declarada **antes** da rota abaixo, senão o `<path:filename>` dela engoliria o caminho.
- `GET /catalogo/midia/<path:filename>` — serve as fotos do catálogo público **sem login**
  (`Cache-Control: public, max-age=31536000, immutable` desde a 268 — o nome é UUID).
- `GET /catalogo/midia/t/<int:largura>/<filename>` — **variante por largura** da foto do catálogo
  (feature 270), gerada sob demanda pelo motor de `app/catalogo/og_ops.py` (`resolve_variante`) e
  cacheada em `uploads/catalog_thumbs/<largura>/`. Allowlist fechada `LARGURAS_PERMITIDAS =
  (128, 320, 480, 640)`: fora dela, ou arquivo ausente, é 404 **sem gravar nada**. Declarada antes da
  rota acima (o `<path:filename>` engoliria `t/128/x.jpg`). Mesmo `immutable` de 1 ano. Quem pede
  é `assetUrl(path, { largura })`/`assetSrcSet()` do `@manto/api-client` — a regra de "quem tem
  variante" é a mesma nos dois lados (`pastas_da_variante`).
- `GET /uploads/t/<int:largura>/<path:filename>` (`app/__init__.py`, `login_required`) — variante
  de **foto de talento** (270) e de **figurino** (292). A allowlist de subpasta é
  `og_ops.SUBPASTAS_COM_VARIANTE` (`talent_photos`, `figurino_photos`); `talent_docs` fica de fora
  de propósito — miniatura de RG é PII espalhada. Cache em `uploads/talent_thumbs/<largura>/` e
  `uploads/figurino_variantes/<largura>/` (**não** `figurino_thumbs`, que é o legado das
  miniaturas do Drive e candidata a `rm -rf` de limpeza).
  `Cache-Control: private, max-age=31536000, immutable` (**`private`**: a rota exige login, e
  `public` deixaria um cache compartilhado servir a foto a quem não logou). Os originais em
  `/uploads/talent_photos/*` e `/uploads/figurino_photos/*` ganharam o mesmo cabeçalho; o resto de
  `/uploads` segue sem cache longo — lá o arquivo pode ser regravado no mesmo caminho.
  ⚠️ O `immutable` no figurino só é seguro porque a **rotação passou a gravar caminho novo**
  (`figurino_ops.rotate_figurino_photo`): regravar por cima serviria a orientação antiga por um ano.
- `flask warm-thumbnails [--familia catalogo|talento|figurino|todas] [--largura N]` — pré-aquece as
  variantes: catálogo a 128 e capas/personagens a 320/480/640; **talento a 128** (o avatar da
  produção e dos comboboxes — a largura que faltava) e 320/480/640; **figurino** nas quatro.
  Idempotente; rodar depois de cada deploy que mude a receita e depois do `compress-images
  --execute`. `--familia` existe para não competir com o app pela CPU logo após um deploy.
- `flask midia-orfa [--familia …] [--csv] [--rapido]` — inventário que cruza **banco × disco** e
  diz, por arquivo, **por que** a foto não aparece: `sumiu` · `não é imagem` · `formato ilegível` ·
  `URL externa` · `campo vazio`. Roda igual no `manto_local` e no Shell do Render, e é a resposta
  para "isto está consertado em todos os ambientes?".
- `flask fix-heic [--execute]` — converte para JPEG o que já está em disco num formato que o
  navegador não abre (HEIC/HEIF/AVIF/TIFF/BMP, extensão que mente), **atualiza a coluna**, apaga o
  original e invalida as variantes. O `compress-images` **não** resolve isso: ele mantém o formato
  de propósito, e reescrever um `.heic` produz um JPEG dentro de um arquivo `.heic`.
- `flask campanha-fotos [--enviar] [--limite N] [--pausa S] [--id N]` — pede aos talentos o reenvio
  do que se perdeu (293). Dry-run por padrão; dedup no `AuditLog` (`action="campanha_fotos_292"`);
  pula devolução permanente em aberto e entrega essas pessoas como lista de WhatsApp; uma conexão
  SMTP para o lote.
- `flask campanha-prazo-pagamento [--enviar] [--limite N] [--pausa S] [--id N]` — avisa os
  talentos ativos de que o cachê sai em até 3 dias úteis (311). Mesmo molde do `campanha-fotos`
  (dedup em `action="campanha_prazo_pagamento_311"`). Duas versões: quem aceitou o termo recebe a
  data do aceite e o link `/termos`; quem não aceitou recebe o link de criar senha de 7 dias com
  `?destino=/termos` (sem senha, ou só a temporária) ou o `/termos` (com senha própria).
- ⚠️ **`MANTO_SEM_THREADS=1`** na frente de qualquer `flask <comando>` no Shell do Render: sem
  isso, `create_app()` sobe o auto-import de talentos (que **escreve no banco** a partir da
  planilha), o sync da agenda e o backup para o Drive.
- `GET /portal/photo/<path:filename>` — foto de figurino que `GET /api/portal/events/<id>/figurino`
  devolve para o portal React; é rota Jinja, mas checa a mesma sessão de talento **e**, desde a
  feature 216, só serve as subpastas de `PORTAL_PHOTO_SUBFOLDERS` (`app/talent_portal/routes.py:41`).
  Ver §4.3 → *RBAC de arquivo*.
- Todo o resto do `app/talent_portal` — Portal do Artista Jinja. ⚠️ Das 21 rotas do `portal_bp`,
  **só `/portal/photo` é alcançável pelo proxy de produção** (`frontend/server.js:175-187`); as
  outras 20 seguem registradas e continuam acessíveis batendo direto no host do Flask, com validação
  mais fraca que a da API. Ver `docs/05_DIVIDA_TECNICA.md` §9.3.

**A `home()` Jinja saiu (feature 206).** A rota `/` do Flask não renderiza mais `home.html`:
devolve **301 para `PLATFORM_BASE_URL`** (`app/config.py`), para capturar acesso residual direto
ao serviço do backend. Quem serve `/` é o `frontend/server.js`. O `dashboard_service.py` continua
sendo fonte única — agora com um consumidor só, `/api/dashboard`.

> ⚠️ **Blocos de tarefa que existiam só na home Jinja não têm equivalente em `/api/dashboard`**:
> reembolsos pendentes, ensaios pendentes/agendados/órfãos, presença pendente, notas fiscais a
> emitir, eventos sem cliente e pré-contratos sem cliente / que precisam de
> revisão. O template `app/templates/home.html` ficou órfão. Reconstruí-los no React é trabalho
> em aberto, não coberto pela 206. (Os eventos sem valor voltaram na feature 299, no painel "Sem
> valor"; o ensaio voltou na 206.)

---

## 4. Estrutura de Permissões e RBAC

### 4.1 Papéis (`app/constants.py` → `RoleName`)

| Papel | Escopo |
|---|---|
| `SUPERADMIN` | Acesso total; `has_permission()` sempre `True`; único que administra catálogo, configurações, logs, desempenho, sincronização e preços |
| `COMERCIAL` | Vendas: criar/editar evento, clientes, pipeline, comissões (só as próprias), orçamento, formulários, catálogo público |
| `FINANCEIRO` | Painel financeiro, pagamentos, gastos recorrentes, comissões (visão gerencial e liquidação), usuários |
| `CASTING` | Banco de Talentos (aprovar/rejeitar/editar), escalação de elenco, avaliações de casting |
| `FIGURINO` | Fichas de figurino (CRUD, fotos, vínculo com Personagem do catálogo) |
| `ENSAIO` | Agenda + EducaManto (leitura/uso) + **bloco de ensaio do evento** (`show_ensaio`, `app/api/agenda_read.py:141`), **painel próprio no dashboard** (`app/api/dashboard_service.py:451`) e **materiais de ensaio** (`_CAN_ENSAIO_MATERIAL`, `app/calendar/routes.py:3627`) — feature 208 |
| `MARKETING` | Cria espaços de revisão de mídia e opera o **módulo de Marketing** (feature 204): painel de postagens e metas de frequência, com leitura dos Temas ativos do catálogo (via `/api/marketing/opcoes`, sem acesso à gestão do catálogo) |
| `ARTISTA_3D` | Gestão total do módulo 3D (Acervo + Fila + presentes do evento) e **leitura** dos eventos — precisa do elenco e do formulário de pré-contrato para saber o que imprimir |
| `REVENDEDOR_EDUCAMANTO` | Perfil restrito: **só** Agenda (visualização) + EducaManto |

**Guard do perfil restrito (`_revendedor_guard`, feature 078 · corrigido na 214).** Roda em
`before_request` e vale só para quem tem **apenas** esse papel (multi-perfil não é restrito). Duas
respostas diferentes por superfície:
- **`/api/*`** → passa nos prefixos `/api/auth`, `/api/agenda`, `/api/events`, `/api/educamanto`
  (o espelho exato das páginas permitidas); fora deles devolve **403 JSON**. Nunca redirect: um
  302 para HTML chega no `apiFetch` como 200 + `index.html` e explode no `JSON.parse` — foi o que
  derrubou o app inteiro para esse perfil depois da migração 206.
- **demais caminhos** → allowlist de páginas (`/agenda`, `/events/`, `/educamanto`, `/auth`,
  `/uploads`, `/static`, `/health`), com `redirect("/agenda")` no resto.

Regra especial: o **responsável EducaManto** (`SiteSetting.educamanto_seller_id`) ganha acesso de
leitura a Vendas/Comissões mesmo sem papel Financeiro — mas continua tratado como **vendedor
comum** na tela de comissões (só vê as próprias, sem ações de pagamento).

### 4.2 "Ver como" (impersonação)
`IMPERSONABLE_ROLES = [CASTING, FIGURINO, COMERCIAL, FINANCEIRO, ENSAIO]`. Só um **superadmin
real** pode ativar. Com impersonação ativa, o usuário conta **apenas** com o papel simulado
(`effectiveRoles()` no frontend; `session["impersonate_role"]` no backend).

### 4.3 Como o RBAC é implementado

> **Regra de arquitetura**: em endpoint de API o RBAC é uma **função chamada no início da view**,
> nunca um decorator Flask. Os decorators legados (`@require_superadmin` etc.) dependem de sessão
> de página; a API reimplementa o mesmo check e valida por **paridade de comportamento**.

Gates por módulo (todos em `app/api/`):

| Gate | Onde | Papéis aceitos |
|---|---|---|
| `_require_superadmin()` | `admin_catalogo_*`, `admin_config_*`, `orcamento_read` (`GET /orcamento/settings`), `orcamento_write` (`POST /orcamento/settings` — desde a 307 com o bloco `datas_especiais`, desde a 309 com `produtos`/`produtos_estimativa` —, `POST`/`DELETE /orcamento/settings/especiais*`) | `SUPERADMIN` |
| `_require_users_access()` | `admin_users_*` | `SUPERADMIN`, `FINANCEIRO` |
| `_can_create_event()` / `_can_edit_event()` | `agenda_write` (delegam para `_CAN_CREATE`/`_CAN_EDIT_EVENT` de `app/calendar/routes.py`) | `COMERCIAL`, `SUPERADMIN` (criar); `_CAN_EDIT_EVENT` (editar) |
| `_can_delete()` | `agenda_write` (delega para `_CAN_DELETE`): excluir, cancelar (e o `GET …/impacto-exclusao` com a prévia `?devolucao=`), recusar solicitação e — feature 303 — `POST /api/events/<id>/devolver-ao-google`, sempre depois do 404. Os dois endpoints da 306, `PATCH /api/events/<id>/devolucao` e `POST /api/events/<id>/multas`, usam a mesma régua por `cancel_ops.pode_editar_venda_do_cancelado` (linha abaixo) | `SUPERADMIN` (papel real; desde a 224 o Comercial só **solicita**) |
| `cancel_ops.pode_editar_venda_do_cancelado(user)` — **a regra única do cancelado** (feature 306) | gate de `PATCH /api/events/<id>/devolucao` e `POST /api/events/<id>/multas`, depois do 404 (os demais → 403); nas portas de dinheiro do evento, a recusa **depois** do gate de hoje — quem passa nele e não passa na regra leva **409 `codigo: "cancelado"`** (`EventoCanceladoError`), em geral por `cancel_ops.recusar_se_cancelado`, que trava o evento e relê antes de decidir. Porta a porta em "RBAC do evento cancelado", abaixo | `SUPERADMIN` pelo **papel real** (`user.roles`; o "Ver como" não conta) — a régua de `_can_delete()` e `_is_superadmin()` |
| `cancel_ops.pode_editar_motivo_do_cancelado(user)` (feature 306b) | gate de `PATCH /api/events/<id>/motivo-cancelamento`, depois do 404 (os demais → 403): só o **texto** do motivo; o dinheiro do cancelado segue com a regra acima. A flag `can_edit_motivo_cancelado` do detalhe segue o "Ver como" | `SUPERADMIN` ou `COMERCIAL` pelo **papel real** |
| `_ve_faixa_sumidos()` | `agenda.py`, `GET /api/events/sumidos-google` (feature 303) | `SUPERADMIN` ou `COMERCIAL` pelo **papel efetivo** (respeita o "Ver como"); os demais recebem **200** com `pode_ver: false` e a lista vazia — nunca 403 |
| — (sem gate de papel) | `POST /api/events/<id>/sync` | qualquer usuário interno logado, como sempre; desde a 303 ele confere o evento no Google antes de mexer e pode **retirar a marca** "Sumiu do Google Agenda" de um evento que voltou |
| `_can_casting()` | `agenda_write` (remover cargo) | `CASTING`, `SUPERADMIN` |
| `_can_manage_sale()` | `agenda_write` (nota fiscal; `PUT /api/events/<id>/acrescimos` e `/parcelas` — na 305 o PUT de acréscimos passa a recusar BV sem quem recebe/PIX e a sincronizar a comissão) | `COMERCIAL`, `FINANCEIRO`, `SUPERADMIN` |
| `_can_manage_sale()` | `PATCH /api/events/<id>/orcamento` (feature 273; na 299 o valor simbólico passou a contar como "sem venda") | `COMERCIAL`, `FINANCEIRO`, `SUPERADMIN`. **Autoria (feature 301)**: *vincular* em evento sem orçamento é livre para quem tem o módulo de Orçamento (COMERCIAL/SUPERADMIN) — FINANCEIRO passa neste gate mas leva **404** ao apontar orçamento que não é dele; *trocar, desvincular ou re-aplicar* sobre vínculo de outra pessoa → **409 `orcamento_de_outro`**, nomeando o autor. Os três verbos: `aplicar` escreve `sale_date`, que decide o mês da comissão |
| `show_comercial` (papel efetivo, respeita "Ver como") | `GET /api/dashboard` — blocos `comercial` e `formularios` (feature 299: o conteúdo mudou, o gate não); o detalhe do evento usa o mesmo corte para `cobranca`/`venda`/`pagamentos`. **Feature 301**: passado este gate, `venda.orcamento` e `orcamento_history_id` saem para quem tem o **módulo de Orçamento** (COMERCIAL ou SUPERADMIN), sem checagem de dono; FINANCEIRO passa no gate mas fica só com `tem_orcamento`. A chave `pode_gerir`, essa sim, depende da autoria do orçamento vinculado | `COMERCIAL`, `FINANCEIRO`, `SUPERADMIN` |
| `_can_confirm()` | `agenda_write` | `COMERCIAL`, `SUPERADMIN` |
| `_require_cobrar()` (feature 317) | `contratos_write`: cobrar, ligar, desligar e descartar contrato da ClickSign; no detalhe, `contrato.pode_cobrar`/`pode_conferir` seguem `can_confirm` (zerado no cancelado) e, na Home, `contratos.pode_cobrar` o papel efetivo | `COMERCIAL`, `SUPERADMIN` (papel real) — FINANCEIRO leva **403** (vê a situação, não age: decisão do dono) |
| papéis de `show_comercial` (feature 317) | `contratos_read`: `GET /api/contratos/a-conferir`; o bloco `contrato` do detalhe e `comercial.contratos` da Home vêm no mesmo `show_comercial` | `COMERCIAL`, `FINANCEIRO`, `SUPERADMIN` — CASTING e os demais: 403 / sem a chave |
| HMAC do aviso (sem papel) | `POST /api/webhooks/clicksign` | público; vale só com `Content-Hmac` correto (404 nos demais) |
| `_is_superadmin()` | dispensar/restaurar cargo, excluir ficha | `SUPERADMIN` |
| `_can_edit_figurino()` | `figurino_write` | `FIGURINO`, `SUPERADMIN` |
| `_can_edit_talent()` | `talents_read/write` | `CASTING`, `SUPERADMIN` |
| `_can_view_vendas(settings)` | `financeiro_read` | `COMERCIAL`, `FINANCEIRO`, `SUPERADMIN` **ou** responsável EducaManto |
| `_require_financeiro()` | `financeiro_write`, `gastos_*` | `FINANCEIRO`, `SUPERADMIN` |
| `_require_vendas()` | `clientes_read.py:24`, `clientes_write.py:25`, `formularios_admin_read.py:34` (importado por `formularios_admin_write`) | `COMERCIAL`, `FINANCEIRO`, `SUPERADMIN` |
| `_require_vendas()` — endpoints da 298 | `formularios_admin_write`: `…/encerrar`, `…/reabrir`, `…/manter-entre-repetidos`, `…/sugestao/<id>/confirmar`, `…/sugestao/<id>/descartar`, `…/usar-cliente-do-evento` | `COMERCIAL`, `FINANCEIRO`, `SUPERADMIN` (papel real — o "Ver como" não se aplica, dívida §3.5) |
| `_pode_criar_evento()` | `formularios_admin_read`: `GET …/para-evento` e a flag do detalhe (delega para `_CAN_CREATE`, sem repetir a lista) | `COMERCIAL`, `SUPERADMIN` — FINANCEIRO leva 403 |
| `_require_vendas()` ⚠️ **homônimo, regra diferente** | `orcamento_read.py` (importado por `orcamento_write.py`) | `COMERCIAL`, `SUPERADMIN` — **FINANCEIRO leva 403**. Gate de **módulo**: passado ele, **não há** checagem de dono (feature 301) — exceto no `DELETE .../historico/<id>`, por `_get_entry_para_excluir` (autor ou SUPERADMIN). A regra de escopo está em §3.13. A 313 não muda gate: o desconto vive no mesmo `POST /calcular` (Financeiro, Casting e Revendedor continuam 403 — `verify_313` cenário 15) |
| `_has_role(COMERCIAL, FIGURINO, SUPERADMIN)` | `catalogo_read.api_catalogo_elenco_busca` | busca visual de elenco / vínculo de ficha |
| `_require_use()` / `_require_manage()` | `educamanto_*` | uso: `COMERCIAL`, `SUPERADMIN`, `ENSAIO`, `REVENDEDOR_EDUCAMANTO`; gestão: `COMERCIAL`, `SUPERADMIN` |
| `require_3d_access()` | `impressoes3d_read/write` | `ARTISTA_3D`, `SUPERADMIN` |
| `require_marketing_access()` | `marketing_read/write` | `MARKETING`, `SUPERADMIN` |
| `_CAN_ENSAIO` (`app/calendar/routes.py:50`) | criar/editar/excluir ensaio | `ENSAIO`, `CASTING`, `SUPERADMIN` |
| `_CAN_ENSAIO_MATERIAL` (`app/calendar/routes.py:3627`) | materiais de ensaio | `ENSAIO`, `CASTING`, `SUPERADMIN` |
| `portal_api_login_required` ⚠️ **exceção declarada à regra do decorator** | todos os `app/api/portal_*.py` | **nenhum papel** — o Portal do Artista não tem papéis. O modelo é "é o dono do recurso": o decorator só confere a sessão de talento (401 sem ela), e cada consulta parte do `talent_id` da sessão, nunca de um id vindo do cliente. Cada módulo declara isso no topo; `portal_figurino.py` era o único dos cinco sem a declaração e a ganhou na **302**. Onde o recurso é de outra pessoa, o portal recusa — a ficha de figurino de evento em que o talento não está escalado devolve **403**, e não o 404 que o Princípio XIII pediria (decisão registrada na 302, `docs/05`) |

> **Terceiro padrão (feature 272): RBAC na emissão, escopo por dono na leitura.** `/api/notificacoes*`
> não tem gate de papel: quem podia agir no fato foi decidido quando ele aconteceu
> (`notificacoes_ops.DESTINATARIOS_POR_KIND`), e cada um lê só a própria caixa (`user_id ==
> current_user.id`, 404 para id alheio). Não é "ausência de chave" nem `flags.<nome>` — ver §3.13.5.
>
> ⚠️ Estes gates **não cobrem tudo**: 83 das 288 rotas de `app/api/` não têm gate de papel além de
> `api_login_required` (a maioria por design — leitura aberta a staff autenticado, ou RBAC por posse
> do recurso). A intenção está declarada na **docstring de topo do módulo**, não na view. E o nome do
> gate pode mentir: veja as duas linhas de `_require_vendas` acima.

#### RBAC do evento cancelado (feature 306)

Nenhum papel novo. Cada porta mantém o gate de hoje e a ordem de hoje (401 → 404 → 403); a regra
única do cancelado (`pode_editar_venda_do_cancelado`, na tabela acima; a regra em `docs/00` §4)
entra **depois** do gate. Onde a porta não recongela o cancelado, o 409 `cancelado` vale **para
todos os papéis, o Superadmin inclusive**. Toda recusa sai pelo envelope de `json_error` com
`codigo` e os extras do caso (`fields`, `dias`, `max_devolucao`, `piso`, `teto`, `pago`,
`devolvido`, `atual`, `event_id`, `novo_principal`, `venda_do_grupo`); a tela lê pela união
`CodigoRecusaCancelamento` (`lib/eventOps.ts`). Deadlock (40P01) nas portas que travam o grupo vira
rollback e 409 `tente_de_novo` (`cancel_ops.traduzir_erro_de_banco`).

| Porta | Gate (papéis) | No cancelado e 409 novos |
|---|---|---|
| `POST /api/events/<id>/cancelar` | `_can_delete()`: `SUPERADMIN` real, depois do 404 | Trava o grupo → `ja_cancelado` → `ensaio` → 400 `alcance` → `sem_outro_dia_vivo` → `grupo_mudou` → `cache_pago` (`dias`) → `devolucao_pendente` (`dias`) → 400 com todos os `fields` → `max_devolucao_mudou` (`max_devolucao`). O `UNIQUE(event_id)` que estoura vira `ja_cancelado`. Sai a 409 de líder de grupo, e o marcado deixa de ser recusado |
| `GET /api/events/<id>/impacto-exclusao` | `_can_delete()`, sem mudança | Sem trava. Na prévia (`?devolucao=`): 400 `fields.devolucao` ou `fields.venda_nova`; evento já cancelado → `ja_cancelado` |
| `PATCH /api/events/<id>/devolucao` **(novo)** | `pode_editar_venda_do_cancelado`: `SUPERADMIN` real, depois do 404 | 400 `devolucao_total` (falta ou não é número), antes da trava → trava → `nao_cancelado` → `regime_sem_retido` (`satelite`, `virtual`) → 400 com os `fields` → `abaixo_do_piso` (`piso`) → `acima_do_teto` (`teto`, só no `dia`) |
| `POST /api/events/<id>/multas` **(novo)** | `pode_editar_venda_do_cancelado`: `SUPERADMIN` real, depois do 404 | Trava → `nao_cancelado` → 400 `fields.multas` ou `fields.multa_<elenco_id>` |
| `GET /api/events/cancelamentos` | `_can_read_cancelamentos()` (feature 312: `SUPERADMIN` ou `FINANCEIRO`, papel real) | Só contrato: `resumo` em cada cancelado, com o PIX só para `show_financeiro`; filtros da 312 abaixo |
| `GET /api/events/<id>` | sem mudança | Só contrato: `event.cancelamento` só com `show_comercial` (§3.3) |
| `PATCH /api/events/<id>/comercial` | `_can_create_event()` (`COMERCIAL`, `SUPERADMIN`), sem mudança | Depois do 409 de satélite e antes do 400 de data e do 403 da 215b: Comercial → `cancelado`; o Financeiro segue fora do gate (403). O Superadmin grava e recongela; o evento que mudou de estado entre a leitura e a trava → `estado_mudou` |
| `PATCH /api/events/<id>` ("Editar tudo") | `_can_create_event()`, sem mudança | Depois do 400 de validação: `sale_value`, `sale_value_gross`, `commission_rate`, `seller_id`, `is_cortesia_permuta` ou `with_invoice` **diferente** do gravado → `cancelado` **para todos, o Superadmin inclusive** (a porta não recongela; `event_ops.venda_mudaria`). Campo igual ao gravado passa |
| `PUT /api/events/<id>/acrescimos` | `_can_manage_sale()` (`COMERCIAL`, `FINANCEIRO`, `SUPERADMIN`), sem mudança | Depois do 409 de satélite e antes do 400 `items`: Comercial e Financeiro → `cancelado`. O Superadmin grava no lugar e recongela; cancelado entre a leitura e a trava → `estado_mudou` |
| `PUT /api/events/<id>/parcelas`; `POST`/`PATCH`/`DELETE /api/events/<id>/invoices[/<id>]` | `_can_manage_sale()`, sem mudança | Trava o evento e relê: Comercial e Financeiro → `cancelado`; Casting e Figurino seguem no 403. O congelado não muda |
| `PATCH /api/events/<id>/orcamento` | `_can_manage_sale()`, sem mudança | Depois do 409 de satélite: `cancelado` **para todos os que passam no gate, o Superadmin inclusive** ("O orçamento de um evento cancelado não se aplica nem se troca."), antes do 400 do corpo, da autoria da 301 e da B8 |
| `POST /api/events/<id>/payments` | `_can_edit_event()` (`CASTING`, `FIGURINO`, `COMERCIAL`, `FINANCEIRO`, `SUPERADMIN`), sem mudança | Trava o grupo (também no vivo) e relê: quem não é Superadmin real → `cancelado`, **antes** de salvar o arquivo; `grupo_mudou` (o arquivo novo é removido) |
| `PATCH`/`DELETE /api/payments/<id>` | `_is_superadmin()`, sem mudança | O Superadmin grava, e o principal cancelado em `venda` se refaz pelo pago do grupo; pago do grupo abaixo do devolvido → `pago_abaixo_do_devolvido` (`pago`, `devolvido`); `grupo_mudou` |
| `POST /api/events/<id>/reimbursements`, `POST /api/reimbursements/<id>/collect` | `_can_edit_event()`, sem mudança | Trava o evento e relê: quem não é Superadmin real → `cancelado` (no `collect`, antes do 400 "já cobrado"). `DELETE /api/reimbursements/<id>` (`_is_superadmin()`) não muda |
| `DELETE /api/events/<id>` | `_can_delete()`, sem mudança | `cancelado` antes do "use o cancelamento": o cancelado não se exclui; o núcleo relê sob trava e recusa de novo |
| `POST`/`DELETE /api/events/<id>/grupo`, `DELETE /api/events/<leader>/grupo/satelites/<sat>` | `_can_group()` (`COMERCIAL`, `FINANCEIRO`, `SUPERADMIN`), sem mudança | Agrupar cancelado, desagrupar ou soltar dia cancelado → `cancelado` para todos (soltar pela tela do principal virava 500); no desagrupar e no soltar, o principal que mudou entre a leitura e a trava → `grupo_mudou` |
| Gastos Extras: `POST /api/gastos`, `…/aprovar`, `…/rejeitar`, `PATCH`/`DELETE /api/gastos/<id>`, `…/vincular-evento` | os de hoje (`POST` sem gate de papel; `DELETE` para Financeiro ou o dono do gasto pendente; os demais `_require_financeiro()`) | Devolução de evento cancelado → `devolucao_travada` (`fields`, `event_id`); `disbursement_type: "cliente"` novo → 400. Ver §3.7 |
| `POST /api/financeiro/pagamentos/set-status` | `_require_financeiro()` (`FINANCEIRO`, `SUPERADMIN`), sem mudança | BV → `bv_nao_esta_a_pagar` ou `valor_mudou` (`atual`); devolução de cancelado → `valor_mudou`. Ver §3.6 |
| `POST /api/roles/<id>/assign` | `_can_edit_event()`, sem mudança | No cancelado, tirar da vaga não manda e-mail de remoção |
| `DELETE /api/admin/users/<id>` | sem mudança | Bloqueio novo `cancelamentos` (400, §3.11) |
| `GET /api/financeiro/dashboard`, `/api/financeiro/comissoes`, `/api/financeiro/pagamentos`, `/api/vendas/pipeline`, `/api/admin/desempenho`, `/api/clientes*`, `/api/dashboard`, `/api/notificacoes` | sem mudança | Só contrato (§3.2, §3.6, §3.13.5) |

O Jinja não recongela: a tela antiga do evento recusa no cancelado as ações de dinheiro para todo
papel, o Superadmin inclusive (§3.3).

**Os 18 códigos de 409** (`CODIGOS_RECUSA_DO_CANCELAMENTO`, `app/constants.py`; nenhuma view
escreve o texto do código à mão):

| `codigo` | Onde nasce |
|---|---|
| `cancelado` | a regra única nas portas acima; para todos em `PATCH /api/events/<id>`, orçamento, exclusão e grupo |
| `ja_cancelado` | `POST …/cancelar` (inclusive o `UNIQUE` que estoura) e a prévia do impacto |
| `ensaio` | `POST …/cancelar` num evento do tipo Ensaio |
| `grupo_mudou` | `POST …/cancelar` (a composição relida na trava mudou; `novo_principal_id` que já não é o dia vivo mais cedo, com `novo_principal`; a venda do grupo mudou desde que o diálogo abriu, com `venda_do_grupo`); `PATCH …/devolucao`, `POST …/multas` e comprovantes (a trava do grupo); desagrupar e soltar dia |
| `sem_outro_dia_vivo` | `POST …/cancelar` com `"so_este_dia"` num principal sem outro dia vivo |
| `cache_pago` | `POST …/cancelar`, com `dias` (os dias alcançados com cachê pago ou no banco) |
| `devolucao_pendente` | `POST …/cancelar`, com `dias` (a pendente de qualquer dia do grupo) |
| `max_devolucao_mudou` | `POST …/cancelar` com "tudo" divergente do máximo relido, com `max_devolucao` |
| `tente_de_novo` | deadlock residual em `…/cancelar`, `…/devolucao`, `…/multas`, `…/comercial`, `…/acrescimos` e nos três comprovantes |
| `nao_cancelado` | `PATCH …/devolucao` e `POST …/multas` em evento vivo |
| `regime_sem_retido` | `PATCH …/devolucao` em `satelite` e `virtual` |
| `abaixo_do_piso` | `PATCH …/devolucao`, com `piso` |
| `acima_do_teto` | `PATCH …/devolucao` no `dia`, com `teto` |
| `pago_abaixo_do_devolvido` | editar ou excluir comprovante, com `pago` e `devolvido` |
| `bv_nao_esta_a_pagar` | set-status do BV |
| `valor_mudou` | set-status do BV e da devolução de cancelado, com `atual` |
| `devolucao_travada` | as seis portas de Gastos Extras, com `fields` e `event_id` |
| `estado_mudou` | `PATCH …/comercial` e `PUT …/acrescimos`, quando o evento muda de estado entre a leitura e a trava |

⚠️ `"cancelado"` (`CODIGO_EVENTO_CANCELADO`) tem homônimos de outros fluxos —
`sumico_ops.CODIGO_CANCELADO` (recusa da devolução ao Google), `SITUACAO_CANCELADO` e
`MOTIVO_FORA_CANCELADO`: nunca compare um com o outro.

#### O cancelado fora das listas e a tela só de consulta (feature 312)

A regra de leitura (o invariante em `docs/04`): **o cancelado não é item de lista nenhuma**. Todo filtro olha só
`cancelled_at` (pedido de exclusão e a marca da 303 não escondem nem travam nada) e nenhum parâmetro o traz de volta
(`incluir_cancelados` não existe). Contratos que mudaram de conteúdo, sem chave nova: `GET /api/agenda/day/<data>`,
`GET /api/agenda/search` (o filtro vem antes do limite de 30, e com ela saem do vínculo de ensaio, da tag NFC e de
`grupo/candidatos`), `GET /api/gastos/eventos?date=`, `GET /api/talents/<id>` (histórico e os quatro números), a Fila
3D e as pendências de presente (`GET /api/3d/fila`), `GET /api/events/<id>` (`group.satellites[]` do principal **vivo**
sem o dia cancelado; `ensaios[]` sem ensaio cancelado), o rótulo `group_label` "(N eventos)" do pipeline e da DRE (só os
dias vivos, `group_ops.dias_vivos`, e só com dois ou mais — um principal vivo cujo único dia caiu é avulso na lista,
a régua de `cobranca_ops._grupo_comercial`), os candidatos automáticos do formulário, o "Agendados" da Home do Ensaio,
a lista de faltantes do figurino (`figurino_ops.list_sheets`; o "associar" também não grava em vaga de cancelado), o
filtro "personagem" do diretório de talentos, o selo "já trabalhou com a Manto" (`routes.ids_de_quem_trabalhou`) e,
no Jinja, o Dia, o conflito de agenda, a disponibilidade do `event_detail`, a lista de shows do vínculo de ensaio, a
de eventos para agrupar, o painel do grupo do principal vivo e os ensaios do show (faixa, tabela e o "primeiro
ensaio" da mensagem).

| Endpoint | Mudança | RBAC |
|---|---|---|
| `GET /api/clientes/<id>` | `events[]` e `event_count` sem o cancelado (sai `events[].cancelado`); **novo** `cancelamentos: {quantidade, retido}`; `form_history[].event_situacao` | inalterado |
| `GET /api/events/cancelamentos[?mes=AAAA-MM][&devolucao=nao_pago\|no_banco\|pago\|sem]` | **novos** `total_retido`, `total_retido_escopo` (`periodo`\|`listados`), `filtros`; sai o `devolucao` legado. Com `mes`, sem limite; sem, os 200 mais recentes. `devolucao` pelo estado das devoluções do **resumo** (o do grupo), antes do corte; no satélite do "todos", só as do próprio dia; `sem` = nenhuma. `mes`/`devolucao` inválidos (ano fora de 2000–2999 inclusive) → 400 `fields`. `reason`/`cancelled_by` só com `show_comercial` | `_can_read_cancelamentos()`: `SUPERADMIN` ou `FINANCEIRO` real; demais 403. Excluir, cancelar e alterar devolução seguem só `_can_delete()` |
| `GET /api/vendas/pipeline` | **novo** `cancelamentos` (sempre; `quantidade: 0` sem cancelado) — `cancel_ops.painel_de_cancelamentos`, a mesma forma do `paineis.cancelamentos` da DRE: `quantidade, pago, devolvido, devolucao_a_pagar, retido, comissao_retido, bv_retido, imposto?, efeito_resultado?, itens[]` (itens com `event_date, seller_name, pago, devolvido, devolucao_a_pagar, comissao_retido`). Comissão pela régua do KPI (`commission_target_id`) | `imposto`/`efeito_resultado` só com a flag `show_financeiro` (SUPERADMIN, FINANCEIRO; segue o "Ver como") |
| `GET /api/financeiro/dashboard` | `paineis.cancelamentos` sai da mesma função, com os totais da cascata (números iguais) e os itens enriquecidos | inalterado |
| `GET /api/events/<id>` do cancelado | `flags.somente_consulta`; `can_edit_event`, `can_edit_core`, `can_confirm`, `can_group`, `can_manage_3d`, `can_request_delete` falsas; `desfazer_presente_3d`/`desfazer_formulario` com o que as duas seriam. `cancellation_reason` e `cancelled_by` só com `show_comercial` (Q9); o "Log de atividades" do Jinja idem (também o do `ensaio_detail`). Documento e nascimento do elenco seguem para Comercial e Superadmin (`show_pii` não lê a `can_confirm` zerada) | inalterado |
| `GET /api/dashboard` | `casting.cancelados_a_avisar?: [{role_id, event_id, event_title, character_name, start_at, cancelled_at, talent_id, talent_name, whatsapp}]` — derivada da escala (`cancel_ops.elenco_dos_dias`), some com a vaga vazia | painel de casting (CASTING, SUPERADMIN) |
| `POST /api/roles/<id>/assign` numa vaga de cancelado | só a remoção: talento no corpo, ou cachê/transporte diferentes dos gravados → 409 `cancelado`; a vaga fica com o cachê e o adicional de transporte; sem e-mail de remoção (306); o último a sair marca lido o `evento.cancelado_escala` do dia | `_can_casting()` (CASTING, SUPERADMIN); FIGURINO, COMERCIAL e FINANCEIRO → 403 "Evento cancelado: quem tira da escala é o Casting." |
| `GET`/`POST /api/avaliar/<token>` (público) | evento cancelado → **410** "Este evento foi cancelado — não há avaliação a fazer.", sem título nem data; nada gravado | público |
| `GET /api/portal/events/<id>/figurino` | depois do 403 "não escalado" e do 404: cancelado → 400 "Este evento foi cancelado." | portal |
| `POST /api/portal/invites/<role_id>/accept` | cancelado → 400, nada gravado | portal |
| `POST /api/portal/invites/<role_id>/reject` | livre; no cancelado não emite `convite.recusado` e, se era o último a avisar, fecha o `evento.cancelado_escala` do dia | portal |
| tags (`serialize_tag`), `GET /api/formularios/respostas/<id>`, pedidos de figurino | `event.situacao` / `event_situacao` (o selo) | inalterados |

**A trava** (`cancel_ops.exigir_evento_vivo`, traduzida por `api_utils.trava_do_cancelado`): toda escrita na tela de
um evento cancelado, **para todo papel, o Superadmin inclusive**, depois do 404 e do 403 de cada rota → **409**
`{codigo: "cancelado", message: "Este evento foi cancelado — a tela fica só para consulta."}`, nada gravado. Alcança:
`PATCH /api/events/<id>`, `…/basico`, `…/confirm`, `…/logistics`, observações, `…/clients`, contratos, `…/travel-estimate`,
materiais, `…/presenca`, `PATCH …/grupo`, `POST …/sync`, `POST …/roles`, as escritas de vaga (`DELETE /roles/<id>`,
transporte, figurino feito e ficha, dismiss/restore, `payment-status`), `PATCH …/3d-gifts/<id>`, `…/3d-dismissal`,
`DELETE /api/clientes/avaliacoes/<id>`, `PATCH`/`DELETE /api/ensaios/<id>` e `POST /api/ensaios/<id>/vincular` de
ensaio cancelado, `POST …/solicitar-exclusao`; no Jinja, **toda**
ação do despachante `POST /events/<id>` (substitui as 8 de venda da 306), as rotas fora dele que escrevem no evento
(o `link-parent` do próprio ensaio cancelado inclusive) e "Imprimir fichas" (`flash` + volta). **Fica livre**: o que a 306 e a 306b gateiam por regra própria (dados de venda,
`PATCH …/devolucao`, `POST …/multas`, `PATCH …/motivo-cancelamento`) e os desfazer (desligar formulário, soltar presente
e tag, tirar da escala). Rota nova que escreve num evento cai na trava por padrão: o cenário 9b do `verify_312` lista
toda regra de escrita com id e falha com uma sem classificação.

**As recusas de vínculo** (`cancel_ops.recusar_se_cancelado_para_ligar`, no núcleo, antes de e-mail ou Google; código
`cancelado`): com campo → **400** `fields` — vincular ensaio (`parent_event_id`), tag NFC nova (`event_id`; o mesmo id
passa), pedido de figurino novo ou troca de evento (`event_id`); sem campo → **409** — agendar ensaio (API e Jinja),
presente 3D novo, ligar formulário (painel, `/formularios`, edição em bloco), escalar, vaga com talento, convidar,
`feedback-link`.

#### RBAC de arquivo — `/uploads/<path>` e `/portal/photo/<path>` (feature 216)

Não é só `@login_required`. `GET /uploads/<path>` (`app/__init__.py:611`) despacha pelo **primeiro
segmento** do caminho, via `UPLOADS_ROLE_BY_SUBFOLDER` (`app/__init__.py:66-71`):

| Subpasta | Quem lê |
|---|---|
| `contracts/`, `payments/`, `invoices/` | `COMERCIAL`, `FINANCEIRO`, `SUPERADMIN` |
| `talent_docs/` | `CASTING`, `SUPERADMIN` |
| `expenses/` | o **dono** do gasto **ou** financeiro (`_can_read_expense_receipt`, `app/__init__.py:94`) |
| demais subpastas | qualquer usuário autenticado |
| `talent_photos/` e `figurino_photos/` | qualquer usuário autenticado — são as **únicas** subpastas com cache longo (`private, immutable`, features 270 e 292) e com variante; `GET /uploads/t/<largura>/<subpasta>/<arq>` gera pela mesma checagem. A lista é `og_ops.SUBPASTAS_COM_VARIANTE`, e o `client.ts` espelha a MESMA regra — o `verify_292` lê os dois e compara |

Devolve **404, não 403**, para não confirmar a existência do arquivo. `GET /portal/photo/<path>`
(`app/talent_portal/routes.py:78`) é restrito às subpastas de `PORTAL_PHOTO_SUBFOLDERS`
(`routes.py:41`) — sem essa allowlist a rota entregava a árvore inteira de `uploads/` ao usuário de
menor privilégio.

### 4.4 Escopo de dados no servidor (não confiar no cliente)

Padrão consolidado na feature 187 e que deve ser replicado: **o servidor decide o escopo**.
Em `GET /api/financeiro/comissoes`, `seller_filter = requested_seller_id if can_manage else
current_user.id` — um vendedor comum recebe apenas os próprios dados, independentemente do
`seller_id` enviado na querystring. `POST /api/financeiro/comissoes/pagar-mes` responde **403**
para quem não é `FINANCEIRO`/`SUPERADMIN`, inclusive para o próprio ID.

A feature **196** replicou o padrão em `GET /api/vendas/pipeline` (Dashboard Comercial), com três
escopos resolvidos por `_resolve_vendas_scope()` em `app/api/financeiro_read.py`:

| Quem | O que enxerga | `commission_target_id` |
|---|---|---|
| `FINANCEIRO`/`SUPERADMIN` | Empresa toda; pode filtrar por `seller_id` | o vendedor filtrado, ou `None` (= comissão da equipe) |
| `COMERCIAL` sem papel de gestão | **Só as próprias vendas** — o `seller_id` da querystring é ignorado | ele mesmo |
| Responsável EducaManto sem papel comercial | Só eventos EducaManto (`(EDU…`) | ele mesmo |

### 4.5 RBAC no frontend
`frontend/apps/internal/src/lib/navigation.tsx` é a config declarativa da navegação, portada de
`app/templates/base.html`, com `isVisible(user)` por item. **Isso é apenas conveniência de UI** —
a autorização real está sempre no servidor.

---

## 5. Arquitetura de Build e Deploy (Render)

### 5.1 Monorepo do frontend
```
frontend/                       npm workspaces
├── apps/internal/              ERP (staff)         → dev: npm run dev:internal (porta 5173)
├── apps/portal/                Portal do Artista   → dev: npm run dev:portal   (porta 5174)
├── apps/public/                Vitrine anônima     → dev: npm run dev:public   (porta 5175)
├── packages/{ui,api-client,money}   consumidos direto do TS-fonte (sem build próprio)
└── server.js                   servidor estático único dos TRÊS SPAs
```

Os pacotes compartilhados não têm build próprio: são resolvidos por alias do Vite + `paths` do
`tsconfig.base.json` e compilados junto com cada app — não há ordem de build a orquestrar.

**Novos no design system (feature 195)** — `frontend/packages/ui/src/components/`:
- `AvatarThumb` — miniatura circular (pessoas) ou quadrada (figurinos/personagens), tamanhos
  `sm|md|lg`, com placeholder de iniciais ou ícone quando não há foto. Recebe a URL **já
  resolvida** — quem chama aplica `assetUrl()`, mantendo `@manto/ui` sem dependência de
  `@manto/api-client`.
- `Combobox` — campo de seleção pesquisável que substitui `<select>` nativo em qualquer lista com
  mais de 10 itens (Princípio X.1). Filtro local ignorando acentos (`José` casa com `jose`) ou
  busca remota via `onQueryChange` + `loading`; navegação por setas/Enter/Esc; miniatura por opção;
  botão de limpar; modo `freeSolo` (o valor é o texto digitado, as opções são apenas sugestões —
  usado por endereços). Dropdown animado com Framer Motion respeitando `useReducedMotion()`.

### 5.2 Três SPAs em um único serviço (feature 186 US6; portal na 191)

`frontend/server.js` substitui o antigo `serve --single` (que só conhece **um** `index.html` de
fallback). Usa `serve-handler` programaticamente, uma vez por app, cada um com seu próprio
fallback de SPA — deep link e refresh funcionam nos três. Os apps montados sob prefixo são
avaliados antes do app da raiz, e o prefixo é removido de `req.url` antes de delegar:

| URL pública | Diretório servido | Fallback |
|---|---|---|
| `/catalogo`, `/catalogo/*`, `/catalogo?*` | `frontend/apps/public/dist` | `index.html` do público |
| `/portal`, `/portal/*`, `/portal?*` | `frontend/apps/portal/dist` | `index.html` do portal |
| `/*` (qualquer outra) | `frontend/apps/internal/dist` | `index.html` do interno |

Coerência de assets: cada app montado usa `base` igual ao seu prefixo **apenas em produção** —
`apps/public/vite.config.ts` (`/catalogo/`) e `apps/portal/vite.config.ts` (`/portal/`) — e passa
o mesmo valor como `basename` ao React Router (`apps/public/src/App.tsx` usa
`import.meta.env.PROD ? "/catalogo" : undefined`; `apps/portal/src/App.tsx` usa
`import.meta.env.BASE_URL`). Em dev tudo continua na raiz.

> O Flask também expõe `/portal/*` (Jinja legado), mas em **outro serviço e outro domínio** — não
> há colisão.

### 5.2.1 Proxy reverso para o Flask (feature 206)

`frontend/server.js` deixou de ser só um servidor estático: com o React consolidado como interface
primária, ele é a **única porta de entrada** (`app.mantoproducoes.com.br`) e repassa ao Flask, via
`http-proxy`, as rotas que ainda são do backend — **antes** de qualquer fallback de SPA. Alvo em
`BACKEND_URL` (envVar `sync: false` do serviço `manto-frontend` no Render — `render.yaml`; default
`http://localhost:5000`).

| Filtro | Por que existe |
|---|---|
| `/api/*` | toda a API JSON (`@manto/api-client`) |
| `/uploads/*` | mídia de `app/storage.py`; é o que `assetUrl()` devolve |
| `/catalogo/midia/*` | fotos públicas do catálogo — casa **antes** do mount `/catalogo`; cobre também as variantes `/catalogo/midia/t/<largura>/*` (feature 270) sem entrada nova |
| `/catalogo/og/*` | miniatura da prévia de link (`app/catalogo/routes.py:og_image`) — feature 216 |
| `/portal/photo/*` | foto de figurino do portal (Jinja, mesma sessão do talento) — **antes** do mount `/portal` |
| `/google/*` | callback do OAuth do Google Calendar (`app/calendar/routes.py`), rota Jinja com `redirect_uri` fixo no Google Console |
| `/avaliar/*` | superfície pública por link já distribuído (feedback da cliente) — hotfix 206b; sem ela o link caía no login do ERP |
| `/cadastro/*` | **não vai ao Flask** (hotfix cadastro-raiz): servido pelo bundle da vitrine SEM reescrever a URL — endereço canônico do cadastro de talento nos hosts `app.` e `portal.`; `/catalogo/cadastro/*` segue vivo para os e-mails de confirmação antigos |
| `/f/*` | **não vai ao Flask**: endereço canônico dos formulários públicos, 302 → `/catalogo/f/<slug>` (formulário React da vitrine), query preservada |
| `/static/*` | CSS/JS das páginas Jinja públicas acima (bundles Vite usam `/assets` — sem colisão) |
| `/figurinos/<id>/print`, `/figurinos/print-event/<id>` | páginas Jinja de impressão que a SPA interna linka; regex restrito ao sub-path |

> ⚠️ **`/health` NÃO está nesta lista.** Na URL pública ele cai no fallback da SPA e devolve
> `index.html` com 200 mesmo com o Flask morto; o `healthCheckPath` do `render.yaml` funciona porque o
> Render bate direto no serviço. Sonda de backend vivo é um endpoint sob `/api/` devolvendo JSON (§5.3).

> ⚠️ **`BACKEND_URL` precisa do esquema.** Um valor sem `https://` (como o painel do Railway exibia o
> domínio privado) fazia o `http-proxy` estourar `TypeError` **síncrono** dentro de `proxy.web`, fora
> do callback de erro — exceção não capturada que **matava o processo a cada chamada de API**.
> `resolveBackendUrl` normaliza e valida, e `proxy.web` roda em `try/catch`; valor inválido vira 502
> com os SPAs de pé. A **fonte de verdade** do valor é o envVar `BACKEND_URL` do serviço
> `manto-frontend` no painel do Render (`sync: false` no `render.yaml`) — hoje a URL pública do
> `manto-backend`, `https://manto-backend.onrender.com`; se o serviço for renomeado, o valor muda no
> painel e esta linha fica velha. No Render o frontend fala com o backend pela URL pública; não há
> rede privada configurada, e o bind do gunicorn (`--bind 0.0.0.0:$PORT`) mora dentro do
> `startCommand` do `render.yaml`.

> ⚠️ **O proxy solta o Flask quando o cliente some (hotfix 263b, 11/09/2026).** O http-proxy só
> desliga o upstream em `req.on('aborted')`, que em Node ≥ 16 não dispara para um GET cujo cliente
> some durante a resposta; sem os ganchos de `res 'close'` do `server.js` (`proxyReq.destroy()` e
> `res.on('pipe') → origem.destroy()`; e o inverso, `proxyReq 'close' → res.destroy()`, para o
> cliente não ficar mudo quando o Flask some), cada vídeo/foto abandonado deixava um socket em CLOSE_WAIT
> com até 6 MB de fila no kernel — 432 MB de `sock` no cgroup e o contêiner morto por memória em
> 08/09 e 10/09. **O gráfico de memória do Render conta buffer TCP do kernel**, não só o processo:
> RSS baixo com memória em 100% é socket preso. `proxyTimeout` é prazo de INATIVIDADE do socket
> com o Flask (180 s em rota normal, 10 min em mídia — nunca zero), e `server.requestTimeout` é
> 30 min porque o default de 5 min do Node respondia 408 a upload longo. A linha `[vida]` do log
> (a cada 5 min) traz `conexoes`, `sumiram`, `rss`, `cgroup` e `sock`; por SSH,
> `egrep "^(sock|anon) " /sys/fs/cgroup/memory.stat` é a leitura direta.

### 5.2.2 Domínios e roteamento por host (feature 206)

Os domínios customizados ativos (`app`, `portal`, `alo`) são custom domains do serviço `manto-frontend`
no Render — CNAME para `manto-frontend.onrender.com`, DNS na Hostinger, TLS emitido pelo Render. O
serviço do Flask não tem domínio próprio: é alcançado só pela URL pública `manto-backend.onrender.com`,
que o proxy usa como `BACKEND_URL`. O `beta.*` não foi migrado (está fora do ar) — e deixou um cookie
para trás (abaixo).

| Domínio | Raiz entrega | Observação |
|---|---|---|
| `app.mantoproducoes.com.br` | `apps/internal` (ERP) | URL principal da plataforma |
| `beta.mantoproducoes.com.br` | — | **fora do ar** desde a migração (não cadastrado no Render); só história |
| `portal.mantoproducoes.com.br` | **302 → `/portal/`** | endereço que os talentos conhecem |
| `alo.mantoproducoes.com.br` | **302 → `/catalogo/v/<caminho>`** | Loja de Interações Virtuais (224d) — `alo.…/<slug>` abre a campanha; a **raiz vai para `/catalogo/v`**, a landing da loja (224e). Já apontou para `/catalogo/`, o catálogo de eventos, e isso entregava outro produto a quem chegava pelo endereço da loja |

> ⚠️ **O `beta.*` deixou um cookie para trás (feature 295).** O endereço histórico está fora do ar,
> mas a feature 144 ligou `SESSION_COOKIE_DOMAIN=".mantoproducoes.com.br"` para ele compartilhar
> sessão com o `app.*`. Desligar a variável **não recolhe** o cookie que ela já gravou: quem logou
> naquele período continua mandando DOIS `session` na mesma requisição, e o Werkzeug entrega o
> primeiro — com o mesmo `Path`, o mais antigo (RFC 6265 §5.4), que é o órfão. O login grava o
> cookie bom, a requisição seguinte é lida pelo órfão e responde 401 **para sempre**, porque o
> servidor não escreve mais naquele domínio e não tem como sobrescrevê-lo. O `after_request`
> `_recolhe_cookie_de_sessao_orfao` (`app/__init__.py`) recolhe o órfão quando chegam dois
> `session` e ninguém se autenticou — na própria resposta 401, antes de a pessoa conseguir logar.
> **Trocar o domínio do cookie de sessão é mudança de duas partes:** muda-se `SESSION_COOKIE_DOMAIN`
> e inscreve-se o domínio antigo em `Config.SESSION_COOKIE_DOMINIOS_OBSOLETOS`.

`ALO_HOSTS` (env do serviço frontend, default `alo.mantoproducoes.com.br`) faz o mesmo pela loja
virtual: é o endereço curto que vai em story e link de bio, no lugar de
`app.mantoproducoes.com.br/catalogo/v/<slug>`. Vale a mesma mecânica e as mesmas ressalvas do
`PORTAL_HOSTS` abaixo — inclusive a de que o prefixo aparece na barra de endereço **depois** do
redirect; deixar a raiz limpa exigiria um segundo build de `apps/public` com `base: "/"`.
Infra: nenhum serviço novo — é domínio custom no serviço de frontend que já serve `app.` e
`portal.`, mais o CNAME.

`PORTAL_HOSTS` (env do serviço frontend, default `portal.mantoproducoes.com.br`) marca os hosts em
que a raiz é o Portal do Artista. Sem essa regra, `portal.*` entregaria `apps/internal/dist` e o
talento cairia na tela de login do staff — o bundle do portal é compilado com `base: "/portal/"` e
o React Router usa `basename={import.meta.env.BASE_URL}`, então **precisa** do prefixo na URL.

Dois detalhes que não são negociáveis nessa regra:
1. É **redirect**, não reescrita de `req.url`. O React Router lê a URL do browser; sem o prefixo
   visível, o bundle certo seria servido e nenhuma rota casaria — tela em branco.
2. **Preserva caminho e query.** O link de redefinição de senha que sai por e-mail é
   `<PORTAL_URL>/reset-password/<token>`; um redirect seco para `/portal/` descartaria o token.

O bloco de proxy roda antes, então `/api` e mídia continuam indo ao Flask também nesse host.

> ⚠️ **Domínio não cadastrado no host = certificado errado + HSTS.** Aprendido no Railway: quando
> `portal.*` deixou de estar cadastrado, a borda passou a apresentar o certificado curinga do
> provedor, que não cobre o hostname — e, com HSTS ativo, o browser nem oferece exceção. O
> diagnóstico rápido é ler o **SAN** do certificado: curinga do provedor significa "o host não
> reconhece este hostname" (cadastro ausente ou CNAME apontando para o alvo antigo), não
> "certificado ainda emitindo". Ao (re)cadastrar um domínio no Render, o CNAME precisa apontar para
> `manto-frontend.onrender.com`.

Os filtros espelham os `server.proxy` dos três `vite.config.ts`, inclusive `changeOrigin: true` —
sem ele, um `BACKEND_URL` de domínio público faria o roteador de borda do host devolver a
requisição para o próprio serviço frontend, em laço. `xfwd: true` envia os `X-Forwarded-*`. Falha
de conexão com o backend responde **502**, sem derrubar os SPAs.

> ⚠️ **O proxy só entra em ação com `VITE_API_BASE_URL` vazia no build.** Com ela preenchida,
> `API_BASE`/`assetUrl()` geram URL absoluta do Flask e o browser fura o proxy — inclusive para
> `/uploads` e `/figurinos/<id>/print`.

### 5.3 Serviços no Render (`render.yaml`)

O deploy é o blueprint `render.yaml` na raiz — o **único** arquivo que descreve produção. Os
arquivos `railway.json`/`nixpacks.toml` (raiz e `frontend/`) foram removidos na feature 296; o que
eles ensinavam está abaixo. Três recursos, todos em Oregon: `manto-postgres` (basic-1gb),
`manto-backend` (python, plano standard) e `manto-frontend` (node, starter). `autoDeploy: true` nos
dois serviços web — **push na `main` é o deploy** (~60s até o bundle novo). Os envVars com
`sync: false` são preenchidos um a um no painel pelo dono, nunca copiando o `.env` inteiro (hotfix
269b); `PORTAL_URL`, `PUBLIC_BASE_URL` e `SESSION_COOKIE_DOMAIN` **não se definem** (o default do
código é o endereço público real; cookie host-only basta e funciona também na URL `*.onrender.com`).

**Serviço backend** — `manto-backend`: `rootDir: .`, `buildCommand: pip install -r requirements.txt`,
`startCommand`:
```
flask db upgrade && python seed.py && gunicorn run:app \
  --workers 3 --worker-class gthread --threads 12 --bind 0.0.0.0:$PORT \
  --timeout 120 --graceful-timeout 120 --max-requests 800 --max-requests-jitter 100 \
  --access-logfile - --access-logformat '%(h)s %(m)s %(U)s %(s)s %(b)s %(D)s'
```

- **Healthcheck**: `healthCheckPath: /health` — o Render bate **direto no serviço**, sem passar pelo
  Node; é ele que gateia a troca de container. Devolve JSON com `threads` e
  `db_pool_em_uso`/`db_pool_disponivel` e é sempre 200 por construção (healthcheck que falha sob
  carga só antecipa a queda). ⚠️ **Na URL pública `/health` não prova nada**: não está em
  `BACKEND_PREFIXES` (§5.2.1), cai no fallback da SPA e responde 200 com `index.html` mesmo com o
  Flask morto. Backend vivo se prova por um endpoint `/api/` devolvendo JSON — ex.:
  `/api/formularios/comum/schema`; como o start é `flask db upgrade && …`, JSON também prova que a
  migration aplicou.
- **Disco persistente**: 10 GB montados em `/opt/render/project/src/instance` — **só no backend**. É
  o único caminho que sobrevive a um deploy: `uploads/` (mídia, comprovantes, contratos),
  `nfc_media/`, `virtual_videos/`, `catalog_thumbs/`, `talent_thumbs/`, `.secret_key`,
  `backup_drive_folder.txt`. Não há S3/R2 em produção (`USE_S3=false`). O conjunto de arquivos local
  é outro: comandos de mídia (`fix-heic → compress-images → warm-thumbnails`, `midia-orfa`) rodam LÁ.
- **Container efêmero**: todo deploy troca o container — mata processos `nohup`, limpa `/tmp`, e
  `/tmp` é tmpfs (RAM): um tar grande ali estourou 2 GB e o kernel matou o container (exit 137).
  Temporário grande vai para a raiz de `instance/` (`_tmp_no_disco()`, `app/backup_drive.py`).
  Rodada longa só quando não há push na fila.
- **Backup da produção**: o próprio backend sobe uma thread (`app/backup_drive.py`) que manda
  `pg_dump` 2×/dia (05h/17h UTC) e mídia 1×/dia (06h UTC; full no dia 1, incremental nos demais)
  para um **Drive compartilhado** do Workspace (`BACKUP_DRIVE_FOLDER_ID` ou
  `instance/backup_drive_folder.txt`; sem id = desligado com log). Conta de serviço não tem cota no
  My Drive — só Shared Drive. Retenção pela lixeira do Drive. Além disso a máquina do dono dumpa o
  banco toda noite (02:00) em `backups/` (`scripts/db/backup-railway.ps1`, nome herdado).
- **Acesso ao servidor**: `ssh -i ~/.ssh/render_manto_ed25519 srv-da8o06on74is73ehf4q0@ssh.oregon.render.com`
  (backend; o frontend é `srv-da8nvsgn74is73ehe9a0`, sem disco). A sessão já vem com as env vars do
  serviço. Comando de app: `cd /opt/render/project/src && MANTO_SEM_THREADS=1 PYTHONPATH=$PWD
  .venv/bin/flask <cmd>` — `MANTO_SEM_THREADS=1` desliga as threads de fundo (auto-import de
  talentos, sync, backup) e `PYTHONPATH` é necessário porque o Python 3.11 (safe-path) não põe o CWD
  no `sys.path`. Plano B quando o classificador bloqueia um script por SSH: Shell do painel do Render.
- **Access log** (desde 26/08/2026): `IP MÉTODO CAMINHO STATUS BYTES MICROSSEGUNDOS`. Antes disso
  nenhuma requisição de produção era registrada; `%(b)s` (bytes) é o campo que nomeia o culpado num
  incidente de lentidão.
- **Concorrência**: teto `workers × threads` = **36 requisições simultâneas**. Cada download de mídia
  segura uma thread do primeiro ao último byte, na velocidade de quem assiste — com 4 threads, dois
  ou três vídeos travavam um worker inteiro e o site parava **sem gerar um único 5xx** (incidente
  de 26/08). `--timeout 120` **não é deadline de requisição** com `gthread` (o heartbeat sai da
  thread principal). Subir `--threads` **exige** subir o pool do SQLAlchemy junto (`app/config.py`,
  `SQLALCHEMY_ENGINE_OPTIONS`, hoje `pool_size 10 + max_overflow 10` = 20 por worker; cada worker
  consome pelas 12 threads de requisição MAIS as 6 de background) — `scripts/validar_startcommand.py`
  confere. As 6 threads de fundo sobem uma vez por worker (3 cópias de cada; desperdício conhecido).
  Assinatura de diagnóstico: **CPU plana + p99 alto + 0% de erro = requisição presa segurando
  thread, não carga**; o 502 nasce no proxy Node quando o Flask não responde.

> ⚠️ **Mexer no `startCommand` derruba a produção quando dá errado.** Em 26/08/2026 (ainda no
> Railway) a flag `--access-log-format` — que **não existe**; o certo é `--access-logformat` — fez o
> gunicorn recusar os argumentos e nunca subir; o healthcheck falhou por 4min51s. No Render a
> mecânica é a mesma: (1) **gunicorn não RODA no Windows**, mas o parser roda —
> `scripts/validar_startcommand.py` lê o `startCommand` do `render.yaml` e reproduz a recusa; rode-o
> **antes de todo push** que mexa nessa linha; (2) **o serviço tem disco**, então o container antigo
> cai antes de o novo responder: start que falha não "mantém a versão anterior" — deixa fora. Regra:
> mudança no `startCommand` vai **sozinha**, num commit só dela, fora do horário, com os Events do
> Render abertos. (Política de retry do Render não conferida; não conte com ela.)

**Serviço frontend** — `manto-frontend`: `runtime: node`, `rootDir: frontend`,
`buildCommand: npm install && npm run build` (compila os **três** SPAs — `frontend/package.json`),
`startCommand: npm run start` → `node server.js`. Variáveis: `BACKEND_URL` (origem pública do
Flask, `sync: false` — §5.2.1), `VITE_API_BASE_URL` **vazia** no build, `PORTAL_HOSTS`/`ALO_HOSTS`
(§5.2.2). ⚠️ **Sem `healthCheckPath` e sem `watchPatterns`**: cada push (inclusive só de docs)
rebuilda os dois serviços e abre ~1 min de 502 na porta pública enquanto o container troca.
Ausência conhecida — decisão pendente do dono (`docs/05`); acrescentar muda o pipeline e vai em
commit isolado. (`npm install` está no blueprint; `npm ci` seria mais seguro — também em `docs/05`.)

**Variáveis que sobrevivem da migração** (`docs/CONTINGENCIA_RENDER.md`, passo 4):
`GOOGLE_OAUTH_REDIRECT_URI` recebe a URL pública registrada no Google Cloud Console +
`/google/callback`, nunca a local; `AUDIT_AGENT_TOKEN` e `MARKETING_AGENT_TOKEN` **não foram
preenchidos** na migração — os agentes semanais respondem 404 desde 28/08 (`docs/05`); `TALENTS_*`,
`FIGURINO_DRIVE_FOLDER_ID` e `GOOGLE_SHEETS_CREDENTIALS` ficaram vazios de propósito (integrações
de planilha aposentadas). Rate limit em memória por worker e threads de background ×3 são
trade-offs herdados, documentados acima.

### 5.4 Dev local

| Alvo | Comando |
|---|---|
| Backend (SQLite casual) | `python run.py` |
| Backend contra a cópia real | `$env:MANTO_SEM_THREADS='1'; $env:FLASK_ENV='development'; .\scripts\db\run-local.ps1` (aponta `DATABASE_URL` para `manto_local`). ⚠️ **O espelho traz o token do Google e as credenciais de e-mail reais** — sem as duas variáveis o `create_app()` sobe as threads de fundo e escreve na agenda da empresa; as travas `_suppress_mail`/`_suppress_calendar_invites` (`app/config.py`) cobrem só e-mail e convite, e `_suppress_calendar_event_writes` (`CALENDAR_SUPPRESS_EVENT_WRITES`, feature 303; escape `CALENDAR_ALLOW_LOCAL_EVENT_WRITES=true`) cobre só a devolução ao Google (303) e a remoção do Google no cancelamento (306; travada, o ato cancela no sistema e avisa na tela) — o sync, a limpeza e o "Sincronizar" continuam LENDO o Google real no local, e criar, editar e excluir evento continuam escrevendo. `/scripts/db/` é gitignored (entrada `/scripts/db/`): contém caminhos e credenciais locais; o conteúdo esperado está em `DEVELOPMENT.md`. Verificação funcional = `specs/NNN-nome/verify_NNN.py` (versionado; os anteriores à 266 em `scripts/db/`) — não há `tests/` nem pytest |
| Frontend staff | `cd frontend && npm run dev:internal` |
| Frontend público | `cd frontend && npm run dev:public` |
| Frontend portal | `cd frontend && npm run dev:portal` |
| Typecheck | `cd frontend && npm run typecheck` — **um comando, cobre os três apps**. Não rode `npx tsc --noEmit` app a app: esquece o `apps/portal`, que é buildado em produção |

Proxies do Vite dev — **cada app do monorepo precisa da sua própria entrada por prefixo de mídia; o
proxy de um não vale para o outro** (é o gap que se repete a cada app novo):
- `apps/internal`: `/api` e `/uploads` → `http://localhost:5000`; `^/figurinos/\d+/print$`
  (regex escopada — **nunca** proxiar o prefixo `/figurinos` inteiro, senão a rota SPA homônima
  é sequestrada).
- `apps/public` (`vite.config.ts:16-29`): `/api`, `/catalogo/midia`, `/catalogo/og` e `/uploads`.
- `apps/portal` (`vite.config.ts:32-38`): `/api`, `/portal/photo` e `/uploads`.

> **Regra de teste**: produção é PostgreSQL. Toda verificação funcional roda contra `manto_local`
> (Postgres), **nunca** contra o SQLite vazio — o SQLite não pega bugs Postgres-only
> (ex.: `float − Decimal` no financeiro).
