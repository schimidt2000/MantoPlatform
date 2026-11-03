---
description: "Tasks da feature 332 — Avisos das Conversas no celular"
---
<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Tasks: 332 — Avisos das Conversas no celular

**Input**: `specs/332-crm-avisos-no-celular/` (spec, plan, research R1–R7, data-model, contracts).

**Verificação (Princípio VIII)**: `verify_332.py` (molde do `verify_330`), com dublê da entrega
(`webpush.enviar`) e o vetor oficial do RFC 8291 para a cifra, escrito na Foundational, antes do núcleo. O `verify_330`, o `verify_328` e o `verify_325` são regressão.

**Base**: worktree `C:\tmp\mp332`, branch `332-crm-avisos-no-celular` sobre a 330. Sem merge e sem push.

---

## Phase 1: Setup

- [X] T001 `app/push/webpush.py`: a cifra RFC 8291, o token VAPID e a entrega, sobre o `cryptography`/`requests` (sem
  biblioteca de Web Push; conferida contra o vetor do RFC em 03/11).
- [X] T002 [P] `app/config.py`:
  - `WEB_PUSH_VAPID_PUBLICA` e `WEB_PUSH_VAPID_PRIVADA` (vazias);
  - `WEB_PUSH_CONTATO` (default `mailto:contato@mantoproducoes.com.br`);
  - `_suppress_push()` com `WEB_PUSH_ALLOW_LOCAL`.

  Também o log `[push] ligado=… travado=…` em `app/__init__.py` e as duas chaves `sync: false` no `render.yaml`.
- [X] T003 [P] `app/push/constantes.py`: textos do XV, TTL, timeout e as `tag`.

## Phase 2: Foundational

- [X] T004 `PushAssinatura` em `app/models.py` e a migration manual `b332d5f7a9c1_push_assinaturas.py`
  (`down_revision="a330c4e8f1b2"`). Aplicar no `manto_local` e ensaiar o downgrade.
- [X] T005 **`specs/332-crm-avisos-no-celular/verify_332.py`** com os 15 cenários da spec. Falha agora.

## Phase 3: História 1 — Ativar os avisos neste aparelho (P1)

- [X] T006 [US1] `app/push/push_ops.py`:
  - `cfg_push()`;
  - `registrar(user_id, dados, navegador)` (upsert por `endpoint`; 422 `fields.aparelho`; 503 desligado);
  - `remover(user_id, endpoint)`.
- [X] T007 [US1] `app/api/push.py`: `GET /api/push/chave`, `POST`/`DELETE /api/push/aparelhos`, com o gate
  `pode_conversas` e o comentário `RBAC:`. Registrar em `app/api/__init__.py`.
- [X] T008 [P] [US1] `frontend/apps/internal/public/`:
  - `manifest.webmanifest`;
  - `sw.js` (push e notificationclick);
  - os ícones 192/512 e o `apple-touch-icon`, a partir do ícone da casa.

  E `index.html` com o `<link rel="manifest">`, o `apple-touch-icon` e o `theme-color`.
- [X] T009 [US1] `src/lib/avisos.ts` (estado do aparelho, ativar, desativar) e
  `src/components/conversas/AvisosNoCelular.tsx` (botão e diálogo com os estados), no cabeçalho de
  `ListaDeConversas.tsx`.

## Phase 4: História 2 — O celular toca quando a cliente escreve (P1)

- [X] T010 [US2] `push_ops.despachar(user_ids, aviso)` (thread própria) e `entregar`:
  - filtra quem é da equipe;
  - passa pelo `webpush.enviar` (VAPID);
  - 404/410 apaga o aparelho;
  - falha só loga;
  - travado → nada sai;
  - atualiza `ultimo_aviso_em`.
- [X] T011 [US2] `app/conversas/celular_ops.py`: `avisar_mensagens(conversa_ids)` (destino pelo responsável ou pela
  equipe; título, corpo, link e `tag`).
