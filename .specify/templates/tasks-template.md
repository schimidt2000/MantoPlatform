---
description: "Template de tasks para implementação de feature (Manto)"
---
<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Tasks: [FEATURE]

**Input**: artefatos em `/specs/[NNN-nome]/`

**Pré-requisitos**: plan.md (obrigatório), spec.md (histórias e seção "Verificação"), research.md,
data-model.md, contracts/

**Verificação (OBRIGATÓRIA neste projeto — constituição, Princípio VIII)**: toda feature gera
`specs/NNN-nome/verify_NNN.py`, executado contra `manto_local` (cópia da produção). A tarefa que
ESCREVE o verify vem na fase Foundational, ANTES do núcleo de negócio — ele nasce falhando pelos
motivos certos e passa ao fim de cada história. Não existe pytest nem `tests/` neste repositório.

**Organização**: por história da spec, cada uma implementável e verificável sozinha.

## Formato: `[ID] [P?] [Story] Descrição`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência)
- **[Story]**: história a que a tarefa pertence (US1, US2, US3…)
- Caminho exato do arquivo na descrição

## Caminhos (Manto)

- Backend: `app/models.py` · `app/<dominio>/<nome>_ops.py` · `app/api/<dominio>_read.py` |
  `_write.py` (+ import em `app/api/__init__.py`) · `migrations/versions/<rev>_<nome>.py`
- Frontend: `frontend/apps/<app>/src/{pages,components,lib}/` · `frontend/packages/ui/src/`
  (+ export em `index.ts`) · `frontend/server.js` (só rota pública nova)
- Verificação: `specs/NNN-nome/verify_NNN.py`

<!--
  ============================================================================
  As tarefas abaixo são EXEMPLO. O /speckit-tasks substitui por tarefas reais a partir da
  spec (histórias e prioridades), do plano, do data-model e dos contratos.
  NÃO deixe exemplos no tasks.md gerado.
  ============================================================================
-->

## Phase 1: Setup

- [ ] T001 Constantes do domínio em `app/constants.py` (nomes, limites, papéis)

---

## Phase 2: Foundational (bloqueia as histórias)

**⚠️ CRITICAL**: nenhuma história começa antes desta fase terminar.

- [ ] T002 Modelo em `app/models.py` conforme `data-model.md` (docstring com o porquê)
- [ ] T003 Migration Alembic **manual** `migrations/versions/<rev>_<nome>.py` (`down_revision` =
      `flask db heads`; upgrade/downgrade completos); aplicar no `manto_local`
- [ ] T004 Núcleo puro `app/<dominio>/<nome>_ops.py` — primitivas compartilhadas + exceção de
      validação própria
- [ ] T005 **`specs/NNN-nome/verify_NNN.py`** — cenários da seção "Verificação" da spec (login só
      pela API; escrita conferida por conexão separada; um cenário que DEVE falhar; limpeza no
      `finally`) — escrito AGORA e FALHANDO nos cenários ainda não construídos

**Checkpoint**: modelo migrado no `manto_local`, primitivas prontas, verify falhando pelos motivos
certos.

---

## Phase 3: História 1 — [Título] (Prioridade: P1) 🎯 MVP

**Objetivo**: [o que esta história entrega]

**Verificação da história (obrigatória)**: cenários [N..M] do `verify_NNN.py` em PASS; tela aberta.

- [ ] T006 [US1] `app/<dominio>/<nome>_ops.py`: [função de negócio]
- [ ] T007 [US1] `app/api/<dominio>_write.py`: endpoint com gate de RBAC declarado (comentário
      `RBAC:` no topo do módulo); registrar em `app/api/__init__.py`
- [ ] T008 [P] [US1] `frontend/apps/<app>/src/lib/<dominio>.ts`: tipos + hooks (`apiFetch`)
- [ ] T009 [US1] `frontend/apps/<app>/src/pages/<Nome>Page.tsx`: tela com loading/erro/sucesso,
      `useReducedMotion`, erro da API apontado no campo

**Checkpoint**: história 1 funcional e verificada sozinha.

---

## Phase 4: História 2 — [Título] (Prioridade: P2)

**Objetivo**: [...]

**Verificação da história (obrigatória)**: cenários [...] em PASS.

- [ ] T010 [US2] [...]

**Checkpoint**: histórias 1 e 2 funcionam de forma independente.

---

[Mais histórias, no mesmo padrão]

---

## Phase N: Polimento e transversais

- [ ] TXXX `cd frontend && npm run typecheck` limpo (três SPAs) e `ruff check` nos arquivos tocados
- [ ] TXXX Tela aberta de verdade (Browser pane); superfície pública em viewport mobile
- [ ] TXXX Gates de RBAC na tabela de `docs/01` §4.3
- [ ] TXXX Docs por fonte única: `docs/01`, `docs/02`, `docs/03` (entrada no topo) — `docs/00`,
      `docs/04`, `docs/05` se aplicável
- [ ] TXXX `quickstart.md` executado de ponta a ponta

---

## Dependências e ordem

- Setup → Foundational (bloqueia tudo) → histórias por prioridade (P1 → P2 → P3) → Polimento
- Dentro da história: `_ops` antes do endpoint; endpoint antes da tela; verify em PASS ao fim
- O verify é escrito ANTES e falha antes de implementar

## Estratégia

- **MVP primeiro**: Setup + Foundational + História 1 → verify + tela → merge quando o dono pedir
- **Incremental**: cada história entrega valor sem quebrar a anterior
- Commit por tarefa ou grupo lógico (`feat(NNN):`), sempre por caminho
