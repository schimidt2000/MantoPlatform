# 01 — Sistema e Banco de Dados

> **Documento vivo.** Atualizado obrigatoriamente ao fim de cada feature (ver regra em
> `CLAUDE.md` → "REGRA OBRIGATÓRIA DE DOCUMENTAÇÃO VIVA").
>
> Última atualização: **2026-07-27** · Estado do repositório: pós-feature **190**
> (`paridade-orcamento-educamanto`) · Head de migration: `9f1c3a7b5e2d` (sem migration nova)

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
               │ app/models.py (SQLAlchemy)   │  → PostgreSQL (Railway)
               └──────────────────────────────┘
```

**Regra de dependência** (Princípio de arquitetura da constituição): a camada só pode depender da
camada abaixo. Rotas (API e Jinja legado) **não** contêm regra de negócio — apenas validam RBAC,
chamam `*_ops` e serializam.

| Camada | Stack |
|---|---|
| Backend | Python 3 · Flask · Flask-Login · Flask-Migrate (Alembic escrito à mão) · SQLAlchemy |
| Banco | PostgreSQL (produção Railway e cópia local `manto_local`); SQLite só para uso casual de dev |
| Frontend | React + TypeScript + Vite + Tailwind CSS + shadcn/ui + Framer Motion + TanStack Query |
| Pacotes internos | `@manto/ui` (design system), `@manto/api-client` (`apiFetch`/`assetUrl`), `@manto/money` (`formatBRL`/`parseBRL`) |
| Integrações | Google Calendar API (OAuth 2.0), Google Sheets API (service account), Google Maps Distance Matrix, ClickSign, Vimeo/Drive (mídia) |
| Storage | `app/storage.py` — abstração local (`instance/uploads/`) ou S3/volume em produção |

### 1.1 Escopo migrado vs. legado

- **React + API (completo)**: tudo que staff autenticado usa (`apps/internal`) e as superfícies
  públicas anônimas (`apps/public`).
- **Ainda 100 % Jinja2/vanilla**: o **Portal do Artista** (`app/talent_portal`) — nunca fez parte
  da migração 144. `frontend/apps/portal` é apenas um scaffold vazio.
- **Jinja legado paralelo**: os `routes.py` dos blueprints já migrados continuam existindo
  (padrão strangler-fig). Decomissioná-los é limpeza futura.

---

## 2. Schema e Models (PostgreSQL)

Fonte única: `app/models.py` (~1.880 linhas). **53 tabelas**, incluindo 3 tabelas de associação.

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
| `calendar_events` | `CalendarEvent` | `google_event_id` (unique), `google_html_link`, `title`, `start_at`/`end_at`, `event_type` (`SHOW`/`CORP`/`R&I`/`ENSAIO`…), `source` (`google_calendar`\|`platform`), `sale_value`, `sale_value_gross`, `sale_date`, `with_invoice`, `is_cortesia_permuta`, `commission_rate`, `confirmed_at`, `feedback_token` (unique), `needs_rehearsal`, `group_name`, `makeup_time`/`makeup_location`, `departure_time`/`departure_location`, `travel_time_minutes`, `travel_distance_km`, `is_outside_sp`, `payment_method`, `payment_installments`, `payment_due_date`, `transport_value`, `acrescimo_value`, `invoice_file`, `invoice_due_date` | `seller_id`→`users`, `client_id`→`clients`, `confirmed_by_id`→`users`, `parent_event_id`→`calendar_events` (ensaios), `group_leader_id`→`calendar_events` (agrupamento comercial), `orcamento_history_id`→`orcamento_history` |
| `event_roles` | `EventRole` | `character_name`, `role_type` (`character`\|`extra`), `cache_value`, `cache_cap`, `travel_cache`, `payment_status`, `invite_status` (`pending`\|`accepted`\|`rejected`), `figurino_done_at`, `event_changed_at`, `needs_makeup`, `is_singer`, `dismissed_at` | `event_id`→`calendar_events`, `talent_id`→`talents`, `figurino_sheet_id`→`figurino_sheets`, `dismissed_by`→`users` |
| `event_observations` | `EventObservation` | observações de evento (texto/foto) | `event_id` |
| `event_contracts` | `EventContract` | arquivo + flag assinado | `event_id` |
| `event_payments` | `EventPayment` | comprovantes de pagamento com valor | `event_id` |
| `event_installments` | `EventInstallment` | parcelas (`due_date`) | `event_id` |
| `event_invoices` | `EventInvoice` | notas fiscais (`issue_date`) | `event_id` |
| `event_acrescimos` | `EventAcrescimo` | acréscimos tipados (`BV`, `Taxa de urgência`, `Outro`…) | `event_id` |
| `event_clients` | `EventClient` | múltiplos clientes por evento com tipo de relação (`Contratante`, `Assessora`, `Mãe/Pai`, `Familiar`, `Outros`) | `event_id`, `client_id` |
| `event_reimbursements` | `EventReimbursement` | reembolso de despesa da cliente | `event_id`, `created_by_id`, `collected_by_id` |
| `event_logs` | `EventLog` | trilha por evento (`actor_name`, `actor_role`, `message`) | `event_id` |
| `ensaio_materials` | `EnsaioMaterial` | materiais de ensaio (upload/link) | `event_id`, `user_id` |
| `audit_logs` | `AuditLog` | trilha global de auditoria (usada por `app.utils.audit`) | — |
| `sync_logs` | `SyncLog` | histórico de sincronização com o Google Calendar | — |
| `import_state` | `ImportState` | estado da importação de planilhas | — |

**Semântica importante de `CalendarEvent`**
- `parent_event_id` = vínculo **Ensaio → evento pai**.
- `group_leader_id` = **agrupamento comercial** (evento satélite → evento principal). São coisas
  distintas — nunca reutilizar um pelo outro.
- `is_educamanto` (property) = título começa com `(EDU` (`EDUCAMANTO_TITLE_PREFIX`).
- `event_requires_client(event)` (em `app/constants.py`): eventos com início ≥ **2026-06-29**
  (`CLIENT_REQUIRED_FROM`) exigem cliente para salvar a venda; anteriores são grandfathered.

### 2.3 Talentos e Casting

| Tabela | Model | Destaques | FKs |
|---|---|---|---|
| `talents` | `Talent` | `full_name`, `artistic_name`, `phone`, `email_contact`, `birth_date`, `status` (`pending`\|`active`, indexado), `source`, `tags`, `skills`, medidas (`height_cm`, `clothing_size_top/bottom`, `shoe_size`), `passport_status`, `rg`, `cpf` (unique, nullable — estrangeiro grava `NULL`), `is_foreigner`, `pix_key`/`pix_key_secondary`, fotos (`photo_face_path`, `photo_full_path`, `doc_photo_path`), CNH, dados de carro, `notes`, `warning_level`, credenciais do portal (`password_hash`, `password_reset_token`, `terms_accepted_at`) | 1:N `media_items` |
| `talent_media` | `TalentMedia` | mídia do portfólio do talento | `talent_id` |
| `event_ratings` | `EventRating` | avaliação de talento por evento | `event_id`, `talent_id` |
| `event_sub_ratings` | `EventSubRating` | notas por critério/sujeito | `rating_id`, `subject_talent_id` |
| `event_rating_versions` | `EventRatingVersion` | versionamento das avaliações | `rating_id` |

### 2.4 Figurino

| Tabela | Model | Destaques | FKs |
|---|---|---|---|
| `figurino_sheets` | `FigurinoSheet` | `character_name`, `character_name_norm` (lowercase sem acentos), `photo_filename`, `pieces` (JSON `[{name, qty}]`), `tags` (JSON `["anjo","natal"]`, feature 183), `notes`, campos de sync do Drive (`drive_file_id` unique, `drive_url`, `thumbnail_url`, `last_synced_at`) | referenciada por `event_roles.figurino_sheet_id` e `catalog_characters.figurino_sheet_id` |
| `figurino_missing_dismissals` | `FigurinoMissingDismissal` | descarte de alerta "personagem sem ficha"; guarda os `event_role_ids` cobertos (JSON) — um `EventRole` novo faz o alerta reaparecer | `dismissed_by`→`users` |

Properties úteis: `pieces_list`, `pieces_count`, `tags_list`, `photo_url` (aceita URL absoluta,
caminho `/uploads/figurino_photos/...` ou fallback para `thumbnail_url` do Drive).

### 2.5 Catálogo (vitrine pública + gerenciador interno)

| Tabela | Model | Destaques | FKs |
|---|---|---|---|
| `catalog_items` | `CatalogItem` | **Tema** — `wp_product_id` (unique, dedupe da importação WordPress), `name`, `slug` (unique), `short_description_html`, `tags` (JSON), `is_active`, `imported_at`, **`video_url`** (feature 185 — Drive/MP4/Vimeo) | M:N `categories`; 1:N `images`, `characters` |
| `catalog_characters` | `CatalogCharacter` | **Personagem filho** (feature 185) — `name`, `slug` (unique, prefixado pelo slug do Tema), `photo_url`, `video_url`, `position`, `is_active` | `catalog_item_id`→`catalog_items` (**ON DELETE CASCADE**), **`figurino_sheet_id`→`figurino_sheets` (ON DELETE SET NULL)** |
| `catalog_item_images` | `CatalogItemImage` | `url`, `original_url`, `position` (**posição 0 = capa**, usada no Open Graph), `file_size_bytes` | `item_id` |
| `catalog_categories` | `CatalogCategory` | `name` (unique), `slug` (unique) | — |
| `catalog_item_categories` | *(association)* | PK composta | `item_id`, `category_id` |

> **`catalog_characters.figurino_sheet_id` é a coluna que materializa o vínculo bidirecional
> Catálogo ↔ Figurino** (feature 186). Não existe coluna espelho do lado de `figurino_sheets` — o
> "personagem vinculado" de uma ficha é derivado por busca inversa nessa mesma coluna.

### 2.6 Financeiro

| Tabela | Model | Destaques | FKs |
|---|---|---|---|
| `commission_payments` | `CommissionPayment` | `event_title` (**cópia**, sobrevive à exclusão do evento), `sale_date`, `payable_from` (EducaManto: só entra no ciclo após a realização), `amount` (`Numeric(12,2)`, **pode ser negativo = estorno**), `status` (`a_pagar`\|`pago`\|`cancelado`), `paid_at`, `notes`. Índices em `seller_id`, `event_id`, `status` | `event_id`→`calendar_events` (nullable), `seller_id`→`users`, `original_id`→`commission_payments` (auto-referência do estorno) |
| `salary_history` | `SalaryHistory` | `salary`, `payment_type` (`semanal`\|`quinzenal`\|`comissao`), `start_date`, `end_date` (`NULL` = vigente) | `user_id` |
| `salary_payments` | `SalaryPayment` | `due_date`, `amount`, `payment_status`, `paid_at`, `month_ref` (`YYYY-MM`); **UNIQUE (`user_id`,`due_date`)**; `advance_amount`/`advance_proof` são legado migrado para `salary_advances` | `user_id`, `salary_history_id` |
| `salary_advances` | `SalaryAdvance` | adiantamentos (N por pagamento) — reduzem o líquido a pagar, **não** o custo de salário do balanço | `salary_payment_id` |
| `special_expenses` | `SpecialExpense` | gastos extras com fluxo de aprovação e reembolso a funcionário | `created_by_id`, `approved_by_id`, `reimburse_user_id`, `event_id` |
| `recurring_expenses` | `RecurringExpense` | contas recorrentes | `created_by_id` |
| `recurring_expense_entries` | `RecurringExpenseEntry` | parcelas geradas da conta recorrente | `recurring_id`, `filled_by_id` |

### 2.7 Clientes, Formulários, Feedback e Orçamento

| Tabela | Model | Destaques | FKs |
|---|---|---|---|
| `clients` | `Client` | cadastro comercial | 1:N `events` |
| `form_responses` | `FormResponse` | respostas dos formulários públicos de pré-contrato (comum/corporativo) | `client_id`, `event_id` (ambos indexados e nullable) |
| `form_field_definitions` | `FormFieldDefinition` | editor de campos dos formulários (ordem, tipo, obrigatoriedade) | — |
| `client_feedbacks` | `ClientFeedback` | avaliação pública da cliente via `feedback_token` do evento | `event_id` |
| `orcamento_history` | `OrcamentoHistory` | histórico da calculadora de orçamento (vira `calendar_events.orcamento_history_id`) | `user_id` |

### 2.8 EducaManto

| Tabela | Model | FKs |
|---|---|---|
| `educamanto_packages` | `EducaMantoPackage` | 1:N `items` |
| `educamanto_items` | `EducaMantoItem` | `package_id` |
| `educamanto_quotes` | `EducaMantoQuote` | `user_id` |

### 2.9 Revisão de Mídia

| Tabela | Model | Destaques | FKs |
|---|---|---|---|
| `review_spaces` | `ReviewSpace` | espaço de revisão | `created_by` |
| `review_assets` | `ReviewAsset` | asset com status de aprovação | `space_id`, `uploaded_by` |
| `review_asset_versions` | `ReviewAssetVersion` | versionamento (replace) | `asset_id`, `uploaded_by` |
| `review_reviewers` | `ReviewReviewer` | revisores atribuídos ao espaço | `space_id`, `user_id` |
| `review_comments` | `ReviewComment` | comentários com resolução | `asset_id`, `user_id`, `resolved_by` |

### 2.10 Configuração global

`site_settings` (`SiteSetting`, **linha única id=1**) concentra: identidade visual
(`logo_path`, cores), `default_commission_rate`, `educamanto_seller_id`, `tax_rate`,
`fator_r_threshold`, `manto_address`, `departure_margin_minutes`, `google_maps_api_key`,
`clicksign_token`/`clicksign_sandbox`, `email_notifications_enabled`, `ratings_fully_anonymous`,
`release_date`, `google_token` (OAuth persistido para sobreviver a redeploy), `pricing_config`
(JSON da calculadora), `calendar_sync_cache`, `calendar_auto_sync_at`, `whatsapp_form_number`.

### 2.11 Migrations

- Alembic via Flask-Migrate, **sempre escritas à mão** (`migrations/versions/`).
- Head atual: **`9f1c3a7b5e2d`** — *catalog characters + video url* (feature 185).
- Cadeia recente: `27acb021e8d6` → `aa1bb2cc3dd4` (review asset status) → `7c2d9e4f1a3b`
  (figurino_missing_dismissals) → `4e6f8a1c2d5b` (figurino_sheet tags) → `9f1c3a7b5e2d`.
- Features **186** e **187** não geraram migration (reusaram colunas existentes).
- Produção aplica `flask db upgrade && python seed.py` no start (ver `railway.json`).

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

### 3.3 Agenda e Eventos — `agenda.py` (leitura) / `agenda_write.py` (escrita)
| Método | Rota |
|---|---|
| GET | `/api/agenda`, `/api/agenda/day/<date_str>`, `/api/talents`, `/api/events/<id>`, `/api/events/new/options`, `/api/events/new/prefill` |
| POST | `/api/events`, `/api/events/<id>/confirm`, `/api/events/<id>/observations`, `/api/events/<id>/sync`, `/api/events/<id>/roles`, `/api/events/<id>/invoices`, `/api/events/<id>/contracts`, `/api/events/<id>/payments`, `/api/events/<id>/reimbursements` |
| POST | `/api/roles/<id>/assign`, `/api/roles/<id>/invite`, `/api/roles/<id>/figurino-done`, `/api/roles/<id>/dismiss`, `/api/roles/<id>/restore` |
| POST | `/api/contracts/<id>/toggle-signed`, `/api/reimbursements/<id>/collect` |
| PATCH | `/api/events/<id>`, `/api/events/<id>/logistics`, `/api/payments/<id>` |
| DELETE | `/api/events/<id>`, `/api/roles/<id>`, `/api/observations/<id>`, `/api/contracts/<id>`, `/api/payments/<id>`, `/api/reimbursements/<id>` |

### 3.4 Talentos — `talents_read.py` / `talents_write.py`
`GET /api/talents/directory`, `/api/talents/character-suggestions`, `/api/talents/<id>`,
`/api/talents/<id>/ratings` · `PATCH /api/talents/<id>` ·
`POST /api/talents/<id>/{approve,reject,notes,photo}` · `DELETE /api/talents/<id>/photo`.
Avaliações: `GET /api/ratings` · `POST /api/ratings/modo-anonimo`.

### 3.5 Figurino — `figurino_read.py` / `figurino_write.py`
`GET /api/figurino` · `POST /api/figurino` · `PATCH|DELETE /api/figurino/<id>` ·
`POST|DELETE /api/figurino/<id>/photo` · `POST /api/figurino/<id>/photo/rotate` ·
`POST /api/figurino/faltantes/dispensar` · `POST /api/figurino/faltantes/associar`.

### 3.6 Financeiro — `financeiro_read.py` / `financeiro_write.py`
| Método | Rota | Nota |
|---|---|---|
| GET | `/api/vendas/pipeline` | pipeline de vendas |
| GET | `/api/financeiro/dashboard` | DRE / KPIs — **feature 189**: `kpis` inclui `margem_bruta`, `margem_ebitda`, `tax_rate` (alíquota do `SiteSetting`, rótulo dos impostos provisionados) e as faixas do Fator R (`fator_r_rate_low`/`fator_r_rate_high`); cada item de `eventos[]` inclui `receita` e `event_type` |
| GET | `/api/financeiro/comissoes` | **feature 187** — KPIs + `by_seller` + `entries` + `can_manage` + `sellers` |
| GET | `/api/financeiro/pagamentos` | planilha de pagamentos |
| POST | `/api/financeiro/comissoes/pagar-mes` | **feature 187** — liquidação em lote atômica |
| POST | `/api/financeiro/pagamentos/set-status`, `/bulk-action` | Status válidos: **`nao_pago` \| `pago` \| `no_banco`** (`_VALID_PAYMENT_STATUS`) — não existem `pendente`/`agendado`. `bulk-action` aceita os 3 + `delete`; itens `commission` não têm `no_banco` e voltam em `skipped` |
| POST | `/api/financeiro/pagamentos/salary/<sp_id>/advance`, `/salary/advance/<adv_id>/delete` | |
| GET | `/api/financeiro/pagamentos/export` | CSV |

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
`GET /api/clientes/`, `/api/clientes/search`, `/api/clientes/<id>`, `/api/clientes/avaliacoes` ·
`POST /api/clientes/quick-create` · `PATCH|DELETE /api/clientes/<id>`.

### 3.9 Catálogo público (anônimo) — `catalogo_read.py`
`GET /api/catalogo`, `/api/catalogo/categorias`, `/api/catalogo/categoria/<slug>`,
`/api/catalogo/<slug>` · **`GET /api/catalogo/elenco-busca`** (autenticado —
`COMERCIAL`/`FIGURINO`/`SUPERADMIN`; devolve Temas + Personagens com `photo_url` e
`figurino_sheet_id`; alimenta a busca visual de elenco e o vínculo pelo lado da Ficha).

### 3.10 Gerenciador de catálogo — `admin_catalogo_read.py` / `admin_catalogo_write.py`
| Método | Rota |
|---|---|
| GET | `/api/admin/catalogo`, `/api/admin/catalogo/<item_id>`, `/api/admin/catalogo/tags` |
| POST | `/api/admin/catalogo`, `/api/admin/catalogo/categorias`, `/api/admin/catalogo/<item_id>/toggle-ativo` |
| PATCH/DELETE | `/api/admin/catalogo/<item_id>` |
| POST | `/api/admin/catalogo/<item_id>/personagens` |
| PATCH/DELETE | `/api/admin/catalogo/personagens/<character_id>` |
| POST | **`/api/admin/catalogo/personagens/mover-em-massa`** (feature 186) |

Ops: `app/admin/catalog_ops.py`, `app/admin/catalog_character_ops.py`
(`unique_character_slug`, `create_character`, `update_character`, `delete_character`,
`move_characters`, validação de `video_url` e de extensão de foto).

### 3.11 Administração — usuários e configuração
`admin_users_read/write.py`: `GET /api/admin/users`, `/api/admin/users/<id>` ·
`POST /api/admin/users` (+ `/<id>/salary`, `/grant-access`, `/reset-password`) ·
`PATCH /api/admin/users/<id>`, `/<id>/pix` · `DELETE /api/admin/users/<id>`.

`admin_config_read/write.py`: `GET /api/admin/settings`, `/logs`, `/desempenho`, `/sync-status`,
`/migrar-arquivos/status`, `/importar-catalogo/status` · `PATCH /api/admin/settings` ·
`POST /api/admin/sync/run`, `/portal-announcement`, `/migrar-arquivos/start`,
`/importar-catalogo/start`.

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

EducaManto: `GET /api/educamanto/{historico,packages,distancia}` ·
`POST /api/educamanto/calcular`, `/packages`, `/packages/<id>/duplicate`, `/orcamento/gerar` ·
`PATCH|DELETE /api/educamanto/packages/<id>` · `GET /api/educamanto/orcamento/<id>/pdf`.
**Novo na feature 190**: `GET /api/educamanto/historico/<id>` — snapshot bruto (`d1`, `d2`,
`ensemble`, `acrescimo`, `transporte`, `client_name`, `packages`) de um orçamento salvo em JSON
(mesmo dado já usado para regerar o PDF, agora também exposto para "Ver" e "Recalcular"); mesmo
RBAC de uso do EducaManto (`_require_use`), sem restrição por dono.

### 3.14 Superfícies públicas (sem login)
`GET /api/cadastro/check-cpf` · `POST /api/cadastro` ·
`GET /api/formularios/<form_type>/schema` · `POST /api/formularios/<form_type>` ·
`GET|POST /api/avaliar/<token>` (feedback da cliente).
Admin dos formulários: `formularios_admin_read/write.py`
(`/api/formularios/respostas*`, `/api/formularios/editor/*`). O `_response_summary` de
`GET /api/formularios/respostas` e `…/respostas/search` inclui **`client_name`** (nome do cliente
vinculado ou `null`) — a coluna "Situação" da tela `/formularios` mostra o badge
"Cliente: `<nome>`" sem abrir o detalhe; `list_responses`/`search_responses` fazem `joinedload`
do cliente para não gerar N+1.

`GET /api/gastos/eventos?date=YYYY-MM-DD` (seletor de vínculo de evento, consumido tanto por
Gastos Extras quanto pelo detalhe de resposta em `/formularios`) respondia **500 no Postgres** até
a feature 188 — `gastos_ops.search_events_by_date` comparava `func.date(start_at)` com uma string.
Corrigido para comparar com o objeto `date`.

### 3.15 Portal do Artista (API parcial, UI ainda Jinja)
`POST /api/portal/auth/login`, `/logout` · `GET /api/portal/auth/me` ·
`GET /api/portal/agenda` · `POST /api/portal/invites/<role_id>/{accept,reject}` ·
`POST /api/portal/roles/<role_id>/ack-change` ·
`GET /api/portal/events/<event_id>/figurino` ·
`POST /api/portal/profile/{photo,document}`.

### 3.16 Rotas Jinja legadas ainda registradas
`app/__init__.py` registra, além de `api_bp`: `auth_bp` (`/auth`), `rh_bp` (`/rh`),
`admin_bp` (`/admin`), `calendar_bp`, `talents_bp`, `financeiro_bp`, `figurino_bp`,
`portal_bp`, `orcamento_bp`, `educamanto_bp`, `gastos_bp`, `cadastro_bp`, `revisao_bp`,
`clientes_bp`, `formularios_bp`, `feedback_bp`, `catalogo_bp`.

Rotas legadas que **ainda têm uso real** (não são só resíduo):
- `GET /figurinos/<id>/print` e `GET /figurinos/print-event/<event_id>` — impressão de ficha.
- `GET /catalogo/midia/<path:filename>` — serve as fotos do catálogo público **sem login**.
- Todo o `app/talent_portal` — Portal do Artista.

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
| `ENSAIO` | Agenda + EducaManto (leitura/uso) |
| `MARKETING` | Cria espaços de revisão de mídia |
| `REVENDEDOR_EDUCAMANTO` | Perfil restrito: **só** Agenda (visualização) + EducaManto |

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
| `_require_superadmin()` | `admin_catalogo_*`, `admin_config_*`, `orcamento_read` | `SUPERADMIN` |
| `_require_users_access()` | `admin_users_*` | `SUPERADMIN`, `FINANCEIRO` |
| `_can_create_event()` / `_can_edit_event()` / `_can_delete()` | `agenda_write` (delegam para `_CAN_CREATE`/`_CAN_EDIT_EVENT`/`_CAN_DELETE` de `app/calendar/routes.py`) | `COMERCIAL`, `SUPERADMIN` |
| `_can_casting()` | `agenda_write` (remover cargo) | `CASTING`, `SUPERADMIN` |
| `_can_manage_sale()` | `agenda_write` (nota fiscal) | `COMERCIAL`, `FINANCEIRO`, `SUPERADMIN` |
| `_can_confirm()` | `agenda_write` | `COMERCIAL`, `SUPERADMIN` |
| `_is_superadmin()` | dispensar/restaurar cargo, excluir ficha | `SUPERADMIN` |
| `_can_edit_figurino()` | `figurino_write` | `FIGURINO`, `SUPERADMIN` |
| `_can_edit_talent()` | `talents_read/write` | `CASTING`, `SUPERADMIN` |
| `_can_view_vendas(settings)` | `financeiro_read` | `COMERCIAL`, `FINANCEIRO`, `SUPERADMIN` **ou** responsável EducaManto |
| `_require_financeiro()` | `financeiro_write`, `gastos_*` | `FINANCEIRO`, `SUPERADMIN` |
| `_require_vendas()` | `clientes_*`, `formularios_admin_read`, `orcamento_read` | `COMERCIAL`, `FINANCEIRO`, `SUPERADMIN` |
| `_has_role(COMERCIAL, FIGURINO, SUPERADMIN)` | `catalogo_read.api_catalogo_elenco_busca` | busca visual de elenco / vínculo de ficha |
| `_require_use()` / `_require_manage()` | `educamanto_*` | uso: `COMERCIAL`, `SUPERADMIN`, `ENSAIO`, `REVENDEDOR_EDUCAMANTO`; gestão: `COMERCIAL`, `SUPERADMIN` |

### 4.4 Escopo de dados no servidor (não confiar no cliente)

Padrão consolidado na feature 187 e que deve ser replicado: **o servidor decide o escopo**.
Em `GET /api/financeiro/comissoes`, `seller_filter = requested_seller_id if can_manage else
current_user.id` — um vendedor comum recebe apenas os próprios dados, independentemente do
`seller_id` enviado na querystring. `POST /api/financeiro/comissoes/pagar-mes` responde **403**
para quem não é `FINANCEIRO`/`SUPERADMIN`, inclusive para o próprio ID.

### 4.5 RBAC no frontend
`frontend/apps/internal/src/lib/navigation.tsx` é a config declarativa da navegação, portada de
`app/templates/base.html`, com `isVisible(user)` por item. **Isso é apenas conveniência de UI** —
a autorização real está sempre no servidor.

---

## 5. Arquitetura de Build e Deploy (Railway)

### 5.1 Monorepo do frontend
```
frontend/                       npm workspaces
├── apps/internal/              ERP (staff)      → dev: npm run dev:internal  (porta 5174)
├── apps/public/                Vitrine anônima  → dev: npm run dev:public    (porta 5175)
├── apps/portal/                scaffold vazio (Portal do Artista NÃO migrado)
├── packages/{ui,api-client,money}   consumidos direto do TS-fonte (sem build próprio)
└── server.js                   servidor estático único dos DOIS SPAs
```

Os pacotes compartilhados não têm build próprio: são resolvidos por alias do Vite + `paths` do
`tsconfig.base.json` e compilados junto com cada app — não há ordem de build a orquestrar.

### 5.2 Dual-SPA em um único serviço (feature 186, US6)

`frontend/server.js` substitui o antigo `serve --single` (que só conhece **um** `index.html` de
fallback). Usa `serve-handler` programaticamente, uma vez por app, cada um com seu próprio
fallback de SPA — deep link e refresh funcionam nos dois:

| URL pública | Diretório servido | Fallback |
|---|---|---|
| `/*` | `frontend/apps/internal/dist` | `index.html` do interno |
| `/catalogo`, `/catalogo/*`, `/catalogo?*` | `frontend/apps/public/dist` (prefixo removido de `req.url`) | `index.html` do público |

Coerência de assets: `apps/public/vite.config.ts` usa `base: "/catalogo/"` **apenas em produção**;
`apps/public/src/App.tsx` usa `basename = import.meta.env.PROD ? "/catalogo" : undefined`. Em dev
tudo continua na raiz.

### 5.3 Serviços no Railway

**Serviço backend** (raiz do repo — `railway.json` + `nixpacks.toml`):
```
flask db upgrade && python seed.py && gunicorn run:app \
  --workers 3 --worker-class gthread --threads 4 --bind 0.0.0.0:$PORT --timeout 120
```
Healthcheck: `/health`. `sync_worker.py` não roda durante o build da imagem.

**Serviço frontend** (`Root Directory = frontend` — `frontend/railway.json` +
`frontend/nixpacks.toml`):
- setup: `nodejs_20` · install: `npm ci` · build: `npm run build` (compila **internal e public**)
- start: `npm run start` → `node server.js`

> ⚠️ Um *Build Command* / *Start Command* customizado no painel do Railway **tem precedência**
> sobre o `nixpacks.toml`. Os dois campos precisam ficar vazios.

### 5.4 Dev local

| Alvo | Comando |
|---|---|
| Backend (SQLite casual) | `python run.py` |
| Backend contra a cópia real | `.\scripts\db\run-local.ps1` (aponta `DATABASE_URL` para `manto_local`) |
| Frontend staff | `cd frontend && npm run dev:internal` |
| Frontend público | `cd frontend && npm run dev:public` |
| Typecheck | `npx tsc --noEmit` dentro de `apps/internal` ou `apps/public` |

Proxies do Vite dev:
- `apps/internal`: `/api` e `/uploads` → `http://localhost:5000`; `^/figurinos/\d+/print$`
  (regex escopada — **nunca** proxiar o prefixo `/figurinos` inteiro, senão a rota SPA homônima
  é sequestrada).
- `apps/public`: `/api` e `/catalogo/midia` → `http://localhost:5000`.

> **Regra de teste**: produção é PostgreSQL. Toda verificação funcional roda contra `manto_local`
> (Postgres), **nunca** contra o SQLite vazio — o SQLite não pega bugs Postgres-only
> (ex.: `float − Decimal` no financeiro).
