---
description: "Task list for feature implementation"
---

# Tasks: Loja de Interações Virtuais

**Input**: Design documents from `/specs/205-loja-interacoes-virtuais/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/virtuais-api.md](./contracts/virtuais-api.md), [quickstart.md](./quickstart.md)

**Tests**: incluídos e **obrigatórios**. O Princípio VIII da constituição exige que os scripts de
verificação funcional sejam escritos **antes** da implementação do núcleo de negócio. Cada cenário
V1–V9 do [quickstart.md](./quickstart.md) tem tarefa própria, ordenada antes do código que valida.

**Organization**: agrupadas por user story, para cada uma ser implementável e verificável sozinha.

> **Regra monetária (Princípio IX, plan.md)**: toda coluna de dinheiro é `Numeric(12,2)`, o Python
> opera em `Decimal`, o JSON trafega reais decimais, e **centavos só existem dentro de**
> `app/integracoes/infinitepay_client.py`. No React, exibir e digitar dinheiro é exclusivamente via
> `@manto/money`. Vale para todas as tarefas abaixo, sem exceção.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivo diferente, sem dependência pendente)
- **[Story]**: a qual user story pertence (US1–US5)
- Todo caminho de arquivo é relativo à raiz do repositório

---

## Phase 1: Setup

- [X] T001 Confirmar que `manto_local` está no ar e é cópia do banco de produção rodando `.\scripts\db\run-local.ps1` (nenhuma verificação desta feature pode rodar contra o SQLite de `instance/`)
- [X] T002 [P] Criar o pacote `app/integracoes/` com `__init__.py` vazio
- [X] T003 [P] Criar `specs/205-loja-interacoes-virtuais/verify_205.py` com o esqueleto (login SUPERADMIN, helpers de request, runner de cenários) no padrão dos `verify_*.py` anteriores
- [X] T004 Adicionar em `app/models.py` os campos novos de `SiteSetting`: `infinitepay_handle` e `infinitepay_webhook_token`

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: nenhuma user story começa antes desta fase fechar.

### Constantes e modelos

- [X] T005 Adicionar em `app/constants.py` as constantes da feature: `EVENT_TYPE_VIRTUAL`, modalidades, ciclos de vida de campanha/slot/pedido, os três status de produção (`pendente`/`gravando`/`finalizado`), `VIRTUAL_SOFT_LOCK_MINUTES`, `VIRTUAL_SLOT_MINUTES`, `VIRTUAL_RETRY_MAX_ATTEMPTS`, `VIRTUAL_RETRY_INTERVAL_MIN`, `VIRTUAL_VIDEO_MAX_BYTES` e `VIRTUAL_ACCESS_SESSION_MIN` (ver [data-model.md](./data-model.md))
- [X] T006 Criar em `app/models.py` o modelo `VirtualCampaign` com os preços em `Numeric(12,2)` (`price_live`, `price_recorded`, `price_gift`) — nenhuma coluna `*_cents` (data-model §1)
- [X] T007 Criar em `app/models.py` o modelo `VirtualCampaignSlot` com `UNIQUE(campaign_id, start_at)` e índices de `status`/`start_at`
- [X] T008 Criar em `app/models.py` o modelo `VirtualOrder` com valores congelados em `Numeric(12,2)` (`price_interaction`, `price_gift`, `total_value`), `UNIQUE(order_nsu)`, `UNIQUE(public_token)`, os campos de tolerância (`grace_until`, `recheck_attempts`, `expired_unverified`) e os de acesso (`access_attempts`, `access_blocked_until`)
- [X] T009 [P] Criar em `app/models.py` o modelo `VirtualPaymentNotification` com `UNIQUE(transaction_nsu)`
- [X] T010 [P] Criar em `app/models.py` o modelo `VirtualMediaDelivery` com `UNIQUE(order_id)` e `video_path`/`video_mime`/`video_size_bytes`
- [X] T011 [P] Criar em `app/models.py` o modelo `VirtualRefundRequest` com `amount` em `Numeric(12,2)`
- [X] T012 [P] Criar em `app/models.py` a associação `virtual_campaign_acervo`
- [X] T013 [P] Criar em `app/models.py` o modelo `VirtualOrderNotification` com **`UNIQUE(order_id, kind)`** — é a trava de idempotência de aviso (FR-028a)
- [X] T014 Escrever à mão a migration `migrations/versions/<rev>_loja_interacoes_virtuais.py` com `down_revision = "b7d4f81a6e0c"`, criando as 7 tabelas com colunas monetárias `Numeric(12,2)`, as restrições únicas e os campos novos de `SiteSetting`
- [X] T015 Aplicar `flask db upgrade` contra `manto_local` e conferir que as tabelas `virtual_*` existem e que nenhuma coluna monetária é `Integer`

### Cliente da operadora e RBAC

- [X] T016 Implementar `app/integracoes/infinitepay_client.py` com `criar_link_pagamento(total: Decimal, ...)` e `consultar_pagamento()`, sem importar Flask — **este é o único arquivo que conhece centavos**: converte `Decimal` → centavos na saída e `paid_amount` → `Decimal` na entrada (contracts §6, Princípio IX)
- [X] T017 Implementar em `infinitepay_client.py` a distinção entre **não pago** (decisão de negócio) e **indisponível** (`timeout`/`5xx` → retido para nova tentativa), com exceções próprias (FR-027d)
- [X] T018 [P] Adicionar em `app/constants.py` o papel/permissão de gestão de campanhas virtuais e criar o gate `require_virtuais_access()` reutilizável (Princípio III — RBAC é função chamada no início da view)
- [X] T019 Criar os módulos de rota vazios `app/api/virtuais_public.py`, `app/api/virtuais_read.py`, `app/api/virtuais_write.py` e `app/api/virtuais_webhook.py`, e registrá-los em `app/api/__init__.py`
- [X] T020 Criar `app/marketing/virtuais_ops.py` com a exceção de validação `VirtuaisValidationError(field, message)` no padrão de `Impressao3DValidationError`

**Checkpoint**: banco migrado com dinheiro em `Numeric`, cliente da operadora isolado, blueprints registrados.

---

## Phase 3: User Story 1 — Admin monta e publica uma campanha (P1) 🎯 MVP

**Goal**: a equipe monta a oferta e publica; a landing existe com os dados configurados.

**Independent Test**: criar campanha, gerar horários, publicar, abrir a URL pública no celular — tudo
sem nenhuma venda existir.

### Verificação primeiro

- [X] T021 [US1] Escrever o cenário **V1** em `verify_205.py`: campanha nasce rascunho, geração de horários é idempotente (2ª execução → `skipped`), publicação libera o endereço público, remoção de slot vendido dá 409

### Núcleo

- [X] T022 [US1] Implementar em `app/marketing/virtuais_ops.py` o CRUD de campanha (`criar_campanha`, `atualizar_campanha`, `alterar_status`) validando personagem ativo e campos obrigatórios de publicação (FR-001, FR-002, FR-003, FR-007)
- [X] T023 [US1] Implementar `gerar_slots(campaign, date, start, end)` criando janelas de 10 min e ignorando as já existentes, devolvendo `(created, skipped)` (FR-004)
- [X] T024 [US1] Implementar `remover_slot()` bloqueando slot reservado ou vendido com mensagem explicativa (FR-008)
- [X] T025 [US1] Implementar `definir_acervo_liberado(campaign, item_ids)` sobre a associação (FR-006)
- [X] T026 [US1] Implementar `serialize_campaign()` e `serialize_campaign_admin()` como fonte única dos payloads, com valores em reais decimais e incluindo vendidos, faturado, horários restantes **e capacidade de vídeo consumida vs total** (FR-005, FR-009)

### API

- [X] T027 [US1] Implementar em `app/api/virtuais_write.py` os endpoints de criação, edição, publicação, acervo liberado, geração e remoção de horários (contracts §3), com gate de RBAC e `json_error` com `fields`
- [X] T028 [US1] Implementar em `app/api/virtuais_read.py` a listagem e o detalhe administrativo das campanhas

### Frontend interno

- [X] T029 [P] [US1] Criar `frontend/apps/internal/src/lib/virtuais.ts` com os tipos TypeScript e as funções de API (sem `any`), tratando valores monetários como string decimal convertida por `@manto/money`
- [X] T030 [US1] Criar `frontend/apps/internal/src/pages/VirtuaisCampanhasPage.tsx` com a listagem, estados de loading/erro/vazio, valores via `formatBRL` e transições do Framer Motion respeitando `useReducedMotion()`
- [X] T031 [US1] Criar `frontend/apps/internal/src/pages/VirtuaisCampanhaFormPage.tsx` com textos, FAQ, upload de capa, os três preços via `MoneyInput` do `@manto/money`, capacidade, prazo de entrega e limites anti-abuso
- [X] T032 [US1] Adicionar no formulário o gerador de horários e a seleção de acervo liberado usando `Combobox` + `AvatarThumb` quadrado do `@manto/ui` (Princípio XII.2)
- [X] T033 [US1] Registrar as rotas novas no router de `frontend/apps/internal/src/App.tsx` e no menu de navegação
- [X] T034 [US1] Rodar **V1** verde contra `manto_local`

**Checkpoint**: campanha publicável de ponta a ponta pelo admin.

---

## Phase 4: User Story 2 — Família compra self-service (P2)

**Goal**: landing mobile-first, checkout, soft lock de 15 min, link de pagamento e o destino de volta
do checkout.

**Independent Test**: em 375px, percorrer a landing, reservar um horário, chegar ao checkout e voltar
para a página do pedido; o horário some para os outros e volta sozinho.

### Verificação primeiro

- [X] T035 [US2] Escrever o cenário **V2** em `verify_205.py`, incluindo a **disputa simultânea com duas conexões reais** (não sequencial), os limites por telefone e por origem, e a expiração preguiçosa

### Pré-requisitos compartilhados

- [X] T036 [US2] Promover `GoogleAddressInput` de `frontend/apps/internal/src/components/` para `frontend/packages/ui/src/google-address-input.tsx`, exportá-lo no índice do pacote e **reapontar o app interno para o pacote** (Princípio I — proibido copiar)
- [X] T037 [US2] Implementar em `app/api/virtuais_public.py` o autocomplete público de endereço com throttle por origem, restrito ao Brasil, chave do Google só no servidor, debounce de 350ms e mínimo de 3 caracteres (FR-015, Princípio XII.3–5, research §R5)

### Núcleo

- [X] T038 [US2] Implementar `listar_slots_disponiveis()` considerando `livre` **ou** `travado` com `locked_until` vencido, e nunca devolvendo horário no passado
- [X] T039 [US2] Implementar `reservar()` com `with_for_update()` na linha do slot, congelando os valores em `Decimal` no pedido, gerando `order_nsu` e `public_token` (FR-017, FR-020, FR-022)
- [X] T040 [US2] Implementar os limites anti-abuso dentro de `reservar()`: uma reserva ativa por telefone (devolvendo o pedido existente) e teto por origem na janela configurada, registrando as recusas (FR-020a–020d)
- [X] T041 [US2] Implementar a idempotência por `client_token` para duplo clique nunca criar dois pedidos (FR-026)
- [X] T042 [US2] Implementar o consumo de capacidade de vídeo gravado com verificação de esgotamento no momento da reserva (FR-023)
- [X] T043 [US2] Integrar `criar_link_pagamento()` ao fim da reserva passando `total_value` como `Decimal` e a `redirect_url` da página do pedido, desfazendo a reserva e devolvendo o horário se a operadora falhar (FR-021, contracts §1)
- [X] T044 [US2] Implementar em `virtuais_ops` o helper único de retry — 3 tentativas nos minutos 0, 1 e 2, falha definitiva registrada e sinalizada — reusado por reconsulta, e-mail e geração de sala (FR-056, FR-056a)
- [X] T045 [US2] Implementar `expirar_reservas()` com `with_for_update()`, que **antes de liberar** consulta a operadora; se paga, efetiva; se indisponível, consome as 3 tentativas (até 2 min) e só então libera marcando `expired_unverified` (FR-018, FR-018a, FR-018b, FR-041a)
- [X] T046 [US2] Iniciar a varredura em `create_app()` de `app/__init__.py` como thread daemon, no padrão de `_start_calendar_sync`: intervalo em `app.config`, guarda de dev, `app_context`, `except Exception` com log que nunca mata a thread, e **claim atômico no banco** no modelo de `_claim_auto_sync` para não rodar em dois workers gunicorn (FR-057, FR-057a, FR-057b)

### API pública

- [X] T047 [US2] Implementar `GET /api/virtuais/campanhas/<slug>` e `GET .../horarios` em `app/api/virtuais_public.py` (contracts §1), com `404` para rascunho e `410` para pausada
- [X] T048 [US2] Implementar `POST /api/virtuais/campanhas/<slug>/reservar` com os códigos `400`/`409`/`429`/`502` e `fields` apontando o campo culpado
- [X] T049 [US2] Implementar `GET /api/virtuais/pedidos/<public_token>` no formato de resumo mínimo — status, horário, valor, `locked_until`, `payment_url` e dica do telefone, **sem nenhum dado sensível** (FR-044, FR-044a)

### Frontend público

- [X] T050 [P] [US2] Criar `frontend/apps/public/src/lib/virtuais.ts` com tipos e chamadas de API
- [X] T051 [US2] Criar `frontend/apps/public/src/pages/CampanhaVirtualPage.tsx` — capa, textos, preços via `formatBRL`, escolha de modalidade, **prazo de entrega do vídeo gravado visível antes da compra** (FR-040) e **FAQ somente ao final da página** com deflexão para WhatsApp (FR-013)
- [X] T052 [US2] Implementar no checkout o formulário da ficha (nome, idade, dicas, telefone, e-mail) com validação que destaca o campo, leva o foco e preserva o digitado (FR-014, FR-025)
- [X] T053 [US2] Implementar a grade de horários com atualização após `409` e o contador regressivo do soft lock (FR-019)
- [X] T054 [US2] Garantir que o botão de reservar mostra estado de carregamento e não permite duplo envio (Princípio V)
- [X] T055 [US2] Criar `frontend/apps/public/src/pages/PedidoVirtualPage.tsx` na **versão mínima** — status, horário, valor e contador — que é o destino do retorno do checkout desde a primeira venda (plan.md, "Regra de sequenciamento da página do pedido")
- [X] T056 [US2] Registrar as rotas `/v/:slug` e `/v/pedido/:token` em `frontend/apps/public/src/App.tsx`, antes do catch-all `/:slug`, **junto com os componentes que já existem** (T050 e T054)
- [X] T057 [US2] Conferir na Browser pane em 320px e 430px: sem rolagem horizontal, toque ≥ 44px, nada abaixo de 12px (Princípio X)
- [X] T058 [US2] Rodar **V2** verde contra `manto_local`

**Checkpoint**: vende até "aguardando pagamento" e a família volta do checkout para uma página real.

---

## Phase 5: User Story 3 — Pagamento vira entrega operacional (P3) ⚠️ FATIA MAIS ARRISCADA

**Goal**: confirmação de pagamento cria evento, escala, sala e avisos, de forma idempotente.

**Independent Test**: disparar a confirmação e verificar, sem ação humana, evento na Agenda com ficha
vinculada, talento pré-escalado e estoque atualizado.

**⚠️ Nenhuma fase posterior começa antes de V3, V7 e V8 passarem.**

### Verificação primeiro

- [X] T059 [US3] Escrever o cenário **V3** em `verify_205.py` cobrindo os 9 casos: efetivação (**com asserção de que `meet_url` foi preenchido**, SC-011), **reentrega quíntupla sem duplicar nada**, segredo inválido, `paid: false`, valor divergente, operadora indisponível (retido), **notificação órfã** (`order_nsu` inexistente), slot já vendido (devolução) e expiração com cobrança paga
- [X] T060 [P] [US3] Escrever o cenário **V8** em `verify_205.py`: as 3 tentativas de reconsulta na expiração (minutos 0, 1 e 2, sem quarta) e **um único e-mail** com o aviso reentregue 5 vezes (FR-056, SC-020)

### Sala de videochamada

- [X] T061 [US3] Estender `insert_event()` em `app/calendar/service.py` com `conference_request_id` opcional e `conferenceDataVersion=1`, mantendo a assinatura atual compatível (research §R2)
- [X] T062 [US3] Implementar em `virtuais_ops` a extração do link da sala a partir de `hangoutLink`/`conferenceData.entryPoints`, persistindo em `VirtualOrder.meet_url` — **sem tocar em `CalendarEvent.google_html_link`**, que mantém seu significado atual
- [X] T063 [US3] Tratar `createRequest` com status `pending`: manter a venda válida, marcar `meet_pending`, reconciliar pelo helper de retry de T044 (3 tentativas) e sinalizar à equipe na falha definitiva (FR-037, FR-056)
- [X] T064 [US3] Implementar `POST /api/virtuais/pedidos/<id>/sala` para regerar a sala pendente

### Efetivação

- [X] T065 [US3] Implementar `processar_notificacao_pagamento()` em `app/marketing/virtuais_ops.py` — registra a notificação, trava o slot com `with_for_update()`, reconsulta na operadora e decide (FR-027 a FR-028)
- [X] T066 [US3] Implementar a idempotência por violação de unicidade em `transaction_nsu`, encerrando com sucesso sem reprocessar (FR-028)
- [X] T067 [US3] Implementar a conferência de `paid` e do valor pago (já convertido para `Decimal` pelo cliente) contra `total_value`, com os desfechos `unpaid`/`divergent`/`unavailable` registrados e sinalizados (FR-027b, FR-027c, FR-027d)
- [X] T068 [US3] Implementar o tratamento da notificação órfã: registrar com `outcome='orfao'` e sinalizar à equipe, sem descartar em silêncio (FR-034)
- [X] T069 [US3] Implementar a criação do `CalendarEvent` com `event_type='VIRTUAL'`, `source='platform'`, `sale_value` em `Decimal` e a sala (FR-029, FR-052)
- [X] T070 [US3] Implementar o vínculo da ficha da criança ao evento e a pré-escala de `EventRole` com talento e figurino da campanha (FR-030, FR-031)
- [X] T071 [US3] Implementar a baixa de capacidade de vídeo gravado e a criação da `VirtualMediaDelivery` com `due_date` derivada do prazo da campanha (FR-033, FR-041)
- [X] T072 [US3] Implementar o caminho de conflito: pedido `cancelado`, `VirtualRefundRequest` `pendente`, **zero** evento/escala/pendência 3D (FR-042, FR-043)
- [X] T073 [US3] Garantir que toda a orquestração roda em **uma transação** e que qualquer exceção desfaz tudo, deixando a notificação como `retido`

### Exibição na Agenda

- [X] T074 [US3] Exibir no detalhe do evento da Agenda a ficha da criança vinculada — nome, idade, dicas, telefone e endereço (FR-030, US3 cenário 2)
- [X] T075 [US3] Exibir no detalhe do evento o acesso à sala de videochamada do pedido, para o talento escalado (FR-036)

### Sincronização blindada

- [X] T076 [US3] Excluir eventos `event_type='VIRTUAL'` + `source='platform'` de **todos** os caminhos da sincronização em `app/calendar/event_ops.py` — importação, atualização e remoção (FR-029a, research §R9)
- [X] T077 [US3] Implementar a sinalização à equipe quando um evento virtual for alterado ou removido direto na agenda externa, sem propagar a mudança para o pedido (FR-029b)
- [X] T078 [US3] Escrever o cenário **V7** em `verify_205.py`: rodar a sincronização completa após vendas e provar que nenhum evento `VIRTUAL` mudou (SC-019)

### Avisos por e-mail

- [X] T079 [US3] Implementar `send_virtual_order_confirmed_email()` em `app/email_service.py` reusando `_html_wrap`/`_btn`/`send_async`, com valores formatados em BRL
- [X] T080 [P] [US3] Implementar `send_virtual_order_cancelled_email()` informando devolução em andamento, sem prometer prazo (FR-043a)
- [X] T081 [US3] Implementar o guard de idempotência de aviso: gravar `VirtualOrderNotification` na **mesma transação** que decide enviar, antes do disparo, e tratar a violação de unicidade como "já avisado" (FR-028a, FR-028b)
- [X] T082 [US3] Registrar falhas de envio no pedido e sinalizá-las à equipe (FR-039c)

### Página do pedido — incremento de confirmação

- [X] T083 [US3] Estender `PedidoVirtualPage.tsx` com o estado "aguardando confirmação" e a transição automática para "confirmado" quando a confirmação chegar, sem recarga manual (FR-035a)
- [X] T084 [US3] Exibir na página do pedido o acesso à sala quando o pedido estiver pago (FR-036)
- [X] T085 [US3] Adicionar na página do pedido o atalho de WhatsApp com mensagem pré-preenchida (FR-039b)

### Webhook e devoluções

- [X] T086 [US3] Implementar `POST /api/webhooks/infinitepay/<token>` em `app/api/virtuais_webhook.py` — **só** valida o segredo, desserializa e delega; `404` para segredo inválido; `200 {"success": true}` em todos os demais casos, inclusive duplicata e conflito (contracts §2)
- [X] T087 [P] [US3] Implementar `GET/PATCH /api/virtuais/devolucoes` para a equipe executar e concluir as devoluções (contracts §5)
- [X] T088 [P] [US3] Criar a tela de devoluções pendentes em `frontend/apps/internal/src/pages/` com `invoice_slug`, `transaction_nsu`, valor em BRL e contato
- [X] T089 [US3] Rodar **V3**, **V7** e **V8** verdes contra `manto_local`

**Checkpoint**: venda vira operação sozinha, de forma idempotente e à prova de reentrega.

---

## Phase 6: User Story 4 — Upsell de presente 3D (P4)

**Goal**: peça 3D no checkout e pendência nascendo na Fila de Impressão existente.

**Independent Test**: comprar com presente e confirmar o pagamento; a peça aparece na Fila 3D
vinculada ao evento, sem intervenção manual.

- [X] T090 [US4] Escrever o cenário **V4** em `verify_205.py`
- [X] T091 [US4] Implementar no fluxo de efetivação a criação do `Event3DGift` com status `pendente` vinculado ao evento, reusando `app/impressoes3d/impressoes3d_ops.add_event_gift` (FR-032, Princípio I)
- [X] T092 [US4] Expor as peças liberadas no payload público da campanha, só quando houver acervo definido (FR-016)
- [X] T093 [US4] Implementar a etapa de presente no checkout público com `Combobox` pesquisável e miniatura quadrada via `AvatarThumb`, somando o valor ao total via `@manto/money` (FR-016, Princípios IX e XII.2)
- [X] T094 [US4] Tornar o endereço obrigatório apenas quando houver presente selecionado, usando o `GoogleAddressInput` do `@manto/ui` (FR-014, FR-015)
- [X] T095 [US4] Ocultar a etapa de presente quando a campanha não tiver acervo liberado e recusar `gift_item_id` nesse caso
- [X] T096 [US4] Rodar **V4** verde contra `manto_local`

---

## Phase 7: User Story 5 — Fila de Produção de Mídia (P5)

**Goal**: tela tabular densa espelhando a Fila 3D, fluxo de status, entrega do vídeo e validação
dupla na página do pedido.

**Independent Test**: com pedidos pagos das duas modalidades, cada entrega aparece em uma linha com
os quatro blocos e o status persiste após recarregar.

### Verificação primeiro

- [X] T097 [US5] Escrever os cenários **V5** e **V6** em `verify_205.py` — este último inclui a **varredura de vazamento**: nenhum payload pode conter o caminho do arquivo e o `subfolder` dos vídeos não pode ser alcançável pelo servidor estático

### Entrega do vídeo (privacidade)

- [X] T098 [US5] Implementar `salvar_video_entrega()` em `virtuais_ops` usando `app/storage.py`, com `subfolder` **fora** de qualquer caminho servido estaticamente, validando extensão e o teto de **250 MB** (FR-038a, FR-038d, research §R3)
- [X] T099 [US5] Implementar a verificação de que o vídeo é reproduzível antes de finalizar a entrega e avisar a família (FR-038b)
- [X] T100 [US5] Implementar `GET /api/virtuais/pedidos/<token>/video` servindo o arquivo sob validação a cada requisição, com suporte a `Range`, **sem jamais devolver a URL do armazenamento** (FR-038e)
- [X] T101 [US5] Implementar `send_virtual_video_ready_email()` em `app/email_service.py`, protegido pelo mesmo guard de idempotência do T080 (FR-039)
- [X] T102 [US5] Implementar o caminho de falha: entrega não finaliza, `last_upload_error` preenchido, família não avisada (FR-038c)

### Página do pedido — incremento de validação dupla

- [X] T103 [US5] Implementar `POST /api/virtuais/pedidos/<public_token>/verificar` conferindo o telefone por dígitos, abrindo sessão de acesso que expira em **30 minutos de inatividade**, com `401`/`attempts_left` e `429`/`blocked_until` (FR-044a–044c)
- [X] T104 [US5] Estender `PedidoVirtualPage.tsx` com o passo de validação do telefone antes de revelar qualquer dado sensível, e com o player do vídeo (FR-044a, FR-038e)
- [X] T105 [US5] Rodar **V6** verde — inclusive a varredura de vazamento

### Fila interna

- [X] T106 [US5] Implementar `listar_fila_producao()` em `virtuais_ops` com filtros por campanha, data e status, reusando `impressoes3d_ops.serialize_gift` para o bloco do presente (FR-045, FR-046, FR-050)
- [X] T107 [US5] Implementar `atualizar_status_entrega()` aceitando **exatamente** `pendente`, `gravando` e `finalizado` — nenhum outro estado — e bloqueando `finalizado` sem vídeo em entregas gravadas (FR-047, FR-048, FR-048a)
- [X] T108 [US5] Implementar os endpoints `GET /api/virtuais/producao`, `PATCH /api/virtuais/producao/<id>` e `POST /api/virtuais/producao/<id>/video` com o gate de RBAC que permite ao talento ver e atualizar o que lhe cabe (FR-051)
- [X] T109 [US5] Criar `frontend/apps/internal/src/pages/FilaProducaoMidiaPage.tsx` espelhando a arquitetura da Fila 3D (feature 200): tabela densa, uma linha por entrega, filtros sem recarregar a página
- [X] T110 [US5] Adicionar na linha o acesso à sala (ao vivo), o envio do vídeo (gravado) e o atalho de WhatsApp com mensagem pré-preenchida (FR-039b, FR-049)
- [X] T111 [US5] Distinguir visualmente pendente/gravando/finalizado e sinalizar prazo vencido ou por vencer (FR-041)
- [X] T112 [US5] Registrar a rota da fila no router e no menu do app interno
- [X] T113 [US5] Rodar **V5** verde contra `manto_local`

---

## Phase 8: Registro Financeiro Segregado

**Purpose**: a receita entra no DRE sem contaminar KPIs de eventos nem comissão (FR-052–055).

- [X] T114 Escrever o cenário **V9** em `verify_205.py`: medir volume, ticket médio e base de comissão antes e depois de 10 vendas virtuais; os três devem ficar iguais e o DRE subir exatamente a soma (SC-014)
- [X] T115 Mapear **todos** os agregadores que somam eventos hoje (painel financeiro/DRE, KPIs, comissão) e listar cada ponto no topo da tarefa seguinte — agregador esquecido é como o KPI se distorce
- [X] T116 Excluir `event_type='VIRTUAL'` por padrão dos indicadores de eventos e do cálculo de comissão em cada ponto mapeado (FR-054)
- [X] T117 Garantir que a receita virtual soma no DRE e é consultável por campanha (FR-053)
- [X] T118 Adicionar a opção explícita de incluir o canal "loja virtual" nos painéis que agregam eventos (FR-055)
- [X] T119 Rodar **V9** verde contra `manto_local`

---

## Phase 9: Polish & Cross-Cutting

- [X] T120 Auditar toda a feature contra a regra monetária: nenhuma coluna ou campo de API `*_cents`, nenhum `float` para dinheiro, nenhum `toFixed`/`Intl.NumberFormat` fora de `@manto/money`, e centavos só em `infinitepay_client.py` (Princípio IX)
- [X] T121 [P] Rodar `npx tsc --noEmit` limpo em `frontend/apps/internal` e `frontend/apps/public`
- [X] T122 [P] Rodar `ruff check` limpo **nos arquivos da feature**. `ruff check app/` inteiro acusa **78 erros pré-existentes** (40 `I001`, 7 `F401`, 6 `E402`…), todos anteriores à 205 e confirmados contra `git show HEAD` — arrumá-los seria mexer em módulos que a feature não toca (Princípio IV). Fica registrado como dívida do repositório, não da feature.
- [X] T123 Rodar a suíte completa `verify_205.py` (V1–V9) contra `manto_local`
- [X] T124 Conferir na Browser pane, em 320px e 430px, a landing, o checkout e a página do pedido (Princípio X)
- [X] T125 [P] Atualizar `docs/01_SISTEMA_E_BANCO.md` com as tabelas, rotas e RBAC novos
- [X] T126 [P] Atualizar `docs/02_MAPA_DE_PAGINAS_E_UX.md` com as rotas públicas e internas
- [X] T127 [P] Acrescentar entrada **no topo** de `docs/03_HISTORICO_MUTACOES.md` com migration, motivação, regras de negócio e as pegadinhas (idempotência do webhook, exclusão da sincronização, vídeo sob validação, centavos só na fronteira)
- [X] T128 Executar `/speckit.converge` para fechar gaps entre spec, plano e implementação

---

## Dependencies

```text
Setup (T001–T004)
   └─> Foundational (T005–T020)   ⚠️ bloqueia tudo
          ├─> US1 (T021–T034)  ← MVP
          ├─> US2 (T035–T058)  depende de US1 (precisa de campanha publicada)
          │      └─> US3 (T059–T089)  ⚠️ depende de US2 (precisa de pedido aguardando)
          │             ├─> US4 (T090–T096)
          │             ├─> US5 (T097–T113)
          │             └─> Financeiro (T114–T119)
          └─────────────────> Polish (T120–T128)
