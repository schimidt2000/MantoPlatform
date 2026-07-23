---

description: "Task list for feature 172 - corrigir elenco incompleto ao criar evento a partir de orçamento"

---

# Tasks: Corrigir elenco incompleto ao criar evento a partir de orçamento

**Input**: Design documents from `/specs/172-criar-evento-orcamento-elenco/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Não solicitados formalmente no spec, mas o script de verificação funcional
(`quickstart.md`) é **obrigatório** antes de "pronto" (Portão de Qualidade da constituição) —
tratado como parte da Fase 3 (US1), não como fase separada opcional.

**Organization**: Feature tem uma única User Story (P1). Tarefas organizadas em Setup/
Foundational (a função de precificação compartilhada, pré-requisito dos dois call sites) → US1
(os dois call sites + verificação) → Polish (changelog/lint).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência entre si)
- **[Story]**: US1 (única user story deste bugfix)

## Path Conventions

Projeto web existente (Flask backend + React frontend) — esta correção é 100% backend, sem
arquivo novo de frontend. Caminhos relativos à raiz do repo.

---

## Phase 1: Setup

Não aplicável — reusa 100% a estrutura de módulos já existente (`app/orcamento/`,
`app/calendar/`). Nenhuma dependência nova, nenhum arquivo de configuração novo.

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: Função de precificação compartilhada que os dois call sites (orçamento e criação
de evento) vão usar — bloqueia a Fase 3 porque os dois refactors dependem dela existir primeiro.

- [X] T001 Adicionar `SOSIA_CUSTOM_ADD_PER_ARTIST = 50` e
  `compute_show_pricing(performers: list[dict], show_sosia_tipo: str) -> tuple[bool, float]`
  em `app/orcamento/pricing.py` — devolve `(has_show, custom_add_per_artist)` usando a fórmula
  ORIGINAL e correta de `has_show` hoje em `app/orcamento/routes.py` (linhas ~221-223:
  `ptype == "cantor" or (ptype == "ator" and show) or (ptype == "especial" and (show or
  cantor_flag or personagem_esp in ESPECIAIS_SEMPRE_SHOW))`), e `custom_add_per_artist =
  SOSIA_CUSTOM_ADD_PER_ARTIST` somente se `show_sosia_tipo == "customizado" and performers`,
  senão `0.0`. Type hints + docstring Google style (Princípio II da constituição).

**Checkpoint**: Função compartilhada pronta — os dois refactors da Fase 3 podem prosseguir.

---

## Phase 3: User Story 1 - Elenco completo ao criar evento a partir de um orçamento salvo (Priority: P1) 🎯 MVP

**Goal**: O elenco (personagens + coordenador + técnico + maquiador) pré-preenchido na tela de
criação de evento a partir de um orçamento bate exatamente com o que foi orçado — incluindo o
acréscimo de "Show customizado" (+R$50/artista) que hoje só entra no total, não no cachê por
personagem.

**Independent Test**: Salvar um orçamento com "Show customizado" ativo (painel Sósia) e 3+
personagens, clicar "Criar evento" a partir dele, e conferir (via `_build_orcamento_prefill`/
`orc_caches_json`) que cada cachê de personagem já inclui o acréscimo — sem precisar do resto
do sistema.

### Implementation for User Story 1

- [X] T002 [P] [US1] Refatorar `app/orcamento/routes.py` (view Jinja legada da calculadora,
  linhas ~206-230 e ~279-283) para chamar `compute_show_pricing(performers, show_sosia_tipo)`
  em vez de recalcular `event_has_show` e o `custom_add = len(performers) * 50` inline — usar o
  `has_show` e o `custom_add_per_artist * len(performers)` devolvidos pela função. Mantém
  `num_makes_regular`/`num_makes_especial` como estão hoje (não fazem parte da função
  compartilhada). Depende de T001.
- [X] T003 [P] [US1] Refatorar `_compute_performer_caches()` em `app/calendar/routes.py`
  (linhas ~2591-2721) para chamar `compute_show_pricing(performers, snapshot.get
  ("show_sosia_tipo", "predefinido"))` no lugar do `has_show = any(...)` inline, e somar
  `custom_add_per_artist` a `cache_1h`/`cache_2h`/`cache_3h`/`cache_4h` de cada personagem
  (`role_type == "character"`) no loop principal — **sem** aplicar a coordenador/técnico/
  maquiador (mesma regra "não conta coord, técnico nem maquiador" do cálculo original). Depende
  de T001.
- [X] T004 [US1] Escrever `scripts/verify_172_orcamento_elenco.py` cobrindo os 5 casos do
  `quickstart.md`: (1) orçamento comum sem regressão, (2) orçamento com show customizado — soma
  dos cachês de personagem bate com o total menos custos fixos, (3) `has_show` unificado entre
  os dois call sites para um caso `especial` com `cantor=True`/`show=False`, (4) paridade contra
  os `OrcamentoHistory` reais mais recentes de `manto_local` (sem regressão no elenco completo
  já confirmado na investigação), (5) fim-a-fim: cria orçamento com show customizado → cria
  evento a partir dele → confere `EventRole.cache_value` já com o acréscimo. Depende de T002,
  T003.
- [X] T005 [US1] Rodar `scripts/verify_172_orcamento_elenco.py` contra `manto_local`
  (`$env:DATABASE_URL` = `.local-db-url`, fora de `app.app_context()`) e corrigir qualquer
  falha antes de prosseguir. Depende de T004.

**Checkpoint**: Elenco pré-preenchido (Jinja e, pelo mesmo endpoint, React) bate com o
orçamento em qualquer combinação de show customizado — US1 completa e testável de forma
independente.

---

## Phase 4: Polish & Cross-Cutting Concerns

- [X] T006 [P] `ruff check app/orcamento/pricing.py app/orcamento/routes.py
  app/calendar/routes.py` — zero warnings nos arquivos tocados.
- [X] T007 Adicionar entrada em `docs/changelog.html` (linguagem simples, o que mudou) e
  republicar no mesmo link já existente do artifact do changelog.
- [X] T008 Confirmar que o contrato JSON de `GET /api/events/new/prefill` não mudou de forma
  (mesmas chaves de `caches[]`) — só os valores de `cache_1h..4h` mudam quando
  `show_sosia_tipo == "customizado"` — checagem rápida de paridade, sem exigir mudança no
  frontend React.
- [X] T009 (achado pós-deploy, causa raiz real) Corrigir `value="{{ prefill.caches | tojson }}"`
  e `value="{{ prefill.acrescimos | tojson }}"` em `app/templates/event_create.html` (linhas
  123-124) para `value="{{ ... | tojson | forceescape }}"` — o atributo HTML quebrava no
  primeiro `"` do JSON embutido, e o elenco nunca era pré-preenchido em nenhum orçamento (não
  só nos com show customizado). Ver Addendum em `research.md`.
