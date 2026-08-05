# 01 — Sistema e Banco de Dados

> **Documento vivo.** Atualizado obrigatoriamente ao fim de cada feature (ver regra em
> `CLAUDE.md` → "REGRA OBRIGATÓRIA DE DOCUMENTAÇÃO VIVA").
>
> Última atualização: **2026-08-05** · Estado do repositório: pós-hotfix **210 (horário, anexos e
> orçamento)** · Head de migration: `e7a1c94f20b3` (*own_item_id em catalog_characters*)
>
> **Contrato de horário (210, não-negociável).** `CalendarEvent.start_at`/`end_at` são **horário de
> parede de São Paulo**, gravados naive (`service.py::parse_event_datetime`) e serializados com
> `.isoformat()` — o ISO que a API devolve **não tem fuso e não é um instante UTC**. No React, para
> preencher formulário ou comparar datas, use `lib/horaLocal.ts` (recorte de string); passar por
> `new Date(iso).toISOString()` desloca +3h e regrava o evento errado no banco e no Google Agenda.
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

### 2.2.1 Impressões e Acervo 3D (features 200, 201 e 202)

| Tabela | Model | Destaques | FKs |
|---|---|---|---|
| `acervo_3d_items` | `Acervo3DItem` | catálogo de peças base: `name`, `photo_url` (**NOT NULL** — foto JPG/PNG de preview), `is_active`, `created_at` | — |
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
| `clients` | `Client` | cadastro comercial; identidade = `phone` normalizado (`NOT NULL UNIQUE`, só dígitos com DDI). `source` ∈ `kommo_import` \| `manual` \| `whatsform_import` (feature 193) | 1:N `events` |
| `form_responses` | `FormResponse` | respostas dos formulários públicos de pré-contrato (`form_type` ∈ `comum` \| `corporativo`) **e** o histórico do WhatsForm importado na feature 193 | `client_id`, `event_id` (ambos indexados e nullable) |
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
(`logo_path`, cores), `default_commission_rate`, `educamanto_seller_id`, `tax_rate`,
`fator_r_threshold`, `manto_address`, `departure_margin_minutes`, `google_maps_api_key`,
`clicksign_token`/`clicksign_sandbox`, `email_notifications_enabled`, `ratings_fully_anonymous`,
`release_date`, `google_token` (OAuth persistido para sobreviver a redeploy), `pricing_config`
(JSON da calculadora), `calendar_sync_cache`, `calendar_auto_sync_at`, `whatsapp_form_number`.

### 2.11 Migrations

- Alembic via Flask-Migrate, **sempre escritas à mão** (`migrations/versions/`).
- Head atual: **`b7d4f81a6e0c`** — *marketing posts com multiplos temas do catalogo* (feature 204b).
- Cadeia recente: `27acb021e8d6` → `aa1bb2cc3dd4` (review asset status) → `7c2d9e4f1a3b`
  (figurino_missing_dismissals) → `4e6f8a1c2d5b` (figurino_sheet tags) → `9f1c3a7b5e2d`
  (catalog characters) → `c8d2f4a6b013` (impressões 3D) → `d9e3a5b7c124` (multi-arquivos)
  → `e4f7b2c9a350` (pendência 3D por evento) → `a3c7e1d59f42` (marketing) → `b7d4f81a6e0c`
  (marketing multi-Tema).
