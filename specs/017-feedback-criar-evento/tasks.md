# Tasks: Feedback ao criar evento

**Input**: `specs/017-feedback-criar-evento/` (spec.md, plan.md)
**Tests**: sem suíte automatizada — verificação de render + checagem manual.

## Phase 1: Estilos + botão

- [ ] T001 [app/templates/event_create.html](../../app/templates/event_create.html): botão "Adicionar
      à Agenda" ganha `id="btn-submit-event"`; adicionar `<style>` com `.field-error` e `.shake`.

## Phase 2: Comportamento

- [ ] T002 [app/templates/event_create.html](../../app/templates/event_create.html): handler de
      submit em `#event-form` — trava duplo envio + estado de carregamento no botão.
- [ ] T003 [app/templates/event_create.html](../../app/templates/event_create.html): no mesmo
      handler, validar título/data/horário; bloquear com realce + shake + foco; remover realce ao
      corrigir o campo.

## Phase 3: Verificação

- [ ] T004 Render (200) com `id="btn-submit-event"`, `.shake`, `.field-error`. Conferência manual:
      título vazio → shake/foco e não envia; duplo clique → 1 submit; corrigir remove realce.

## Dependencies
- T001 → T002/T003. T004 ao fim.

## Notes
- Validação do servidor permanece (rede de segurança). Sem mudança de rota/dados.
