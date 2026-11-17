---
description: "Tasks da feature 348 — origem completa"
---
# Tasks: 348 — Origem completa

**Input**: artefatos em `/specs/348-origem-completa/`

**Pré-requisitos**: plan.md, spec.md, research.md, data-model.md, contracts/

**Verificação (Princípio VIII)**: `specs/348-origem-completa/verify_348.py`, contra o espelho `manto_348` (exceção
registrada no `plan.md`). Escrito na fase Foundational, antes do núcleo; nasce falhando nos cenários ainda não
construídos e passa ao fim de cada história.

## Formato: `[ID] [P?] [Story] Descrição`

---

## Phase 1: Setup

- [X] T001 Constantes do código do site e do contato `site` em `app/conversas/constantes.py` (`CONTATO_SITE`,
      `ALFABETO_DO_CODIGO`, `TAMANHO_DO_CODIGO = 5`, `VALIDADE_DO_CODIGO = timedelta(days=90)`,
      `JANELA_DA_ORIGEM = timedelta(days=90)`, `REGEX_DO_CODIGO`, `LINHA_DO_CODIGO = "Código do site: #{codigo}"`,
      `ORIGEM_DO_SITE = "Site"`, `MARCADORES_DO_CLIQUE`, `MARCADORES_UTM`)

---

## Phase 2: Foundational (bloqueia as histórias)

- [X] T002 Modelos em `app/models.py`: classe `OrigemCodigo` (`origem_codigos`); colunas novas em `ConversaAnuncio`
      (`ctwa_clid`, `codigo_id`), `AnuncioMeta` (`conjunto_id`, `conjunto_nome`), `OrcamentoHistory` (`conversa_id`,
      `origem_contato_id`), `CalendarEvent` (`conversa_id`, `origem_contato_id`, `frente` com FK
      `marketing_frentes.slug`) e `Client` (`utm_campaign_id`) — conforme `data-model.md`
- [X] T003 Migration manual `migrations/versions/a348c0d1e2f3_origem_completa.py` (`down_revision = "d334b2c4e6f8"`):
      tabela, colunas, FKs, índices; dados (fila do conjunto, `utm_campaign_id` da Meta) e o preenchimento retroativo
      do `ctwa_clid` em Python (`_preencher_ctwa_clid(bind)`, tolerante a JSON corrompido); downgrade completo;
      aplicar no `manto_348` e fazer ida e volta
- [X] T004 Esqueleto do núcleo: `app/calendar/frente_ops.py` (assinaturas + `FrenteInvalida`),
      `app/conversas/codigo_ops.py` e `app/conversas/origem_ops.py` (assinaturas + `ConversaNaoEncontrada`)
- [X] T005 **`specs/348-origem-completa/verify_348.py`** — os 16 cenários da tabela da spec (molde do `verify_334.py`:
      dublês da Meta e do Google Agenda, disjuntor de rede, login pela API, conexão separada, cenários que DEVEM
      falhar, limpeza no `finally`) — rodado AGORA, falhando nos cenários não construídos. O cenário 13 compara também
      `frente_sql()` com a expressão de 16/11 em todos os eventos reais sem frente gravada (SC-006)

**Checkpoint**: `manto_348` em `a348c0d1e2f3`; verify roda e falha pelos motivos certos.

---

## Phase 3: História 1 — O clique no anúncio de WhatsApp fica guardado (P1) 🎯 MVP

**Verificação**: cenários 1 a 3 em PASS.

- [X] T006 [P] [US1] `app/integracoes/meta_anuncios_client.py`: `fields=name,campaign{id,name},adset{id,name}` e
      devolver `conjunto_id`/`conjunto_nome`
- [X] T007 [US1] `app/conversas/anuncio_ops.py`: `ctwa_clid` em `contato_do_whatsapp`/`registrar_contato`; conjunto
      em `_consultar_um`; `utm_campaign_id` em `aplicar_na_ficha`, `_propagar` e `_propagar_pendentes`

**Checkpoint**: cenários 1–3 verdes.

---

## Phase 4: História 2 — O clique no Google chega à conversa (P1)

**Verificação**: cenários 4 a 7 em PASS; lista de desejos e formulário em 390 px.

- [X] T008 [US2] `app/conversas/codigo_ops.py`: `criar_codigo(marcadores)`, `codigo_valido(texto)`,
      `anexar_a_mensagem(mensagem, codigo, form_response)`, `ler_na_mensagem(conversa, texto, momento)` (UPDATE
      condicional, contato `site`, ficha)
- [X] T009 [US2] `app/conversas/anuncio_ops.py`: origem "Site" na ficha sem origem a partir do primeiro contato
      `site` (`aplicar_na_ficha` passa a cobrir os dois tipos)
- [X] T010 [US2] `app/conversas/aviso_ops.py`: `_gravar_recebida` chama `codigo_ops.ler_na_mensagem` na mensagem de
      texto nova
- [X] T011 [US2] `app/api/origem_public.py` (novo, `POST /api/origem/codigo`, público, `20 per hour`) e import em
      `app/api/__init__.py`
- [X] T012 [US2] `app/api/formularios_write.py`: `origem_codigo` → `codigo_ops.anexar_a_mensagem`
- [X] T013 [P] [US2] `frontend/apps/public/src/lib/origem.ts` (captura, guarda 90 dias, pede o código, lê o código
      guardado; fora da loja) e chamada no `frontend/apps/public/src/App.tsx`
