---
description: "Tasks da feature 339 — mudança no evento avisa o Casting, e o teto do cachê acompanha"
---
# Tasks: Mudança no evento avisa o Casting, e o teto do cachê acompanha

**Input**: artefatos em `/specs/339-evento-mudou-avisa-casting/`

**Pré-requisitos**: plan.md, spec.md (histórias 1–6, seção "Verificação", "Textos"), research.md
(R1–R9), data-model.md, contracts/api.md, checklists/regras.md

**Verificação (OBRIGATÓRIA — Princípio VIII)**: `verify_339.py` escrito na Phase 2, antes do núcleo,
falhando pelos motivos certos; cada história fecha com os cenários dela em PASS.

**Organização**: US1 = História 1 (teto autorizado), US2 = História 2 (troca de tipo), US3 = História 3
("Ciente"), US4 = História 4 (vaga a mais), US5 = História 5 (orçamento novo), US6 = História 6 (título ↔
vagas ↔ ensaio). Ordem de execução do plano: US1 → US3 → US2 → US6 → US4 → US5.

## Formato: `[ID] [P?] [Story] Descrição`

---

## Phase 1: Setup

- [X] T001 Conferir o banco de verificação: `flask db current` no `manto_local` com o `.venv` do checkout
      principal; se não estiver em `d323b5a1c0e7`, criar `manto_339` do dump noturno e apontar o
      `DATABASE_URL` para ele (`quickstart.md` §1)

---

## Phase 2: Foundational (bloqueia as histórias)

**⚠️ CRITICAL**: nenhuma história começa antes desta fase terminar.

- [X] T002 Colunas em `app/models.py` conforme `data-model.md`: `EventRole.teto_autorizado`,
      `teto_autorizado_por` (FK `users.id`, relação `autorizador` com `foreign_keys` explícito),
      `teto_autorizado_em`, `sobrando_desde`; `Notification.ciente_em` — com comentário do porquê
- [X] T003 Migration manual `migrations/versions/e339a7c1b2d4_teto_autorizado_e_ciente.py`
      (`down_revision = "d323b5a1c0e7"`): 5 colunas, FK `ON DELETE SET NULL`, `UPDATE` de preenchimento
      do R1 (`does_transport IS NOT TRUE`), downgrade completo; aplicar no banco de verificação
- [X] T004 [P] Núcleo puro novo `app/calendar/teto_ops.py`: `teto_efetivo(role, parcela)`,
      `teto_da_nota(role, parcela)` (sem o cachê atual), `gravar_teto_autorizado(role, *, cache,
      parcela, autor_id, agora)` — regras do `data-model.md`
- [X] T005 [P] Núcleo puro novo `app/calendar/titulo_ops.py`: `chave_do_nome`, `contar_personagens(titulo)`,
      `tirar_ultima_ocorrencia(titulo, nome)`, `acrescentar_personagem(titulo, nome)` — preservam o
      prefixo `(TIPO)` e o resto do título (R2)
- [X] T006 **`specs/339-evento-mudou-avisa-casting/verify_339.py`** — os 28 cenários da spec (+27b) com
      `GoogleFalso` em `app.calendar.service.build`/`load_credentials`, e-mail falso, espião de
      `send_removal_email` em todos os módulos `app.*`, evento descartável `source="platform"`,
      usuários descartáveis (Casting A/B, Ensaio, Comercial, Superadmin), login só por
      `POST /api/auth/login`, conferência por conexão separada, limpeza no `finally` — escrito AGORA e
      falhando nos cenários ainda não construídos

**Checkpoint**: migration aplicada; `teto_ops`/`titulo_ops` importáveis; verify roda e falha pelos
motivos certos.

---

## Phase 3: História 1 — Teto autorizado na vaga (P1) 🎯 MVP

**Objetivo**: o valor que o Superadmin autoriza vira teto da vaga e sobrevive à troca de pessoa.

**Verificação**: cenários 1–4 e 21 em PASS.

- [X] T007 [US1] `app/calendar/casting_ops.py::assign_role`: trocar o `max` local por
      `teto_ops.teto_efetivo`; gravar/limpar com `teto_ops.gravar_teto_autorizado` (só Superadmin, com
      talento, cachê > 0); nota "acima do cap" por `teto_da_nota`; `EventLog` ao autorizar/limpar
- [X] T008 [US1] `app/api/agenda_read.py::_serialize_role`: `cache_cap_efetivo` por `teto_efetivo`;
      `teto_autorizado`, `teto_autorizado_por` (nome), `teto_autorizado_em` só para Superadmin
- [ ] T009 [P] [US1] `frontend/apps/internal/src/lib/agenda.ts`: campos opcionais em `RoleItem`
      (`teto_autorizado?`, `teto_autorizado_por?`, `teto_autorizado_em?`, `sobrando?`)
