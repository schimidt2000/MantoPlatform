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

- [X] T001 [P] `app/conversas/constantes.py`: os textos da 333 (recusas do orçamento e da ficha, "ficha já existia"),
  o mapa dos formulários (`comum` → "Pré-contrato" e `/f/pre-contrato`; `corporativo` → "Corporativo" e
  `/f/corporativo`) e o texto do formulário. O período (30 dias) e o limite (50) dos recentes ficam na tela, que
  passa o `date_from` ao `GET /api/orcamento/historico` (R6).
- [X] T002 [P] `app/clientes/client_ops.py`: `quick_create_client(..., source="manual")` e o balde `conversa` em
  `client_metrics`.

## Phase 2: Foundational

- [X] T003 `app/models.py`: `OrcamentoEnvio`; `OrcamentoHistory.client_id`; `Conversa.ficha_manual`. Migration à mão
  `migrations/versions/c333e1a5b7d9_orcamento_na_conversa.py` (`down_revision="b332d5f7a9c1"`). Aplicar no `manto_local`
  e ensaiar o downgrade.
- [X] T004 **`specs/333-crm-orcamento-na-conversa/verify_333.py`** com os 14 cenários da spec. Falha agora.

## Phase 3: Histórias 1, 2 e 3 — Enviar o orçamento e ligar à ficha (P1)

- [X] T005 [US1] `app/conversas/envio_ops.py`: `conferir_envio(conversa, cfg)`, público (o `_pre_condicoes` com janela).
- [X] T006 [US3] `app/conversas/ficha_ops.py`: `ligar(conversa_id, dados)` (existente ou nova, `reaproveitada`),
  `remover(conversa_id)` e `ficha_para_envio(conversa, cliente, entry)` (R3). `aviso_ops._vincular_cliente` respeita a
  `ficha_manual`.
- [X] T007 [US1] `app/conversas/costura_ops.py`: `dividir_texto`, `enviar_orcamento` (pré-condições → ficha → registro
  → partes → PDF → ids; R1) e `serializar_envio`.
- [X] T008 [US1] `app/api/conversas_costura.py`: `POST /api/conversas/<id>/orcamento`, `POST`/`DELETE
  /api/conversas/<id>/ficha` com `pode_conversas` e o comentário `RBAC:`. Registrar em `app/api/__init__.py` (uma
  linha). `leitura_ops.serializar_conversa` ganha `ficha_manual`.
- [X] T009 [US3] `app/api/orcamento_read.py`: `enviado_em` no histórico (um SELECT agrupado); `cliente` e `envios` no
  detalhe (`costura_ops.envios_do_orcamento`).
- [X] T010 [US1] Front:
  - `lib/conversas.ts`: `useEnviarOrcamento` e `useFichaDaConversa`;
  - `lib/orcamento.ts`: os tipos novos;
  - `components/conversas/EnvioDoOrcamento.tsx`: a escolha do orçamento, o resumo, a ficha quando falta e "Enviar
    orçamento";
  - `CaixaDeEnvio.tsx`: o botão "Enviar orçamento".
- [X] T011 [US2] `pages/OrcamentoResultadoPage.tsx`: "Enviar na conversa" (escolher a conversa e enviar pelo
  `EnvioDoOrcamento`), "Abrir conversa" e o cartão "Envios na conversa".
- [X] T012 [US3] `pages/OrcamentoHistoricoPage.tsx`: o selo "Enviado na conversa · dd/mm".

## Phase 4: História 4 — Ligar, trocar ou criar a ficha (P2)

- [X] T013 [US4] `components/conversas/FichaDaConversaDialog.tsx` (busca pela `/api/clientes/search` e criação) e, no
  cabeçalho de `ConversaAberta.tsx`, "Ligar à ficha" sem ficha e "Trocar ficha"/"Remover vínculo" com ela.

## Phase 5: História 5 — Enviar o link do formulário (P2)

- [X] T014 [US5] `costura_ops.formularios_da_conversa` e `GET /api/conversas/<id>/formularios`. Na `CaixaDeEnvio`,
  "Enviar formulário" insere o texto escolhido no campo.

## Phase 6: História 6 — "Criar evento" traz a cliente (P2)

