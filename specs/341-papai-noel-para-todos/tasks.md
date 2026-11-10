---
description: "Tarefas da feature 341 — Papai Noel para qualquer idade e vídeo com data"
---
<!-- ADAPTADO PARA A MANTO (2026-09-08) -->
# Tasks: 341

**Verificação (Princípio VIII)**: `verify_341.py` contra o `manto_340`, escrito na Foundational,
antes do núcleo.

## Phase 1: Setup

- [ ] T001 Coluna `recorded_delivery_until` (Date, nulo) em `VirtualCampaign`, `app/models.py`, com o porquê
- [ ] T002 Migration manual `migrations/versions/e341a1b2c3d4_entrega_do_video.py` (`down_revision =
      "e340c1a2b3d4"`); aplicar no `manto_340`

## Phase 2: Foundational

- [ ] T003 **`specs/341-papai-noel-para-todos/verify_341.py`** — os 9 cenários da spec (e-mails
      capturados, dublês de Google e InfinitePay, conexão separada, limpeza no `finally`); rodar e
      registrar a falha pelos motivos certos

## Phase 3: História 2 — o vídeo tem data de entrega (P1)

- [ ] T004 [US2] `app/marketing/virtuais_ops.py`: `prazo_do_video(campanha, hoje)`; efetivação usa;
      `criar_campanha`/`atualizar_campanha` aceitam `recorded_delivery_until` (`_parse_date`, vazio
      limpa); serializers público e da gestão trazem o campo
- [ ] T005 [US2] `app/api/virtuais_write.py`: `POST` repassa `recorded_delivery_until`
- [ ] T006 [US2] `app/email_service.py`: e-mail de compra do vídeo com a data do prazo da entrega
- [ ] T007 [P] [US2] `frontend/apps/internal/src/lib/virtuais.ts` e
      `pages/VirtuaisCampanhaFormPage.tsx`: tipo, input e campo "Entrega dos vídeos até" com
      `FieldError`
- [ ] T008 [P] [US2] `frontend/apps/public/src/lib/virtuais.ts`: tipo opcional + helpers de data por
      texto; `CampanhaVirtualPage.tsx` "entregue até 13 de dezembro" / "em até N dias"

## Phase 4: História 1 — a loja convida para qualquer idade (P1)

- [ ] T009 [US1] `app/marketing/virtuais_ops.py`: erros da ficha ("Informe o nome de quem vai
      receber.", "Informe a idade.") e "Para:" na descrição do evento
- [ ] T010 [US1] `app/email_service.py`: confirmação (cartinha condicionada, sem "dados da criança") e
      preheader do vídeo pronto
- [ ] T011 [P] [US1] `frontend/apps/public/src/lib/lojaTema.ts`: herói, formatos, passos, FAQ (+ "É só
      para criança?"), dicas da ficha, dicas do dia, regra de redação no topo
- [ ] T012 [P] [US1] `CampanhaVirtualPage.tsx` (cartão ao vivo, rótulo "Nome de quem vai receber") e
      `PedidoVirtualPage.tsx` ("Para", texto do telefone)
- [ ] T013 [P] [US1] Internos: `FilaProducaoMidiaPage.tsx` e `PedidoVirtualSection.tsx` ("Para")

## Phase 5: Polimento

- [ ] T014 Regressão `verify_304.py` e `verify_205.py` contra o `manto_340`
- [ ] T015 `ruff check` nos tocados; `ruff format` no verify e na migration; `npm run typecheck`
- [ ] T016 Tela: campanha e pedido em 375×812; gestão com o campo novo; texto lido pelo XV
- [ ] T017 Docs: `docs/01` (§2 coluna, §3.13.4 campo), `docs/02`, `docs/03`, `docs/04` (prazo)

## Dependências

Setup → Foundational → US2 → US1 → Polimento. T004, T009 tocam `virtuais_ops.py` em sequência; T006
e T010 tocam `email_service.py` em sequência; T008 e T012 tocam `CampanhaVirtualPage.tsx` em
sequência.