- [X] T010 Adicionar checagem de regressão renderizando `GET /events/new?orcamento_id=<id>` de
  verdade (Flask test client) e validando que o hidden input `orc-caches-json` produz JSON
  válido e idêntico a `_build_orcamento_prefill` — em
  `scripts/db/verify_172_orcamento_elenco.py`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 2)**: Sem dependências — pode começar imediatamente. Bloqueia a Fase 3.
- **User Story 1 (Phase 3)**: Depende da Fase 2 completa (T001).
- **Polish (Phase 4)**: Depende da Fase 3 completa (T002-T005).

### Dentro da User Story 1

- T002 e T003 podem rodar em paralelo entre si (arquivos diferentes), mas ambos dependem de T001.
- T004 depende de T002 e T003 (o script testa o comportamento já corrigido nos dois call sites).
- T005 depende de T004.

### Parallel Opportunities

- T002 e T003 — arquivos diferentes (`app/orcamento/routes.py` vs. `app/calendar/routes.py`),
  ambos só dependem de T001 já pronto.
- T006 (lint) pode rodar em paralelo com T007 (changelog) na Fase 4.

---

## Parallel Example: User Story 1

```bash
# Depois de T001 pronto, os dois refactors em paralelo:
Task: "Refatorar app/orcamento/routes.py para usar compute_show_pricing()"
Task: "Refatorar _compute_performer_caches() em app/calendar/routes.py para usar compute_show_pricing()"
```

---

## Implementation Strategy

### MVP First (única User Story)

1. Completar Fase 2: `compute_show_pricing()` em `app/orcamento/pricing.py` (T001).
2. Completar Fase 3: os dois call sites refatorados + verificação funcional passando (T002-T005).
3. **PARAR e VALIDAR**: rodar o script de verificação contra `manto_local` — sem falhas.
4. Fase 4: lint, changelog, confirmação de paridade de contrato JSON.

## Notes

- Sem migration — nenhuma mudança em `app/models.py`.
- Sem tela React nova ou alterada — o React já consome `GET /api/events/new/prefill`, que passa
  a devolver valores corretos automaticamente.
- Commit atômico ao final de cada tarefa concluída, por instrução do usuário (fluxo autônomo).