- Features **186**, **187**, **199** e **203** não geraram migration (reusaram colunas existentes).
- Os papéis `ARTISTA_3D` e `MARKETING` **não** vêm por migration: papéis são linhas de `roles`
  semeadas por `seed.py` (mesmo tratamento de `REVENDEDOR_EDUCAMANTO`), e o Railway roda
  `flask db upgrade && python seed.py` no start.
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
| POST | `/api/roles/<id>/payment-status`, `/api/roles/<id>/figurino-sheet` *(feature 192)* |
| POST | `/api/events/<id>/travel-estimate`, `/api/events/<id>/materials`, `/api/events/<id>/feedback-link` *(feature 192)* |
| POST | `/api/contracts/<id>/toggle-signed`, `/api/reimbursements/<id>/collect` |
| PATCH | `/api/events/<id>`, `/api/events/<id>/logistics`, `/api/payments/<id>` |
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
> figurino-done DELETE, travel-estimate) · `_CAN_ENSAIO_MATERIAL` (materials) ·
> Comercial/Superadmin (feedback-link).

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
| GET | `/api/vendas/pipeline` | **Dashboard Comercial** (feature 196 — o payload plano do "pipeline" da 156 deixou de existir). Aceita `period` (`este_mes`/`mes_anterior`/`30d`/`custom`+`start`/`end`) e `seller_id`. Devolve `kpis` (`total_vendido`, `ticket_medio`, `eventos_fechados`, `comissao_prevista`, `desconto_concedido`), `eventos[]` (venda, cliente, contrato, cobrança, vendedor — **sem custo e sem lucro**), `can_filter_seller`, `scope_label` e `sellers` (só gestor). Núcleo em `app/financeiro/vendas_ops.py`. **Feature 205**: vendas da Loja Virtual (`event_type='VIRTUAL'`) saem do funil por padrão e voltam com `?incluir_loja_virtual=1`; o consolidado do canal vem em `loja_virtual` **só para gestor** (`can_filter_seller`) |
| POST | `/api/virtuais/pedidos/<id>/avisos/<kind>/reenviar` | **Feature 205f**: reentrega um aviso automático que falhou (FR-039c). Só age sobre aviso já registrado e **falhado** — reenviar um entregue dá 400, para não mandar um segundo e-mail à família. Gate: `COMERCIAL`/`SUPERADMIN` |
| GET | `/api/financeiro/dashboard` | DRE / KPIs — **feature 189**: `kpis` inclui `margem_bruta`, `margem_ebitda`, `tax_rate` (alíquota do `SiteSetting`, rótulo dos impostos provisionados) e as faixas do Fator R (`fator_r_rate_low`/`fator_r_rate_high`); cada item de `eventos[]` inclui `receita` e `event_type`. **Feature 205**: a receita virtual continua na cascata da DRE (Fator R e break-even exatos) mas sai de `ticket_medio` e `a_receber_clientes`; `paineis.loja_virtual` traz o consolidado do canal e `?incluir_loja_virtual=1` reincorpora o canal aos indicadores de evento (FR-055) |
| GET | `/api/financeiro/comissoes` | **feature 187** — KPIs + `by_seller` + `entries` + `can_manage` + `sellers` |
| GET | `/api/financeiro/pagamentos` | planilha de pagamentos |
| POST | `/api/financeiro/comissoes/pagar-mes` | **feature 187** — liquidação em lote atômica |
| POST | `/api/financeiro/pagamentos/set-status`, `/bulk-action` | Status válidos: **`nao_pago` \| `pago` \| `no_banco`** (`_VALID_PAYMENT_STATUS`) — não existem `pendente`/`agendado`. **Feature 199**: os 3 status valem para TODOS os tipos de item (`cache`/`salary`/`expense`/`bv`/`commission`/`recurring`), inclusive `bulk-action`; `_build_commission_items`/`_build_recurring_items` (`app/financeiro/routes.py`) passaram a incluir `no_banco` no filtro de leitura — antes esses itens sumiam da planilha ao virar `no_banco` |
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
| `DELETE` | `/api/3d/acervo/<id>` | Exclui a peça e seus arquivos. **400** se houver evento vinculado. |
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
- **Ainda não implementado**: segregação financeira (FR-052–055) e o fechamento do ciclo.

### 3.14 Superfícies públicas (sem login)
`GET /api/cadastro/check-cpf` · `POST /api/cadastro` ·
`GET /api/formularios/<form_type>/schema` · `POST /api/formularios/<form_type>` ·
`GET|POST /api/avaliar/<token>` (feedback da cliente) ·
`GET /api/virtuais/campanhas/<slug>` e `.../horarios` (feature 205).
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
`must_change_password`, `terms_accepted` e `pending_steps`) ·

> `must_redirect_to_classic` **saiu do payload do login na 206**. Virou sempre `false` na 191
> (troca de senha e aceite de termos passaram a ser telas React, guiadas por `pending_steps`) e
> foi removido junto com `portal_ops.needs_classic_portal_flow`, que já era código morto — o
> talento entra sempre no portal React.

