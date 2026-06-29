# Tasks: Local do ensaio e da maquiagem no portal e na mensagem copiada

**Feature**: 093-local-ensaio-maquiagem | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

**Escopo**: alteração de template (Jinja2 + JS no cliente). Sem migração, sem novo modelo/rota.

## Phase 1 — Mensagem copiada: local do ensaio (US1, P1) 🎯 MVP

- [ ] **T001** Em [event_detail.html](../../app/templates/event_detail.html) (bloco
  `{% if event.ensaios %}`, ~linhas 2378-2385), exportar o local do primeiro ensaio como constante JS:
  `const _ensaioLoc = {{ (first_ensaio.location or "") | tojson }};`. No ramo `{% else %}`, definir
  `_ensaioLoc = ""` junto de `_ensaioDate/_ensaioStart/_ensaioEnd` para evitar `ReferenceError`.

- [ ] **T002** Em `buildWAMsg` ([event_detail.html](../../app/templates/event_detail.html), seção
  "Ensaio", ~linhas 2425-2436), adicionar a linha de local condicional, espelhando a maquiagem:
  `if (_ensaioLoc) msg += \`${em.local} Local: ${_ensaioLoc}\n\`;` logo após a linha de horário do
  ensaio e antes do bloco de materiais. Cobre FR-001, FR-002, FR-005, FR-006.

## Phase 2 — Paridade e não-regressão (US2, P2)

- [ ] **T003** Verificar em [portal/home.html](../../app/templates/portal/home.html) que o local do
  ensaio (cartões de convite pendente ~linha 183 e próximos eventos ~linha 297) e o local da maquiagem
  (~linhas 157-169 e 277-285) continuam exibidos de forma condicional. Ajustar apenas se houver
  inconsistência ou rótulo órfão. Cobre FR-004.

- [ ] **T004** Verificar que a maquiagem na mensagem copiada permanece intacta (FR-003) e que os demais
  campos do convite (evento, personagem, data, horário, local do evento, cachê, materiais) não
  regridem. Cobre SC-004.

## Phase 3 — Verificação manual

- [ ] **T005** Rodar o app contra `manto_local` (`.\scripts\db\run-local.ps1`) e, na página de um
  evento com ensaio **com** local + maquiagem com local: clicar em "Copiar convite" e conferir que a
  mensagem contém o local do ensaio e o local da maquiagem (SC-001, SC-003).

- [ ] **T006** Repetir com um evento cujo ensaio **não** tem local (e/ou sem ensaio): conferir que
  nenhuma linha/rótulo de local de ensaio vazio aparece na mensagem (SC-002).

## Dependências

- T001 → T002 (a constante precisa existir antes de ser usada).
- T003/T004 são verificações independentes (podem rodar em paralelo com a Phase 1).
- T005/T006 dependem de T001-T002 concluídas.

## Critério de pronto

- Local do ensaio presente na mensagem copiada quando existir; omitido quando não.
- Local da maquiagem e do ensaio coerentes entre portal e mensagem.
- Sem regressão nos demais campos. Checklist de "Pronto" do CLAUDE.md aplicável (ruff/format quando
  houver código Python — aqui é só template).