- [X] T015 [US6] `app/calendar/routes.py` (`_build_orcamento_prefill`): a chave `cliente`. `lib/eventCreate.ts` e
  `pages/EventCreatePage.tsx`: somar a cliente como "Contratante", sem repetir.

## Phase 7: Polimento

- [X] T016 `pages/ClientsListPage.tsx` e `lib/clientes.ts`: "Conversa" no gráfico de clientes novos.
- [X] T017 `ruff`, `npm run typecheck`; verifies 333, 332, 330, 328 e 325 verdes.
- [X] T018 Tela pela worktree em desktop e 375×812 (quickstart §2).
- [X] T019 Docs: `docs/01` (tabela, colunas, endpoints, RBAC, origem), `docs/02`, `docs/03` (**NÃO PUBLICADO**),
  `docs/04` e o plano. Gates CHK001–CHK011.

## Dependências

Setup → Foundational → US1/US2/US3 (juntas: o envio é um só) → US4 → US5 → US6 → Polimento. O T006 mexe na
`_vincular_cliente` (325): os verifies 325 e 330 rodam logo depois. US4, US5 e US6 são independentes entre si e podem
sair em qualquer ordem depois da Phase 3.

## Estratégia

MVP = Phase 3: o orçamento sai pela conversa, das duas portas, e fica ligado à ficha. É o portão da Fase 3. US4–US6
completam o fluxo até o evento.

## Phase 8: Convergence

Revisão independente (só leitura) de 03/11 sobre o diff `332-crm-avisos-no-celular..HEAD`: 18 achados (0 críticos, 0
altos, 4 médios, 14 baixos).

- [X] T020 `costura_ops._primeiro_nome`: nome que não começa por letra (o telefone que batizou a ficha) vale como sem nome, "Oi! …" per R7, FR-010 (bug)
- [X] T021 PDF que a Meta recusou: "Enviar só o PDF" (`somente_pdf`, chave nova) na conferência, e o aviso de parte não entregue no lugar da confirmação per Casos de borda, Constituição XV (partial)
- [X] T022 `EnvioDoOrcamento`: a confirmação olha a `situacao` das mensagens antes de dizer "enviado" per Constituição XV (bug)
- [X] T023 Docs (T019) e portões CHK001–CHK011 per T019, Constituição XIII (missing)
- [X] T024 A ficha do orçamento no resumo (histórico com `cliente`, detalhe): os textos "fica ligado" e "nasce" dizem a verdade, e o "Criar ficha" não sugere o nome de um orçamento que já é de outra ficha per FR-006, FR-007 (bug)
- [X] T025 Erro da ficha visível mesmo quando a tela não pedia a escolha (conversa desatualizada) per defeito (bug)
- [X] T026 `useAtualizarAposCostura` invalida os formulários (o nome do texto) per FR-010 (bug)
- [X] T027 Ficha nova com `phone_display` (o telefone legível) per defeito (bug)
- [X] T028 Ficha automática do WhatsApp com o wa_id como veio (E.164), sem o "55" do `normalize_phone` em número estrangeiro per defeito (bug)
- [X] T029 `OrcamentoHistory.client_id` gravado por `UPDATE … WHERE client_id IS NULL` per FR-006 (bug)
- [X] T030 História 4: o botão "Trocar ficha" abre o diálogo com "Remover vínculo" (sem componente de menu na casa) — registrar na spec per História 4 (partial)
- [X] T031 `EscolhaDeFicha`: o erro de `nome`/`telefone` marca o campo certo per Casos de borda (partial)
- [X] T032 Contrato: `fields.nome`/`fields.telefone` também no POST do orçamento per contracts (contradicts)
- [X] T033 `texto_mensagem_id` gravado assim que a primeira parte sai per FR-005 (partial)
- [X] T034 `verify_333`: queda no meio (só o que faltou sai), `enviado_em` é o último envio, primeiro nome com ficha batizada pelo telefone, número estrangeiro, `phone_display` e "só o PDF" per Princípio VIII (partial)
- [X] T035 Registrar no `docs/03` as quatro mudanças fora do plano (`ficha_pelo_telefone` em `ficha_ops`, `nome_do_pdf`, 422 da chave de outro pedido, `{"id"}` aceito) per CLAUDE.md §8 (unrequested)
- [X] T036 Comentários: `nome_do_pdf` (o e-mail usa outro nome) e `Client.source` (falta `conversa`) per defeito (bug)