`POST /api/portal/auth/first-access` (senha temporária por e-mail) ·
`POST /api/portal/auth/forgot-password` (silencioso — nunca revela se a conta existe) ·
`GET /api/portal/auth/reset-password/<token>` (valida o token) ·
`POST /api/portal/auth/reset-password` · `POST /api/portal/auth/change-password` ·
`POST /api/portal/auth/accept-terms`.

**Agenda, convites e figurino**
`GET /api/portal/agenda` · `POST /api/portal/invites/<role_id>/{accept,reject}` ·
`POST /api/portal/roles/<role_id>/ack-change` ·
`GET /api/portal/events/<event_id>/figurino`.

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
que muda conteúdo grava a versão anterior em `EventRatingVersion` (feature 181).

**Núcleo de negócio** (fonte única, reusada pelo Jinja legado): `app/talent_portal/portal_ops.py`
(agenda, convites, figurino, uploads, perfil, portfólio, histórico),
`portal_account_ops.py` (credenciais e termos) e `portal_rating_ops.py` (avaliações).

### 3.16 Rotas Jinja legadas ainda registradas
`app/__init__.py` registra, além de `api_bp`: `auth_bp` (`/auth`), `rh_bp` (`/rh`),
`admin_bp` (`/admin`), `calendar_bp`, `talents_bp`, `financeiro_bp`, `figurino_bp`,
`portal_bp`, `orcamento_bp`, `educamanto_bp`, `gastos_bp`, `cadastro_bp`, `revisao_bp`,
`clientes_bp`, `formularios_bp`, `feedback_bp`, `catalogo_bp`.

Rotas legadas que **ainda têm uso real** (não são só resíduo):
- `GET /figurinos/<id>/print` e `GET /figurinos/print-event/<event_id>` — impressão de ficha.
  Só a **primeira** é linkada pelo React (`FigurinoListPage.tsx`) e, por isso, só ela está no
  proxy de `server.js`; a `print-event` continua sendo link interno de página Jinja.
- `GET /catalogo/midia/<path:filename>` — serve as fotos do catálogo público **sem login**.
- `GET /portal/photo/<path:filename>` — foto de figurino que `GET /api/portal/events/<id>/figurino`
  devolve para o portal React; é rota Jinja, mas checa a mesma sessão de talento.
- Todo o resto do `app/talent_portal` — Portal do Artista Jinja.

**A `home()` Jinja saiu (feature 206).** A rota `/` do Flask não renderiza mais `home.html`:
devolve **301 para `PLATFORM_BASE_URL`** (`app/config.py`), para capturar acesso residual direto
ao serviço do backend. Quem serve `/` é o `frontend/server.js`. O `dashboard_service.py` continua
sendo fonte única — agora com um consumidor só, `/api/dashboard`.

> ⚠️ **Blocos de tarefa que existiam só na home Jinja não têm equivalente em `/api/dashboard`**:
> reembolsos pendentes, ensaios pendentes/agendados/órfãos, presença pendente, notas fiscais a
> emitir, eventos sem valor, eventos sem cliente e pré-contratos sem cliente / que precisam de
> revisão. O template `app/templates/home.html` ficou órfão. Reconstruí-los no React é trabalho
> em aberto, não coberto pela 206.

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
| `MARKETING` | Cria espaços de revisão de mídia e opera o **módulo de Marketing** (feature 204): painel de postagens e metas de frequência, com leitura dos Temas ativos do catálogo (via `/api/marketing/opcoes`, sem acesso à gestão do catálogo) |
| `ARTISTA_3D` | Gestão total do módulo 3D (Acervo + Fila + presentes do evento) e **leitura** dos eventos — precisa do elenco e do formulário de pré-contrato para saber o que imprimir |
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
| `require_3d_access()` | `impressoes3d_read/write` | `ARTISTA_3D`, `SUPERADMIN` |
| `require_marketing_access()` | `marketing_read/write` | `MARKETING`, `SUPERADMIN` |

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

## 5. Arquitetura de Build e Deploy (Railway)

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
`BACKEND_URL` (variável do serviço frontend no Railway; default `http://localhost:5000`).