- [ ] T010 [US1] `frontend/apps/internal/src/components/EventDetail/CastingSection.tsx`: linha do teto
      do Superadmin com "autorizado por … em …" / "autorizado antes da 339"; `tetoEfetivo` só do servidor

**Checkpoint**: Casting troca a pessoa e salva os R$ 400 autorizados.

---

## Phase 4: História 3 — "Ciente" por pessoa (P1)

**Objetivo**: avisos do evento com faixa que só some para quem clicou "Ciente".

**Verificação**: cenários 10–12 em PASS (depois da US2, que produz o aviso).

- [X] T011 [US3] `app/notificacoes/notificacoes_ops.py`: `KIND_EVENTO_TIPO_SHOW`,
      `KIND_EVENTO_VAGA_SOBRANDO`, entradas em `DESTINATARIOS_POR_KIND`, `KINDS_COM_CIENTE`;
      `marcar_ciente(user_id, id)`; `encerrar_avisos(event_id, prefixo_chave)` (ciente para todos);
      `avisos_pendentes(user_id, event_id)`; `serializar` com `ciente_em`; retenção conta
      `KINDS_COM_CIENTE` sem `ciente_em` como não lida
- [X] T012 [US3] `app/api/notificacoes_write.py`: `POST /api/notificacoes/<id>/ciente` (login, escopo
      por dono, 404 alheio ou sem Ciente), docstring de RBAC
- [X] T013 [US3] `app/api/agenda_read.py::serialize_event_detail`: chave `avisos` (do usuário que pede,
      com `dados` derivado da `dedupe_key`) antes do retorno antecipado do ENSAIO
- [ ] T014 [P] [US3] `frontend/apps/internal/src/lib/notificacoes.ts`: `useMarcarCiente` (invalida
      `["event", id]` e `["notificacoes"]`); tipo `AvisoDoEvento` e `avisos?` em `EventoDetalhe`
      (`lib/agenda.ts`)
- [ ] T015 [US3] `frontend/apps/internal/src/components/EventDetail/AvisosDoEvento.tsx` (novo): faixa
      no molde do `QuadroDoPedido`, textos da spec, lista de escalados do `elenco` (cachê só se veio no
      payload), botão "Ciente" com loading e erro inline
- [ ] T016 [US3] `frontend/apps/internal/src/components/EventDetail/EventHeader.tsx`: renderizar a
      faixa e manter a mutação do "Ciente" aqui
- [ ] T017 [P] [US3] `frontend/apps/internal/src/components/notificacoes/NotificacaoItem.tsx`: ícones
      dos dois `kind` novos

---

## Phase 5: História 2 — Virar SHOW sobe os tetos e avisa (P1)

**Objetivo**: troca de tipo com SHOW recalcula teto, avisa Casting/Ensaio/Superadmin e manda o e-mail
do Ensaio.

**Verificação**: cenários 5–9 em PASS.

- [X] T018 [US2] `app/calendar/teto_ops.py::recalcular_tetos_pelo_tipo(event, *, show)` (R3): snapshot
      copiado com `show` ligado/desligado, `_compute_performer_caches` na duração real, casamento por
      nome, coordenadores em sequência, Técnico de Som pela tabela; devolve as mudanças
- [X] T019 [US2] `app/notificacoes/notificacoes_ops.py::notificar_troca_de_tipo_show(event, *, entrou,
      autor_id)`: destinatários por papel menos o autor, `urgent` em até 7 dias, textos da spec
- [X] T020 [US2] `app/calendar/event_ops.py`: `aplicar_troca_de_tipo` recebe `autor_id`;
      `_entrar_em_show`/`_sair_de_show` chamam o recálculo, gravam `EventLog` dos tetos, emitem o
      aviso e (só entrando) `notify_ensaio_team`; aviso do FR-013 nos `warnings` quando há orçamento;
      `update_event_core`/`update_event_basics` repassam o autor
- [X] T021 [US2] `app/api/agenda_write.py`: `PATCH /api/events/<id>` e `/basico` passam
      `current_user.id` como autor

---

## Phase 6: História 6 — Título acompanha as vagas, ensaio acompanha o título (P1)

**Objetivo**: remover/acrescentar vaga ajusta uma ocorrência do título; ensaio futuro acompanha.

**Verificação**: cenários 23–27b em PASS.

- [X] T022 [US6] `app/calendar/titulo_ops.py`: `ajustar_titulo_apos_remocao(event, nome)`,
      `ajustar_titulo_apos_inclusao(event, nome)` (regra de contagem do FR-027/028),
      `propagar_titulo_aos_ensaios(event)` (não cancelados, início futuro em hora de SP),
      `empurrar_titulos_ao_google(eventos) -> list[str]` (depois do commit; pula "Sumiu do Google";
      falha vira aviso e `EventLog`)
- [X] T023 [US6] `app/calendar/casting_ops.py`: `delete_role` e `add_role` chamam o ajuste do título e a
      propagação, e devolvem os eventos a empurrar
