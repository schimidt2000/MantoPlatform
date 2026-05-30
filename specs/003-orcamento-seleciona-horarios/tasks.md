# Tasks: Selecionar quais durações entram no orçamento

**Input**: `specs/003-orcamento-seleciona-horarios/` (spec.md, plan.md)

**Tests**: sem suíte automatizada — verificação manual no app real.

## Format: `[ID] [P?] [Story] Descrição`

---

## Phase 1: User Story 1 — Selecionar durações (P1) 🎯 MVP

**Goal**: o vendedor escolhe quais durações entram; o orçamento (mensagem + resumo + PDF)
mostra só as marcadas. Padrão = todas marcadas.

**Independent Test**: gerar um orçamento marcando só 2h e 4h → mensagem, resumo e PDF
mostram apenas 2h e 4h.

- [ ] T001 [US1] Em [index.html](../../app/templates/orcamento/index.html), adicionar bloco
      "Incluir no orçamento" com 3 checkboxes `name="incluir_duracao"` (valores `1h`/`2h`/`4h`),
      todas `checked` por padrão, perto dos controles de duração.
- [ ] T002 [US1] Em `_process_quote()` ([app/orcamento/routes.py](../../app/orcamento/routes.py)):
      ler `request.form.getlist("incluir_duracao")` (vazio → todas); derivar `show_1h/2h/4h`;
      montar `investimento` e `pix_vista` só com as marcadas; gravar `show_1h/show_2h/show_4h`
      em `session["orcamento_quote"]`.
- [ ] T003 [US1] Em [resultado.html](../../app/templates/orcamento/resultado.html): exibir cada
      KPI (1h/2h/4h) só se a flag correspondente; tornar `--cols` dinâmico (contar visíveis + custom).
      Usar default `True` para compatibilidade com quotes antigos (`quote.show_1h` ausente).
- [ ] T004 [US1] Em [pdf.py](../../app/orcamento/pdf.py): renderizar no "Investimento" e nas
      linhas de "PIX à vista" apenas as durações marcadas (flags do quote, default `True`).

**Checkpoint**: durações selecionáveis refletidas nas 3 saídas.

---

## Phase 2: Polish

- [ ] T005 [P] `ruff check` nos arquivos .py tocados; verificação no app real: gerar orçamento
      com subconjunto de durações e conferir mensagem (`/resultado`) e PDF (`/pdf`); confirmar
      que sem interação o resultado é idêntico ao atual (regressão zero).

---

## Dependencies & Execution Order

- **T001 → T002** (form alimenta o gerador).
- **T002 → T003, T004** (as flags `show_*` no quote são consumidas pelo template e pelo PDF).
- T005 ao final.

## Notes
- Padrão = todas marcadas → comportamento idêntico ao atual (FR-007).
- Fallback "vazio → todas" evita orçamento sem valores (FR-005).
- Custom fora de escopo da seleção (segue incluído quando informado).
