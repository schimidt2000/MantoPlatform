# Tasks: Corrigir acréscimos ausentes no orçamento final

**Feature**: 103-fix-acrescimo-orcamento-final | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

> Correção de defeito de transmissão de formulário. Sem migração. Verificar contra `manto_local`.

## Phase 1 — Correção (US1, P1) 🎯 MVP

- [ ] **T001** Em [orcamento.js](../../app/static/js/orcamento.js) `orcAcrescimoRowHtml`: adicionar os
  atributos `name` aos campos da linha de acréscimo — `acrescimo_tipo[]` (select tipo),
  `acrescimo_descricao[]` (input descrição), `acrescimo_value[]` (input valor) e `acrescimo_is_percent[]`
  (select R$/%). Cobre FR-001..FR-005.

## Phase 2 — Verificação

- [ ] **T002** Contra `manto_local`: submeter um orçamento com 1 acréscimo em R$ e conferir que os totais
  do resultado incluem o acréscimo (aumentam exatamente pelo valor); repetir com %; conferir que sem
  acréscimo nada muda. Cobre SC-001, SC-002, SC-003.

- [ ] **T003** [P] JS com chaves balanceadas; boot do app; Jinja parse de `orcamento/index.html`.

## Dependências

- T001 → T002/T003.

## Critério de pronto

- Acréscimos aparecem no orçamento final (mensagem/PDF), iguais à prévia; BV embutido; sem regressão.