- [X] T012 [US2] `aviso_ops` e `instagram_ops`:
  - os processadores juntam no conjunto `chegadas` as conversas com mensagem nova da cliente;
  - `processar_aviso` chama `avisar_mensagens` depois do commit, sem levantar.

## Phase 5: História 3 — Os avisos das Conversas também tocam (P2)

- [X] T013 [US3] `equipe_ops`: `alertar_esperas` avisa no celular, depois do commit, quem recebeu cada alerta;
  `definir_responsavel` avisa o destino da transferência.

## Phase 6: Polimento

- [X] T014 `ruff`, `npm run typecheck`; verifies 332, 330, 328 e 325 verdes.
- [X] T015 Tela pela worktree: painel, manifesto e SW servidos; desktop e 375×812.
- [X] T016 Docs: `docs/01` (tabela, endpoints, RBAC, envs, dependência), `docs/02`, `docs/03` (**NÃO PUBLICADO**),
  `docs/04`, `docs/05` e o plano. Gates CHK001–CHK011.

## Dependências

Setup → Foundational → US1 → US2 → US3 → Polimento. O T012 mexe no `processar_aviso`: os verifies 325 e 330 rodam
logo depois.

## Phase 7: Convergence

Revisão independente (só leitura) de 03/11 sobre o diff `330-crm-instagram-direct..HEAD`: 17 achados.

- [X] T017 CRITICAL `requirements.txt`: fixar `cryptography==46.0.7` (estava só no `.venv`, instalado pela sessão da 329; no Render o boot quebraria no import do `webpush`) e corrigir "sem dependência nova" em plan, research e docs per plan: Dependência nova (contradicts)
- [X] T018 `push_ops`: validar o ponto `p256dh` na curva no registro (422) e capturar qualquer falha por aparelho dentro do laço da entrega per FR-006/FR-007 (bug)
- [X] T019 `push_ops`: uma thread por rodada (`despachar_varios`), aparelhos lidos para dados simples e conexão devolvida ao pool antes da rede; 410 e `ultimo_aviso_em` numa transação curta depois per FR-006 (bug)
- [X] T020 `avisos.ts`/`AvisosNoCelular.tsx`: POST que falha desfaz a assinatura; "ativo" só depois de o servidor confirmar per US1/AC1, Princípio V (bug)
- [X] T021 `verify_332`: dublê no `requests.post` do `webpush`, conferindo o JWT VAPID (assinatura, `aud`, `exp`, `sub`), os cabeçalhos e decifrando o corpo com a chave do aparelho; 410 e 500 pelo HTTP per Princípio VIII (partial)
- [X] T022 `verify_332`: conferir que `WEB_PUSH_SUPPRESS` derivado do banco local é `True` antes de liberar per FR-008 (partial)
- [X] T023 Texto "tente de novo" → "tente novamente" no componente e na spec per Constituição XV (contradicts)
- [X] T024 `despachar` nunca levanta (try em volta da checagem e da thread) per FR-006 (partial)
- [X] T025 `celular_ops`: rollback no `except` per FR-006 (bug)
- [X] T026 `celular_ops`: o corpo do aviso é a última mensagem da cliente (sem reação), não a `ultima_previa` per FR-004 (partial)
- [X] T027 `AvisosNoCelular`: falha ao ler o estado do aparelho mostra erro com "Tentar novamente" per Princípio V (bug)
- [X] T028 `AvisosNoCelular`: ícone de celular (o sino já é o das notificações) per US1 (partial)
- [X] T029 "Sair" desativa os avisos deste aparelho (o aviso traz nome e trecho da cliente) per plano §9 LGPD (missing)
- [X] T030 `push_ops.chaves`: par VAPID que não confere = desligado, com aviso na subida per Princípio XIV (missing)
- [X] T031 `verify_332`: toque em botão (WhatsApp e Instagram), eco e reação do Instagram, alerta sem responsável e a entrega pela thread per FR-003/FR-005 (partial)
- [X] T032 Registrar `WEB_PUSH_SUPPRESS=true` (trava forçada) no research R5 per R5 (unrequested)
- [X] T033 Docs (T016) e portões CHK001–CHK011 per T016 (missing)
