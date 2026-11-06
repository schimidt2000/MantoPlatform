---
description: "Tasks da feature 335 — Linha do tempo da ficha e funil das conversas"
---
<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Tasks: 335 — Linha do tempo da ficha e funil das conversas

**Input**: `specs/335-crm-linha-do-tempo/` (spec, plan, research R1–R7, data-model, contracts).

**Verificação (Princípio VIII)**: `verify_335.py` (molde do `verify_334`), escrito na Foundational, antes do núcleo. Os
verifies 325, 328, 330, 332, 333 e 334 são regressão.

**Base**: worktree `C:\tmp\mp335`, branch `335-crm-linha-do-tempo` sobre a 334. Sem merge e sem push.

---

## Phase 1: Setup

- [X] T001 `app/conversas/constantes.py`: as etapas do funil e os rótulos, os rótulos de "Sem responsável", "Sem
  anúncio" e "Campanha desconhecida", os limites (366 dias, 200 parados, 300 marcos) e os títulos dos marcos.

## Phase 2: Foundational

- [X] T002 **`specs/335-crm-linha-do-tempo/verify_335.py`** com os 9 cenários da spec. Falha agora.

## Phase 3: Histórias 2, 3 e 4 — O funil (P1/P2)

- [X] T003 [US2] `app/conversas/funil_ops.py`: a coorte do período (primeiro contato, R1), a etapa mais avançada (R2),
  os filtros, a contagem com as porcentagens, a divisão por vendedor/campanha/canal e as opções de campanha.
- [X] T004 [US4] `funil_ops.parados`: quem parou na etapa, até 200, com o total.
- [X] T005 [US2] `app/api/conversas_funil.py` (gate `pode_conversas`, validação do período e dos filtros) e o registro
  em `app/api/__init__.py`.

## Phase 4: História 1 — A linha do tempo (P1)

- [X] T006 [US1] `app/clientes/linha_do_tempo_ops.py`: os oito tipos de marco (R5), sem cancelados, do mais novo para o
  mais antigo, com os links conforme o acesso.
- [X] T007 [US1] `GET /api/clientes/<id>/linha-do-tempo` em `app/api/clientes_read.py`.

## Phase 5: Telas

- [X] T008 [US1] `lib/clientes.ts` (tipos e hook) e `components/LinhaDoTempoDaFicha.tsx`; o cartão na
  `ClientDetailPage.tsx`.
- [X] T009 [US2] `lib/funil.ts` e `pages/FunilPage.tsx`: período, filtros, as etapas (tocáveis), a divisão e a lista
  "Pararam em …"; rota `/funil` em `App.tsx` e o item "Funil" no menu Comercial (`lib/navigation.tsx`).

## Phase 6: Polimento

- [X] T010 `ruff`, `npm run typecheck`; verifies 335, 334, 333, 332, 330, 328 e 325 verdes.
- [X] T011 Tela pela worktree em desktop e 375×812 (quickstart §2).
- [X] T012 Docs: `docs/01`, `docs/02`, `docs/03` (**NÃO PUBLICADO**), `docs/04`, `docs/05` e o plano. Gates
  CHK001–CHK011.

## Phase 7: Convergence

Revisor independente, só de leitura: 9 achados (0 críticos, 0 altos, 1 médio, 8 baixos).

- [X] T013 O filtro de campanha volta para "Todas" quando o período ou o canal muda; a campanha escolhida que sumiu
  da lista fica como opção "(0)" per FR-007, Constitution V (contradicts)
- [X] T014 Textos de erro com "Tente novamente." e a data invertida dizendo o que fazer per Constitution XV
  (contradicts)
- [X] T015 Os títulos dos marcos, a origem da ficha e o limite de 300 em `constantes.py` per T001, Constitution II
  (partial)
- [X] T016 O principal do grupo só conta vivo no funil, como na linha do tempo per FR-003 (contradicts)
- [X] T017 A parcela recebida conta no funil sem marco na ficha: aceito e registrado (`docs/05` 197) per Premissas
  (partial)
- [X] T018 O orçamento da ficha conta pelo envio no funil, como na linha do tempo per research R2/R5 (contradicts)
- [X] T019 `verify_335`: a ficha do Kommo, a hora do PIX, o grupo na linha do tempo e a virada do dia em São Paulo per
  FR-001, FR-011 (partial)
- [X] T020 `verify_335`: o filtro "Sem anúncio", a linha "Sem responsável", o período padrão e o cancelado com
  pagamento e avaliação; a meta de 2 s com volume real fica registrada (`docs/05` 198) per FR-007/FR-008/FR-011,
  SC-004 (partial)
- [X] T021 O funil apagado (e `aria-busy`) enquanto o filtro novo carrega per Constitution V (partial)

## Dependências

Setup → Foundational → funil (T003–T005) e linha do tempo (T006–T007), independentes → telas → polimento.
