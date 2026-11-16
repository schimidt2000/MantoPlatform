# Tarefas: 344 — A loja conta as visitas e pede licença

**Input**: `spec.md`, `plan.md`, `data-model.md`, `contracts/api.md`, `research.md`

## Fase 1: Preparação

- [X] T001 Restaurar o espelho `manto_344` do dump `backups/manto_2026-11-16_0200.dump` e gravar a URL em `C:\tmp\mp344\.local-db-url`; ligar `frontend/node_modules` por junção

## Fase 2: Fundação (bloqueia as histórias)

- [X] T002 Escrever `specs/344-loja-visitas-e-privacidade/verify_344.py` com os 18 cenários da spec e rodá-lo ANTES do núcleo (deve falhar por falta de tabela, colunas e rotas)
- [X] T003 Constantes em `app/constants.py` (`VIRTUAL_ORIGENS`, rótulos, `VIRTUAL_ACEITE_VERSAO`, `VIRTUAL_DICAS_RETENCAO_DIAS`, `CLIENT_SOURCE_LOJA`) e `LOJA_PUBLIC_BASE_URL` com default real em `app/config.py`
- [X] T004 Modelos em `app/models.py` (`VirtualCampaignVisit`; colunas em `VirtualOrder`, `Client`, `SiteSetting`) e migration à mão `migrations/versions/e344a1b2c3d4_loja_visitas_e_privacidade.py` sobre `f310b2a4c6e8`; `flask db upgrade` no `manto_344`

## Fase 3: História 1 — Contagem de visitas (P1)

- [X] T005 [US1] `normalizar_origem`, `registrar_visita` (upsert) e `funil_da_campanha` em `app/marketing/virtuais_ops.py`; `reservar` grava `origem`
- [X] T006 [US1] `POST /api/virtuais/campanhas/<slug>/visita` e campos novos do `reservar` em `app/api/virtuais_public.py`; `GET /api/virtuais/campanhas/<id>/funil` em `app/api/virtuais_read.py`
- [X] T007 [P] [US1] Origem da visita + `useRegistrarVisita` em `frontend/apps/public/src/lib/virtuais.ts`; disparo na `CampanhaVirtualPage.tsx` e `origem` no reservar
- [X] T008 [P] [US1] Card "Visitas e vendas" com links e copiar em `frontend/apps/internal/src/pages/VirtuaisCampanhaFormPage.tsx` (+ hook e tipos no lib da loja do internal)

## Fase 4: História 2 — LGPD (P1)

- [X] T009 [US2] `reservar` grava `buyer_name` e o aceite; `_cliente_da_venda` (SAVEPOINT) chamado em `_efetivar_no_banco`; `apagar_dicas_vencidas` na `ciclo_de_varredura` — `app/marketing/virtuais_ops.py`
- [X] T010 [P] [US2] CRM: balde `loja` em `client_ops.client_metrics`, aceite e origem na ficha (`app/api/clientes_read.py`); tooltip do gráfico em `ClientsListPage.tsx` e linha do aceite em `ClientDetailPage.tsx` (+ tipos)
- [X] T011 [P] [US2] Página `frontend/apps/public/src/pages/PrivacidadeLojaPage.tsx` + rota `/v/privacidade` em `App.tsx`
- [X] T012 [US2] Formulário da `CampanhaVirtualPage.tsx`: "Seu nome", caixinha desmarcada, linha com link para o aviso; payload com `buyer_name` e `marketing_opt_in`

## Fase 5: História 3 — Pixel da Meta (P2)

- [X] T013 [US3] `meta_pixel_id` em `app/admin/config_ops.py` (validação só dígitos) e `app/api/admin_config_read.py`; `GET /api/virtuais/rastreamento` em `app/api/virtuais_public.py`
- [X] T014 [P] [US3] Campo "ID do Pixel da Meta" em `AdminSettingsPage.tsx` + `lib/adminConfig.ts`
- [X] T015 [US3] `frontend/apps/public/src/lib/pixel.ts` + `components/loja/AvisoCookies.tsx`; montagem e PageView no `LojaLayout.tsx`; `InitiateCheckout` na reserva; `Purchase` no `PedidoVirtualPage.tsx`; parágrafo de cookies no aviso de privacidade

## Fase 6: Portões e fechamento

- [X] T016 `verify_344.py` verde; regressão `verify_310/340/341/310b/205` no `manto_344`
- [X] T017 `ruff check` nos tocados, `ruff format` nos novos; `npm run typecheck`
- [X] T018 Telas no Browser pane: loja (375×812: campanha, privacidade, aviso de cookies com e sem ID, pedido), campanha interna (card e links), configurações, ficha do cliente
- [X] T019 Docs: `docs/01` (tabela, colunas, endpoints, RBAC §4.3), `docs/02`, `docs/03` (entrada + índice), `docs/04` (invariantes), `docs/05` (dívidas)
- [X] T020 Commits por caminho (`feat(344):`), memória do projeto, links por canal para o dono

## Dependências
Fase 1 → Fase 2 → (US1 ∥ US2 ∥ US3 no backend em sequência por arquivo: `virtuais_ops.py` é compartilhado) → Fase 6.
MVP = US1 + US2 (as duas P1).
