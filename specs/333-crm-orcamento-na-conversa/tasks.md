---
description: "Tasks da feature 333 — Orçamento e formulário pela conversa"
---
<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Tasks: 333 — Orçamento e formulário pela conversa

**Input**: `specs/333-crm-orcamento-na-conversa/` (spec, plan, research R1–R10, data-model, contracts).

**Verificação (Princípio VIII)**: `verify_333.py` (molde do `verify_330`, com a `MetaFalsa`), escrito na Foundational,
antes do núcleo. `verify_325`, `verify_328`, `verify_330` e `verify_332` são regressão.

**Base**: worktree `C:\tmp\mp333`, branch `333-crm-orcamento-na-conversa` sobre a 332. Sem merge e sem push.

---

## Phase 1: Setup

- [ ] T001 [P] `app/conversas/constantes.py`: os textos da 333 (recusas do orçamento e da ficha, "ficha já existia"),
  o mapa dos formulários (`comum` → "Pré-contrato" e `/f/pre-contrato`; `corporativo` → "Corporativo" e
  `/f/corporativo`) e o texto do formulário. O período (30 dias) e o limite (50) dos recentes ficam na tela, que
  passa o `date_from` ao `GET /api/orcamento/historico` (R6).
- [ ] T002 [P] `app/clientes/client_ops.py`: `quick_create_client(..., source="manual")` e o balde `conversa` em
  `client_metrics`.

## Phase 2: Foundational

- [ ] T003 `app/models.py`: `OrcamentoEnvio`; `OrcamentoHistory.client_id`; `Conversa.ficha_manual`. Migration à mão
  `migrations/versions/c333e1a5b7d9_orcamento_na_conversa.py` (`down_revision="b332d5f7a9c1"`). Aplicar no `manto_local`
  e ensaiar o downgrade.
- [ ] T004 **`specs/333-crm-orcamento-na-conversa/verify_333.py`** com os 14 cenários da spec. Falha agora.

## Phase 3: Histórias 1, 2 e 3 — Enviar o orçamento e ligar à ficha (P1)

- [ ] T005 [US1] `app/conversas/envio_ops.py`: `conferir_envio(conversa, cfg)`, público (o `_pre_condicoes` com janela).
- [ ] T006 [US3] `app/conversas/ficha_ops.py`: `ligar(conversa_id, dados)` (existente ou nova, `reaproveitada`),
  `remover(conversa_id)` e `ficha_para_envio(conversa, cliente, entry)` (R3). `aviso_ops._vincular_cliente` respeita a
  `ficha_manual`.
- [ ] T007 [US1] `app/conversas/costura_ops.py`: `dividir_texto`, `enviar_orcamento` (pré-condições → ficha → registro
  → partes → PDF → ids; R1) e `serializar_envio`.
- [ ] T008 [US1] `app/api/conversas_costura.py`: `POST /api/conversas/<id>/orcamento`, `POST`/`DELETE
  /api/conversas/<id>/ficha` com `pode_conversas` e o comentário `RBAC:`. Registrar em `app/api/__init__.py` (uma
  linha). `leitura_ops.serializar_conversa` ganha `ficha_manual`.
- [ ] T009 [US3] `app/api/orcamento_read.py`: `enviado_em` no histórico (um SELECT agrupado); `cliente` e `envios` no
  detalhe (`costura_ops.envios_do_orcamento`).
- [ ] T010 [US1] Front:
  - `lib/conversas.ts`: `useEnviarOrcamento` e `useFichaDaConversa`;
  - `lib/orcamento.ts`: os tipos novos;
  - `components/conversas/EnvioDoOrcamento.tsx`: a escolha do orçamento, o resumo, a ficha quando falta e "Enviar
    orçamento";
  - `CaixaDeEnvio.tsx`: o botão "Enviar orçamento".
- [ ] T011 [US2] `pages/OrcamentoResultadoPage.tsx`: "Enviar na conversa" (escolher a conversa e enviar pelo
  `EnvioDoOrcamento`), "Abrir conversa" e o cartão "Envios na conversa".
- [ ] T012 [US3] `pages/OrcamentoHistoricoPage.tsx`: o selo "Enviado na conversa · dd/mm".

## Phase 4: História 4 — Ligar, trocar ou criar a ficha (P2)

- [ ] T013 [US4] `components/conversas/FichaDaConversaDialog.tsx` (busca pela `/api/clientes/search` e criação) e, no
  cabeçalho de `ConversaAberta.tsx`, "Ligar à ficha" sem ficha e "Trocar ficha"/"Remover vínculo" com ela.

## Phase 5: História 5 — Enviar o link do formulário (P2)

- [ ] T014 [US5] `costura_ops.formularios_da_conversa` e `GET /api/conversas/<id>/formularios`. Na `CaixaDeEnvio`,
  "Enviar formulário" insere o texto escolhido no campo.

## Phase 6: História 6 — "Criar evento" traz a cliente (P2)

- [ ] T015 [US6] `app/calendar/routes.py` (`_build_orcamento_prefill`): a chave `cliente`. `lib/eventCreate.ts` e
  `pages/EventCreatePage.tsx`: somar a cliente como "Contratante", sem repetir.

## Phase 7: Polimento

- [ ] T016 `pages/ClientsListPage.tsx` e `lib/clientes.ts`: "Conversa" no gráfico de clientes novos.
- [ ] T017 `ruff`, `npm run typecheck`; verifies 333, 332, 330, 328 e 325 verdes.
- [ ] T018 Tela pela worktree em desktop e 375×812 (quickstart §2).
- [ ] T019 Docs: `docs/01` (tabela, colunas, endpoints, RBAC, origem), `docs/02`, `docs/03` (**NÃO PUBLICADO**),
  `docs/04` e o plano. Gates CHK001–CHK011.

## Dependências

Setup → Foundational → US1/US2/US3 (juntas: o envio é um só) → US4 → US5 → US6 → Polimento. O T006 mexe na
`_vincular_cliente` (325): os verifies 325 e 330 rodam logo depois. US4, US5 e US6 são independentes entre si e podem
sair em qualquer ordem depois da Phase 3.

## Estratégia

MVP = Phase 3: o orçamento sai pela conversa, das duas portas, e fica ligado à ficha. É o portão da Fase 3. US4–US6
completam o fluxo até o evento.