- [X] T024 [US6] `app/api/agenda_write.py`: `POST /api/events/<id>/roles` e `DELETE /api/roles/<id>`
      empurram ao Google depois do commit e devolvem `warnings`
- [X] T025 [US6] `app/calendar/event_ops.py`: `update_event_core`/`update_event_basics` propagam o
      título aos ensaios quando ele mudou (sem ajuste automático: o título do formulário vale)
- [ ] T026 [P] [US6] `frontend/apps/internal/src/lib/casting.ts`: `useAddRole`/`useDeleteRole`/
      `useAssignRole` mostram `warnings` da resposta

---

## Phase 7: História 4 — Vaga a mais pelo título (P2)

**Objetivo**: título que perde ocorrências remove vaga vazia ou marca a ocupada e avisa.

**Verificação**: cenários 13–18 e 22 em PASS.

- [X] T027 [US4] `app/calendar/titulo_ops.py`: `reconciliar_vagas_pelo_titulo(event, antigo, novo, *,
      autor_id)` (R5: só nomes que perderam ocorrências; vazias saem — dispensadas primeiro, depois
      maior id; sobra ocupada → `sobrando_desde` + aviso) e `resolver_sobra(event, nome)`
- [X] T028 [US4] `app/notificacoes/notificacoes_ops.py::notificar_vaga_sobrando(...)`
- [X] T029 [US4] `app/calendar/routes.py::sync_events`: reconciliação antes do guard da plataforma
      quando o título mudou; ramo de remoção de nome ausente apaga só vaga sem talento (sem e-mail);
      propagação do título aos ensaios quando `titulo_mudou`
- [X] T030 [US4] `app/calendar/event_ops.py`: `update_event_core`/`update_event_basics` chamam a
      reconciliação depois de gravar título e elenco
- [X] T031 [US4] `app/calendar/casting_ops.py`: `assign_role` (pessoa tirada de vaga marcada → vaga vazia
      sai se ainda sobrar) e `delete_role` chamam `resolver_sobra`; cancelamento encerra os avisos
      (`app/calendar/cancel_ops.py`); `POST /api/roles/<id>/assign` (`app/api/agenda_write.py`) empurra
      — no implement: a remoção pela sobra não muda o título, então não há o que empurrar ao Google; o endpoint segue sem `warnings` (analyze U1 resolvido assim)
- [X] T032 [US4] `app/api/agenda_read.py::_serialize_role`: `sobrando: {pedido, vagas}` para quem vê o
      elenco
- [ ] T033 [US4] `frontend/apps/internal/src/components/EventDetail/CastingSection.tsx`: marca "O título
      pede N — remova alguém da escala." no card

---

## Phase 8: História 5 — Orçamento novo reescreve os tetos (P2)

**Verificação**: cenários 19–20 em PASS.

- [X] T034 [US5] `app/calendar/orcamento_evento_ops.py`: `aplicar_equipe_do_orcamento(...,
      reescrever_tetos)`; `set_event_orcamento` passa `True` no vínculo novo; `tetos_reescritos` no
      relatório e `EventLog`

---

## Phase 9: Polimento e transversais

- [X] T035 `verify_339.py` inteiro em PASS no banco de verificação
- [ ] T036 `cd frontend && npm run typecheck` limpo; `ruff check` nos arquivos Python tocados; `ruff
      format` em `teto_ops.py`, `titulo_ops.py`, migration e verify
- [ ] T037 Tela aberta (skill `manto-conferir-tela`): faixa como Casting A/B, Ensaio e Superadmin;
      "Ciente" por pessoa; sino; card com marca e linha do teto; desktop e 375×812
- [ ] T038 Texto revisado pelo Princípio XV na tela aberta, junto dos vizinhos
- [ ] T039 `docs/01` (colunas, `POST /api/notificacoes/<id>/ciente` e portas alteradas em §4.3),
      `docs/02` (detalhe do evento, sino), `docs/04` §Agenda (troca de tipo, título × vagas × ensaio,
      teto efetivo), `docs/05` (personagem que entra no título), `docs/03` (entrada no topo + índice)
- [ ] T040 `/speckit-converge` sem gaps

---

## Dependências e ordem

- Phase 1 → Phase 2 (bloqueia tudo) → US1 → US3 → US2 → US6 → US4 → US5 → Polimento.
- US3 antes de US2/US4: os produtores de aviso usam o catálogo e a faixa da US3.
- US6 antes de US4: a resolução da sobra (US4) remove vaga pelo mesmo caminho do `delete_role` (US6),
  que já sabe não reescrever o título quando título e vagas batem.
- Paralelo: T004/T005 (módulos diferentes); T009 com T007/T008; T014/T017 com T011–T013; T026 com
  T022–T025.

## Estratégia

- **MVP**: Phase 1–3 (US1) — destrava o Casting no caso real.
- Incremental: cada história fecha com os cenários dela em PASS; commit por história (`feat(339):`), por
  caminho.