```

**Regras de bloqueio**:

- US3 é a fatia de risco: **nada depois dela começa antes de V3, V7 e V8 passarem**.
- T016/T017 (cliente da operadora) bloqueiam T043 e T045 — a conversão de centavos precisa existir antes de qualquer chamada.
- T044 (helper de retry) bloqueia T045, T081 e T063 — as três dependem da mesma política de 3 tentativas.
- T046 (varredura em segundo plano) depende de T045; sem o claim atômico, dois workers gunicorn expiram a mesma reserva.
- T036 (promoção do `GoogleAddressInput`) bloqueia T094 além do checkout de US2.
- T055 (página do pedido mínima) bloqueia T056 — registrar a rota antes do componente quebra o build.
- T055 é pré-requisito de T083, T084, T085 (US3) e T104 (US5): a página cresce em três incrementos.
- T081 (guard de idempotência de aviso) bloqueia T101 — o e-mail de vídeo usa o mesmo guard.
- T098 (subfolder fora do caminho estático) bloqueia T100; inverter a ordem cria janela de vazamento.
- T115 (mapear agregadores) bloqueia T116 — implementar sem o mapa é como se esquece um painel.

## Parallel Opportunities

- **Foundational**: T009–T013 são modelos em blocos distintos de `models.py`; T018 é independente
- **US1**: T029 (lib de API) roda junto com T022–T026 (backend)
- **US3**: T080 (e-mail de cancelamento), T087 e T088 (devoluções) são independentes do núcleo de efetivação; T060 pode ser escrito junto com T059
- **US5**: a trilha de vídeo/privacidade (T098–T105) e a trilha da fila interna (T106–T112) tocam arquivos diferentes
- **Polish**: T121, T122, T125, T126 e T127 rodam todos em paralelo

## Implementation Strategy

**MVP**: Phase 1 + 2 + 3 (US1). Ao fim, a equipe monta e publica uma campanha e vê a landing — sem
vender ainda, mas com a oferta revisável.

**Primeiro incremento vendável**: + US2. Vende até "aguardando pagamento", e quem paga já volta para
uma página do pedido real — a conversão em operação ainda é manual.

**Produto completo**: + US3, que é onde a promessa de "atrito zero" se cumpre. US4, US5 e o
financeiro segregado são incrementos sobre um canal que já está vendendo.

**Sugestão de commits**: um commit atômico por tarefa ou por bloco coeso de tarefas (Princípio IV),
sempre com `tsc` e `ruff` limpos antes.

---

## Phase 10: Convergence

> Apurado por `/speckit.converge` em **2026-08-04**, com T001–T127 concluídas. Os quatro itens
> compartilham o mesmo ponto cego: o comportamento quando um serviço externo falha e **ninguém
> está olhando**. `verify_205.py` finge o Google e a operadora, então esses caminhos passam
> verdes sem nunca exercitar a falha real.

- [X] T129 Estender a varredura de segundo plano (`app/__init__.py:_start_virtual_sweep`) para rodar, no mesmo ciclo já protegido por `claim_sweep`, as outras duas rotinas que o requisito nomeia: retentativa dos pedidos com `meet_pending` e alerta de prazo de vídeo próximo/vencido. Hoje o laço chama só `expirar_reservas()` per FR-057 (partial)
- [X] T130 Aplicar a política de retry à geração da sala: envolver a chamada `insert_event` em `virtuais_ops._criar_evento_google` com `executar_com_retry`, para que uma falha transitória do Google não deixe o pedido parado em `meet_pending` esperando clique humano per FR-056 (partial)
- [X] T131 Expor os avisos que falharam: incluir em `serialize_delivery` (Fila de Produção) e no bloco `pedido_virtual` do painel do evento os registros `VirtualOrderNotification` com `sent_ok = False`, com o motivo, para que o reforço manual por WhatsApp seja feito com consciência do que falhou per FR-039c, FR-056a (missing)
- [X] T132 Envolver o envio de e-mail em `virtuais_ops._enviar_aviso` com `executar_com_retry`, mantendo a trava de unicidade `UNIQUE(order_id, kind)` intacta — o retry é da entrega, não do registro per FR-056 (partial)
- [X] T133 Acrescentar a `verify_205.py` o cenário **V10**, que força cada falha externa (Google indisponível na criação da sala, e-mail lançando exceção, prazo de vídeo vencido) e prova que o retry acontece, que a varredura recupera o pedido e que a falha aparece no payload da Fila — sem isso as quatro correções acima voltam a ser invisíveis

---

## Phase 11: Convergence (2ª passagem)

> Apurado por `/speckit.converge` após T129–T133. Implementado na mesma sessão, por instrução
> explícita de tratar novo gap como desenvolvimento imediato.
>
> Os dois primeiros só apareceram **porque** a fase anterior existiu: ao expor as falhas de aviso
> no painel, ficou visível um aviso que nunca era enviado; e ao persistir o progresso do retry,
> ficou evidente que a decisão tomada "sem confirmação" não chegava a lugar nenhum.

- [X] T134 Registrar `send_virtual_video_ready_email` em `_enviadores_de_aviso()`: o `kind` `video_pronto` não tinha enviador, então `_enviar_aviso` gravava a linha (a trava de idempotência), não achava a função e voltava calado — a família nunca recebia o e-mail e o sistema constava como tendo avisado per FR-039 (missing)
- [X] T135 Travar a classe do bug acima com **V5.11b** (o aviso do vídeo foi disparado, não só registrado) e **V5.11c** (todo `VIRTUAL_NOTIFICATION_KINDS` tem enviador). V5.11 contava a linha, que é gravada **antes** do disparo — por isso passava verde com o envio quebrado per FR-039 (partial)
- [X] T136 Levar a origem do conflito até quem usa a informação: `_abrir_devolucao` grava `conflito_sem_confirmacao` quando o horário foi liberado com a operadora fora, o payload devolve `reason_label`/`sem_confirmacao`, e a tela de Devoluções destaca o caso. O `expired_unverified` era gravado e nenhuma tela lia — registrar onde ninguém lê é o mesmo que não registrar per FR-018b (partial)
- [X] T137 Alinhar o gate dos endpoints de reenvio de aviso e de regeração de sala a `require_producao_access()`: as duas ações nascem no banner da Fila de Produção, e com o gate de campanhas o `CASTING` — que é quem trabalha nessa tela — veria os botões e levaria 403. Não alarga permissão: `CASTING` já finaliza entrega e dispara e-mail à família pelo mesmo gate per Princípio V (contradicts)
