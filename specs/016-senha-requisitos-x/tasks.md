# Tasks: Marcar requisitos de senha não cumpridos com "✗"

**Input**: `specs/016-senha-requisitos-x/` (spec.md, plan.md)
**Tests**: sem suíte automatizada — verificação de render + checagem manual.

## Phase 1: Criar senha (change_password)

- [ ] T001 [app/templates/portal/change_password.html](../../app/templates/portal/change_password.html):
      regra `:not(.ok) .icon::before` passa de `'○'` cinza para `'✗'` vermelho (alerta). `.ok`
      mantém `'✓'` verde.

## Phase 2: Redefinir senha (reset_password)

- [ ] T002 [app/templates/portal/reset_password.html](../../app/templates/portal/reset_password.html):
      adicionar `<span class="icon"></span>` em cada `<li>` de exigência; CSS `list-style:none` +
      ícones `✓` (`.ok`) / `✗` (não cumprido), espelhando o change_password.
- [ ] T003 [app/templates/portal/reset_password.html](../../app/templates/portal/reset_password.html):
      no `checkStrength`, alternar a classe `.ok` por regra (`classList.toggle('ok', r.ok)`) em vez
      de `rule-ok`.

## Phase 3: Verificação

- [ ] T004 Render das duas páginas (200); change_password tem `content:'✗'` em `:not(.ok)`;
      reset_password tem `.icon` por regra + toggle de `.ok`. Conferência manual do tempo real.

## Dependencies
- T001 independente. T002→T003. T004 ao fim.

## Notes
- Mudança puramente visual; validação e submit inalterados. first_access fora (sem exigências).