- [X] T014 [P] [US2] `frontend/apps/public/src/lib/wishlist.ts`: linha do código na mensagem
- [X] T015 [P] [US2] `frontend/apps/public/src/components/formularios/DynamicForm.tsx`: `origem_codigo` no envio

**Checkpoint**: cenários 4–7 verdes.

---

## Phase 5: História 3 — Cada venda sabe de qual conversa e contato veio (P1)

**Verificação**: cenários 8 a 11 em PASS; aba Comercial com a origem.

- [X] T016 [US3] `app/conversas/origem_ops.py`: `contato_de_origem`, `ligar_orcamento`, `ligar_evento`,
      `acompanhar_orcamento`, `ao_criar_evento`, `origem_da_venda`
- [X] T017 [US3] `app/conversas/costura_ops.py`: `enviar_orcamento` chama `origem_ops.ligar_orcamento` no primeiro
      envio
- [X] T018 [US3] `app/calendar/orcamento_evento_ops.py`: `set_event_orcamento` chama `origem_ops.acompanhar_orcamento`
      ao ligar, trocar e desligar
- [X] T019 [US3] `app/calendar/routes.py` (`_create_event_core`) e `app/api/agenda_write.py` (`_build_create_event_data`
      + validação de `conversa_id` antes do Google): a criação liga a conversa ou herda do orçamento
- [X] T020 [US3] `app/api/agenda_read.py`: `venda.origem` no detalhe (com `pode_abrir`)
- [X] T021 [P] [US3] `frontend/apps/internal/src/lib/agenda.ts` (tipo `venda.origem?`) e
      `frontend/apps/internal/src/components/EventDetail/ComercialSection.tsx` (linha "Origem da venda" no VendaPanel)

**Checkpoint**: cenários 8–11 verdes.

---

## Phase 6: História 4 — A frente é escolhida na venda (P2)

**Verificação**: cenários 12 a 14 em PASS; aba Comercial em desktop e 390 px.

- [X] T022 [US4] `app/calendar/frente_ops.py`: `sugestao`, `frente_do_evento`, `frente_sql`, `validar`,
      `opcoes`, `frente_na_criacao`; `app/marketing/comando_ops.py`: `frente_venda_sql` devolve `frente_ops.frente_sql()`
      e `SOCIAL_REGEX` passa a vir de `frente_ops`
- [X] T023 [US4] `app/api/agenda_write.py` (`/comercial`: validação e obrigatoriedade; criação: validação da `frente`)
      e `app/calendar/event_ops.py` (`update_event_comercial` grava a frente); `_create_event_core` grava a frente na
      criação
- [X] T024 [US4] `app/api/agenda_read.py`: `venda.frente` no detalhe
- [X] T025 [US4] `frontend/apps/internal/src/lib/agenda.ts` (tipo `venda.frente?`),
      `frontend/apps/internal/src/lib/eventInline.ts` (`EventComercialInput.frente?`) e `ComercialSection.tsx` (campo
      "Frente" no VendaForm, erro no campo, linha "Frente" no VendaPanel)

**Checkpoint**: cenários 12–14 verdes.

---

## Phase 7: História 5 — O lead casa com a campanha pelo id (P2)

**Verificação**: cenário 15 em PASS.

- [X] T026 [US5] `app/marketing/desempenho_ops.py`: `attributed_clients` leva `utm_campaign_id`; `_campaign_table`
      agrupa por (plataforma, id) e casa por id com fallback de nome; `retornos_por_campanha` por `campanha_id`

**Checkpoint**: verify inteiro verde.

---

## Phase 8: Polimento e transversais

- [X] T027 `cd frontend && npm run typecheck` limpo e `ruff check` nos arquivos Python tocados (`ruff format` só nos
      novos)
- [X] T028 Telas no Browser pane com backend 5348 e Vite 6348: lista de desejos e formulário em 390×844; aba
      Comercial em desktop e 390 (skill `manto-conferir-tela`); temporários apagados antes do commit
- [X] T029 Texto novo revisado pelo Princípio XV na tela aberta
- [X] T030 Docs: `docs/01` (schema, endpoint novo, campos novos, contrato da 349/351, §4.3), `docs/02` (aba
      Comercial, lista de desejos, formulários), `docs/03` (entrada no topo + índice), `docs/04` (invariante da venda ↔
      conversa e da frente), `docs/05` (quitar a 215; registrar a retenção do código)
- [X] T031 `quickstart.md` executado de ponta a ponta

---

## Dependências e ordem

- Setup → Foundational (T002–T005) → US1 → US2 → US3 → US4 → US5 → Polimento.
- US3 depende do contato `site` da US2 só para o cenário com código; o resto é independente.
- US4 e US5 não dependem de US1–US3.
- Paralelo: T006 (cliente da Meta) ao lado de T007; T013–T015 entre si; T021 ao lado de T016–T020, com o contrato
  da API já fixado.

## Estratégia

- MVP: Setup + Foundational + US1 (o `ctwa_clid` é o dado que se perde se não for guardado agora).
- Commits por grupo lógico, `feat(348):`/`docs(348):`, stage por caminho.

---

## Phase 9: Convergence

- [X] T032 Documentar a chave `linha` da resposta de `POST /api/origem/codigo` em `specs/348-origem-completa/contracts/api.md` per plan: texto da mensagem com fonte única no servidor (partial)