| Filtro | Por que existe |
|---|---|
| `/api/*` | toda a API JSON (`@manto/api-client`) |
| `/uploads/*` | mídia de `app/storage.py`; é o que `assetUrl()` devolve |
| `/catalogo/midia/*` | fotos públicas do catálogo — casa **antes** do mount `/catalogo` |
| `/portal/photo/*` | foto de figurino do portal (Jinja, mesma sessão do talento) — **antes** do mount `/portal` |
| `/google/*` | callback do OAuth do Google Calendar (`app/calendar/routes.py`), rota Jinja com `redirect_uri` fixo no Google Console |
| `/cadastro/*`, `/avaliar/*` | superfícies públicas por link já distribuído (cadastro de talentos, feedback da cliente) — hotfix 206b; sem elas o link caía no login do ERP |
| `/f/*` | **não vai ao Flask**: endereço canônico dos formulários públicos, 302 → `/catalogo/f/<slug>` (formulário React da vitrine), query preservada |
| `/static/*` | CSS/JS das páginas Jinja públicas acima (bundles Vite usam `/assets` — sem colisão) |
| `/figurinos/<id>/print`, `/figurinos/print-event/<id>` | páginas Jinja de impressão que a SPA interna linka; regex restrito ao sub-path |

> ⚠️ **`BACKEND_URL` precisa do esquema.** `mantoplatform.railway.internal` (como o painel do
> Railway exibe o domínio privado) fazia o `http-proxy` estourar `TypeError` **síncrono** dentro
> de `proxy.web`, fora do callback de erro — exceção não capturada que **matava o processo a cada
> chamada de API**. `resolveBackendUrl` agora normaliza e valida, e `proxy.web` roda em
> `try/catch`; valor inválido vira 502 com os SPAs de pé. Ainda assim, defina explicitamente:
> `https://mantoplatform-production.up.railway.app`.
>
> A rede privada (`http://mantoplatform.railway.internal:<porta>`) **não funciona hoje**: o
> gunicorn sobe com `--bind 0.0.0.0` (só IPv4) e a rede privada do Railway é IPv6-only. Para
> migrar para ela, troque o bind para `[::]:$PORT` em `railway.json` e `nixpacks.toml`.

### 5.2.2 Domínios e roteamento por host (feature 206)

Os **três** domínios customizados apontam para o serviço `manto-frontend-internal` (porta 8080). O
serviço do Flask não tem domínio próprio: é alcançado só pelo `mantoplatform-production.up.railway.app`
que o proxy usa como `BACKEND_URL`.

| Domínio | Raiz entrega | Observação |
|---|---|---|
| `app.mantoproducoes.com.br` | `apps/internal` (ERP) | URL principal da plataforma |
| `beta.mantoproducoes.com.br` | `apps/internal` (ERP) | endereço histórico, mesmo conteúdo |
| `portal.mantoproducoes.com.br` | **302 → `/portal/`** | endereço que os talentos conhecem |

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

> ⚠️ **Domínio removido do Railway = certificado curinga + HSTS.** Quando `portal.*` deixou de
> estar cadastrado, a borda passou a apresentar o certificado `*.up.railway.app`, que não cobre o
> host — e, com HSTS ativo, o browser nem oferece exceção. O diagnóstico rápido é ler o **SAN** do
> certificado: `*.up.railway.app` significa "o Railway não reconhece este hostname" (cadastro
> ausente ou CNAME apontando para o alvo antigo), e não "Let's Encrypt ainda emitindo". Cada
> domínio customizado recebe um alvo de CNAME único — ao recadastrar, o CNAME **precisa** ser
> atualizado para o novo valor.

Os filtros espelham os `server.proxy` dos três `vite.config.ts`, inclusive `changeOrigin: true` —
sem ele, um `BACKEND_URL` de domínio público faria o roteador de borda do Railway devolver a
requisição para o próprio serviço frontend, em laço. `xfwd: true` envia os `X-Forwarded-*`. Falha
de conexão com o backend responde **502**, sem derrubar os SPAs.

> ⚠️ **O proxy só entra em ação com `VITE_API_BASE_URL` vazia no build.** Com ela preenchida,
> `API_BASE`/`assetUrl()` geram URL absoluta do Flask e o browser fura o proxy — inclusive para
> `/uploads` e `/figurinos/<id>/print`.

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
- variáveis: `BACKEND_URL` (origem do Flask, ver §5.2.1) e `VITE_API_BASE_URL` **vazia** no build

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
