---
description: "Tasks da feature 332 — Avisos das Conversas no celular"
---
<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Tasks: 332 — Avisos das Conversas no celular

**Input**: `specs/332-crm-avisos-no-celular/` (spec, plan, research R1–R7, data-model, contracts).

**Verificação (Princípio VIII)**: `verify_332.py` (molde do `verify_330`), com dublê do `push_ops.webpush`, escrito na
Foundational, antes do núcleo. O `verify_330`, o `verify_328` e o `verify_325` são regressão.

**Base**: worktree `C:\tmp\mp332`, branch `332-crm-avisos-no-celular` sobre a 330. Sem merge e sem push.

---

## Phase 1: Setup

- [ ] T001 `requirements.txt` com `pywebpush==2.0.3`, instalado no `.venv` local.
- [ ] T002 [P] `app/config.py`:
  - `WEB_PUSH_VAPID_PUBLICA` e `WEB_PUSH_VAPID_PRIVADA` (vazias);
  - `WEB_PUSH_CONTATO` (default `mailto:contato@mantoproducoes.com.br`);
  - `_suppress_push()` com `WEB_PUSH_ALLOW_LOCAL`.

  Também o log `[push] ligado=… travado=…` em `app/__init__.py` e as duas chaves `sync: false` no `render.yaml`.
- [ ] T003 [P] `app/push/constantes.py`: textos do XV, TTL, timeout e as `tag`.

## Phase 2: Foundational

- [ ] T004 `PushAssinatura` em `app/models.py` e a migration manual `b332d5f7a9c1_push_assinaturas.py`
  (`down_revision="a330c4e8f1b2"`). Aplicar no `manto_local` e ensaiar o downgrade.
- [ ] T005 **`specs/332-crm-avisos-no-celular/verify_332.py`** com os 15 cenários da spec. Falha agora.

## Phase 3: História 1 — Ativar os avisos neste aparelho (P1)

- [ ] T006 [US1] `app/push/push_ops.py`:
  - `cfg_push()`;
  - `registrar(user_id, dados, navegador)` (upsert por `endpoint`; 422 `fields.aparelho`; 503 desligado);
  - `remover(user_id, endpoint)`.
- [ ] T007 [US1] `app/api/push.py`: `GET /api/push/chave`, `POST`/`DELETE /api/push/aparelhos`, com o gate
  `pode_conversas` e o comentário `RBAC:`. Registrar em `app/api/__init__.py`.
- [ ] T008 [P] [US1] `frontend/apps/internal/public/`:
  - `manifest.webmanifest`;
  - `sw.js` (push e notificationclick);
  - os ícones 192/512 e o `apple-touch-icon`, gerados.

  E `index.html` com o `<link rel="manifest">`, o `apple-touch-icon` e o `theme-color`.
- [ ] T009 [US1] `src/lib/avisos.ts` (estado do aparelho, ativar, desativar) e
  `src/components/conversas/AvisosNoCelular.tsx` (botão e diálogo com os estados), no cabeçalho de
  `ListaDeConversas.tsx`.

## Phase 4: História 2 — O celular toca quando a cliente escreve (P1)

- [ ] T010 [US2] `push_ops.enviar(user_ids, aviso)`:
  - filtra quem é da equipe;
  - passa pelo `webpush` com VAPID;
  - 404/410 apaga o aparelho;
  - falha só loga;
  - travado → nada sai;
  - atualiza `ultimo_aviso_em`.
- [ ] T011 [US2] `app/conversas/avisos_ops.py`: `avisar_mensagens(conversa_ids)` (destino pelo responsável ou pela
  equipe; título, corpo, link e `tag`).
- [ ] T012 [US2] `aviso_ops` e `instagram_ops`:
  - os processadores devolvem também as conversas com mensagem nova da cliente;
  - `processar_aviso` chama `avisar_mensagens` depois do commit, sem levantar.

## Phase 5: História 3 — Os avisos das Conversas também tocam (P2)

- [ ] T013 [US3] `equipe_ops`: `alertar_esperas` avisa no celular, depois do commit, quem recebeu cada alerta;
  `definir_responsavel` avisa o destino da transferência.

## Phase 6: Polimento

- [ ] T014 `ruff`, `npm run typecheck`; verifies 332, 330, 328 e 325 verdes.
- [ ] T015 Tela pela worktree: painel, manifesto e SW servidos; desktop e 375×812.
- [ ] T016 Docs: `docs/01` (tabela, endpoints, RBAC, envs, dependência), `docs/02`, `docs/03` (**NÃO PUBLICADO**),
  `docs/04`, `docs/05` e o plano. Gates CHK001–CHK011.

## Dependências

Setup → Foundational → US1 → US2 → US3 → Polimento. O T012 mexe no `processar_aviso`: os verifies 325 e 330 rodam
logo depois.
