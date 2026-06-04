# Implementation Plan: Marcar requisitos de senha não cumpridos com "✗"

**Branch**: `016-senha-requisitos-x` | **Date**: 2026-06-04 | **Spec**: [spec.md](./spec.md)

## Summary

Mudança visual nas telas de senha do portal: a exigência **não cumprida** passa a exibir "✗" (cor
de alerta) em vez de marcador neutro; a cumprida mantém "✓" verde. Em tempo real, conforme digita.
Sem mudança de validação, rota ou dados.

## Technical Context

**Language/Version**: Jinja2 + CSS + JS vanilla (templates do portal).
**Storage**: nenhum.
**Constraints**: só visual; não alterar regras de senha nem o submit; distinção por símbolo (não só
cor); tempo real (JS já existente).
**Scale/Scope**: 2 templates — `change_password.html` (criar senha) e `reset_password.html`
(redefinir). `first_access.html` não tem lista de exigências (fora).

## Constitution Check

- **I. Reutilizar antes de criar** ✅ — usa a estrutura/JS de regras já existentes.
- **II. Padrões** ✅ — ajuste mínimo de CSS/JS.
- **III. Camadas** ✅ — só apresentação.
- **IV. Não quebrar** ✅ — validação e submit inalterados; sem migration.
- **V. UI/UX (pt-BR)** ✅ — clareza: "✗" para o que falta, "✓" para o cumprido; símbolo + cor.
- **VI. Planejar antes de codar** ✅ — este plano. Pedido claro, sem clarificações.

## Project Structure

```text
app/templates/portal/
├── change_password.html   # CSS: regra :not(.ok) → "✗" (alerta) em vez de "○"
└── reset_password.html    # adicionar ícone ✓/✗ por regra (span .icon) + CSS + toggle no JS
```

## Design Detalhado

### 1. change_password.html (alvo direto)
- Hoje: `.pw-rules li:not(.ok) .icon::before { content:'○'; color:#ccc; }`. O JS já alterna a
  classe `.ok` por regra.
- Mudança: trocar para `content:'✗'; color:#dc2626;` (vermelho de alerta). `.ok` mantém "✓" verde.

### 2. reset_password.html (consistência)
- Hoje: `<li id="r-...">` em lista com bullets; JS marca `rule-ok` (verde) nas atendidas, sem ícone
  nas demais.
- Mudança: adicionar `<span class="icon"></span>` em cada `<li>`; remover bullets (list-style:none);
  CSS espelhando o change_password: cumprido (`.ok`) → "✓" verde; não cumprido → "✗" vermelho. No
  `checkStrength`, trocar `el.className = r.ok ? 'rule-ok' : ''` por toggle de `.ok`
  (`el.classList.toggle('ok', r.ok)`), mantendo o resto.
- Estado inicial (campo vazio): as regras aparecem com "✗" (nada cumprido) — coerente com FR-001.

### Verificação
- Render das duas páginas (200, sem erro de template).
- change_password: CSS contém `content:'✗'` no `:not(.ok)`.
- reset_password: cada `<li>` tem `.icon`; JS faz toggle de `.ok`.
- (Manual) digitar senha parcial → faltantes "✗", atendidas "✓", em tempo real.

### Fora de escopo
- Mudar regras/força de senha; mexer em first_access (sem lista de exigências); back-end.
